// eBPF Network Policy for Agent Sandboxing
// Compile with: clang -O2 -target bpf -c ebpf-agent-policy.c -o ebpf-agent-policy.o
// Load with: cilium bpf policy add ...

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/udp.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_endian.h>

#define MAX_AGENTS 1024
#define MAX_ALLOWED_DESTS 64

// Agent identity map: container_id -> agent_config
struct agent_config {
    __u32 agent_id;
    __u32 allowed_dest_count;
    __u32 allowed_dests[MAX_ALLOWED_DESTS];  // IPv4 addresses in network byte order
    __u16 allowed_ports[MAX_ALLOWED_DESTS];  // Port numbers in host byte order
    __u8  protocols[MAX_ALLOWED_DESTS];      // IPPROTO_TCP=6, IPPROTO_UDP=17
    __u8  default_deny;                      // 1 = deny all except allowed
    __u8  log_allowed;                       // 1 = log allowed connections
    __u8  log_denied;                        // 1 = log denied connections
    __u8  reserved[3];
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, MAX_AGENTS);
    __type(key, __u64);      // container_id (cgroup id)
    __type(value, struct agent_config);
} agent_configs SEC(".maps");

// DNS allowlist map: agent_id -> allowed domains (hashed)
struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 10000);
    __type(key, __u64);      // hash of domain name
    __type(value, __u32);    // agent_id that is allowed
} dns_allowlist SEC(".maps");

// Connection tracking for rate limiting
struct conn_track_key {
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8  protocol;
    __u8  pad[3];
};

struct conn_track_val {
    __u64 packets;
    __u64 bytes;
    __u64 last_seen;
    __u32 agent_id;
};

struct {
    __uint(type, BPF_MAP_TYPE_LRU_HASH);
    __uint(max_entries, 50000);
    __type(key, struct conn_track_key);
    __type(value, struct conn_track_val);
} conn_track SEC(".maps");

// Per-agent counters
struct agent_counters {
    __u64 allowed_packets;
    __u64 denied_packets;
    __u64 allowed_bytes;
    __u64 denied_bytes;
    __u64 dns_queries;
    __u64 dns_blocked;
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, MAX_AGENTS);
    __type(key, __u32);      // agent_id
    __type(value, struct agent_counters);
} agent_stats SEC(".maps");

// Ring buffer for audit events
struct audit_event {
    __u64 timestamp;
    __u32 agent_id;
    __u32 src_ip;
    __u32 dst_ip;
    __u16 src_port;
    __u16 dst_port;
    __u8  protocol;
    __u8  action;      // 0=allow, 1=deny, 2=dns_allow, 3=dns_deny
    __u8  direction;   // 0=ingress, 1=egress
    __u8  pad[2];
};

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 1 << 20);  // 1MB
} audit_events SEC(".maps");

// Helper: extract container ID from cgroup
static __always_inline __u64 get_container_id(void) {
    return bpf_get_current_cgroup_id();
}

// Helper: check if IP is in allowed list
static __always_inline int is_dest_allowed(struct agent_config *cfg, __u32 dst_ip, __u16 dst_port, __u8 protocol) {
    for (int i = 0; i < cfg->allowed_dest_count && i < MAX_ALLOWED_DESTS; i++) {
        if (cfg->allowed_dests[i] == dst_ip && 
            cfg->allowed_ports[i] == dst_port && 
            cfg->protocols[i] == protocol) {
            return 1;
        }
    }
    return 0;
}

// Helper: log audit event
static __always_inline void log_audit_event(__u32 agent_id, __u32 src_ip, __u32 dst_ip,
                                            __u16 src_port, __u16 dst_port, __u8 protocol,
                                            __u8 action, __u8 direction) {
    struct audit_event *event = bpf_ringbuf_reserve(&audit_events, sizeof(*event), 0);
    if (!event) return;

    event->timestamp = bpf_ktime_get_ns();
    event->agent_id = agent_id;
    event->src_ip = src_ip;
    event->dst_ip = dst_ip;
    event->src_port = src_port;
    event->dst_port = dst_port;
    event->protocol = protocol;
    event->action = action;
    event->direction = direction;

    bpf_ringbuf_submit(event, 0);
}

// Main egress filter - attach to tc egress on container veth
SEC("classifier/egress")
int agent_egress_filter(struct __sk_buff *skb) {
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return TC_ACT_OK;
    
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return TC_ACT_OK;
    
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end) return TC_ACT_OK;
    
    __u32 src_ip = ip->saddr;
    __u32 dst_ip = ip->daddr;
    __u8 protocol = ip->protocol;
    
    __u16 src_port = 0, dst_port = 0;
    
    if (protocol == IPPROTO_TCP) {
        struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
        if ((void *)(tcp + 1) > data_end) return TC_ACT_OK;
        src_port = bpf_ntohs(tcp->source);
        dst_port = bpf_ntohs(tcp->dest);
    } else if (protocol == IPPROTO_UDP) {
        struct udphdr *udp = (void *)ip + (ip->ihl * 4);
        if ((void *)(udp + 1) > data_end) return TC_ACT_OK;
        src_port = bpf_ntohs(udp->source);
        dst_port = bpf_ntohs(udp->dest);
    }
    
    // Get agent config
    __u64 container_id = get_container_id();
    struct agent_config *cfg = bpf_map_lookup_elem(&agent_configs, &container_id);
    if (!cfg) {
        // No config = default deny
        log_audit_event(0, src_ip, dst_ip, src_port, dst_port, protocol, 1, 1);
        return TC_ACT_SHOT;
    }
    
    // Check if destination is allowed
    int allowed = is_dest_allowed(cfg, dst_ip, dst_port, protocol);
    
    if (allowed) {
        if (cfg->log_allowed) {
            log_audit_event(cfg->agent_id, src_ip, dst_ip, src_port, dst_port, protocol, 0, 1);
        }
        
        // Update connection tracking
        struct conn_track_key ct_key = {
            .src_ip = src_ip, .dst_ip = dst_ip,
            .src_port = src_port, .dst_port = dst_port,
            .protocol = protocol
        };
        struct conn_track_val *ct_val = bpf_map_lookup_elem(&conn_track, &ct_key);
        if (ct_val) {
            __sync_fetch_and_add(&ct_val->packets, 1);
            __sync_fetch_and_add(&ct_val->bytes, skb->len);
            ct_val->last_seen = bpf_ktime_get_ns();
        } else {
            struct conn_track_val new_val = {
                .packets = 1, .bytes = skb->len,
                .last_seen = bpf_ktime_get_ns(), .agent_id = cfg->agent_id
            };
            bpf_map_update_elem(&conn_track, &ct_key, &new_val, BPF_ANY);
        }
        
        // Update agent stats
        struct agent_counters *stats = bpf_map_lookup_elem(&agent_stats, &cfg->agent_id);
        if (stats) {
            __sync_fetch_and_add(&stats->allowed_packets, 1);
            __sync_fetch_and_add(&stats->allowed_bytes, skb->len);
        }
        
        return TC_ACT_OK;
    } else {
        if (cfg->log_denied) {
            log_audit_event(cfg->agent_id, src_ip, dst_ip, src_port, dst_port, protocol, 1, 1);
        }
        
        struct agent_counters *stats = bpf_map_lookup_elem(&agent_stats, &cfg->agent_id);
        if (stats) {
            __sync_fetch_and_add(&stats->denied_packets, 1);
            __sync_fetch_and_add(&stats->denied_bytes, skb->len);
        }
        
        return TC_ACT_SHOT;
    }
}

// DNS filter - attach to tc egress on container veth (port 53)
SEC("classifier/dns")
int agent_dns_filter(struct __sk_buff *skb) {
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;
    
    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end) return TC_ACT_OK;
    
    if (eth->h_proto != bpf_htons(ETH_P_IP)) return TC_ACT_OK;
    
    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end) return TC_ACT_OK;
    
    if (ip->protocol != IPPROTO_UDP) return TC_ACT_OK;
    
    struct udphdr *udp = (void *)ip + (ip->ihl * 4);
    if ((void *)(udp + 1) > data_end) return TC_ACT_OK;
    
    // Only handle DNS (port 53)
    if (bpf_ntohs(udp->dest) != 53 && bpf_ntohs(udp->source) != 53) {
        return TC_ACT_OK;
    }
    
    // Simple DNS query parsing - check question section for domain
    // This is a simplified version; production would need full DNS parsing
    unsigned char *dns = (void *)udp + sizeof(*udp);
    if (dns + 12 > data_end) return TC_ACT_OK;  // DNS header
    
    // Skip DNS header (12 bytes), parse question
    unsigned char *qname = dns + 12;
    if (qname > data_end) return TC_ACT_OK;
    
    // Hash the domain name for allowlist lookup
    __u64 hash = 0;
    unsigned char *p = qname;
    while (p < data_end && *p != 0 && (p - qname) < 255) {
        hash = hash * 31 + *p;
        p++;
    }
    
    __u64 container_id = get_container_id();
    struct agent_config *cfg = bpf_map_lookup_elem(&agent_configs, &container_id);
    if (!cfg) return TC_ACT_SHOT;
    
    // Check DNS allowlist
    __u32 *allowed_agent = bpf_map_lookup_elem(&dns_allowlist, &hash);
    int allowed = (allowed_agent && *allowed_agent == cfg->agent_id);
    
    struct agent_counters *stats = bpf_map_lookup_elem(&agent_stats, &cfg->agent_id);
    if (stats) {
        if (allowed) {
            __sync_fetch_and_add(&stats->dns_queries, 1);
        } else {
            __sync_fetch_and_add(&stats->dns_blocked, 1);
        }
    }
    
    log_audit_event(cfg->agent_id, ip->saddr, ip->daddr, 
                    bpf_ntohs(udp->source), bpf_ntohs(udp->dest),
                    IPPROTO_UDP, allowed ? 2 : 3, 1);
    
    return allowed ? TC_ACT_OK : TC_ACT_SHOT;
}

char _license[] SEC("license") = "GPL";
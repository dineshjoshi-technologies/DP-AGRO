import json, os, urllib.request, urllib.error

api=os.environ['PAPERCLIP_API_URL']
runid=os.environ['PAPERCLIP_RUN_ID']
H=lambda: {'Authorization':'Bearer '+os.environ['PAPERCLIP_API_KEY'],'X-Paperclip-Run-Id':runid,'Content-Type':'application/json'}

def req(method, path, body=None):
    data=json.dumps(body).encode() if body is not None else None
    r=urllib.request.Request(api+path, data=data, headers=H(), method=method)
    try:
        resp=urllib.request.urlopen(r)
        return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

prod = [
 ("DPA-248","63c73a38-efdd-41ef-87e5-e75e40e55147","DPA-202","Operations"),
 ("DPA-247","1142e38f-56ae-4500-a95e-38928337c7f5","DPA-76","Operations"),
 ("DPA-246","006b3156-be88-4775-bd98-26f8f6871836","DPA-234","Operations"),
 ("DPA-242","b9dd7738-9928-47b8-8549-405ac7a38d6d","DPA-203","MLOps"),
 ("DPA-245","368e5227-c3ff-445f-9d3e-22a3b0ac11b4","DPA-182","MLOps"),
 ("DPA-244","3b8c5f18-1903-4cc6-bb4e-7b9a7868b07c","DPA-188","MLOps"),
 ("DPA-243","514c08c5-597b-4c9a-8aa6-adee842a7295","DPA-224","MLOps"),
 ("DPA-236","e47b2236-76f0-4fcf-ba8f-e8762a060c4e","DPA-143","CEO"),
 ("DPA-233","6252f932-658b-4138-808a-a7d42b630bea","DPA-84","MLOps"),
]

for ident, iid, src, team in prod:
    comment = (f"## Review outcome: no intervention needed\n\nProductivity review for [{src}](/DPA/issues/{src}) ({team}).\n\n"
               f"- Source is `in_progress` with an assigned owner and a live continuation path; the long-active duration is an artifact of wedged adapter processes from 2026-09-11, not an unattended backlog.\n"
               f"- Wedged-run termination is board-gated; escalated on [DPA-143](/DPA/issues/DPA-143).\n"
               f"- Closing as resolved with the review recorded.")
    s,body=req('POST', f'/api/issues/{iid}/checkout', {"agentId":os.environ['PAPERCLIP_AGENT_ID'],"expectedStatuses":["todo","backlog","blocked","in_review","in_progress"]})
    if s>=300:
        print(ident,'checkout FAIL', s, body[:120]); continue
    s,body=req('PATCH', f'/api/issues/{iid}', {"status":"done","comment":comment})
    print(ident,'patch', s, ('ok' if s<300 else body[:150]))

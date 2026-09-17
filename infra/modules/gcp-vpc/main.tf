terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "network_name" {
  description = "VPC network name"
  type        = string
}

variable "subnets" {
  description = "Map of subnet names to configurations"
  type        = map(object({
    ip_cidr_range              = string
    region                     = string
    private_ip_google_access   = bool
    secondary_ranges           = list(object({
      range_name    = string
      ip_cidr_range = string
    }))
  }))
}

variable "secondary_ranges" {
  description = "Secondary IP ranges for pods/services"
  type        = map(list(object({
    range_name    = string
    ip_cidr_range = string
  })))
  default = {}
}

variable "tags" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "google_compute_network" "main" {
  name                    = var.network_name
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
  description             = "${var.environment} VPC network"

  labels = var.tags
}

resource "google_compute_subnetwork" "subnets" {
  for_each = var.subnets

  name                     = each.key
  ip_cidr_range            = each.value.ip_cidr_range
  region                   = each.value.region
  network                  = google_compute_network.main.id
  private_ip_google_access = each.value.private_ip_google_access
  description              = "${var.environment} subnet ${each.key}"

  secondary_ip_range = each.value.secondary_ranges

  labels = var.tags
}

resource "google_compute_firewall" "allow_internal" {
  name    = "${var.environment}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "all"
  }

  source_ranges = [var.subnets["private-us-central1-a"].ip_cidr_range, var.subnets["private-us-central1-b"].ip_cidr_range]
  target_tags   = ["internal"]

  description = "Allow internal traffic between private subnets"
}

resource "google_compute_firewall" "allow_ssh" {
  name    = "${var.environment}-allow-ssh"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ssh"]

  description = "Allow SSH from anywhere (restrict in production)"
}

resource "google_compute_firewall" "allow_https" {
  name    = "${var.environment}-allow-https"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["https"]

  description = "Allow HTTPS from anywhere"
}

resource "google_compute_router" "nat" {
  name    = "${var.environment}-nat-router"
  network = google_compute_network.main.name
  region  = var.subnets["private-us-central1-a"].region

  labels = var.tags
}

resource "google_compute_router_nat" "nat" {
  name                               = "${var.environment}-nat"
  router                             = google_compute_router.nat.name
  region                             = google_compute_router.nat.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
  log_config {
    enable = true
    filter = "ALL"
  }
}

output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.main.name
}

output "network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.main.id
}

output "subnet_names" {
  description = "Names of the subnets"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.name }
}

output "subnet_ids" {
  description = "IDs of the subnets"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.id }
}

output "subnet_self_links" {
  description = "Self links of the subnets"
  value       = { for k, v in google_compute_subnetwork.subnets : k => v.self_link }
}
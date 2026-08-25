terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.20.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Dedicated Least-Privilege Service Account for Agent Runtime
resource "google_service_account" "agent_sa" {
  account_id   = "cloud-sre-agent-sa"
  display_name = "Cloud SRE Multi-Agent Service Account"
}

# IAM Role Bindings for Observability and Telemetry Access
resource "google_project_iam_member" "logging_viewer" {
  project = var.project_id
  role    = "roles/logging.viewer"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "monitoring_viewer" {
  project = var.project_id
  role    = "roles/monitoring.viewer"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

# Storage Bucket for Persistent Episodic Vector Checkpoints
resource "google_storage_bucket" "memory_backup" {
  name                     = "${var.project_id}-sre-agent-episodic-memory"
  location                 = var.region
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
}

# Cloud Run V2 Deployment with Secure Secret Injection
resource "google_cloud_run_v2_service" "sre_agent_service" {
  name     = var.service_name
  location = var.region

  template {
    service_account = google_service_account.agent_sa.email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
      }

      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }

      env {
        name  = "COORDINATOR_MODEL"
        value = "gemini-2.5-pro"
      }

      env {
        name  = "WORKER_MODEL"
        value = "gemini-2.5-flash"
      }

      env {
        name  = "ENABLE_STRUCTURED_LOGGING"
        value = "true"
      }

      # Secure Injection of API Key from Secret Manager (Zero Hardcoding)
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_api_key.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

variable "project_id" {
  description = "Google Cloud Project ID"
  type        = string
  default     = "demo-cloud-sre-project"
}

variable "region" {
  description = "Primary Google Cloud deployment region"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run SRE Agent service"
  type        = string
  default     = "cloud-sre-agent"
}

variable "container_image" {
  description = "Container image URL for the agent"
  type        = string
  default     = "gcr.io/demo-cloud-sre-project/cloud-sre-agent:latest"
}

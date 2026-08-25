output "cloud_run_url" {
  description = "Public URL of the deployed Cloud SRE Agent service"
  value       = google_cloud_run_v2_service.sre_agent_service.uri
}

output "service_account_email" {
  description = "Service Account email used by the agent"
  value       = google_service_account.agent_sa.email
}

output "secret_manager_id" {
  description = "Secret Manager ID storing the Gemini API Key"
  value       = google_secret_manager_secret.gemini_api_key.id
}

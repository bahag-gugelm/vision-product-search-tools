output "job_runner_sa_email" {
  value = "${google_service_account.pc_vision_product_search_tools_sa.email}"
}
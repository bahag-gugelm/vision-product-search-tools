resource "google_service_account" "pc_vision_product_search_tools_sa" {
  account_id   = "pc-vision-product-search-tools"
  display_name = "pc-vision-product-search-tools"
}

resource "google_project_iam_binding" "pc_vision_product_search_tools_sa" {
  project = "${var.project_id}"
  for_each = toset([
    "roles/storage.admin",
    "roles/cloudscheduler.admin",
    "roles/run.invoker"
  ])
  role = each.key
  members = [
    "serviceAccount:${google_service_account.pc_vision_product_search_tools_sa.email}"
  ]
}
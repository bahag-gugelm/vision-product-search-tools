provider "google" {
  project = var.project_id
  region  = var.project_region
  zone    = "europe-west1-b"
}

terraform {
  backend "gcs" {
    prefix = "pc-vision-product-search-tools/state"
  }
}

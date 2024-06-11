resource "google_storage_bucket" "src_storage_bucket" {
  name          = var.storage_bucket_id
  location      = var.project_region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}

resource "google_storage_bucket" "bulk_csv_bucket" {
  name          = var.bulk_csv_bucket_id
  location      = var.project_region
  force_destroy = true

  uniform_bucket_level_access = true

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}
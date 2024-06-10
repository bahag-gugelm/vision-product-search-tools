module "service_account" {
  source = "./modules/service_account"
  project_id = var.project_id
  project_region = var.project_region
  
}

resource "google_artifact_registry_repository" "pc_vision_product_search_tools_docker" {
  provider      = google-beta
  location      = var.project_region
  repository_id = var.image_folder
  description   = "Repository for the image search tools images"
  format        = "DOCKER"
  project       = var.project_id

  cleanup_policies {
    id     = "keep-minimum-versions"
    action = "KEEP"
    most_recent_versions {
      keep_count = 5
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  secrets = {
    postgres_server       = var.postgres_server,
    postgres_user       = var.postgres_user,
    postgres_password   = var.postgres_password
    postgres_db         = var.postgres_db
    assets_api_user     = var.assets_api_user
    assets_api_password = var.assets_api_password
  }
}

resource "google_secret_manager_secret" "pc_vision_product_search_tools_secrets" {
  for_each  = local.secrets
  secret_id = each.key
  replication {
    user_managed {
      replicas {
        location = var.project_region
      }
    }
  }
}

resource "google_secret_manager_secret_version" "secrets" {
  for_each    = local.secrets
  secret      = google_secret_manager_secret.pc_vision_product_search_tools_secrets[each.key].id
  secret_data = each.value
}

resource "google_secret_manager_secret_iam_binding" "secret_bindings" {
  for_each  = local.secrets
  secret_id = google_secret_manager_secret.pc_vision_product_search_tools_secrets[each.key].id
  role      = "roles/secretmanager.secretAccessor"
  members = [
    "serviceAccount:${module.service_account.job_runner_sa_email}"
  ]
}

resource "google_cloud_run_v2_job" "vision_import_assets" {
  name     = "pc-vision-product-search-tools-${var.env_name}"
  location = var.project_region

  template {
    template {
      timeout = "10800s" # 3 hours
      service_account = "${module.service_account.job_runner_sa_email}"
      containers {
        image = "${var.docker_image_name}:${var.git_sha}"
        resources {
          limits = {
            cpu    = "8"
            memory = "8192Mi"
          }
        }
        env {
          name = "POSTGRES_SERVER"
          value_source {
            secret_key_ref {
              secret = "postgres_server"
              version = "latest"
            }
          }
        }
        env {
          name = "POSTGRES_USER"
          value_source {
            secret_key_ref {
              secret = "postgres_user"
              version = "latest"
            }
          }
        }
        env {
          name = "POSTGRES_PASSWORD"
          value_source {
            secret_key_ref {
              secret = "postgres_password"
              version = "latest"
            }
          }
        }
        env {
          name = "POSTGRES_DB"
          value_source {
            secret_key_ref {
              secret = "postgres_db"
              version = "latest"
            }
          }
        }
        env {
          name = "ASSETS_API_USER"
          value_source {
            secret_key_ref {
              secret = "assets_api_user"
              version = "latest"
            }
          }
        }
        env {
          name = "ASSETS_API_PASSWORD"
          value_source {
            secret_key_ref {
              secret = "assets_api_user"
              version = "latest"
            }
          }
        }
        dynamic "env" {
          for_each = tomap({
            "PROJECT_ID"          = "${var.project_id}"
            "PROJECT_REGION"      = "${var.project_region}"
            "STORAGE_BUCKET_ID"   = "${var.storage_bucket_id}"
          })

          content {
            name  = env.key
            value = env.value
          }
        }
      }
      vpc_access{
        connector = "projects/${var.project_id}/locations/${var.project_region}/connectors/serverless-vpc-connector"
        egress = "ALL_TRAFFIC"
      }
    }
  }

  lifecycle {
    ignore_changes = [
      launch_stage,
    ]
  }
  # depends_on = [module.artifact_registry.output]
}
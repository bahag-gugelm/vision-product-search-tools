variable "project_region" {
  type = string
}
variable "storage_bucket_id" {
  type = string
  default = "vision-product-search-src"
}
variable "bulk_csv_bucket_id" {
  type = string
  default = "vision-product-search-csv"
}

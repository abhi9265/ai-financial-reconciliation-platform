variable "aws_region" {
  type = string
  default = "ap-south-1"
}
variable "project_name" {
  type = string
  default = "reconciliation-platform"
}
variable "staging_domain" {
  type = string
}
variable "acm_certificate_arn" {
  type = string
  sensitive = true
}
variable "container_image" {
  type = string
}
variable "api_desired_count" {
  type = number
  default = 1
}
variable "worker_desired_count" {
  type = number
  default = 1
}
variable "db_instance_class" {
  type = string
  default = "db.t4g.micro"
}
variable "redis_node_type" {
  type = string
  default = "cache.t4g.micro"
}
variable "api_cpu" {
  type = number
  default = 512
}
variable "api_memory" {
  type = number
  default = 1024
}
variable "worker_cpu" {
  type = number
  default = 1024
}
variable "worker_memory" {
  type = number
  default = 2048
}

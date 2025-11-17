terraform {
  required_version = ">= 1.6.0"
}

variable "docker_host" {
  description = "TCP endpoint for the Hetzner VM's Docker daemon"
  type        = string
}

variable "stack_name" {
  description = "Identifier for the stack and container"
  type        = string
  default     = "debug-cloud"
}

variable "app_image" {
  description = "Image to run via the docker_node module"
  type        = string
}

variable "app_env" {
  description = "Environment variables"
  type        = map(string)
  default     = {}
}

variable "app_ports" {
  description = "Port forwards in host:container notation"
  type        = list(string)
  default     = ["8000:8000"]
}

variable "runner_token" {
  description = "Optional token passed to the container"
  type        = string
  default     = ""
  sensitive   = true
}

module "docker_node" {
  source = "../modules/docker_node"

  docker_host   = var.docker_host
  stack_name    = var.stack_name
  app_image     = var.app_image
  app_env       = var.app_env
  app_ports     = var.app_ports
  runner_token  = var.runner_token
}

output "docker_host" {
  description = "The TCP endpoint for the remote Docker engine"
  value       = module.docker_node.docker_host
}

output "container_name" {
  description = "Container name launched on the VM"
  value       = module.docker_node.container_name
}

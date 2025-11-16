terraform {
  required_version = ">= 1.6.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

variable "docker_host" {
  description = "TCP or SSH URI for the Docker daemon"
  type        = string
}

variable "app_image" {
  description = "Image to run inside the provisioned docker host"
  type        = string
}

variable "stack_name" {
  description = "Prefix used for container names"
  type        = string
}

variable "app_ports" {
  description = "List of port mappings in host:container format"
  type        = list(string)
  default     = []

  validation {
    condition = alltrue([
      for mapping in var.app_ports : (
        length(split(":", mapping)) == 2
        && can(tonumber(split(":", mapping)[0]))
        && can(tonumber(split(":", mapping)[1]))
        && tonumber(split(":", mapping)[0]) >= 1
        && tonumber(split(":", mapping)[0]) <= 65535
        && tonumber(split(":", mapping)[1]) >= 1
        && tonumber(split(":", mapping)[1]) <= 65535
      )
    ])

    error_message = "Each port mapping must be HOST:CONTAINER with integer ports in the range 1-65535."
  }
}

variable "app_env" {
  description = "Environment variables passed to the container"
  type        = map(string)
  default     = {}
}

variable "runner_token" {
  description = "Optional runner/api token injected into the container"
  type        = string
  default     = ""
  sensitive   = true
}

provider "docker" {
  host = var.docker_host
}

data "docker_registry_image" "app" {
  name = var.app_image
}

resource "docker_image" "app" {
  name          = data.docker_registry_image.app.name
  pull_triggers = [data.docker_registry_image.app.sha256_digest]
}

locals {
  env_with_token = merge(
    var.app_env,
    var.runner_token != "" ? { "DEBUG_SERVER_TOKEN" = var.runner_token } : {}
  )
}

resource "docker_container" "app" {
  name  = "${var.stack_name}-app"
  image = docker_image.app.image_id

  dynamic "ports" {
    for_each = var.app_ports
    content {
      internal = tonumber(split(":", ports.value)[1])
      external = tonumber(split(":", ports.value)[0])
    }
  }

  env = [for k, v in local.env_with_token : "${k}=${v}"]
  restart = "unless-stopped"
}

output "container_name" {
  value = docker_container.app.name
}

output "container_id" {
  value = docker_container.app.id
}

output "docker_host" {
  value = var.docker_host
}

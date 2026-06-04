variable "location" {
  description = "Azure region for the function app"
  type        = string
  default     = "West Europe"
}

variable "vm_resource_group" {
  description = "Resource group where the target VM lives"
  type        = string
  default     = "my-vm-rg"
}

variable "vm_name" {
  description = "Name of the VM to start and stop"
  type        = string
  default     = "mgmt-vm"
}

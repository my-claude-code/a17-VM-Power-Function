terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

# ── Existing VM resource group (where mgmt-vm lives) ─────────────────────────
data "azurerm_resource_group" "vm_rg" {
  name = var.vm_resource_group
}

# ── Resource group for the function app ──────────────────────────────────────
resource "azurerm_resource_group" "rg" {
  name     = "rg-vm-power-function"
  location = var.location
}

# ── Storage account (required by Azure Functions) ────────────────────────────
resource "azurerm_storage_account" "fn" {
  name                     = "stvmpowerivansto"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# ── Consumption plan (pay per execution, first 1M calls/month free) ───────────
resource "azurerm_service_plan" "fn" {
  name                = "plan-vm-power"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  os_type             = "Linux"
  sku_name            = "Y1"
}

# ── Function App ──────────────────────────────────────────────────────────────
resource "azurerm_linux_function_app" "fn" {
  name                       = "fn-vm-power-ivansto"
  resource_group_name        = azurerm_resource_group.rg.name
  location                   = azurerm_resource_group.rg.location
  storage_account_name       = azurerm_storage_account.fn.name
  storage_account_access_key = azurerm_storage_account.fn.primary_access_key
  service_plan_id            = azurerm_service_plan.fn.id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "FUNCTIONS_WORKER_RUNTIME" = "python"
    "AZURE_SUBSCRIPTION_ID"    = data.azurerm_client_config.current.subscription_id
    "PYTHONPATH"               = "/home/site/wwwroot/.python_packages/lib/site-packages"
  }
}

# ── Grant function managed identity Contributor on the VM resource group ──────
resource "azurerm_role_assignment" "fn_vm_contributor" {
  scope                = data.azurerm_resource_group.vm_rg.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_linux_function_app.fn.identity[0].principal_id
}

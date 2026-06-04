output "function_app_name" {
  value = azurerm_linux_function_app.fn.name
}

output "function_url" {
  description = "Base URL — append ?action=start&code=KEY or ?action=stop&code=KEY"
  value       = "https://${azurerm_linux_function_app.fn.name}.azurewebsites.net/api/vm-power"
}

output "ACTION_REQUIRED" {
  value = <<-EOT
    1. Deploy the function code:
       bash deploy.sh

    2. Get your function key:
       az functionapp keys list \
           --resource-group rg-vm-power-function \
           --name ${azurerm_linux_function_app.fn.name} \
           --query "functionKeys.default" -o tsv

    3. Start the VM (returns the public IP):
       curl "https://${azurerm_linux_function_app.fn.name}.azurewebsites.net/api/vm-power?action=start&code=<KEY>"

    4. Stop the VM (deallocates — no compute charges):
       curl "https://${azurerm_linux_function_app.fn.name}.azurewebsites.net/api/vm-power?action=stop&code=<KEY>"
  EOT
}

import azure.functions as func
import json
import os
import logging
from azure.identity import ManagedIdentityCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

VM_NAME = os.environ.get("VM_NAME", "mgmt-vm")
VM_RG   = os.environ.get("VM_RG",   "my-vm-rg")


def _clients():
    credential   = ManagedIdentityCredential()
    subscription = os.environ["AZURE_SUBSCRIPTION_ID"]
    return (
        ComputeManagementClient(credential, subscription),
        NetworkManagementClient(credential, subscription),
    )


def _get_public_ip(compute_client, network_client):
    vm      = compute_client.virtual_machines.get(VM_RG, VM_NAME)
    nic_id  = vm.network_profile.network_interfaces[0].id
    nic     = network_client.network_interfaces.get(VM_RG, nic_id.split("/")[-1])
    pip_ref = nic.ip_configurations[0].public_ip_address
    if not pip_ref:
        return None
    pip = network_client.public_ip_addresses.get(VM_RG, pip_ref.id.split("/")[-1])
    return pip.ip_address


@app.route(route="vm-power")
def vm_power(req: func.HttpRequest) -> func.HttpResponse:
    action = req.params.get("action", "").lower()

    if action not in ("start", "stop"):
        return func.HttpResponse(
            json.dumps({"error": "action must be 'start' or 'stop'"}),
            status_code=400,
            mimetype="application/json",
        )

    try:
        compute_client, network_client = _clients()

        if action == "start":
            logging.info("Starting VM %s...", VM_NAME)
            compute_client.virtual_machines.begin_start(VM_RG, VM_NAME).result()
            public_ip = _get_public_ip(compute_client, network_client)
            return func.HttpResponse(
                json.dumps({"status": "started", "vm": VM_NAME, "public_ip": public_ip}),
                mimetype="application/json",
            )

        else:
            logging.info("Deallocating VM %s...", VM_NAME)
            compute_client.virtual_machines.begin_deallocate(VM_RG, VM_NAME).result()
            return func.HttpResponse(
                json.dumps({"status": "stopped", "vm": VM_NAME}),
                mimetype="application/json",
            )

    except Exception as exc:
        logging.error("Error: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=500,
            mimetype="application/json",
        )

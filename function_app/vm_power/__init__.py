import azure.functions as func
import json
import os
import logging
import urllib.request
import urllib.error
import time

VM_NAME = os.environ.get("VM_NAME", "mgmt-vm")
VM_RG   = os.environ.get("VM_RG",   "my-vm-rg")
API_VER_COMPUTE = "api-version=2023-03-01"
API_VER_NETWORK = "api-version=2023-09-01"


def get_token():
    endpoint = os.environ["IDENTITY_ENDPOINT"]
    header   = os.environ["IDENTITY_HEADER"]
    url = f"{endpoint}?api-version=2019-08-01&resource=https://management.azure.com/"
    req = urllib.request.Request(url, headers={"X-IDENTITY-HEADER": header})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())["access_token"]


def arm(method, path, token):
    req = urllib.request.Request(
        f"https://management.azure.com{path}",
        method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        data=b"",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        if e.code == 202:
            return {}
        raise


def wait_running(sub, token, timeout=180):
    path = (f"/subscriptions/{sub}/resourceGroups/{VM_RG}"
            f"/providers/Microsoft.Compute/virtualMachines/{VM_NAME}"
            f"/instanceView?{API_VER_COMPUTE}")
    deadline = time.time() + timeout
    while time.time() < deadline:
        view = arm("GET", path, token)
        for s in view.get("statuses", []):
            if s.get("code") == "PowerState/running":
                return
        time.sleep(10)


def get_public_ip(sub, token):
    vm = arm("GET",
             f"/subscriptions/{sub}/resourceGroups/{VM_RG}"
             f"/providers/Microsoft.Compute/virtualMachines/{VM_NAME}?{API_VER_COMPUTE}",
             token)
    nic_id   = vm["properties"]["networkProfile"]["networkInterfaces"][0]["id"]
    nic_name = nic_id.split("/")[-1]
    nic_rg   = nic_id.split("/")[4]
    nic = arm("GET",
              f"/subscriptions/{sub}/resourceGroups/{nic_rg}"
              f"/providers/Microsoft.Network/networkInterfaces/{nic_name}?{API_VER_NETWORK}",
              token)
    pip_ref = nic["properties"]["ipConfigurations"][0]["properties"].get("publicIPAddress")
    if not pip_ref:
        return None
    pip_id   = pip_ref["id"]
    pip_name = pip_id.split("/")[-1]
    pip_rg   = pip_id.split("/")[4]
    pip = arm("GET",
              f"/subscriptions/{sub}/resourceGroups/{pip_rg}"
              f"/providers/Microsoft.Network/publicIPAddresses/{pip_name}?{API_VER_NETWORK}",
              token)
    return pip["properties"].get("ipAddress")


def main(req: func.HttpRequest) -> func.HttpResponse:
    action = req.params.get("action", "").lower()
    sub    = os.environ["AZURE_SUBSCRIPTION_ID"]

    if action not in ("start", "stop"):
        return func.HttpResponse(
            json.dumps({"error": "action must be 'start' or 'stop'"}),
            status_code=400, mimetype="application/json")

    try:
        token = get_token()

        if action == "start":
            logging.info("Starting %s...", VM_NAME)
            arm("POST",
                f"/subscriptions/{sub}/resourceGroups/{VM_RG}"
                f"/providers/Microsoft.Compute/virtualMachines/{VM_NAME}/start?{API_VER_COMPUTE}",
                token)
            wait_running(sub, token)
            ip = get_public_ip(sub, token)
            return func.HttpResponse(
                json.dumps({"status": "started", "vm": VM_NAME, "public_ip": ip}),
                mimetype="application/json")

        else:
            logging.info("Deallocating %s...", VM_NAME)
            arm("POST",
                f"/subscriptions/{sub}/resourceGroups/{VM_RG}"
                f"/providers/Microsoft.Compute/virtualMachines/{VM_NAME}/deallocate?{API_VER_COMPUTE}",
                token)
            return func.HttpResponse(
                json.dumps({"status": "stopped", "vm": VM_NAME}),
                mimetype="application/json")

    except Exception as exc:
        logging.error("Error: %s", exc)
        return func.HttpResponse(
            json.dumps({"error": str(exc)}),
            status_code=500, mimetype="application/json")

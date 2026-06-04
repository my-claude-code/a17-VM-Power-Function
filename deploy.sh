#!/bin/bash
# Run this after terraform apply to push the function code.
set -euo pipefail

FUNCTION_APP="fn-vm-power-ivansto"
RG="rg-vm-power-function"

echo "==> Installing packages into zip bundle..."
cd function_app
pip install \
    --target=".python_packages/lib/site-packages" \
    -r requirements.txt \
    --quiet

echo "==> Packaging function code with dependencies..."
zip -r ../function.zip . --exclude "*.pyc" --exclude "*__pycache__*"
cd ..

echo "==> Deploying to Azure Function App..."
az functionapp deployment source config-zip \
    --resource-group "$RG" \
    --name "$FUNCTION_APP" \
    --src function.zip

echo "==> Cleaning up..."
rm -f function.zip
rm -rf function_app/.python_packages

echo ""
echo "==> Getting function key..."
FUNCTION_KEY=$(az functionapp keys list \
    --resource-group "$RG" \
    --name "$FUNCTION_APP" \
    --query "functionKeys.default" -o tsv)

FUNCTION_URL="https://$FUNCTION_APP.azurewebsites.net/api/vm-power"

echo ""
echo "============================================================"
echo " Deployed!"
echo "============================================================"
echo ""
echo "--- Start VM (returns public IP) ---"
echo "curl \"$FUNCTION_URL?action=start&code=$FUNCTION_KEY\""
echo ""
echo "--- Stop VM (deallocates — no compute charges) ---"
echo "curl \"$FUNCTION_URL?action=stop&code=$FUNCTION_KEY\""
echo "============================================================"

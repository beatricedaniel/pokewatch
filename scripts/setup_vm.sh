#!/bin/bash
# ============================================================================
# PokeWatch VM Setup Script
#
# USAGE: Copy this script to your VM and run it:
#   scp -i /path/to/key.pem scripts/setup_vm.sh user@VM-IP:~/
#   ssh -i /path/to/key.pem user@VM-IP "chmod +x ~/setup_vm.sh && ~/setup_vm.sh"
# ============================================================================

set -e

echo "============================================="
echo "  PokeWatch VM Setup"
echo "============================================="

# ----------------------------------------------------------------------------
# 1. Update system
# ----------------------------------------------------------------------------
echo "[1/5] Updating system..."
sudo apt-get update && sudo apt-get upgrade -y

# ----------------------------------------------------------------------------
# 2. Install K3s (with readable kubeconfig)
# ----------------------------------------------------------------------------
echo "[2/5] Installing K3s..."
curl -sfL https://get.k3s.io | sh -s - --write-kubeconfig-mode 644

# Wait for K3s to be ready
echo "Waiting for K3s to be ready..."
sleep 15

# ----------------------------------------------------------------------------
# 3. Configure kubectl
# ----------------------------------------------------------------------------
echo "[3/5] Configuring kubectl..."
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(whoami):$(whoami) ~/.kube/config
chmod 600 ~/.kube/config

# Set KUBECONFIG for current session
export KUBECONFIG=~/.kube/config

# Verify kubectl works
kubectl get nodes

# ----------------------------------------------------------------------------
# 4. Install Helm
# ----------------------------------------------------------------------------
echo "[4/5] Installing Helm..."
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
helm version

# ----------------------------------------------------------------------------
# 5. Create namespaces
# ----------------------------------------------------------------------------
echo "[5/5] Creating namespaces..."
kubectl create namespace pokewatch --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace airflow --dry-run=client -o yaml | kubectl apply -f -

# ----------------------------------------------------------------------------
# Done
# ----------------------------------------------------------------------------
echo ""
echo "============================================="
echo "  Setup Complete!"
echo "============================================="
echo ""
echo "Next: Create secrets on this VM (run manually):"
echo ""
echo "kubectl create secret generic pokewatch-secrets -n pokewatch \\"
echo "  --from-literal=POKEMON_PRICE_API_KEY=\"xxx\" \\"
echo "  --from-literal=MLFLOW_TRACKING_URI=\"xxx\" \\"
echo "  --from-literal=MLFLOW_TRACKING_USERNAME=\"xxx\" \\"
echo "  --from-literal=MLFLOW_TRACKING_PASSWORD=\"xxx\" \\"
echo "  --from-literal=DAGSHUB_USER_TOKEN=\"xxx\""
echo ""
echo "kubectl create secret generic pokewatch-secrets -n airflow \\"
echo "  --from-literal=POKEMON_PRICE_API_KEY=\"xxx\" \\"
echo "  --from-literal=MLFLOW_TRACKING_URI=\"xxx\" \\"
echo "  --from-literal=MLFLOW_TRACKING_USERNAME=\"xxx\" \\"
echo "  --from-literal=MLFLOW_TRACKING_PASSWORD=\"xxx\" \\"
echo "  --from-literal=DAGSHUB_USER_TOKEN=\"xxx\""

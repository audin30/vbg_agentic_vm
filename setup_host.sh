#!/bin/bash
# setup_host.sh - Prepares Host A for the Security Hub

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y libldap2-dev libsasl2-dev gcc curl python3.12-venv python3.12-dev

echo "Installing Node.js 20.x..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "Creating service account..."
sudo useradd -r -s /bin/false vbg-hub || echo "User already exists"

echo "Setting up application directory..."
sudo mkdir -p /opt/vbg-hub
sudo chown -R vbg-hub:vbg-hub /opt/vbg-hub

echo "Host setup complete. Manual steps remaining: Copy code to /opt/vbg-hub and configure .env"

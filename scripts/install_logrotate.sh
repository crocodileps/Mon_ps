#!/bin/bash
# Installation script for logrotate configuration
# Usage: sudo bash /home/Mon_ps/scripts/install_logrotate.sh

set -e

echo "Installing logrotate configuration for Mon_PS..."

# Copy config file
cp /home/Mon_ps/config/logrotate-monps.conf /etc/logrotate.d/monps
chown root:root /etc/logrotate.d/monps
chmod 644 /etc/logrotate.d/monps

# Test configuration
echo "Testing logrotate configuration..."
logrotate -d /etc/logrotate.d/monps

echo "✅ Logrotate configuration installed successfully"
echo "Logs will be rotated daily, kept for 14 days, and compressed"

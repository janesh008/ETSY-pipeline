#!/bin/bash
# ==============================================================================
# GCP GPU VM Creation Script for Etsy Pipeline
# Run this script from your Google Cloud Shell to create the GPU VM.
# ==============================================================================

# Variables
VM_NAME="etsy-image-worker"
ZONE="us-central1-a"  # Ensure this matches your GCP_LOCATION in .env
MACHINE_TYPE="n1-standard-8"
GPU_TYPE="nvidia-tesla-t4"
DISK_SIZE="70GB"

echo "🚀 Creating GPU VM: $VM_NAME in $ZONE..."

# We use Google's Deep Learning image which comes with NVIDIA drivers pre-installed.
gcloud compute instances create "$VM_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --accelerator="type=$GPU_TYPE,count=1" \
    --maintenance-policy="TERMINATE" \
    --image-family="common-cu121-debian-11" \
    --image-project="deeplearning-platform-release" \
    --boot-disk-size="$DISK_SIZE" \
    --boot-disk-type="pd-ssd" \
    --scopes="https://www.googleapis.com/auth/cloud-platform" \
    --metadata-from-file="startup-script=vm_startup.sh"

echo "✅ VM Creation requested."
echo "Wait a few minutes for the startup script to finish downloading the 25 GB models."
echo "You can view startup progress by SSHing into the VM and running:"
echo "  sudo journalctl -u google-startup-scripts.service -f"

#!/bin/bash
# ==============================================================================
# GCP GPU VM Creation Script for Etsy Pipeline (Optimized for 3s Generation)
# Run this script from your Google Cloud Shell to create the GPU VM.
# ==============================================================================

# Variables
VM_NAME="etsy-image-worker"
ZONE="us-central1-a"       # Ensure you have your approved Nvidia L4 quota in this region/zone
MACHINE_TYPE="g2-standard-8"
GPU_TYPE="nvidia-l4"
DISK_SIZE="120GB"          # Increased to handle OS + deep learning drivers + 25GB models safely

echo "🚀 Creating High-Performance GPU VM: $VM_NAME in $ZONE..."

echo "🔍 Finding the latest Deep Learning image for Ubuntu 22.04..."
IMAGE_NAME=$(gcloud compute images list \
    --project=deeplearning-platform-release \
    --filter="family ~ pytorch-.*-ubuntu-2204" \
    --format="value(name)" \
    --sort-by="~creationTimestamp" \
    --limit=1)

echo "✅ Using Image: $IMAGE_NAME"

# Using Google's modern CUDA Deep Learning Image optimized for the L4 architecture
gcloud compute instances create "$VM_NAME" \
    --zone="$ZONE" \
    --machine-type="$MACHINE_TYPE" \
    --accelerator="type=$GPU_TYPE,count=1" \
    --maintenance-policy="TERMINATE" \
    --image="$IMAGE_NAME" \
    --image-project="deeplearning-platform-release" \
    --boot-disk-size="$DISK_SIZE" \
    --boot-disk-type="pd-ssd" \
    --scopes="https://www.googleapis.com/auth/cloud-platform" \
    --metadata-from-file="startup-script=vm_startup.sh"

echo "✅ VM Creation requested."
echo "Wait a few minutes for the startup script to finish downloading the 25 GB models."
echo "You can view startup progress by SSHing into the VM and running:"
echo "  sudo journalctl -u google-startup-scripts.service -f"

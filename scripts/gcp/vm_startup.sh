#!/bin/bash
# ==============================================================================
# GCP VM Startup Script
# Runs as root on boot. Installs ComfyUI, dependencies, and downloads models.
# ==============================================================================

set -e

echo "--- Starting VM Setup ---"

# 1. Update and install basic dependencies
apt-get update -y
apt-get install -y python3.11-venv git wget unzip

# 2. Setup ComfyUI in /opt
if [ ! -d "/opt/ComfyUI" ]; then
    echo "--- Cloning ComfyUI ---"
    cd /opt
    git clone https://github.com/comfyanonymous/ComfyUI.git
    cd ComfyUI
    
    echo "--- Setting up Python Venv for ComfyUI ---"
    python3 -m venv venv
    source venv/bin/activate
    
    echo "--- Installing ComfyUI Requirements ---"
    pip install torch torchvision torchaudio --extra-index-url https://download.pytorch.org/whl/cu121
    pip install -r requirements.txt
    deactivate
    
    # Ensure correct permissions for the default GCP user (adjust if needed, usually 'USER' or standard login)
    chown -R 1000:1000 /opt/ComfyUI
else
    echo "--- ComfyUI already installed ---"
fi

# 3. Download z_image_turbo models (total ~25 GB)
echo "--- Downloading Models ---"
mkdir -p /opt/ComfyUI/models/vae
mkdir -p /opt/ComfyUI/models/text_encoders
mkdir -p /opt/ComfyUI/models/diffusion_models

# Download VAE (ae.safetensors)
if [ ! -f "/opt/ComfyUI/models/vae/ae.safetensors" ]; then
    echo "Downloading VAE..."
    wget -q --show-progress "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors?download=true" -O /opt/ComfyUI/models/vae/ae.safetensors
fi

# Download Text Encoder (qwen_3_4b.safetensors)
if [ ! -f "/opt/ComfyUI/models/text_encoders/qwen_3_4b.safetensors" ]; then
    echo "Downloading Text Encoder..."
    wget -q --show-progress "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors?download=true" -O /opt/ComfyUI/models/text_encoders/qwen_3_4b.safetensors
fi

# Download Diffusion Model (z_image_turbo_bf16.safetensors)
if [ ! -f "/opt/ComfyUI/models/diffusion_models/z_image_turbo_bf16.safetensors" ]; then
    echo "Downloading Diffusion Model..."
    wget -q --show-progress "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors?download=true" -O /opt/ComfyUI/models/diffusion_models/z_image_turbo_bf16.safetensors
fi

chown -R 1000:1000 /opt/ComfyUI/models

echo "--- VM Setup Complete ---"

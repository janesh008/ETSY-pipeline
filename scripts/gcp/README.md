# GCP GPU VM Setup Guide

Follow these steps to provision and configure the GPU VM for image generation.

## 1. Create the VM from Google Cloud Shell

Open the [Google Cloud Console](https://console.cloud.google.com/), click the **Cloud Shell** icon (terminal icon in the top right), and run these commands to download and run the setup script:

```bash
# Download the VM creation script and startup script
mkdir -p etsy_setup && cd etsy_setup
wget https://raw.githubusercontent.com/<YOUR-GITHUB-USERNAME>/ETSY-pipeline/main/scripts/gcp/gpu_vm_create.sh
wget https://raw.githubusercontent.com/<YOUR-GITHUB-USERNAME>/ETSY-pipeline/main/scripts/gcp/vm_startup.sh

# Make executable and run
chmod +x gpu_vm_create.sh
./gpu_vm_create.sh
```
*(Note: Replace `<YOUR-GITHUB-USERNAME>` with your actual repo path, or just copy-paste the contents of `gpu_vm_create.sh` and `vm_startup.sh` into Cloud Shell files).*

This command provisions the `n1-standard-8` VM with an NVIDIA T4 GPU and a 70 GB SSD. It uses Google's Deep Learning image, which comes with NVIDIA drivers pre-installed. 
The `vm_startup.sh` script runs automatically in the background on the VM to install ComfyUI and download the 25 GB of z_image_turbo models.

## 2. Connect to the VM and Start ComfyUI

Wait about 5-10 minutes for the startup script to finish downloading the models. Then, SSH into the VM:

```bash
gcloud compute ssh etsy-image-worker --zone=us-central1-a
```

Start the ComfyUI server in the background:
```bash
cd /opt/ComfyUI
source venv/bin/activate
# Run it in a screen session or use nohup so it stays running when you disconnect
nohup python main.py --listen 127.0.0.1 --port 8188 > comfyui.log 2>&1 &
```

## 3. Clone Your Repo and Start the Image Worker

Still SSH'd into the VM, clone your code and set it up:

```bash
# Clone the repository
git clone https://github.com/<YOUR-GITHUB-USERNAME>/ETSY-pipeline.git
cd ETSY-pipeline

# Create a virtual environment and install the pipeline package
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Copy your .env file
cp .env.example .env
nano .env # Fill in your GCP_PROJECT_ID, GCS_BUCKET, etc.

# Start the worker daemon
python scripts/run_image_worker.py --daemon
```

Alternatively, to have the worker start automatically when the VM boots, you can install the systemd service:

```bash
sudo cp scripts/gcp/image_worker.service /etc/systemd/system/
# Edit the file to replace 'user' with your actual linux username (run `whoami` to check)
sudo nano /etc/systemd/system/image_worker.service
sudo systemctl daemon-reload
sudo systemctl enable image_worker
sudo systemctl start image_worker
```

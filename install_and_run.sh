#!/bin/bash

# Update package list and install system dependencies
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Create a virtual environment
python3 -m venv monitor_env

# Activate the virtual environment
source monitor_env/bin/activate

# Install Python dependencies
pip install PyQt5 watchdog


# Run the file monitor script
python3 guardQT.py

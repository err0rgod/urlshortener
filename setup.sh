#!/bin/bash

# Update and install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv redis-server postgresql postgresql-contrib nginx

# Start Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Please configure your .env file and PostgreSQL database."

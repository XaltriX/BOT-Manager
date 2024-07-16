#!/bin/bash

# Update the instance
sudo yum update -y

# Install Docker
sudo amazon-linux-extras install docker -y
sudo service docker start
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Clone your repository (replace with your actual repository URL)
https://github.com/xdevilxyz/BOT-Manager
cd BOT-Manager

# Build and run the Docker container
sudo docker-compose up -d --build

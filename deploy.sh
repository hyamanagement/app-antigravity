#!/bin/bash

# AWS Deployment Script for Video Script Generator
# This script automates the deployment process on Amazon Linux 2023 or Ubuntu 22.04

set -e  # Exit on error

echo "========================================="
echo "Video Script Generator - AWS Deployment"
echo "========================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "Cannot detect OS. Exiting."
    exit 1
fi

echo "Detected OS: $OS"
echo ""

# Update system
echo "Step 1: Updating system packages..."
if [ "$OS" = "amzn" ]; then
    sudo yum update -y
elif [ "$OS" = "ubuntu" ]; then
    sudo apt update && sudo apt upgrade -y
fi

# Install Python
echo ""
echo "Step 2: Installing Python 3.11..."
if [ "$OS" = "amzn" ]; then
    sudo yum install python3.11 python3.11-pip -y
elif [ "$OS" = "ubuntu" ]; then
    sudo apt install python3.11 python3.11-venv python3-pip -y
fi

# Install Node.js
echo ""
echo "Step 3: Installing Node.js 18..."
if [ "$OS" = "amzn" ]; then
    curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
    sudo yum install nodejs -y
elif [ "$OS" = "ubuntu" ]; then
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt install nodejs -y
fi

# Install Git
echo ""
echo "Step 4: Installing Git..."
if [ "$OS" = "amzn" ]; then
    sudo yum install git -y
elif [ "$OS" = "ubuntu" ]; then
    sudo apt install git -y
fi

# Install Nginx
echo ""
echo "Step 5: Installing Nginx..."
if [ "$OS" = "amzn" ]; then
    sudo yum install nginx -y
elif [ "$OS" = "ubuntu" ]; then
    sudo apt install nginx -y
fi

# Install PM2
echo ""
echo "Step 6: Installing PM2..."
sudo npm install -g pm2

# Install build tools
echo ""
echo "Step 7: Installing build tools..."
if [ "$OS" = "amzn" ]; then
    sudo yum groupinstall "Development Tools" -y
elif [ "$OS" = "ubuntu" ]; then
    sudo apt install build-essential -y
fi

# Create application directory
echo ""
echo "Step 8: Setting up application directory..."
sudo mkdir -p /var/www
cd /var/www

# Clone repository (you'll need to update this with your repo URL)
echo ""
echo "Step 9: Cloning repository..."
read -p "Enter your Git repository URL: " REPO_URL
if [ -d "app-antigravity" ]; then
    echo "Directory already exists. Skipping clone."
else
    sudo git clone "$REPO_URL" app-antigravity
    sudo chown -R $USER:$USER app-antigravity
fi

cd app-antigravity

# Setup environment variables
echo ""
echo "Step 10: Setting up environment variables..."
if [ ! -f .env ]; then
    echo "Creating .env file..."
    read -p "Enter your OpenAI API Key: " OPENAI_KEY
    read -p "Enter your OpenRouter API Key: " OPENROUTER_KEY
    read -p "Enter your Apify API Token: " APIFY_TOKEN
    
    cat > .env << EOF
OPENAI_API_KEY=$OPENAI_KEY
OPENROUTER_API_KEY=$OPENROUTER_KEY
APIFY_API_TOKEN=$APIFY_TOKEN
NODE_ENV=production
EOF
    echo ".env file created successfully!"
else
    echo ".env file already exists. Skipping."
fi

# Setup backend
echo ""
echo "Step 11: Setting up backend..."
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
cd ..

# Setup frontend
echo ""
echo "Step 12: Setting up frontend..."
cd frontend
npm install

# Ask if user wants to build now
read -p "Build frontend now? (y/n): " BUILD_NOW
if [ "$BUILD_NOW" = "y" ]; then
    npm run build
fi
cd ..

# Create PM2 ecosystem file
echo ""
echo "Step 13: Creating PM2 configuration..."
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [
    {
      name: 'backend',
      cwd: '/var/www/app-antigravity/backend',
      script: '/var/www/app-antigravity/backend/venv/bin/uvicorn',
      args: 'main:app --host 0.0.0.0 --port 8000',
      env: {
        PYTHONPATH: '/var/www/app-antigravity',
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
    },
    {
      name: 'frontend',
      cwd: '/var/www/app-antigravity/frontend',
      script: 'npm',
      args: 'start',
      env: {
        NODE_ENV: 'production',
        PORT: 3000,
      },
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
    }
  ]
};
EOF

# Configure Nginx
echo ""
echo "Step 14: Configuring Nginx..."
read -p "Enter your domain name (or press Enter to skip): " DOMAIN

if [ -n "$DOMAIN" ]; then
    sudo tee /etc/nginx/conf.d/app-antigravity.conf > /dev/null << EOF
# Backend API
server {
    listen 80;
    server_name api.$DOMAIN;

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}

# Frontend
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF
    
    # Test and restart Nginx
    sudo nginx -t
    sudo systemctl restart nginx
    sudo systemctl enable nginx
    
    echo "Nginx configured for domain: $DOMAIN"
else
    echo "Skipping Nginx configuration. You can configure it manually later."
fi

# Start application
echo ""
echo "Step 15: Starting application with PM2..."
read -p "Start the application now? (y/n): " START_NOW
if [ "$START_NOW" = "y" ]; then
    pm2 start ecosystem.config.js
    pm2 save
    
    # Setup PM2 startup
    echo ""
    echo "Setting up PM2 to start on boot..."
    pm2 startup
    echo "Please run the command above if it was displayed."
fi

echo ""
echo "========================================="
echo "Deployment Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. If you configured a domain, point your DNS to this server's IP"
echo "2. Install SSL certificate: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN -d api.$DOMAIN"
echo "3. Check application status: pm2 status"
echo "4. View logs: pm2 logs"
echo ""
echo "Your application should be accessible at:"
if [ -n "$DOMAIN" ]; then
    echo "  Frontend: http://$DOMAIN"
    echo "  Backend API: http://api.$DOMAIN"
else
    echo "  Frontend: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3000"
    echo "  Backend API: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):8000"
fi
echo ""

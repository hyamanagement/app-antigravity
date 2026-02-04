# AWS Linux Server Deployment Guide

This guide provides step-by-step instructions for deploying the Video Script Generator application on an Amazon AWS Linux server.

## Prerequisites

- AWS account with EC2 access
- SSH key pair for server access
- Domain name (optional, for production)

---

## 1. Server Setup

### Launch EC2 Instance

**Recommended Specifications:**
- **Instance Type**: `t3.medium` or larger (2 vCPU, 4GB RAM minimum)
- **AMI**: Amazon Linux 2023 or Ubuntu 22.04 LTS
- **Storage**: 20GB+ SSD
- **Security Group Rules**:
  - SSH (22) - Your IP
  - HTTP (80) - 0.0.0.0/0
  - HTTPS (443) - 0.0.0.0/0
  - Custom TCP (3000) - 0.0.0.0/0 (for testing, remove in production)
  - Custom TCP (8000) - 0.0.0.0/0 (for testing, remove in production)

### Connect to Server

```bash
ssh -i your-key.pem ec2-user@your-server-ip
# or for Ubuntu:
ssh -i your-key.pem ubuntu@your-server-ip
```

---

## 2. Install System Dependencies

### For Amazon Linux 2023

```bash
# Update system
sudo yum update -y

# Install Python 3.11+
sudo yum install python3.11 python3.11-pip -y

# Install Node.js 18+ and npm
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install nodejs -y

# Install Git
sudo yum install git -y

# Install Nginx (reverse proxy)
sudo yum install nginx -y

# Install PM2 (process manager)
sudo npm install -g pm2

# Install build tools (for some Python packages)
sudo yum groupinstall "Development Tools" -y
```

### For Ubuntu 22.04

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install Node.js 18+ and npm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install nodejs -y

# Install Git
sudo apt install git -y

# Install Nginx
sudo apt install nginx -y

# Install PM2
sudo npm install -g pm2

# Install build tools
sudo apt install build-essential -y
```

---

## 3. Clone and Setup Application

```bash
# Create application directory
sudo mkdir -p /var/www
cd /var/www

# Clone repository (replace with your repo URL)
sudo git clone https://github.com/hyamanagement/app-antigravity.git
sudo chown -R $USER:$USER app-antigravity
cd app-antigravity

# Create .env file
cp .env.example .env  # if you have one, otherwise create manually
nano .env
```

### Configure Environment Variables

Add the following to `.env`:

```bash
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
APIFY_API_TOKEN=your_apify_token_here

# Server Configuration
NODE_ENV=production
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://your-domain.com
```

---

## 4. Setup Backend (FastAPI)

```bash
cd /var/www/app-antigravity/backend

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Test backend
uvicorn main:app --host 0.0.0.0 --port 8000
# Press Ctrl+C to stop after verifying it works
```

### Create PM2 Process for Backend

```bash
# Deactivate venv first
deactivate

# Create PM2 ecosystem file
cat > /var/www/app-antigravity/ecosystem.config.js << 'EOF'
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
```

---

## 5. Setup Frontend (Next.js)

```bash
cd /var/www/app-antigravity/frontend

# Install dependencies
npm install

# Create production build
npm run build

# Test production build
npm start
# Press Ctrl+C to stop after verifying it works
```

### Update Frontend API Configuration

Edit `frontend/lib/api.ts` to use environment variable for backend URL:

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

Create `frontend/.env.production`:

```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## 6. Configure Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/conf.d/app-antigravity.conf
```

Add the following configuration:

```nginx
# Backend API
server {
    listen 80;
    server_name api.yourdomain.com;  # or use IP for testing

    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }
}

# Frontend
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;  # or use IP for testing

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Test and Start Nginx

```bash
# Test configuration
sudo nginx -t

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Restart if already running
sudo systemctl restart nginx
```

---

## 7. Start Application with PM2

```bash
cd /var/www/app-antigravity

# Start both backend and frontend
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
# Follow the command it outputs

# Check status
pm2 status

# View logs
pm2 logs backend
pm2 logs frontend
```

---

## 8. SSL Certificate (Production - Optional but Recommended)

### Install Certbot

**Amazon Linux:**
```bash
sudo yum install certbot python3-certbot-nginx -y
```

**Ubuntu:**
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Obtain SSL Certificate

```bash
# For both domains
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com -d api.yourdomain.com

# Follow the prompts
# Certbot will automatically update your Nginx configuration
```

### Auto-renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up a cron job for renewal
```

---

## 9. Firewall Configuration (Optional but Recommended)

```bash
# For Amazon Linux (firewalld)
sudo systemctl start firewalld
sudo systemctl enable firewalld
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --reload

# For Ubuntu (ufw)
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

---

## 10. Monitoring and Maintenance

### PM2 Monitoring

```bash
# Real-time monitoring
pm2 monit

# View logs
pm2 logs

# Restart services
pm2 restart all
pm2 restart backend
pm2 restart frontend

# Stop services
pm2 stop all
```

### Update Application

```bash
cd /var/www/app-antigravity

# Pull latest changes
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Update frontend
cd ../frontend
npm install
npm run build

# Restart services
pm2 restart all
```

### View Nginx Logs

```bash
# Access logs
sudo tail -f /var/log/nginx/access.log

# Error logs
sudo tail -f /var/log/nginx/error.log
```

---

## 11. Troubleshooting

### Backend Not Starting

```bash
# Check logs
pm2 logs backend

# Test manually
cd /var/www/app-antigravity/backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Check if port is in use
sudo lsof -i :8000
```

### Frontend Not Starting

```bash
# Check logs
pm2 logs frontend

# Test manually
cd /var/www/app-antigravity/frontend
npm start

# Check if port is in use
sudo lsof -i :3000
```

### Nginx Issues

```bash
# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx
```

### Check Disk Space

```bash
df -h
```

### Check Memory Usage

```bash
free -h
htop  # install with: sudo yum install htop -y
```

---

## 12. Security Best Practices

1. **Keep system updated**:
   ```bash
   sudo yum update -y  # Amazon Linux
   sudo apt update && sudo apt upgrade -y  # Ubuntu
   ```

2. **Use environment variables**: Never commit API keys to Git

3. **Enable firewall**: Only allow necessary ports

4. **Use SSL certificates**: Always use HTTPS in production

5. **Regular backups**: Backup your `.env` file and database (if any)

6. **Monitor logs**: Regularly check PM2 and Nginx logs

7. **Limit SSH access**: Use key-based authentication only

8. **Set up fail2ban** (optional):
   ```bash
   sudo yum install fail2ban -y  # Amazon Linux
   sudo apt install fail2ban -y  # Ubuntu
   sudo systemctl start fail2ban
   sudo systemctl enable fail2ban
   ```

---

## Quick Reference Commands

```bash
# PM2
pm2 status              # Check status
pm2 restart all         # Restart all services
pm2 logs               # View logs
pm2 monit              # Monitor resources

# Nginx
sudo systemctl restart nginx    # Restart
sudo nginx -t                   # Test config
sudo systemctl status nginx     # Check status

# Application
cd /var/www/app-antigravity
git pull                        # Update code
pm2 restart all                 # Restart services

# System
df -h                          # Check disk space
free -h                        # Check memory
htop                           # Monitor processes
```

---

## Cost Estimation (AWS)

**Monthly costs for t3.medium instance:**
- EC2 Instance: ~$30-40/month
- Storage (20GB): ~$2/month
- Data Transfer: Variable (first 1GB free)
- **Total**: ~$35-45/month

**To reduce costs:**
- Use t3.small for lower traffic (~$15/month)
- Use AWS Free Tier (first 12 months)
- Stop instance when not in use (development)

---

## Support

For issues or questions:
1. Check PM2 logs: `pm2 logs`
2. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify environment variables in `.env`
4. Ensure all API keys are valid

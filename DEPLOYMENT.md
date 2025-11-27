# 🚀 Deployment Guide

Since this application uses **GDAL** (geospatial libraries), the best way to host it is using **Docker**. This ensures all complex dependencies work perfectly on any server.

## Option 1: Deploy to Render (Easiest Cloud Option)

Render is a cloud platform that supports Docker and has a free tier.

1. **Push your code** to GitHub (you already did this!).
2. **Sign up** at [render.com](https://render.com).
3. Click **"New +"** → **"Web Service"**.
4. Connect your GitHub repository (`Pokhara-Multi-Hazard-Monitoring`).
5. Select **"Docker"** as the Runtime (it should auto-detect the Dockerfile).
6. Choose a plan (Free or Starter).
7. Click **"Create Web Service"**.

Render will build your Docker image and deploy it. Your API will be available at `https://your-app-name.onrender.com`.

**Note:** The Free tier spins down after inactivity. For production, use the Starter plan ($7/mo).

---

## Option 2: Deploy to a VPS (DigitalOcean, AWS EC2, Linode)

This gives you full control and is cheaper for heavy processing.

### 1. Get a Server
- Ubuntu 22.04 or 24.04
- At least 2GB RAM (4GB recommended for ML training)

### 2. Install Docker
SSH into your server and run:
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install -y docker-compose-plugin
```

### 3. Clone & Run
```bash
# Clone your repo
git clone https://github.com/Kafle33/Pokhara-Multi-Hazard-Monitoring.git
cd Pokhara-Multi-Hazard-Monitoring

# Start the application
sudo docker compose up -d --build
```

Your app is now running at `http://YOUR_SERVER_IP:8000`!

### 4. (Optional) Setup Domain & SSL
To get `https://yourdomain.com`, use Nginx and Certbot:
```bash
sudo apt install nginx certbot python3-certbot-nginx
```
Configure Nginx to proxy pass to port 8000.

---

## Option 3: Run Locally with Docker

If you have Docker Desktop installed on your computer:

```bash
docker compose up --build
```

This is cleaner than using `venv` because it isolates all system libraries.

---

## ⚠️ Important Notes

1. **Data Persistence**:
   - In **Option 2 (VPS)**, data in `data/` is persisted automatically via volumes.
   - In **Option 1 (Render)**, the filesystem is ephemeral (deleted on restart). To save outputs permanently on Render, you need to add a **Disk** (paid feature) and mount it to `/app/data`.

2. **Performance**:
   - ML training (Random Forest) requires CPU/RAM.
   - If processing fails on the Free tier, upgrade to a plan with 2GB+ RAM.

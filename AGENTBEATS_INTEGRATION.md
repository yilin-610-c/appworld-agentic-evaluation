# AgentBeats Integration Guide

This guide follows the [AgentBeats blog-3](https://docs.agentbeats.org/Blogs/blog-3/) to integrate your AppWorld Green Agent with the AgentBeats platform.

## Overview

Integration with AgentBeats takes three main steps:
1. **Wrap your agent with an AgentBeats Controller** (local setup)
2. **Deploy your agent** (requires cloud infrastructure)
3. **Publish on AgentBeats** (web form)

## Step 1: AgentBeats Controller (✅ COMPLETED)

### What We've Done

✅ **Installed earthshaker**
```bash
pip install earthshaker
```

✅ **Created run.sh script**
- Location: `/appworld_green_agent/run.sh`
- Reads `$HOST` and `$AGENT_PORT` environment variables
- Starts the green agent with these parameters

✅ **Modified CLI to support host/port**
- `python main.py green --host HOST --port PORT`
- Compatible with AgentBeats controller

### Test Locally

#### 1. Start the Controller

```bash
cd /home/lyl610/green1112/appworld_green_agent
agentbeats run_ctrl
```

This will:
- Launch the AgentBeats controller
- Show a local management UI
- Automatically start your agent using `run.sh`
- Provide a proxy URL for accessing your agent

#### 2. Access the Management UI

Once the controller starts, you should see output like:
```
AgentBeats Controller running on http://localhost:8000
Agent proxy URL: http://localhost:8000/proxy
```

Open the management UI in your browser:
```
http://localhost:8000
```

#### 3. Verify Agent Card

Test that the agent card is accessible through the proxy:
```bash
curl http://localhost:8000/proxy/.well-known/agent-card.json
```

### Expected Controller Features

The AgentBeats Controller provides:
1. **Service API**: Display and manage agent process state
2. **Auto-restart**: Easy agent reset between test runs
3. **Proxy**: Routes requests to your agent
4. **Management UI**: Debug and monitor your agent

---

## Step 2: Deploy Your Agent (🌐 YOUR ACTION REQUIRED)

To make your agent accessible over the network, you need to deploy it with a public IP and HTTPS.

### Option A: Manual Deployment (Traditional)

#### Requirements:
- Cloud VM (e.g., AWS EC2, Google Cloud Compute Engine, Azure VM)
- Public IP address or domain name
- SSL certificate for HTTPS

#### Steps:

1. **Provision a Cloud VM**
   ```bash
   # Example: Google Cloud
   gcloud compute instances create appworld-agent \
     --machine-type=e2-medium \
     --image-family=ubuntu-2204-lts \
     --image-project=ubuntu-os-cloud
   ```

2. **Configure Public IP/Domain**
   - Assign a static IP
   - Or configure a domain name pointing to your VM

3. **Install Dependencies on VM**
   ```bash
   # SSH into your VM
   ssh your-vm
   
   # Install Python 3.13
   # Install conda/miniconda
   # Install project dependencies
   pip install -r requirements.txt
   pip install earthshaker
   ```

4. **Transfer Your Project**
   ```bash
   # From your local machine
   scp -r appworld_green_agent your-vm:~/
   ```

5. **Obtain SSL Certificate**
   ```bash
   # On your VM, using Let's Encrypt
   sudo apt install certbot
   sudo certbot certonly --standalone -d your-domain.com
   ```

6. **Configure Nginx (Optional)**
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

7. **Start the Controller**
   ```bash
   cd appworld_green_agent
   agentbeats run_ctrl
   ```

8. **Make it Persistent (Optional)**
   ```bash
   # Create a systemd service
   sudo nano /etc/systemd/system/agentbeats.service
   ```

   ```ini
   [Unit]
   Description=AgentBeats Controller
   After=network.target

   [Service]
   Type=simple
   User=your-user
   WorkingDirectory=/home/your-user/appworld_green_agent
   ExecStart=/home/your-user/miniconda3/envs/appworld_agent_py313/bin/agentbeats run_ctrl
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl enable agentbeats
   sudo systemctl start agentbeats
   ```

### Option B: Containerized Deployment (Modern) ⭐ RECOMMENDED

#### Using Google Cloud Run

1. **Create a Procfile**
   ```bash
   cd /home/lyl610/green1112/appworld_green_agent
   echo "web: agentbeats run_ctrl" > Procfile
   ```

2. **Generate requirements.txt**
   ```bash
   pip freeze > requirements.txt
   ```

3. **Build with Google Cloud Buildpacks**
   ```bash
   # Install gcloud CLI if not already installed
   # https://cloud.google.com/sdk/docs/install

   # Authenticate
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID

   # Build and deploy
   gcloud run deploy appworld-green-agent \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars OPENAI_API_KEY=your-key-here
   ```

4. **Cloud Run automatically provides**:
   - HTTPS endpoint
   - Auto-scaling
   - No manual certificate management
   - Easy updates

#### Your Controller URL

After deployment, you'll get a URL like:
```
https://appworld-green-agent-xxxxxxxxx-uc.a.run.app
```

This is your **public controller URL** needed for Step 3.

---

## Step 3: Publish on AgentBeats (📝 YOUR ACTION REQUIRED)

Once your agent is deployed and publicly accessible, publish it on AgentBeats:

### Steps:

1. **Visit AgentBeats Website**
   - Go to the AgentBeats platform (URL to be provided by AgentBeats)
   - Look for "Publish Agent" or similar option

2. **Fill Out the Form**
   
   Required information:
   - **Controller URL**: Your public HTTPS URL from Step 2
     - Example: `https://your-domain.com` or
     - `https://appworld-green-agent-xxx.a.run.app`
   
   Optional information:
   - Agent name: "AppWorld Green Agent"
   - Description: "A2A-compatible green agent for AppWorld benchmark assessment"
   - Tags: "benchmark", "appworld", "evaluation", "green-agent"
   - Documentation link: Your GitHub repo or docs

3. **Submit**
   - Your agent will be registered on AgentBeats
   - Others can now discover and interact with your agent
   - You can run assessments through the platform

### After Publishing

Your agent will be:
- ✅ Discoverable on AgentBeats platform
- ✅ Accessible for assessments by other users
- ✅ Integrated with AgentBeats dashboard for results
- ✅ Part of the AgentBeats ecosystem

---

## Testing Your Deployment

Before publishing, verify your deployed agent works:

### 1. Test Agent Card Access

```bash
curl https://your-controller-url/proxy/.well-known/agent-card.json
```

Should return your agent card JSON.

### 2. Test Controller Status

```bash
curl https://your-controller-url/status
```

Should show agent process status.

### 3. Test with Local Launcher

Modify your local launcher to use the deployed agent:

```python
green_url = "https://your-controller-url/proxy"
```

Run an evaluation to ensure everything works.

---

## Security Considerations

### Authentication (Future Enhancement)

Currently, the deployed agent has no authentication, which may be vulnerable to:
- DoS attacks
- Excessive LLM API usage
- Unauthorized access

**Mitigation strategies**:
1. Set API rate limits on your cloud provider
2. Monitor LLM API usage and set billing alerts
3. Consider adding authentication layer (not covered in blog-3)
4. Use AgentBeats hosted mode when available (future feature)

### Environment Variables

Make sure to securely configure:
- `OPENAI_API_KEY`: Your OpenAI key
- `APPWORLD_ROOT`: Path to AppWorld data

For Cloud Run:
```bash
gcloud run services update appworld-green-agent \
  --set-env-vars OPENAI_API_KEY=your-key \
  --set-env-vars APPWORLD_ROOT=/workspace/appworld
```

---

## Troubleshooting

### Controller Won't Start
```bash
# Check if port is already in use
lsof -i :8000

# Check run.sh permissions
ls -l run.sh
chmod +x run.sh

# Check agent starts manually
python main.py green --host localhost --port 9001
```

### Agent Not Accessible After Deployment
- Check firewall rules allow traffic on port 8000 (or your configured port)
- Verify SSL certificate is valid
- Check agent logs for errors
- Ensure environment variables are set

### Cloud Run Build Fails
- Verify `requirements.txt` is up to date
- Check Python version compatibility (3.13)
- Review build logs in Cloud Console

---

## Summary

### ✅ Completed (Local)
1. Installed earthshaker
2. Created `run.sh` script
3. Modified CLI to support host/port parameters
4. Ready for local controller testing

### 🌐 To Do (Your Action)
1. Test locally with `agentbeats run_ctrl`
2. Choose deployment method (VM or Cloud Run)
3. Deploy to cloud with public HTTPS URL
4. Publish on AgentBeats platform

### 📚 Resources
- [AgentBeats Blog-3](https://docs.agentbeats.org/Blogs/blog-3/)
- [AgentBeats Documentation](https://docs.agentbeats.org/)
- [Google Cloud Run Docs](https://cloud.google.com/run/docs)
- [Earthshaker on PyPI](https://pypi.org/project/earthshaker/)

---

**Next Steps**: 
1. Test locally: `agentbeats run_ctrl`
2. Deploy to cloud (choose your platform)
3. Publish on AgentBeats website

Good luck! 🚀



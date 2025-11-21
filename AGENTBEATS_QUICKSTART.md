# AgentBeats Integration - Quick Start

## ✅ What's Been Done (Already Completed)

We've prepared everything needed for AgentBeats integration:

1. ✅ Installed `earthshaker` package
2. ✅ Created `run.sh` script
3. ✅ Modified `main.py` to support `--host` and `--port` parameters

## 🧪 Test Locally (5 minutes)

Try the AgentBeats controller locally:

```bash
cd /home/lyl610/green1112/appworld_green_agent

# Start the controller
agentbeats run_ctrl
```

Open your browser to `http://localhost:8000` to see the management UI.

Test the agent card:
```bash
curl http://localhost:8000/proxy/.well-known/agent-card.json
```

**Stop the controller**: Press Ctrl+C

---

## 🌐 Deploy to Cloud (Your Action Required)

### Option 1: Google Cloud Run (Easiest) ⭐

```bash
# 1. Create Procfile
echo "web: agentbeats run_ctrl" > Procfile

# 2. Generate requirements
pip freeze > requirements.txt

# 3. Deploy (replace YOUR_PROJECT_ID and your-key)
gcloud run deploy appworld-green-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your-key-here
```

You'll get a URL like: `https://appworld-green-agent-xxx.a.run.app`

### Option 2: Your Own VM

See the full guide in `AGENTBEATS_INTEGRATION.md` for:
- VM setup
- SSL certificate
- Nginx configuration
- Systemd service

---

## 📝 Publish on AgentBeats

1. Visit the AgentBeats website
2. Find "Publish Agent" form
3. Enter your controller URL: `https://your-deployment-url`
4. Fill in optional details (name, description, tags)
5. Submit!

---

## 📚 Full Documentation

- **Complete Guide**: `AGENTBEATS_INTEGRATION.md`
- **AgentBeats Blog-3**: https://docs.agentbeats.org/Blogs/blog-3/

---

## Need Help?

**Local testing issues?**
```bash
# Verify run.sh is executable
chmod +x run.sh

# Test agent manually
python main.py green --host localhost --port 9001
```

**Deployment issues?**
- Check `AGENTBEATS_INTEGRATION.md` for detailed troubleshooting
- Ensure OPENAI_API_KEY is set
- Verify firewall/security group settings

---

**Status**: ✅ Ready for local testing and deployment!



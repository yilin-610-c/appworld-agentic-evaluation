# 🚀 Ready to Deploy!

## ✅ Files Created

All necessary files for Cloud Run deployment have been prepared:

### 1. **Procfile** ✅
```
web: agentbeats run_ctrl
```
Tells Cloud Run to start the AgentBeats controller.

### 2. **requirements.txt** ✅
- Contains 138 Python packages
- **Modified**: Removed problematic `-e git+` appworld line
- Added explanatory comments

### 3. **.gcloudignore** ✅
Excludes unnecessary files from deployment:
- Git files
- Local appworld directory (too large)
- Python cache
- Development files
- Documentation files

### 4. **run.sh** ✅ (Already existed)
Script that starts your green agent.

---

## ⚠️ Important: AppWorld Data Issue

**The Challenge**: AppWorld requires large data files (Git LFS) that cannot be easily deployed to Cloud Run.

**For Your First Deployment**: 
- Deploy **without** full AppWorld functionality (for testing infrastructure)
- The controller will run, but won't be able to execute real AppWorld tasks
- This is okay for verifying the deployment works!

**See** `CLOUD_RUN_DEPLOYMENT.md` for solutions to include AppWorld data.

---

## 🎯 Deployment Command

### Prerequisites

1. **Install Google Cloud CLI** (if not already):
   ```bash
   # https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate**:
   ```bash
   gcloud auth login
   ```

3. **Set your project**:
   ```bash
   gcloud config set project YOUR_PROJECT_ID
   ```

4. **Enable APIs** (first time only):
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

### Deploy Command

```bash
cd /home/lyl610/green1112/appworld_green_agent

gcloud run deploy appworld-green-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 5 \
  --set-env-vars OPENAI_API_KEY=sk-your-actual-key-here
```

**Replace**: `sk-your-actual-key-here` with your real OpenAI API key!

### What This Does:

- `--source .`: Deploy from current directory
- `--region us-central1`: Deploy to US Central region
- `--allow-unauthenticated`: Anyone can access (needed for AgentBeats)
- `--memory 2Gi`: Allocate 2GB RAM
- `--cpu 2`: Use 2 CPU cores
- `--timeout 300`: 5 minute timeout
- `--max-instances 5`: Maximum 5 concurrent instances
- `--set-env-vars`: Set environment variables

---

## 📋 Deployment Steps

### Step 1: Verify Prerequisites

```bash
# Check gcloud is installed
gcloud --version

# Check you're authenticated
gcloud auth list

# Check project is set
gcloud config get-value project
```

### Step 2: Review Files

```bash
cd /home/lyl610/green1112/appworld_green_agent

# Check Procfile
cat Procfile

# Check requirements.txt (should NOT have -e git line)
grep "appworld" requirements.txt
```

### Step 3: Deploy!

Run the deployment command above.

You'll see output like:
```
Building using Buildpacks...
✓ Creating Container Repository
✓ Uploading sources
✓ Building Container
✓ Pushing Container
✓ Deploying Revision
✓ Routing traffic

Service [appworld-green-agent] revision [appworld-green-agent-00001] has been deployed
and is serving 100 percent of traffic.
Service URL: https://appworld-green-agent-xxxxxxxxxx-uc.a.run.app
```

### Step 4: Save Your URL!

**This URL is important!** It's your public controller endpoint.

Example:
```
https://appworld-green-agent-abc123xyz-uc.a.run.app
```

### Step 5: Test Deployment

```bash
# Test the controller (in browser or curl)
# In WSL, you can use curl:
curl https://your-deployed-url

# Test agent card access
curl https://your-deployed-url/proxy/.well-known/agent-card.json
```

---

## 🎉 After Successful Deployment

### What You'll Have:

✅ **Public HTTPS URL** for your controller
✅ **AgentBeats controller** running in the cloud
✅ **Automatic scaling** (scales to zero when not used)
✅ **HTTPS** automatically configured
✅ **Logs** available in Google Cloud Console

### What Won't Work Yet:

❌ **Real AppWorld tasks** (need to add data - see CLOUD_RUN_DEPLOYMENT.md)

### Next Steps:

1. **Publish on AgentBeats**:
   - Go to AgentBeats website
   - Fill in the publish form
   - Enter your Cloud Run URL
   - Submit!

2. **Monitor Your Deployment**:
   - View logs: `gcloud run logs read --service appworld-green-agent`
   - View metrics in Cloud Console
   - Set up billing alerts

3. **Add AppWorld Data** (when ready):
   - See `CLOUD_RUN_DEPLOYMENT.md`
   - Choose Option 3 (Cloud Storage) or Option 4 (Docker image)

---

## 💰 Cost Estimates

### Cloud Run Pricing (as of 2024):

- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GiB-second
- **Requests**: First 2 million free per month
- **Free tier**: Includes generous free quotas

### Typical Monthly Cost:

- **Light usage** (testing): $0 - $5
- **Moderate usage** (100 requests/day): $5 - $20
- **Heavy usage** (1000+ requests/day): $50+

**Plus**: OpenAI API costs (separate)

### Set Budget Alert:

```bash
# In Google Cloud Console
# Billing → Budgets & alerts → Create Budget
```

---

## 🐛 Troubleshooting

### Build Fails

**Error**: "Could not find a version that satisfies the requirement appworld"
→ **Fix**: Make sure the `-e git+` line is removed from requirements.txt

**Error**: "Cloud Build timed out"
→ **Fix**: The build is too large. Consider using pre-built Docker image.

### Deployment Succeeds but Controller Won't Start

**Check logs**:
```bash
gcloud run logs read --service appworld-green-agent --limit 50
```

**Common issues**:
- Missing environment variables
- Port configuration (Cloud Run uses $PORT, should be handled automatically)

### Can't Access the URL

- Check if service is public: `--allow-unauthenticated`
- Verify the URL is correct
- Check service status in Cloud Console

---

## 📚 Documentation

- **Deployment guide**: `CLOUD_RUN_DEPLOYMENT.md`
- **AgentBeats integration**: `AGENTBEATS_INTEGRATION.md`
- **Quick start**: `AGENTBEATS_QUICKSTART.md`

---

## ✨ Summary

**You're ready to deploy!** Just run:

```bash
gcloud run deploy appworld-green-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars OPENAI_API_KEY=your-key
```

**This will give you a public HTTPS URL that you can publish on AgentBeats!**

Good luck! 🚀



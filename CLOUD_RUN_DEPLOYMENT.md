# Cloud Run Deployment Guide

## ⚠️ Important: AppWorld Data Challenge

Before deploying, you need to understand a **critical issue**: AppWorld requires large data files that are not suitable for direct Cloud Run deployment.

### The Problem

1. **AppWorld uses Git LFS** for large data files
2. **Cloud Build may not handle Git LFS** properly
3. **Container size limit**: Cloud Run has container size limits
4. **Data location**: AppWorld expects data at `$APPWORLD_ROOT/data`

### Solutions

We have three options:

---

## Option 1: Deploy Without Full AppWorld Data (Testing Only) ⚡

**For initial testing**, deploy a version that can handle basic functionality but won't work with real AppWorld tasks.

### Steps:

1. **Modify requirements.txt** to remove the problematic appworld line:
   ```bash
   # Remove this line:
   -e git+https://github.com/StonyBrookNLP/appworld.git@...#egg=appworld
   
   # Add instead (if available on PyPI):
   appworld
   ```

2. **Deploy**:
   ```bash
   gcloud run deploy appworld-green-agent \
     --source . \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars OPENAI_API_KEY=your-key
   ```

3. **Limitations**: Won't work with actual AppWorld tasks, but controller will run.

---

## Option 2: Include Minimal AppWorld Data 📦

Include only a subset of tasks for demonstration.

### Steps:

1. **Create a minimal data directory**:
   ```bash
   mkdir -p appworld_minimal/data/tasks
   # Copy only a few tasks
   cp -r /home/lyl610/green1112/appworld/data/tasks/82e2fac_1 \
         appworld_minimal/data/tasks/
   ```

2. **Create .dockerignore** to exclude full appworld:
   ```
   appworld/
   !appworld_minimal/
   ```

3. **Modify run.sh** to use minimal data:
   ```bash
   export APPWORLD_ROOT=/workspace/appworld_minimal
   ```

4. **Deploy**: Same as Option 1

**Pros**: Works with a few tasks
**Cons**: Limited functionality

---

## Option 3: Use Cloud Storage (Production) 🌐

For production deployment with full AppWorld capabilities.

### Steps:

1. **Upload AppWorld data to Cloud Storage**:
   ```bash
   # Create bucket
   gsutil mb gs://your-project-appworld-data
   
   # Upload data
   gsutil -m cp -r /home/lyl610/green1112/appworld/data \
                  gs://your-project-appworld-data/
   ```

2. **Create startup script** that downloads data:
   ```bash
   # startup.sh
   #!/bin/bash
   if [ ! -d "/workspace/appworld/data" ]; then
       echo "Downloading AppWorld data..."
       gsutil -m cp -r gs://your-project-appworld-data/data \
                      /workspace/appworld/
   fi
   exec agentbeats run_ctrl
   ```

3. **Update Procfile**:
   ```
   web: bash startup.sh
   ```

4. **Grant permissions** to Cloud Run service account

**Pros**: Full functionality
**Cons**: More complex, longer startup time

---

## Option 4: Use Artifact Registry with Pre-built Image 🐳

Build a Docker image locally with all data, push to registry.

### Steps:

1. **Create Dockerfile**:
   ```dockerfile
   FROM python:3.13-slim
   
   WORKDIR /workspace
   
   # Copy appworld data
   COPY appworld /workspace/appworld
   
   # Copy project
   COPY . /workspace/app
   WORKDIR /workspace/app
   
   # Install dependencies
   RUN pip install -r requirements.txt
   
   # Set environment
   ENV APPWORLD_ROOT=/workspace/appworld
   ENV PORT=8080
   
   CMD ["agentbeats", "run_ctrl"]
   ```

2. **Build and push**:
   ```bash
   docker build -t gcr.io/YOUR_PROJECT/appworld-green-agent .
   docker push gcr.io/YOUR_PROJECT/appworld-green-agent
   ```

3. **Deploy from image**:
   ```bash
   gcloud run deploy appworld-green-agent \
     --image gcr.io/YOUR_PROJECT/appworld-green-agent \
     --region us-central1
   ```

**Pros**: Complete control
**Cons**: Large image size, manual builds

---

## Recommended Approach

### For Now: Option 1 (Test Deployment)

Deploy a basic version to verify the infrastructure works:

```bash
cd /home/lyl610/green1112/appworld_green_agent

# Fix requirements.txt (remove -e git line)
# Then deploy
gcloud run deploy appworld-green-agent-test \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=your-key \
  --memory 2Gi \
  --timeout 300
```

This will:
- ✅ Deploy the controller
- ✅ Test Cloud Run infrastructure
- ✅ Get a public HTTPS URL
- ❌ Won't work with actual AppWorld tasks yet

### For Production: Option 3 or 4

Once basic deployment works, implement full data solution.

---

## Deployment Checklist

### Before Deploying:

- [ ] Google Cloud CLI installed (`gcloud --version`)
- [ ] Authenticated (`gcloud auth login`)
- [ ] Project set (`gcloud config set project YOUR_PROJECT`)
- [ ] Cloud Run API enabled
- [ ] Billing enabled
- [ ] OpenAI API key ready

### Files Ready:

- [x] `Procfile` created
- [x] `requirements.txt` generated
- [ ] `requirements.txt` fixed (remove -e git line)
- [ ] `.gcloudignore` created (optional, to exclude large files)

### After Deploying:

- [ ] Test the deployed URL
- [ ] Check logs in Cloud Console
- [ ] Monitor costs
- [ ] Set up billing alerts

---

## Quick Deploy Command

Once requirements.txt is fixed:

```bash
gcloud run deploy appworld-green-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 5 \
  --set-env-vars OPENAI_API_KEY=sk-your-key-here
```

---

## Troubleshooting

### Build fails with "appworld not found"
→ Fix requirements.txt, remove `-e git+...` line

### Container too large
→ Use Option 3 (Cloud Storage) or Option 4 (pre-built image)

### Timeout during startup
→ Increase timeout: `--timeout 600`

### Out of memory
→ Increase memory: `--memory 4Gi`

---

## Next Steps

1. Decide which option to use
2. Fix requirements.txt
3. Run the deployment command
4. Test the deployed URL
5. Publish on AgentBeats with your Cloud Run URL

---

Need help with any of these steps? Check the error logs in Cloud Console or ask for assistance!



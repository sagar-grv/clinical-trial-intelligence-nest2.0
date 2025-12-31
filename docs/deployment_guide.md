# 🚀 Deployment Guide

This guide covers how to push your code to GitHub and deploy it to Streamlit Cloud.

## 📝 Prerequisites

- A GitHub account.
- A Streamlit Cloud account (you can sign up using GitHub).

## Step 1: Push Code to GitHub

I have already initialized a local Git repository and created a `.gitignore` file to keep your secrets and database safe.

Run the following commands in your terminal to upload the code:

1. **Stage and Commit Files**:

    ```bash
    git add .
    git commit -m "Initial commit of Clinical Trial Intelligence Platform"
    ```

2. **Create a Repository on GitHub**:
    - Go to [GitHub.com](https://github.com/new).
    - Name your repository (e.g., `clinical-trial-intelligence`).
    - **Important**: Choose **Private** if you have sensitive data, or **Public** for a portfolio.
    - Click "Create repository".

3. **Link and Push**:
    - Copy the commands under "…or push an existing repository from the command line".
    - It will look like this (replace `YOUR_USERNAME` and `REPO_NAME`):

    ```bash
    git remote add origin https://github.com/YOUR_USERNAME/REPO_NAME.git
    git branch -M main
    git push -u origin main
    ```

## Step 2: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**:
    - Visit [share.streamlit.io](https://share.streamlit.io/).
    - Log in with GitHub.

2. **Create App**:
    - Click **"New app"**.
    - Select "Use existing repo".
    - Choose your repository: `YOUR_USERNAME/clinical-trial-intelligence`.
    - Branch: `main`.
    - Main file path: `app.py`.

3. **Set Secrets (CRITICAL)**:
    - Before clicking "Deploy", click **"Advanced settings"**.
    - Go to the **"Secrets"** section.
    - You MUST add your API keys here, or the AI features will fail.
    - Format:

    ```toml
    gemini_api_key = "YOUR_GOOGLE_GEMINI_API_KEY"
    ```

4. **Launch**:
    - Click **"Deploy"**.
    - Wait a few minutes for the build to complete.

## ⚠️ Important Notes

- **Database**: This app uses SQLite (`clinical_trials.db`), which is a file-based database. **Streamlit Cloud resets the file system on every reboot.**
  - *Implication*: Your uploaded files and analysis history will DISAPPEAR if the app restarts or goes to sleep.
  - *Production Fix*: For persistent data, you must connect to an external database like **Supabase**, **Neon (PostgreSQL)**, or **Google Cloud SQL**.
- **Memory**: Free tier instances have limited RAM (1GB). Large Excel files might crash the app.

## ✅ Verification

Once deployed, verify:

1. Upload a small test file.
2. Check if the "Analysis in progress" bar appears.
3. Generate an AI email draft to confirm the API key is working.

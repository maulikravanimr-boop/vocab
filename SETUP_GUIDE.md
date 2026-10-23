# Direct Google Keep to GitHub Pages Automation

This setup uses GitHub Actions and `gkeepapi` to automatically pull new words from your Google Keep notes (`Gujarati wordbank` and `Urdu/Hindi wordbank`) and deploy them to GitHub Pages every day—without needing to open Gemini or Google Sheets.

---

### Step 1: Add Files to your GitHub Repository
Commit or upload these files to your GitHub repository root:
- `index.html`
- `sync_keep.py`
- `.github/workflows/keep_sync.yml`

---

### Step 2: Configure Repository Permissions
In your GitHub repository:
1. Go to **Settings** > **Actions** > **General**.
2. Under **Workflow permissions**, select **Read and write permissions**, then click **Save**.

---

### Step 3: Add Google Credentials in GitHub Secrets
1. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret** and add:
   - **Name**: `GOOGLE_EMAIL`
     **Value**: Your Google account email address.
   - **Name**: `GOOGLE_APP_PASSWORD`
     **Value**: A 16-character Google App Password (generate one at [Google Account Security > 2-Step Verification > App passwords](https://myaccount.google.com/apppasswords)).
   - *(Optional / If 2FA requires Master Token)*: `GOOGLE_MASTER_TOKEN`

---

### How it Works:
- **Daily Automatic Sync**: Every day at 10:30 AM IST (05:00 UTC), GitHub Actions logs into your Keep account, extracts new words from your notes, merges them into `index.html`, and commits the update.
- **Manual 1-Click Sync**: Go to the **Actions** tab in your GitHub repository, tap **Direct Keep Sync to GitHub Pages**, and click **Run workflow** anytime!

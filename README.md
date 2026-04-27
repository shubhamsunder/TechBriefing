# Zoomcar Daily AI & Marketplace Brief

An automated pipeline that aggregates, summarizes, and emails the latest news about AI tools and Marketplace competitors, tailored for Product Managers.

## How it works
1. **Aggregates:** Scrapes RSS feeds and Google News search queries.
2. **Summarizes:** Uses the Gemini 1.5 Flash API to parse raw text, filter the noise, and generate crisp 2-sentence PM-focused summaries.
3. **Emails:** Injects the data into a responsive HTML email and sends it via SMTP.
4. **Automates:** Hosted on GitHub Actions to run Daily (Mon-Sat 8:00 AM IST) and Weekly (Sun 8:00 AM IST).

## Setup Instructions

### 1. Create a Dedicated Email Account
You requested a random account. Since I cannot create an account automatically due to Google's captchas, please follow these steps:
1. Go to gmail.com and create a new free account (e.g., `zoomcar.briefs@gmail.com`).
2. Go to your Google Account Settings -> Security.
3. **CRITICAL STEP**: You MUST enable **2-Step Verification**. Google hides the "App Passwords" feature unless 2-Step Verification is fully turned on.
4. Once 2-Step Verification is on, search for **App Passwords** in the settings search bar.
5. Generate a new App Password for "Mail". You will get a 16-character password (e.g., `abcd efgh ijkl mnop`). Save this.

### 2. Get a Gemini API Key
1. Go to Google AI Studio (aistudio.google.com).
2. Create an API key. This is free for reasonable usage limits.

### 3. Deploy to GitHub
1. Create a new Private repository on your GitHub account.
2. Push all the files in this folder to that repository.
3. In your GitHub repository, go to **Settings > Secrets and variables > Actions**.
4. Click **New repository secret** and add the following 4 secrets:
    - `GEMINI_API_KEY`: Your Gemini API Key
    - `SMTP_EMAIL`: The new gmail address you created (e.g., `zoomcar.briefs@gmail.com`)
    - `SMTP_PASSWORD`: The 16-character App Password (no spaces)
    - `RECIPIENT_EMAIL`: Your personal or work email address where you want to receive the brief.

### 4. Running it
Once the secrets are in place, the GitHub actions will run automatically at 8:00 AM IST. 
You can also trigger them manually by going to the "Actions" tab in your repository, selecting the workflow, and clicking "Run workflow".

## Local Testing
To test this on your machine:
```bash
# Install dependencies
pip install -r requirements.txt

# Run the script manually
export GEMINI_API_KEY="your_api_key"
export SMTP_EMAIL="your_sender_email@gmail.com"
export SMTP_PASSWORD="your_app_password"

# For daily summary
python main.py --recipient "your_personal_email@gmail.com"

# For weekly summary
python main.py --weekly --recipient "your_personal_email@gmail.com"
```

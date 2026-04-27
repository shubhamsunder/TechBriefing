import os
import smtplib
import argparse
import feedparser
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from jinja2 import Environment, FileSystemLoader
import google.generativeai as genai
from bs4 import BeautifulSoup
import time
import json

# Define RSS feeds to pull from
FEEDS = {
    "AI_Tech": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        "https://www.artificialintelligence-news.com/feed/",
        "https://news.google.com/rss/search?q=AI+product+management+OR+LLM+updates&hl=en-US&gl=US&ceid=US:en"
    ],
    "Global_Marketplaces": [
        "https://skift.com/feed/",
        "https://www.phocuswire.com/rss",
        "https://news.google.com/rss/search?q=Airbnb+OR+Uber+OR+Turo+OR+Getaround+product+news+OR+earnings&hl=en-US&gl=US&ceid=US:en"
    ],
    "Indian_Startups": [
        "https://inc42.com/feed/",
        "https://entrackr.com/feed/",
        "https://news.google.com/rss/search?q=Flipkart+OR+MakeMyTrip+OR+Zoomcar+OR+Rapido+OR+Ola+product+news&hl=en-IN&gl=IN&ceid=IN:en"
    ]
}

def clean_html(raw_html):
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    return soup.get_text(separator=" ", strip=True)

def fetch_feed_data(timeframe_days):
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=timeframe_days)
    aggregated_data = {
        "AI_Tech": [],
        "Global_Marketplaces": [],
        "Indian_Startups": []
    }

    for category, urls in FEEDS.items():
        for url in urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                # Get published date
                published_time = entry.get("published_parsed", entry.get("updated_parsed"))
                if not published_time:
                    continue
                
                dt = datetime(*published_time[:6], tzinfo=timezone.utc)
                if dt >= cutoff_date:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    summary = clean_html(entry.get("summary", ""))
                    
                    aggregated_data[category].append(f"Title: {title}\nLink: {link}\nSnippet: {summary[:300]}...")

    return aggregated_data

def summarize_with_gemini(raw_data, is_weekly):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not found. Sending raw data.")
        return None

    genai.configure(api_key=api_key)
    # Using Gemini 2.5 Flash Lite for highest free tier quota
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    period = "Weekly" if is_weekly else "Daily"
    
    final_parsed_data = {
        "ai_updates": [],
        "global_marketplaces": [],
        "indian_startups": []
    }
    
    # Process each category separately to stagger requests and avoid large payload/rate limits
    categories = [
        ("AI_Tech", "ai_updates", "Top 5 AI Technology & PM updates"),
        ("Global_Marketplaces", "global_marketplaces", "Top 5 Global Marketplace updates (Mobility/Travel like Turo, Airbnb, Uber)"),
        ("Indian_Startups", "indian_startups", "Top 5 Indian Startups & Marketplaces updates")
    ]
    
    for raw_key, json_key, focus in categories:
        if not raw_data.get(raw_key):
            continue
            
        print(f"Summarizing category: {raw_key}...")
        prompt = f"""
You are an expert AI assistant curating a {period} newsletter for a Supply-side Product Manager at Zoomcar.
Your goal is to review the following raw news items and extract the most relevant, high-impact news.

Filter out noise and select: {focus}.
For each selected item, write a crisp, 2-sentence summary highlighting WHY a PM should care. Include the original link.

Format the output EXACTLY as a JSON array of objects with keys: "title", "summary", "link".
Example:
[
  {{"title": "...", "summary": "...", "link": "..."}}
]

Raw Data:
{raw_data[raw_key]}
"""
        try:
            response = model.generate_content(prompt)
            text_response = response.text
            # Strip any markdown json block formatting if present
            if text_response.startswith("```json"):
                text_response = text_response[7:-3].strip()
            elif text_response.startswith("```"):
                text_response = text_response[3:-3].strip()
                
            parsed = json.loads(text_response)
            if isinstance(parsed, list):
                final_parsed_data[json_key] = parsed
            elif isinstance(parsed, dict) and json_key in parsed:
                final_parsed_data[json_key] = parsed[json_key]
                
        except Exception as e:
            print(f"Error during summarization for {raw_key}: {e}")
            
        # Stagger the requests by 15 seconds to strictly avoid the rate limits
        print("Waiting 15 seconds before the next API call to respect rate limits...")
        time.sleep(15)

    return final_parsed_data

def send_email(html_content, recipient_email, is_weekly):
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")
    
    if not sender_email or not sender_password:
        print("SMTP_EMAIL or SMTP_PASSWORD not set. Cannot send email.")
        return
        
    msg = EmailMessage()
    period = "Weekly" if is_weekly else "Daily"
    msg['Subject'] = f"Shubham's Agent - {'Weekly' if is_weekly else 'Daily'} tech brief"
    msg['From'] = f"Zoomcar Brief <{sender_email}>"
    msg['To'] = recipient_email
    
    msg.set_content("Please enable HTML to view this email.")
    msg.add_alternative(html_content, subtype='html')

    try:
        # Using Gmail SMTP by default, but this works for many providers
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
        print(f"Email sent successfully to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

def main():
    parser = argparse.ArgumentParser(description="Run the AI/Marketplace News Aggregator")
    parser.add_argument("--weekly", action="store_true", help="Run the weekly summary (defaults to daily)")
    parser.add_argument("--recipient", type=str, required=True, help="Email address to send the brief to")
    args = parser.parse_args()

    timeframe_days = 7 if args.weekly else 1
    print(f"Fetching news for the last {timeframe_days} day(s)...")
    
    raw_data = fetch_feed_data(timeframe_days)
    
    # Check if we got any data
    total_articles = sum(len(items) for items in raw_data.values())
    if total_articles == 0:
        print("No new articles found in the given timeframe.")
        return

    print(f"Accumulated {total_articles} articles. Summarizing...")
    summary_json = summarize_with_gemini(raw_data, args.weekly)
    
    if not summary_json:
        print("Failed to generate summary.")
        return

    # Render HTML
    print("Rendering email template...")
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("email_template.html")
    
    html_output = template.render(
        is_weekly=args.weekly,
        ai_updates=summary_json.get("ai_updates", []),
        global_marketplaces=summary_json.get("global_marketplaces", []),
        indian_startups=summary_json.get("indian_startups", []),
        date=datetime.now().strftime("%B %d, %Y")
    )
    
    print("Sending email...")
    send_email(html_output, args.recipient, args.weekly)

if __name__ == "__main__":
    main()

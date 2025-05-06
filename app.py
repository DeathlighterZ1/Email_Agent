import streamlit as st
import requests
import json
import time
from datetime import datetime
import schedule
import threading

# Resend API key (replace with your actual key)
RESEND_API_KEY = st.secrets["RESEND_API_KEY"]

# Function to fetch cryptocurrency data with retry mechanism
def fetch_crypto_data(max_retries=3, retry_delay=5):
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": "bitcoin,ethereum",
        "vs_currencies": "usd",
        "include_24hr_change": "true"
    }
    
    for attempt in range(max_retries):
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:
            if attempt < max_retries - 1:  # Don't sleep on the last attempt
                st.warning(f"Rate limit hit. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                st.error("Rate limit exceeded. Please try again later.")
        else:
            st.error(f"Error fetching data: {response.status_code}")
            return None
    
    return None

# Function to send email using Resend API
def send_email(recipient, subject, html_content):
    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "Crypto Updates <onboarding@resend.dev>",  # Use Resend's default domain
        "to": recipient,
        "subject": subject,
        "html": html_content
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.status_code == 200, response.json()

# Function to create email content
def create_email_content(crypto_data):
    btc_price = crypto_data["bitcoin"]["usd"]
    btc_change = crypto_data["bitcoin"]["usd_24h_change"]
    eth_price = crypto_data["ethereum"]["usd"]
    eth_change = crypto_data["ethereum"]["usd_24h_change"]
    
    html = f"""
    <h2>Daily Cryptocurrency Update</h2>
    <p>Date: {datetime.now().strftime('%Y-%m-%d')}</p>
    <h3>Bitcoin (BTC)</h3>
    <p>Current Price: ${btc_price:,.2f}</p>
    <p>24h Change: {btc_change:.2f}%</p>
    <h3>Ethereum (ETH)</h3>
    <p>Current Price: ${eth_price:,.2f}</p>
    <p>24h Change: {eth_change:.2f}%</p>
    """
    return html

# Function to send daily updates
def send_daily_updates():
    subscribers = load_subscribers()
    if not subscribers:
        print("No subscribers to send emails to.")
        return
    
    crypto_data = fetch_crypto_data()
    if not crypto_data:
        print("Failed to fetch cryptocurrency data.")
        return
    
    email_content = create_email_content(crypto_data)
    subject = "Daily Cryptocurrency Update"
    
    for email in subscribers:
        success, response = send_email(email, subject, email_content)
        if success:
            print(f"Email sent successfully to {email}")
        else:
            print(f"Failed to send email to {email}: {response}")

# Save subscribers to file
def save_subscribers(subscribers):
    with open("subscribers.json", "w") as f:
        json.dump(subscribers, f)

# Load subscribers from file
def load_subscribers():
    try:
        with open("subscribers.json", "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Schedule the daily task
def run_scheduler():
    schedule.every().day.at("08:00").do(send_daily_updates)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

# Streamlit UI
def main():
    st.title("Cryptocurrency Email Updates")
    
    # Display current crypto rates
    with st.expander("Current Cryptocurrency Rates", expanded=True):
        crypto_data = fetch_crypto_data()
        if crypto_data:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Bitcoin (BTC)")
                st.write(f"Price: ${crypto_data['bitcoin']['usd']:,.2f}")
                change = crypto_data['bitcoin']['usd_24h_change']
                st.write(f"24h Change: {change:.2f}%")
                
            with col2:
                st.subheader("Ethereum (ETH)")
                st.write(f"Price: ${crypto_data['ethereum']['usd']:,.2f}")
                change = crypto_data['ethereum']['usd_24h_change']
                st.write(f"24h Change: {change:.2f}%")
    
    # Subscription form
    st.subheader("Subscribe to Daily Updates")
    email = st.text_input("Enter your email address:")
    
    if st.button("Subscribe"):
        if not email or "@" not in email:
            st.error("Please enter a valid email address.")
        else:
            subscribers = load_subscribers()
            if email in subscribers:
                st.info("You are already subscribed!")
            else:
                subscribers.append(email)
                save_subscribers(subscribers)
                st.success("Successfully subscribed to daily cryptocurrency updates!")
    
    # Display current subscribers
    with st.expander("Current Subscribers"):
        subscribers = load_subscribers()
        if subscribers:
            for email in subscribers:
                st.write(email)
        else:
            st.write("No subscribers yet.")
    
    # Manual send option (for testing)
    if st.button("Send Test Email"):
        send_daily_updates()
        st.success("Test emails sent!")

if __name__ == "__main__":
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Run the Streamlit app
    main()




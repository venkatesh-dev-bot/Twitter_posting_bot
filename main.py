import os
import time
import random
import logging
import tweepy
import streamlit as st
from datetime import datetime, timedelta
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("cryptoxpress_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CryptoXpress_TwitterBot")
logger.setLevel(logging.INFO)

# Tweet interval in minutes
TWEET_INTERVAL = 15

# Simulation mode (set to False to actually post to Twitter)
SIMULATION_MODE = False

# Initialize session state
if 'tweet_history' not in st.session_state:
    st.session_state.tweet_history = []
if 'last_posted' not in st.session_state:
    st.session_state.last_posted = None
if 'next_post_time' not in st.session_state:
    st.session_state.next_post_time = None
if 'bot_running' not in st.session_state:
    st.session_state.bot_running = False

# Twitter API credentials
TWITTER_API_KEY = os.getenv("consumer_key")
TWITTER_API_SECRET = os.getenv("consumer_secret")
TWITTER_ACCESS_TOKEN = os.getenv("access_token")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("access_token_secret")
TWITTER_BEARER_TOKEN = os.getenv("Bearer_token")

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

# Twitter client
@st.cache_resource
def get_twitter_client():
    try:
        return tweepy.Client(
            bearer_token=TWITTER_BEARER_TOKEN,
            consumer_key=TWITTER_API_KEY,
            consumer_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
    except Exception as e:
        logger.error(f"Failed to initialize Twitter client: {str(e)}")
        return None

# Gemini model
@st.cache_resource
def get_gemini_model():
    try:
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            api_key=GOOGLE_API_KEY,
            temperature=0.7,
            max_output_tokens=150
        )
    except Exception as e:
        logger.error(f"Failed to initialize Gemini model: {str(e)}")
        return None

# Content configuration
TOPICS = [
    "cryptocurrency market updates",
    "crypto payment solutions",
    "defi innovations",
    "crypto wallet security",
    "blockchain technology",
    "crypto market analysis",
    "crypto investment strategies",
    "crypto trading tips",
    "NFT marketplace trends",
    "fintech advancements",
    "crypto regulation updates",
    "digital banking innovations",
    "CryptoXpress features",
    "crypto-fiat conversion",
    "crypto mass adoption"
]

HASHTAGS = [
    "#CryptoXpress", "#CryptoPayments", "#Cryptocurrency",
    "#Blockchain", "#DeFi", "#DigitalBanking", "#FinTech",
    "#CryptoWallet", "#CryptoTrading", "#NFTs"
]

# Predefined tweets for fallback
FALLBACK_TWEETS = [
    "CryptoXpress offers seamless crypto-to-fiat conversions, making digital assets more accessible for everyday use. #CryptoXpress #FinTech",
    "Security is our priority at CryptoXpress. Our multi-layer protection keeps your digital assets safe. #CryptoXpress #CryptoWallet",
    "DeFi integration in CryptoXpress allows you to earn passive income while maintaining liquidity. #CryptoXpress #DeFi",
    "CryptoXpress simplifies blockchain complexity, making crypto accessible to everyone. #CryptoXpress #Cryptocurrency",
    "Our CryptoXpress wallet supports multiple cryptocurrencies, giving you flexibility in your digital asset management. #CryptoXpress #Blockchain"
]

def generate_tweet_content():
    """Generate tweet content"""
    try:
        # Try using AI model with direct message formatting
        if GOOGLE_API_KEY:
            model = get_gemini_model()
            if model:
                topic = random.choice(TOPICS)
                hashtag_list = ", ".join(HASHTAGS)
                
                prompt = f"""Create an engaging tweet about {topic} for CryptoXpress.
                Include insights relevant to crypto investors.
                Mention CryptoXpress naturally in the tweet.
                Include 1-2 hashtags from this list: {hashtag_list}
                Keep it under 240 characters.
                Only return the tweet content, no other text."""
                
                # Format the input for Google Generative AI
                messages = [{"role": "user", "content": prompt}]
                response = model.invoke(messages)
                content = response.content.strip()
                
                # Validate and clean up
                if content and len(content) <= 240:
                    # Add hashtag if none present
                    if not any(hashtag.lower() in content.lower() for hashtag in HASHTAGS):
                        content += " " + random.choice(HASHTAGS)
                    
                    # Truncate if too long
                    if len(content) > 240:
                        content = content[:237] + "..."
                        
                    return content, topic
    except Exception as e:
        logger.error(f"AI generation failed: {str(e)}")
    
    # Fallback to predefined tweets
    content = random.choice(FALLBACK_TWEETS)
    return content, "CryptoXpress features"

def post_tweet():
    """Post a tweet"""
    try:
        # Generate content
        tweet_content, topic = generate_tweet_content()
        
        # Simulation mode
        if SIMULATION_MODE:
            tweet_id = "sim_" + str(int(time.time()))
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"
            logger.info(f"SIMULATION MODE: Tweet would have been posted: {tweet_content[:30]}...")
        else:
            # Actual posting
            client = get_twitter_client()
            if not client:
                logger.error("Twitter client not available")
                return False
                
            response = client.create_tweet(text=tweet_content)
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/user/status/{tweet_id}"
            logger.info(f"Tweet posted with ID: {tweet_id}")
        
        # Update state
        now = datetime.now()
        st.session_state.last_posted = now
        st.session_state.next_post_time = now + timedelta(minutes=TWEET_INTERVAL)
        
        # Add to history
        tweet_data = {
            'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
            'topic': topic,
            'content': tweet_content,
            'url': tweet_url,
            'simulated': SIMULATION_MODE
        }
        st.session_state.tweet_history.append(tweet_data)
        
        # Keep history optimized
        if len(st.session_state.tweet_history) > 100:
            st.session_state.tweet_history = st.session_state.tweet_history[-100:]
            
        return True
    except Exception as e:
        logger.error(f"Posting failed: {str(e)}")
        return False

def start_bot():
    """Start the bot"""
    st.session_state.bot_running = True
    # Post immediately when starting
    post_tweet()
    logger.info("Bot started - will post every 15 minutes")

def stop_bot():
    """Stop the bot"""
    st.session_state.bot_running = False
    st.session_state.next_post_time = None
    logger.info("Bot stopped")

def check_and_post():
    """Check if it's time to post and post if needed"""
    if not st.session_state.bot_running:
        return False
        
    now = datetime.now()
    
    # If next post time is set and we've reached it
    if st.session_state.next_post_time and now >= st.session_state.next_post_time:
        return post_tweet()
    return False

def main():
    st.set_page_config(
        page_title="CryptoXpress Twitter Bot",
        page_icon="🚀",
        layout="wide"
    )
    
    # Custom styling
    st.markdown("""
    <style>
    .main .block-container {padding-top: 2rem;}
    h1 {color: #0052FF;}
    .stButton>button {background: #0052FF; color: white;}
    .tweet-card {border: 1px solid #e6ecf0; border-radius: 12px; padding: 1.5rem; margin: 1rem 0;}
    </style>
    """, unsafe_allow_html=True)
    
    st.title("🚀 CryptoXpress Twitter Bot")
    
    # Check if it's time to post
    if check_and_post():
        st.success("Tweet posted automatically!")
    
    # Layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.header("Control Panel")
        
        # Start/Stop button
        if st.button("▶️ Start Bot" if not st.session_state.bot_running else "⏹️ Stop Bot"):
            if not st.session_state.bot_running:
                start_bot()
            else:
                stop_bot()
        
        # Bot status
        status = "Running 🟢" if st.session_state.bot_running else "Stopped 🔴"
        st.info(f"Bot Status: {status}")
        
        # Status information
        st.subheader("Status")
        
        # Next post time
        if st.session_state.next_post_time and st.session_state.bot_running:
            time_remaining = st.session_state.next_post_time - datetime.now()
            if time_remaining.total_seconds() > 0:
                mins, secs = divmod(int(time_remaining.total_seconds()), 60)
                st.info(f"Next tweet in: {mins} min {secs} sec")
        
        # Last posted time
        if st.session_state.last_posted:
            time_since = (datetime.now() - st.session_state.last_posted).seconds // 60
            st.metric("Last Posted", f"{time_since} mins ago")
        
        # Tweet count
        st.metric("Total Tweets", len(st.session_state.tweet_history))
    
    # Tweet History
    with col2:
        st.header("Tweet History")
        if not st.session_state.tweet_history:
            st.info("No tweets posted yet. Start the bot to begin!")
        else:
            for tweet in reversed(st.session_state.tweet_history):
                st.markdown(f"""
                <div class="tweet-card">
                    <div style="color: #0052FF; font-weight: bold;">{tweet['topic'].title()}</div>
                    <p>{tweet['content']}</p>
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <small>{tweet['timestamp']}</small>
                        <div>
                            <a href="{tweet['url']}" target="_blank" style="text-decoration: none;">🔗 View</a>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Auto-refresh the app every few seconds to check for new tweets
    if st.session_state.bot_running:
        st.empty()
        time.sleep(1)
        st.rerun()

if __name__ == "__main__":
    main()

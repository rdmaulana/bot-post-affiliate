import random
import logging
import requests
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
import openai

# Logging setuo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Firebase setup
firebase_sa = os.getenv("FIREBASE_CREDENTIALS_PATH", "secret/firebase.json")
cred = credentials.Certificate(firebase_sa)
firebase_admin.initialize_app(cred)
db = firestore.client()

# OpenAI API setup
openai.api_key = os.getenv("OPENAI_API_KEY")

# Twitter X API setup
bearer_token = os.getenv("X_BEARER_TOKEN")

def create_openai_response(prompt):
    logging.info(f"Generating OpenAI response for prompt: {prompt}")
    response = openai.Completion.create(
        engine="text-davinci-003",  # Pilih model sesuai kebutuhan
        prompt=prompt,
        max_tokens=50,  # Batasi panjang respon
        n=1,
        stop=None,
        temperature=0.7
    )
    generated_text = response.choices[0].text.strip()
    logging.info(f"Generated response: {generated_text}")
    return generated_text

def get_viral_tweets():
    logging.info("Fetching viral tweets...")
    url = "https://api.twitter.com/2/tweets/search/recent"
    query_params = {
        'query': 'is:reply has:likes has:retweets lang:en',
        'tweet.fields': 'public_metrics',
        'max_results': 5  # Batasi hasil untuk percobaan
    }
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }
    response = requests.get(url, headers=headers, params=query_params)
    tweets = response.json()
    logging.info(f"Fetched {tweets} data.")
    logging.info(f"Fetched {len(tweets['data'])} tweets.")
    return tweets

def post_reply(tweet_id, reply_text):
    logging.info(f"Posting reply to tweet ID {tweet_id} with text: {reply_text}")
    url = f"https://api.twitter.com/2/tweets"
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "text": reply_text,
        "reply": {"in_reply_to_tweet_id": tweet_id}
    }
    response = requests.post(url, headers=headers, json=payload)
    logging.info(f"Reply posted with response: {response.json()}")
    return response.json()

def get_affiliate_link():
    logging.info("Fetching affiliate link from Firestore...")
    docs = db.collection('products').stream()
    links = [doc.to_dict().get('tweet_link') for doc in docs if doc.exists]
    if links:
        selected_link = random.choice(links)
        logging.info(f"Selected affiliate link: {selected_link}")
        return selected_link
    else:
        logging.warning("No affiliate links found in Firestore.")
        return None

def main():
    logging.info("Starting script ...")
    try:
        tweets = get_viral_tweets()
        for tweet in tweets['data']:
            tweet_id = tweet['id']
            tweet_text = tweet['text']
            public_metrics = tweet['public_metrics']
            
            # Filter berdasarkan jumlah likes, retweets, dan replies
            if public_metrics['like_count'] > 1000 and public_metrics['retweet_count'] > 500:
                logging.info(f"Processing tweet ID {tweet_id} with metrics: {public_metrics}")
                prompt = f"Balas tweet ini dengan bahasa gen z: {tweet_text}"
                reply_content = create_openai_response(prompt)
                
                # Dapatkan link afiliasi
                affiliate_link = get_affiliate_link()
                
                if affiliate_link:
                    reply_content += f"\n\n{affiliate_link}"
                
                # Post reply
                post_reply(tweet_id, reply_content)
            else:
                logging.info(f"Tweet ID {tweet_id} does not meet engagement criteria.")
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")

    logging.info("Script process completed.")

if __name__ == "__main__":
    main()

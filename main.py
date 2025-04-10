from my_openai_client import get_stock_market_reaction
import time
import random
from datetime import datetime, timezone, date
from truth_api import Api
import requests
import os
from dateutil import parser as date_parse


def main():
    now_date = datetime.now(timezone.utc)
    api = Api()
    error_sleep = 10
    while True:
        try:
            last_tweet = api.pull_statuses("realDonaldTrump", replies=False)
        except Exception as e:
            print(f"Error: {e}")
            print(f"Sleeping for {error_sleep} seconds bc of error...")
            time.sleep(10)
            error_sleep += 10
            continue
        error_sleep = 10
        if last_tweet.get("created_at") is not None:
            print(f"Last Tweet: {last_tweet['content']}")
            print(f"Created At: {last_tweet['created_at']}")
            created_at = date_parse.parse(last_tweet["created_at"]).replace(
                tzinfo=timezone.utc
            )
            if created_at > now_date:
                now_date = created_at
                print(f"Tweet: {last_tweet['content']}")
                stock_market_reaction = get_stock_market_reaction(last_tweet["content"])
                print(f"Stock Market Reaction: {stock_market_reaction}")
                if stock_market_reaction in ["extremely strong", "strong"]:
                    print("Tweet is likely to impact the stock market.")
                    # pinging the discord server
                    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
                    discord_id = os.getenv("DISCORD_ID")
                    message = {
                        "content": f"<@{discord_id}>\nNew impactful tweet detected!\n\n**Tweet Content:** {last_tweet['content']}\n**Stock Market Reaction:** {stock_market_reaction}"
                    }

                    try:
                        response = requests.post(webhook_url, json=message)
                        response.raise_for_status()
                        print("Successfully sent webhook notification.")
                    except requests.RequestException as e:
                        print(f"Failed to send webhook notification: {e}")

        random_number = random.randint(10, 20)
        print(f"Sleeping for {random_number} seconds...")
        time.sleep(random_number)


if __name__ == "__main__":
    main()

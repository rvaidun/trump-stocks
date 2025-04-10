from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
import json

client = OpenAI()


def get_stock_market_reaction(tweet):
    """
    Analyze the potential stock market reaction to a given tweet.

    Args:
        tweet (str): The tweet text to analyze.

    Returns:
        str: The predicted reaction (e.g., "extremely strong", "strong", "moderate", "weak", "no reaction").
    """
    prompt = (
        f"Analyze the following tweet and predict its impact on the US stock market: {tweet}\n"
        "Classify the reaction as one of the following: extremely strong, strong, moderate, weak, or no reaction."
    )

    try:
        response = client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            input=[
                {
                    "role": "system",
                    "content": "Your goal is to determine if the tweet is talking about the economy or stock market. If it is, classify the reaction as one of the following: extremely strong, strong, moderate, weak, or no reaction. If it is not talking about the economy or stock market, return 'no reaction'. Having a strong reaction means that the tweet is likely to have a significant impact on the stock market and stocks will go up or down significantly. If you are not sure, return 'no reaction'.",
                },
                {"role": "user", "content": prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "stock_market_reaction",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "reaction": {
                                "type": "string",
                                "enum": [
                                    "extremely strong",
                                    "strong",
                                    "moderate",
                                    "weak",
                                    "no reaction",
                                ],
                            }
                        },
                        "required": ["reaction"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            },
        )
        result = json.loads(response.output_text)
        print(json.dumps(result, indent=2))
        return result["reaction"]
    except Exception as e:
        print(f"Error while fetching data from OpenAI API: {e}")
        return "Error"


# tweet = """
# This is a GREAT time to move your COMPANY into the United States of America, like Apple, and so many others, in record numbers, are doing. ZERO TARIFFS, and almost immediate Electrical/Energy hook ups and approvals. No Environmental Delays. DON’T WAIT, DO IT NOW!
# """
# get_stock_market_reaction(tweet)

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
        "Example 1:\n"
        "Tweet: 'The latest unemployment figures indicate improvement, likely boosting investor confidence.'\n"
        'Output: {"reaction": "moderate"}\n\n'
        "Example 2:\n"
        "Tweet: 'Enjoyed a wonderful meal tonight!'\n"
        'Output: {"reaction": "no reaction"}\n\n'
        f"Analyze the following tweet for indications that it discusses the US economy or stock market:\n"
        f"Tweet: {tweet}\n\n"
        "If the tweet discusses topics like financial performance, market conditions, economic indicators, or other related factors, "
        "classify the tweet's expected market reaction as one of the following: extremely strong, strong, moderate, or weak. "
        "If not, or if the content is ambiguous, output 'no reaction'.\n\n"
        'Return your answer exactly in JSON format: {"reaction": "<reaction_value>"}.'
    )

    try:
        response = client.responses.create(
            model="gpt-4o-mini-2024-07-18",
            input=[
                {
                    "role": "system",
                    "content": "You are a financial analyst",
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
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "The reasoning behind the classification",
                            },
                        },
                        "required": ["reaction", "reasoning"],
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


if __name__ == "__main__":
    # Example usage
    tweet = """
Based on the lack of respect that China has shown to the World’s Markets, I am hereby raising the Tariff charged to China by the United States of America to 125%, effective immediately. At some point, hopefully in the near future, China will realize that the days of ripping off the U.S.A., and other Countries, is no longer sustainable or acceptable. Conversely, and based on the fact that more than 75 Countries have called Representatives of the United States, including the Departments of Commerce, Treasury, and the USTR, to negotiate a solution to the subjects being discussed relative to Trade, Trade Barriers, Tariffs, Currency Manipulation, and Non Monetary Tariffs, and that these Countries have not, at my strong suggestion, retaliated in any way, shape, or form against the United States, I have authorized a 90 day PAUSE, and a substantially lowered Reciprocal Tariff during this period, of 10%, also effective immediately. Thank you for your attention to this matter!
    """
    reaction = get_stock_market_reaction(tweet)
    print(f"Predicted stock market reaction: {reaction}")

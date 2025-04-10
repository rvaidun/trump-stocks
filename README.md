# Realtime Trump Stock Market Impact Analyzer

A real-time monitoring system that analyzes tweets from specific accounts (currently configured for @realDonaldTrump) and predicts their potential impact on the stock market. The system uses OpenAI's GPT-4 model to analyze tweet content and sends Discord notifications for tweets that are likely to have a significant market impact.

## Features

- Real-time tweet monitoring
- AI-powered stock market impact analysis
- Discord notifications for impactful tweets
- Automatic retry mechanism for error handling
- Configurable monitoring intervals

## Prerequisites

- Python 3.8+
- OpenAI API key
- Discord webhook URL
- Discord user ID for mentions

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
OPENAI_API_KEY=your_openai_api_key
DISCORD_WEBHOOK_URL=your_discord_webhook_url
DISCORD_ID=your_discord_user_id
TRUTHSOCIAL_USERNAME=truthsocial_username
TRUTHSOCIAL_PASSWORD=truthsocial_password
TRUTHSOCIAL_TOKEN=your_truthsocial_token
```
The `TRUTHSOCIAL_TOKEN` is optional. If not provided, the script will use the `TRUTHSOCIAL_USERNAME` and `TRUTHSOCIAL_PASSWORD` for authentication and will retrieve the token automatically. After you get the token from the first run of the script you can set it in the `.env` file for future use.
## Installation
For this I am using [uv](https://github.com/astral-sh/uv) package manager.
1. Clone the repository:
```bash
git clone <repository-url>
cd stocks
```

2. Install the required dependencies:
```bash
uv sync
```

## Usage

Run the main script:
```bash
uv run main.py
```

The program will:
1. Continuously monitor for new tweets
2. Analyze each tweet's potential market impact
3. Send Discord notifications for tweets with "extremely strong" or "strong" market impact
4. Automatically retry on errors with increasing backoff intervals

## Market Impact Classification

The system classifies tweets into five categories of market impact:
- Extremely strong
- Strong
- Moderate
- Weak
- No reaction

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
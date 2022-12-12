import logging
import os

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from revChatGPT.revChatGPT import AsyncChatbot as ChatGPT3Bot

from telegram_bot import ChatGPT3TelegramBot


def extract_openai_tokens(email, password) -> (str, str, str):
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        # ---------------------
        page.goto("https://chat.openai.com/auth/login", wait_until="networkidle")
        page.get_by_role("button", name="Log in").click()
        page.get_by_label("Email address").fill(email)
        page.locator("button[name=\"action\"]").click()
        page.get_by_label("Password").click()
        page.get_by_label("Password").fill(password)
        page.get_by_role("button", name="Continue").click()
        # ---------------------
        with page.expect_response('**/auth/session', timeout=3000):
            cookies = context.cookies()
            session_token = [cookie['value'] for cookie in cookies if cookie['name'] == '__Secure-next-auth.session-token'][0]
            cf_clearance = [cookie['value'] for cookie in cookies if cookie['name'] == 'cf_clearance'][0]
            user_agent = page.evaluate('() => navigator.userAgent')
            return session_token, cf_clearance, user_agent


def main():
    # Read .env file
    load_dotenv()

    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    # Check if the required environment variables are set
    required_values = ['TELEGRAM_BOT_TOKEN', 'OPENAI_EMAIL', 'OPENAI_PASSWORD']
    missing_values = [value for value in required_values if os.environ.get(value) is None]
    if len(missing_values) > 0:
        logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
        exit(1)

    # Extract OpenAI tokens
    session_token, cf_clearance, user_agent = extract_openai_tokens(
        email=os.environ.get('OPENAI_EMAIL'),
        password=os.environ.get('OPENAI_PASSWORD')
    )

    # Setup configuration
    chatgpt_config = {
        'session_token': session_token,
        'cf_clearance': cf_clearance,
        'user_agent': user_agent
    }
    telegram_config = {
        'token': os.environ['TELEGRAM_BOT_TOKEN'],
        'allowed_user_ids': os.environ.get('ALLOWED_TELEGRAM_USER_IDS', '*'),
        'use_stream': os.environ.get('USE_STREAM', 'true').lower() == 'true'
    }

    if os.environ.get('PROXY', None) is not None:
        chatgpt_config.update({'proxy': os.environ.get('PROXY')})

    debug = os.environ.get('DEBUG', 'true').lower() == 'true'

    # Setup and run ChatGPT and Telegram bot
    gpt3_bot = ChatGPT3Bot(config=chatgpt_config, debug=debug)
    telegram_bot = ChatGPT3TelegramBot(config=telegram_config, gpt3_bot=gpt3_bot)
    telegram_bot.run()


if __name__ == '__main__':
    main()

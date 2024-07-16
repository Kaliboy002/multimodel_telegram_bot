import os
import json
import requests
import telebot
import logging
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keep_alive import keep_alive

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the available models
MODELS = {
    "Mistral-7B-Instruct-v0.3":
    "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
    "Meta-Llama-3-8B":
    "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B",
    "SDXL-Flash":
    "https://api-inference.huggingface.co/models/sd-community/sdxl-flash",
    "Fluently-XL-v3-Lightning":
    "https://api-inference.huggingface.co/models/fluently/Fluently-XL-v3-Lightning",
    "Fluently-anime":
    "https://api-inference.huggingface.co/models/fluently/Fluently-anime",
    "Juggernaut-X-v10":
    "https://api-inference.huggingface.co/models/RunDiffusion/Juggernaut-X-v10",
    "Juggernaut-X-Hyper":
    "https://api-inference.huggingface.co/models/RunDiffusion/Juggernaut-X-Hyper",
    "RealVisXL_V4.0":"https://api-inference.huggingface.co/models/SG161222/RealVisXL_V4.0",
}

IMAGE_MODELS = {
    "SDXL-Flash", "Fluently-XL-v3-Lightning", "Fluently-anime",
    "Fluently-v4-LCM", "Juggernaut-X-v10", "Juggernaut-X-Hyper", "RealVisXL_V4.0"
}


# Initialize the Telegram bot
class HuggingFaceTelegramBot:

    def __init__(self, models, telegram_token):
        self.models = models
        self.current_model_key = "Mistral-7B-Instruct-v0.3"  # Default model key
        self.api_endpoint = self.models[self.current_model_key]
        self.bot = telebot.TeleBot(telegram_token)
        huggingface_token = os.getenv("HUGGINGFACE_TOKEN")

        if not huggingface_token:
            raise ValueError("HUGGINGFACE_TOKEN environment variable not set")

        self.request_headers = {
            "Authorization": f"Bearer {huggingface_token}",
            "Content-Type": "application/json"
        }

        # Set up message handlers
        self.bot.message_handler(commands=['start', 'help', 'info', 'model'])(
            self.handle_commands)
        self.bot.callback_query_handler(func=lambda call: True)(
            self.handle_callback_query)
        self.bot.message_handler(func=lambda message: True)(self.on_message)

    def query_huggingface(self, payload):
        try:
            data = json.dumps(payload)
            response = requests.post(self.api_endpoint,
                                     headers=self.request_headers,
                                     data=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return {"error": str(e)}

    def query_huggingface_image(self, payload):
        try:
            data = json.dumps(payload)
            response = requests.post(self.api_endpoint,
                                     headers=self.request_headers,
                                     data=data)
            response.raise_for_status()
            return response.content  # Return raw image content
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise RuntimeError(
                "The service is temporarily unavailable because of overloading. Please try again later."
            )

    def handle_commands(self, message):
        chat_id = message.chat.id
        command = message.text.split()[0][
            1:]  # Get the command without the '/'

        if command == "start":
            response = (
                "Hello! I am an AI-powered bot. You can interact with me by sending any text message. "
                "Use /help to see available commands.")
            self.bot.send_message(chat_id, response)
        elif command == "help":
            response = (
                "Here are some commands you can use:\n"
                "/start - Start the bot\n"
                "/help - Show this help message\n"
                "/info - Get information about this bot\n"
                "/model - Switch to a different AI model\n\n"
                "To use the bot, simply send any text message, and I will respond with AI-generated text or images."
            )
            self.bot.send_message(chat_id, response)
        elif command == "info":
            response = (
                "I am a Telegram bot powered by an AI models made by Alamain H. "
                "I can generate responses to your text messages and create iamges. "
                "Feel free to ask me anything!")
            self.bot.send_message(chat_id, response)
        elif command == "model":
            self.show_model_selection(chat_id)
        else:
            response = "Unknown command. Use /help to see available commands."
            self.bot.send_message(chat_id, response)

    def show_model_selection(self, chat_id):
        markup = InlineKeyboardMarkup()
        for model_name in self.models.keys():
            markup.add(
                InlineKeyboardButton(
                    model_name, callback_data=f"switch_model_{model_name}"))
        self.bot.send_message(chat_id,
                              "Select a model to switch:",
                              reply_markup=markup)

    def handle_callback_query(self, call):
        if call.data.startswith("switch_model_"):
            model_key = call.data[len("switch_model_"):]
            if model_key in self.models:
                self.current_model_key = model_key
                self.api_endpoint = self.models[model_key]
                self.bot.answer_callback_query(
                    call.id, f"Switched to model: {model_key}")
                self.bot.send_message(call.message.chat.id,
                                      f"Switched to model: {model_key}")
            else:
                self.bot.answer_callback_query(call.id,
                                               "Model not recognized.")
        self.bot.edit_message_reply_markup(call.message.chat.id,
                                           call.message.message_id,
                                           reply_markup=None)

    def on_message(self, message):
        chat_id = message.chat.id
        if message.text:
            command = message.text

            # Send "typing" action
            self.bot.send_chat_action(chat_id, 'typing')

            # Send "Processing" message
            processing_message = self.bot.send_message(
                chat_id, "Processing your request, please wait...")

            payload = {"inputs": command}

            if self.current_model_key in IMAGE_MODELS:
                try:
                    response = self.query_huggingface_image(payload)
                    self.bot.send_photo(chat_id, response)
                except RuntimeError as e:
                    self.bot.send_message(chat_id, str(e))
            else:
                response = self.query_huggingface(payload)
                if isinstance(response, dict) and "error" in response:
                    error_message = response["error"]
                    if "Failed to fetch model" in error_message:
                        self.bot.send_message(
                            chat_id,
                            "Sorry, the selected model is not available at the moment."
                        )
                    else:
                        self.bot.send_message(
                            chat_id,
                            "Sorry, an error occurred while processing your request."
                        )
                elif isinstance(response, list) and response:
                    bot_response = response[0].get(
                        "generated_text",
                        "Sorry, I couldn't generate a response.")
                    # Reply to the user's prompt
                    self.bot.reply_to(message, bot_response)
                else:
                    self.bot.send_message(
                        chat_id, "Sorry, I couldn't generate a response.")

            # Delete the "Processing" message
            self.bot.delete_message(chat_id, processing_message.message_id)

            # Rate limiting: delay to avoid hitting API rate limits
            time.sleep(1)

    def run(self):
        self.bot.delete_webhook()
        keep_alive()
        logger.info("Starting bot polling...")
        self.bot.polling()


def main():
    telegram_token = os.getenv("TELEGRAM_TOKEN")

    if not telegram_token:
        raise ValueError("TELEGRAM_TOKEN environment variable not set")

    bot = HuggingFaceTelegramBot(MODELS, telegram_token)
    bot.run()


if __name__ == "__main__":
    main()

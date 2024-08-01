import os
import telebot
import logging
import time
import tempfile
import queue
import threading
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keep_alive import keep_alive
from gradio_client import Client
from telebot.types import BotCommand

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the available Gradio model URLs with their API information
MODEL_URLS = {
    "Imagineo-4K": {
        "url": "https://prithivmlmods-imagineo-4k.hf.space",
        "api_name": "/run"
    },
    "stable-diffusion-3-medium": {
        "url": "https://stabilityai-stable-diffusion-3-medium.hf.space",
        "api_name": "/infer"
    },
    # Add more models as needed
}

# Define custom names for models
CUSTOM_MODEL_NAMES = {
    "Imagineo-4K": "Photorealism",
    "stable-diffusion-3-medium": "Base SD Medium",
    # Add more custom names as needed
}

IMAGE_MODELS = {"Imagineo-4K", "stable-diffusion-3-medium"}  # Add all image model keys here

# Initialize the Telegram bot
class GradioTelegramBot:

    def __init__(self, model_urls, custom_model_names, telegram_token):
        self.model_urls = model_urls
        self.custom_model_names = custom_model_names
        self.current_model_key = "Imagineo-4K"  # Default model key
        self.clients = self.initialize_clients(model_urls)
        self.bot = telebot.TeleBot(telegram_token)
        self.request_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self.process_queue)
        self.worker_thread.daemon = True
        self.worker_thread.start()

        # Set up message handlers
        self.bot.message_handler(commands=['start', 'help', 'info', 'model'])(
            self.handle_commands)
        self.bot.callback_query_handler(func=lambda call: True)(
            self.handle_callback_query)
        self.bot.message_handler(func=lambda message: True)(self.on_message)

        # Set up the command menu
        self.setup_command_menu()

    def initialize_clients(self, model_urls):
        clients = {}
        for key, info in model_urls.items():
            try:
                clients[key] = Client(info["url"])
            except Exception as e:
                logger.error(f"Failed to initialize Gradio client for {key}: {str(e)}")
                clients[key] = None
        return clients

    def setup_command_menu(self):
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help message"),
            BotCommand("info", "Get information about this bot"),
            BotCommand("model", "Switch to a different AI model"),
            BotCommand("generate", "Generate an image (use in groups)")
        ]
        self.bot.set_my_commands(commands)

    def generate_image(self, prompt):
        current_client = self.clients[self.current_model_key]
        current_model_info = self.model_urls[self.current_model_key]

        if not current_client:
            logger.error(f"Client for model {self.current_model_key} is not available.")
            return None

        try:
            if self.current_model_key == "Imagineo-4K":
                result = current_client.predict(
                    prompt=prompt,
                    negative_prompt="(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation",
                    use_negative_prompt=True,
                    style="3840 x 2160",
                    collage_style="Hi-Res",
                    filter_name="Zero filter",
                    grid_size="1x1",
                    seed=0,
                    width=1024,
                    height=1024,
                    guidance_scale=6,
                    randomize_seed=True,
                    api_name=current_model_info["api_name"]
                )
            elif self.current_model_key == "stable-diffusion-3-medium":
                result = current_client.predict(
                    prompt=prompt,
                    negative_prompt="(deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), disconnected limbs, mutation, mutated, ugly, disgusting, blurry, amputation",
                    seed=0,
                    randomize_seed=True,
                    width=1024,
                    height=1024,
                    guidance_scale=5,
                    num_inference_steps=28,
                    api_name=current_model_info["api_name"]
                )
            else:
                raise ValueError(f"Unsupported model: {self.current_model_key}")

            # Process the result based on the model
            if self.current_model_key == "Imagineo-4K":
                if isinstance(result, tuple) and len(result) > 0:
                    images = result[0]
                    if images and isinstance(images, list) and len(images) > 0 and 'image' in images[0]:
                        return images[0]['image']
            elif self.current_model_key == "stable-diffusion-3-medium":
                if isinstance(result, (list, tuple)) and len(result) > 0:
                    if isinstance(result[0], bytes):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                            temp_file.write(result[0])
                            return temp_file.name
                    elif isinstance(result[0], str):
                        return result[0]
                else:
                    logger.error("Unexpected result structure for stable-diffusion-3-medium")
                    return None

            raise ValueError("Invalid response from API")

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None

    def handle_commands(self, message):
        chat_id = message.chat.id
        command = message.text.split()[0][1:]  # Get the command without the '/'

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
                "I am a Telegram bot powered by AI models. "
                "I can generate responses to your text messages and create images. "
                "Feel free to ask me anything!")
            self.bot.send_message(chat_id, response)
        elif command == "model":
            self.show_model_selection(chat_id)
        else:
            response = "Unknown command. Use /help to see available commands."
            self.bot.send_message(chat_id, response)

    def show_model_selection(self, chat_id):
        markup = InlineKeyboardMarkup()
        for model_key, custom_name in self.custom_model_names.items():
            markup.add(
                InlineKeyboardButton(custom_name, callback_data=f"switch_model_{model_key}")
            )
        self.bot.send_message(chat_id, "Select a model to switch:", reply_markup=markup)

    def handle_callback_query(self, call):
        if call.data.startswith("switch_model_"):
            model_key = call.data[len("switch_model_"):]
            if model_key in self.model_urls:
                self.current_model_key = model_key
                custom_name = self.custom_model_names[model_key]
                self.bot.answer_callback_query(call.id, f"Switched to model: {custom_name}")
                self.bot.send_message(call.message.chat.id, f"Switched to model: {custom_name}")
            else:
                self.bot.answer_callback_query(call.id, "Model not recognized.")
        self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    def on_message(self, message):
        chat_id = message.chat.id
        chat_type = message.chat.type

        if chat_type in ['group', 'supergroup']:
            # In group chats, only respond to messages starting with '/'
            if message.text and message.text.startswith('/'):
                if message.text.startswith('/generate '):
                    prompt = message.text[10:]  # Remove '/generate ' from the start
                    self.queue_request(chat_id, prompt, message.message_id)
                else:
                    # Handle other commands if needed
                    self.handle_commands(message)
        else:
            # In private chats, process all messages as before
            if message.text:
                self.queue_request(chat_id, message.text, message.message_id)

    def queue_request(self, chat_id, prompt, message_id):
        # Send "typing" action
        self.bot.send_chat_action(chat_id, 'typing')

        # Send "Processing" message as a reply to the user's message
        processing_message = self.bot.send_message(
            chat_id,
            "Your request has been queued. Please wait...",
            reply_to_message_id=message_id
        )

        # Add the request to the queue
        self.request_queue.put(
            (chat_id, prompt, message_id, processing_message.message_id)
        )

    def process_queue(self):
        while True:
            chat_id, prompt, original_message_id, processing_message_id = self.request_queue.get()

            try:
                if self.current_model_key in IMAGE_MODELS:
                    # Generate the image using the Gradio API
                    image_path = self.generate_image(prompt)

                    if image_path:
                        # Send the image as a reply to the original message
                        with open(image_path, 'rb') as image:
                            self.bot.send_photo(
                                chat_id,
                                image,
                                reply_to_message_id=original_message_id
                            )
                        # If it's a temporary file, delete it after sending
                        if image_path.startswith(tempfile.gettempdir()):
                            os.remove(image_path)
                    else:
                        self.bot.send_message(
                            chat_id,
                            "Sorry, I couldn't generate an image at the moment. You have exceeded your GPU Quota Please try again after 5 minutes or use other models. We are currently experiencing overload. To see Other models list use /model command",
                            reply_to_message_id=original_message_id
                        )
                else:
                    self.bot.send_message(
                        chat_id,
                        "Sorry, I couldn't generate a response.",
                        reply_to_message_id=original_message_id
                    )
            except Exception as e:
                logger.error(f"Error in process_queue: {str(e)}")
                self.bot.send_message(
                    chat_id,
                    "I'm having trouble processing your request. Please try again later.",
                    reply_to_message_id=original_message_id
                )
            finally:
                # Delete the "Processing" message
                self.bot.delete_message(chat_id, processing_message_id)

                # Rate limiting: delay to avoid hitting API rate limits
                time.sleep(1)

            self.request_queue.task_done()

    def run(self):
        self.bot.delete_webhook()
        keep_alive()
        logger.info("Starting bot polling...")
        self.bot.polling()


def main():
    telegram_token = os.getenv("TELEGRAM_TOKEN")

    if not telegram_token:
        raise ValueError("TELEGRAM_TOKEN environment variable not set")

    bot = GradioTelegramBot(MODEL_URLS, CUSTOM_MODEL_NAMES, telegram_token)
    bot.run()


if __name__ == "__main__":
    main()

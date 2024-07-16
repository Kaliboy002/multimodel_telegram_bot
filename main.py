import os
import telebot
import logging
import time
import tempfile
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from keep_alive import keep_alive
from gradio_client import Client

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

IMAGE_MODELS = {"Imagineo-4K", "stable-diffusion-3-medium"}  # Add all image model keys here

# Initialize the Telegram bot
class GradioTelegramBot:
    def __init__(self, model_urls, telegram_token):
        self.model_urls = model_urls
        self.current_model_key = "Imagineo-4K"  # Default model key
        self.clients = {key: Client(info["url"]) for key, info in model_urls.items()}
        self.bot = telebot.TeleBot(telegram_token)

        # Set up message handlers
        self.bot.message_handler(commands=['start', 'help', 'info', 'model'])(self.handle_commands)
        self.bot.callback_query_handler(func=lambda call: True)(self.handle_callback_query)
        self.bot.message_handler(func=lambda message: True)(self.on_message)

    def generate_image(self, prompt):
        current_client = self.clients[self.current_model_key]
        current_model_info = self.model_urls[self.current_model_key]

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

        print("Result from Gradio API:", result)  # Debug print
        print("Type of result:", type(result))  # Print the type of the result
        if isinstance(result, (list, tuple)):
            print("Length of result:", len(result))
            for i, item in enumerate(result):
                print(f"Item {i} type:", type(item))
                print(f"Item {i} content:", item)

        # Process the result based on the model
        if self.current_model_key == "Imagineo-4K":
            if isinstance(result, tuple) and len(result) > 0:
                images = result[0]
                if images and isinstance(images, list) and len(images) > 0 and 'image' in images[0]:
                    return images[0]['image']
        elif self.current_model_key == "stable-diffusion-3-medium":
            if isinstance(result, (list, tuple)) and len(result) > 0:
                # If the result is binary image data
                if isinstance(result[0], bytes):
                    # Save the binary data to a temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
                        temp_file.write(result[0])
                        return temp_file.name
                # If the result is a file path
                elif isinstance(result[0], str):
                    return result[0]
            else:
                print("Unexpected result structure for stable-diffusion-3-medium")
                return None

        raise ValueError("Invalid response from Gradio API")

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
        for model_name in self.model_urls.keys():
            markup.add(
                InlineKeyboardButton(
                    model_name, callback_data=f"switch_model_{model_name}"))
        self.bot.send_message(chat_id, "Select a model to switch:", reply_markup=markup)

    def handle_callback_query(self, call):
        if call.data.startswith("switch_model_"):
            model_key = call.data[len("switch_model_"):]
            if model_key in self.model_urls:
                self.current_model_key = model_key
                self.bot.answer_callback_query(call.id, f"Switched to model: {model_key}")
                self.bot.send_message(call.message.chat.id, f"Switched to model: {model_key}")
            else:
                self.bot.answer_callback_query(call.id, "Model not recognized.")
        self.bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

    def on_message(self, message):
        chat_id = message.chat.id
        if message.text:
            command = message.text

            # Send "typing" action
            self.bot.send_chat_action(chat_id, 'typing')

            # Send "Processing" message
            processing_message = self.bot.send_message(chat_id, "Processing your request, please wait...")

            if self.current_model_key in IMAGE_MODELS:
                try:
                    # Generate the image using the Gradio API
                    image_path = self.generate_image(command)
                    print("Generated image path:", image_path)  # Debug print

                    if image_path:
                        # Send the image
                        with open(image_path, 'rb') as image:
                            self.bot.send_photo(chat_id, image)
                        # If it's a temporary file, delete it after sending
                        if image_path.startswith(tempfile.gettempdir()):
                            os.remove(image_path)
                    else:
                        self.bot.send_message(chat_id, "Sorry, I couldn't generate an image. Please try again.")
                except Exception as e:
                    self.bot.send_message(chat_id, f"Error: {str(e)}")
                    print(f"Error details: {e}")  # Print full error details to console
            else:
                self.bot.send_message(chat_id, "Sorry, I couldn't generate a response.")

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

    bot = GradioTelegramBot(MODEL_URLS, telegram_token)
    bot.run()

if __name__ == "__main__":
    main()

# Gradio Telegram Bot

This repository contains a Python-based Telegram bot that interacts with various AI models via the Gradio API to generate images based on user prompts. The bot supports multiple AI models, allowing users to switch between them and generate images directly in their Telegram chats.

## Features

- **Multiple AI Models**: Switch between different AI models to generate images.
- **Image Generation**: Generate images based on user prompts using the selected AI model.
- **Telegram Integration**: Fully integrated with Telegram for seamless user interaction.
- **Custom Commands**: Use various commands to interact with the bot and switch models.

## Installation

1. **Clone the Repository**:
   ```sh
   git clone https://github.com/MrAlaminH/multimodel_telegram_bot.git
   cd multimodel_telegram_bot
   ```

2. **Install Dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

3. **Set Up Environment Variables**:
   Create a `.env` file in the project root directory and add your Telegram bot token:
   ```env
   TELEGRAM_TOKEN=your-telegram-bot-token
   ```

4. **Run the Bot**:
   ```sh
   python main.py
   ```

## Usage

### Commands

- `/start`: Start the bot and receive a welcome message.
- `/help`: Get a list of available commands and their usage.
- `/info`: Get information about the bot.
- `/model`: Switch to a different AI model.
- `/generate [prompt]`: Generate an image based on the provided prompt (use in group chats).

### Example

1. **Starting the Bot**:
   Send `/start` to initiate a conversation with the bot.

2. **Generating an Image**:
   In a group chat, send `/generate A scenic view of mountains during sunset` to generate an image based on the prompt.

3. **Switching Models**:
   Use `/model` to see a list of available models and select one to switch.

## Development

### Logging

Logging is configured at the INFO level. You can modify the logging configuration in the `bot.py` file.

### Adding More Models

To add more AI models, update the `MODEL_URLS` and `CUSTOM_MODEL_NAMES` dictionaries in the `bot.py` file with the necessary API information and custom names.

### Error Handling

The bot includes error handling for API requests and provides appropriate feedback to users if an error occurs.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any changes.

## License

This project is licensed under the MIT License.

---

## Acknowledgements

Special thanks to the developers of [Gradio](https://gradio.app/) for providing the API interface and the community for their support.

---

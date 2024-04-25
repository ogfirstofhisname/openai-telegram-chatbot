# openai-telegram-chatbot
A Telegram-based chatbot interface for OpenAI's GPT model, supporting the following types of messages:
- Normal text messages
- Voice messages (auto-transcribed to text)
- Images, with or without captions (processed using GPT's vision capability)
- Text files, with or without captions, for longer texts, code snippets, etc.

Tested with Python 3.10 on Windows and Linux.

The implementation is a single script that can run indefinitely - useful for running on a Raspberry Pi or a cloud server. I run it on my Orange Pi.

### Issues of security and privacy
Currently, this project does not support end-to-end encryption for messages, which means that the messages are held as plaintext in the server's memory.

Additionally, this project does not support authentication, which means that anyone who knows the Telegram bot's username can send messages to the bot, potentially abusing the OpenAI API which costs money per use.

Avoid using this project with sensitive information or in production environments, and make sure that your OpenAI API has a hard spending limit to mitigate abuse.


## Setup
**This project does not work out of the box,** as it requires an OpenAI API key and a Telegram bot token.

You need to get them both and put them into files in the project's /files subdirectory.

Optionally, you can also define the system prompt for the GPT model in the /files subdirectory.

### Set up the project
1. Clone the repository into a local directory.
2. Make sure you have Python installed (version 3.10 or later).
3. (Optional) Create a virtual environment by running `python -m venv venv` in the project's root directory.
4. Install the required packages by running `pip install -r requirements.txt` in the project's root directory. If you are using a virtual environment, make sure it is activated.
5. Download and install ffmpeg from [here](https://ffmpeg.org/download.html) and add the install directory to your system PATH. This is required for processing voice messages.

Now proceed to the next steps to set up the OpenAI API key and the Telegram bot token.

### Set up Telegram bot token
Follow [this guide](https://core.telegram.org/bots/features#botfather) to create a new bot and get its token: 

Once you have the token, create a file named `telegram_bot_token' (no extension) in the project's /files subdirectory and paste the token into it.

### Set up OpenAI API key
Browse to [this page](https://platform.openai.com/api-keys) and create a new API key.

Once you have the key, create a file named `openai_api_key' (no extension) in the project's /files subdirectory and paste the key into it.

### Set up system prompt (optional)
OpenAI's GPT models are trained to accept a "system prompt" that helps guide the model's responses.

The system prompt (typically 10-1000 words long) is where you can adjust the behavior of your chat bot.

To apply your own system prompt, create a file named `system_prompt' (no extension) in the project's /files subdirectory and paste the system prompt into it.

Learn more about OpenAI's system prompts [here](https://platform.openai.com/docs/guides/prompt-engineering/six-strategies-for-getting-better-results).

## Running the project
To run the project, simply run ```powershell python src\chatbot.py``` (in Windows Powershell) or ```bash python src/chatbot.py``` (in Linux terminal) in the project's root directory. If you are using a virtual environment, make sure it is activated.
'''
A script that implements a chatbot using the OpenAI API and the Telegram API.
The script's error handling policy is to crash on setup errors, and to keep running on runtime errors while informing the chat user.
The script uses the OpenAI API to interact with the GPT-4 model, and the Telegram API to interact with the chat users.

See the README.md file for more information on how to set up the API keys and tokens.
'''


### CHATBOT PARAMETERS - edit according to your use case ###
############################################################
default_gpt_model = 'gpt-4o'  # as of May 2024, the most capable LLM in the world + vision capabilities
temperature = 0.5  # set to higher for more creative responses or lower for more deterministic output
api_retry_time = 60 # max time to retry the OpenAI API in case of timeout


### Imports ###
###############
import os, time
from typing import Tuple
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai


### Main ###
############
def main():
    ### Prepare the Telegram API token, OpenAI API key, and system prompt from auxiliary files

    API_TOKEN = get_telegram_api_token()
    OPENAI_KEY = get_openai_key()
    system_message_dict = get_system_message_dict()
    allowed_ids = get_allowed_ids()

    ### Initialize OpenAI client
    # client = openai.OpenAI(api_key=OPENAI_KEY)
    client = openai.OpenAI(api_key=OPENAI_KEY)


    ### Initialize the Telegram bot
    application = ApplicationBuilder().token(API_TOKEN).build()
    application.bot_data.update({'client': client, 'system_message_dict': system_message_dict})
    application.bot_data.update({'allowed_ids': allowed_ids})

    start_handler = CommandHandler('start', start_restart_command_handle_function)
    restart_handler = CommandHandler('restart', start_restart_command_handle_function)
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), text_message_handle_function)
    voice_handler = MessageHandler(filters.VOICE, voice_message_handle_function)
    file_handler = MessageHandler(filters.ATTACHMENT & (~filters.PHOTO), text_file_handle_function)
    image_handler = MessageHandler(filters.PHOTO, image_file_handle_function)

    application.add_handler(start_handler)
    application.add_handler(restart_handler)
    application.add_handler(text_handler)
    application.add_handler(voice_handler)
    application.add_handler(file_handler)
    application.add_handler(image_handler)

    application.run_polling()


### Functions ###
#################
def transcribe_mp3_to_text(mp3_filename: str, client: openai.OpenAI) -> Tuple[str, bool]:
    '''
    Transcribes an mp3 file to text using the whisper-1 model from OpenAI.
    The function returns a tuple with the transcript text and a boolean indicating success.
    
    '''
    transcript_text = ''
    success = False
    # make sure that file exists
    if not os.path.exists(mp3_filename):
        print(f"File {mp3_filename} not found. Make sure that ffmpeg is installed and in the system path.")
        return '', False
    # check file size to make sure it fits within the OpenAI API limit of 25MB
    file_stats = os.stat(mp3_filename)
    if file_stats.st_size >= 25*1024*1024:
        # file size too big, return a coherent error message and False for success
        print(f'File size is {file_stats.st_size} bytes. File is too big for OpenAI API. Returning an error message as output.')
        return 'This is an error message replacing a speech-to-text output: File size too big. Try using a shorter audio sample.', False
    # try to transcribe the audio file
    try:
        with open(mp3_filename, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            transcript_text = str(transcript.text)
            success = True
    except Exception as e:
        print(f"Error in transcribing audio file: {e}")
        return '', False
    
    return transcript_text, success

def get_system_message_dict(system_prompt_file:str='./files/system_prompt', temperature:float=0.5) -> dict:
    '''
    Reads the system prompt from a file and returns it as a dict.
    The system prompt file should be a text file with the system prompt string.
    The system prompt string can optionally contain the placeholder 'TEMPERATURE_VAL' which will be replaced with the temperature parameter.
    If the file does not exist, a default system message is returned.

    Args:
    system_prompt_file (str): the path to the system prompt file, defaults to './files/system_prompt'
    temperature (float): the temperature parameter used in the GPT model, defaults to 0.5

    Returns:
    system_message_dict (dict): an openai-compatible dict with the system message
    '''

    # get path to directory of current script and join with file name
    dir_path = os.path.dirname(os.path.realpath(__file__))
    system_prompt_file = os.path.join(dir_path, system_prompt_file)
    # check if the file exists
    if not os.path.exists(system_prompt_file):
        # if the file does not exist, use a default system message
        system_message = 'You are a helpful assitant in a Telegram chat bot platform.'
    else:
        # read the prompt string from the file, using utf-8 encoding
        with open(system_prompt_file, encoding='utf-8') as file:
            system_message = file.read()
            if 'TEMPERATURE_VAL' in system_message:
                system_message = system_message.replace('TEMPERATURE_VAL', str(temperature))
            system_message = system_message.replace('\n', '')
    # convert the system message into a compatible dict
    system_message_dict = {
            'role': 'system',
            'content': system_message
        }
    print(f'got system message, length: {len(system_message)}')
    return system_message_dict

def get_openai_key(openai_api_key_file:str='./files/openai_api_key') -> str:
    '''
    Reads the OpenAI API key from a file and returns it as a string.
    The OpenAI API key file should be a text file with the API key string.

    Args:
    openai_api_key_file (str): the path to the OpenAI API key file, defaults to './files/openai_api_key'

    Returns:
    OPENAI_KEY (str): the OpenAI API key as a string
    '''
    # get path to directory of current script and join with file name
    dir_path = os.path.dirname(os.path.realpath(__file__))
    openai_api_key_file = os.path.join(dir_path, openai_api_key_file)
    print(f'looking for OpenAI key file at {openai_api_key_file}')
    # read the key from the file
    with open(openai_api_key_file) as file:
        OPENAI_KEY = file.readline()
    print(f'got OpenAI key, length: {len(OPENAI_KEY)}')
    return OPENAI_KEY

def get_telegram_api_token(telegram_api_token_file:str='./files/telegram_api_token') -> str:
    '''
    Reads the Telegram API token from a file and returns it as a string.
    The Telegram API token file should be a text file with the API token string.

    Args:
    telegram_api_token_file (str): the path to the Telegram API token file, defaults to './files/telegram_api_token'

    Returns:
    API_TOKEN (str): the Telegram API token as a string
    '''
    # get path to directory of current script and join with file name
    dir_path = os.path.dirname(os.path.realpath(__file__))
    telegram_api_token_file = os.path.join(dir_path, telegram_api_token_file)
    print(f'looking for API token file at {telegram_api_token_file}')
    # read the token from the file
    with open(telegram_api_token_file) as file:
        API_TOKEN = file.readline()
    print(f'got API token, length: {len(API_TOKEN)}')
    return API_TOKEN

def get_allowed_ids(allowed_ids_file:str='./files/allowed_ids') -> list:
    '''
    Reads the allowed chat user IDs from a file and returns them as a list of strings.
    The allowed IDs file should be a text file with the allowed chat user IDs, one per line.

    Args:
    allowed_ids_file (str): the path to the allowed IDs file, defaults to './files/allowed_ids'

    Returns:
    allowed_ids (list): a list of allowed chat user IDs as strings
    '''
    # get path to directory of current script and join with file name.
    dir_path = os.path.dirname(os.path.realpath(__file__))
    allowed_ids_file = os.path.join(dir_path, allowed_ids_file)
    print(f'looking for allowed IDs file at {allowed_ids_file}')
    # check if the file exists. If not, return an empty list
    if not os.path.exists(allowed_ids_file):
        print(f'Allowed IDs file not found at {allowed_ids_file}.')
        return []
    # read the allowed IDs from the file
    try:
        with open(allowed_ids_file) as file:
            allowed_ids = file.readlines()
            allowed_ids = [x.strip() for x in allowed_ids]
        # verify that the IDs are all strings
        allowed_ids = [x for x in allowed_ids if isinstance(x, str)]
        # verify that the IDs are all non-empty
        allowed_ids = [x for x in allowed_ids if len(x) > 0]
        # verify that the IDs are all numeric
        allowed_ids = [x for x in allowed_ids if x.isnumeric()]
        # verify that the IDs are all positive
        allowed_ids = [x for x in allowed_ids if int(x) > 0]
        print(f'got allowed IDs, length: {len(allowed_ids)}')
        return allowed_ids
    except Exception as e:
        print(f'Error reading allowed IDs file: {e}')
        return []


def interact_with_gpt_model(client: openai.OpenAI, conversation: list, model:str=default_gpt_model, temperature:float=0.5) -> str:
    '''
    Interacts with the GPT model using the OpenAI API.
    The function returns the response from the GPT model as a string.

    Args:
    client (openai.OpenAI): the OpenAI client object
    conversation (list): a list of dictionaries with the conversation history
    model (str): the name of the GPT model to use, defaults to default_gpt_model
    temperature (float): the temperature parameter used in the GPT model, defaults to 0.5

    Returns:
    gpt_response (str): the response from the GPT model as a string
    '''
    gpt_response = ''
    time_to_wait = 1  # exponential backoff: timeout retry wait time starts at 1 second and doubles on each retry
    t0 = time.time()
    success = False
    error_message = ''
    while True and time.time()-t0 < api_retry_time:
        try:
            gpt_response = client.chat.completions.create(
                model=model,
                messages=conversation,
                n=1,
                temperature = temperature,
                stream = False
            )
            gpt_response = gpt_response.choices[0].message.content
            success = True
            break
        except openai.RateLimitError as e:
            error_message =+ f'rate limit error: {e}; '
            print('rate limit error, trying again...')
        except openai.APIError as e:
            error_message =+ f'API error: {e}; '
            print(f'API error: {e}, trying again...')
        except Exception as e:
            error_message =+ f'unknown error: {e}; '
            print(f'unknown error: {e}, trying again...')
        finally:
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2
    if not success:
        gpt_response = 'Problem getting response from GPT model. Please try again later.'
        print(f'Errors in getting response from GPT model: {error_message}')
    return gpt_response

def init_conversation_and_system_message(context: ContextTypes.DEFAULT_TYPE,):
    system_message_dict = context.bot_data['system_message_dict']
    if not 'conversation' in context.user_data:
        # initialize the conversation list in the user_data
        context.user_data.update({'conversation': []})
    if len(context.user_data['conversation']) == 0:
        # add the system message to the conversation
        context.user_data['conversation'].append(system_message_dict)


### Async handler functions ###
###############################
async def text_message_handle_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_dict_to_append = {
        'role': 'user',
        'content': update.message.text
    }
    # get the user ID
    user_id = str(update.effective_user.id)
    # if the user is not in the allowed IDs list, print an error and return
    if not user_id in context.bot_data['allowed_ids'] and len(context.bot_data['allowed_ids']) > 0:
        text = f'You are not authorized to use this chatbot. Your user ID is {user_id}.'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        return
    # make sure the conversation is initialized and the system message is added
    init_conversation_and_system_message(context)

    # append the user message to the conversation
    context.user_data['conversation'].append(message_dict_to_append)

    ### interact with the GPT model
    gpt_response = interact_with_gpt_model(context.bot_data['client'], context.user_data['conversation'], model=default_gpt_model, temperature=temperature)

    # send the response to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')

    # append the response to the chat
    message_dict_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    context.user_data['conversation'].append(message_dict_to_append)

async def start_restart_command_handle_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # check if the user is in the allowed IDs list. If not, print an error and return
    user_id = str(update.effective_user.id)
    if not user_id in context.bot_data['allowed_ids'] and len(context.bot_data['allowed_ids']) > 0:
        text = f'You are not authorized to use this chatbot. Your user ID is {user_id}.'
        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        return
    context.user_data['conversation'] = []

async def voice_message_handle_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # make sure the conversation is initialized and the system message is added
    init_conversation_and_system_message(context)

    # make sure previous audio files are deleted
    try:
        os.remove(user_id+'_chatbot_audio_file.mp3')
    except Exception as e:
        pass
    try:
        os.remove(user_id+'_chatbot_audio_file.opus')
    except Exception as e:
        pass

    ### download the voice message
    try:
        fid = update.message.voice.file_id
        voice_file = await context.bot.get_file(fid)
        path = user_id+'_chatbot_audio_file.opus'
        await voice_file.download_to_drive(custom_path=path)
    except Exception as e:
        print('error downloading voice file: ',e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Error transcripting voice message, encountered an error while downloading the voice file: {e}')
        return

    ### convert the voice message to mp3
    try:
        os.system('ffmpeg -i '+path+' -ac 2 -b:a 192k '+user_id+'_chatbot_audio_file.mp3')
    except Exception as e:
        print('error converting voice file: ',e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Error transcripting voice message, encountered an error while converting the audio file: {e}')
        return
    
    ### transcribe the mp3 file to text
    s, success = transcribe_mp3_to_text(user_id+'_chatbot_audio_file.mp3', context.bot_data['client'])
    if not success:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=s)
        return
    # if success, continue
    await context.bot.send_message(chat_id=update.effective_chat.id, text='transcripted voice message:\n'+s, parse_mode='Markdown')
    try:
        os.remove(user_id+'_chatbot_audio_file.mp3')
        os.remove(user_id+'_chatbot_audio_file.opus')
    except Exception as e:
        pass
    
    # append the user message to the conversation
    message_to_append = {
        'role': 'user',
        'content': s
    }
    context.user_data['conversation'].append(message_to_append)

    ### interact with the GPT model
    gpt_response = interact_with_gpt_model(context.bot_data['client'], context.user_data['conversation'], model=default_gpt_model, temperature=temperature)

    # send the response to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')

    # append the response to the chat
    message_dict_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    context.user_data['conversation'].append(message_dict_to_append)

async def text_file_handle_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # make sure there are no previous attachment files
    try:
        os.remove(user_id+'_chatbot_text_file')
    except Exception:
        pass

    # make sure the conversation is initialized and the system message is added
    init_conversation_and_system_message(context)

    # download the file
    try:
        fid = update.message.document.file_id
        doc_file = await context.bot.get_file(fid)
        path = user_id+'_chatbot_text_file'
        await doc_file.download_to_drive(custom_path=path)
    except Exception as e:
        print('error downloading file: ',e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Error processing file, encountered an error while downloading the file: {e}')
        return
    
    # try to read the file into a string
    try:
        with open(path, 'r') as file:
            s = file.read()
    except Exception as e:
        print('error reading file: ',e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Error processing file, encountered an error while reading the file: {e}')
        return
    
    # append the attachment caption to the conversation, if it exists, and append the entire text to the conversation
    if update.message.caption:
        s =  update.message.caption + '\n' + s
    message_to_append = {
        'role': 'user',
        'content': s
    }
    context.user_data['conversation'].append(message_to_append)

    ### interact with the GPT model
    gpt_response = interact_with_gpt_model(context.bot_data['client'], context.user_data['conversation'], model=default_gpt_model, temperature=temperature)

    # send the response to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')

    # append the response to the chat
    message_dict_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    context.user_data['conversation'].append(message_dict_to_append)

    # remove the file
    try:
        os.remove(user_id+'_chatbot_text_file')
    except Exception:
        pass

async def image_file_handle_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    '''
    Handles image messages by using the openai vision API to generate a description of the image.
    from openai import OpenAI.
    API snippet from openai.com:

    response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[
        {
        "role": "user",
        "content": [
            {"type": "text", "text": "What’s in this image?"},
            {
            "type": "image_url",
            "image_url": {
                "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
            },
            },
        ],
        }
    ],
    max_tokens=300,
    )
    '''
    # make sure the conversation is initialized and the system message is added
    init_conversation_and_system_message(context)

    # get the image file's url
    fid = update.message.photo[-1].file_id
    image_file = await context.bot.get_file(fid)
    image_url = str(image_file.file_path)

    # append the image caption to the conversation, if it exists
    s =  update.message.caption
    if s is None:
        s = ''
    message_to_append={
        "role": "user",
        "content": [
            {"type": "text", "text": s},
            # {"type": "text", "text": "What’s in this image?"},
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url,
                },
            },
        ],
    }
    context.user_data['conversation'].append(message_to_append)

    ### interact with the GPT model
    gpt_response = interact_with_gpt_model(context.bot_data['client'], context.user_data['conversation'], model=default_gpt_model, temperature=temperature)

    # send the response to the user
    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')

    # append the response to the chat
    message_dict_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    context.user_data['conversation'].append(message_dict_to_append)





if __name__ == '__main__':
    main()
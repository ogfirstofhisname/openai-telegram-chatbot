import telegram
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from telegram.ext import MessageHandler, filters
import openai
import time, logging, os
import tiktoken
import pprint


debug_to_chat = False  # set to True to send debug messages to the chat, False to suppress them from the chat
default_gpt_model = 'gpt-4-turbo'
temperature = 0.5

# system_message = {
#         'role': 'system',
#         'content': 
#             'You are a helpful assitant in a Telegram chat, speaking both English and Hebrew. ' + 
#             'Here is information you can provide to users about yourself: ' + 
#             'The chat platform remembers all the messages in the chat until a restart command is provided by the user. ' + 
#             'For the restart command, the user needs to type: /restart or /start. ' + 
#             'Deleting the messages can be done with the restart command, which deletes the entire chat. '
#             'The chat retains the messeges until restarted, but they are not stored anywhere. ' + 
#             'This means that the user should copy and save valuable conversations, otherwise they will be lost eventually. ' + 
#             'The chat is created by Ohad Gertel (אוהד גרטל). He does not keep or see any of the messages, but he could, theoretically. Therefore, the chat is not 100% private. ' + 
#             "The chat is considered private as long as you trust the chat's creator, just like any other online service. " + 
#             "No other user can see the messages in the chat. They are only visible to the user's Telegram number. " +
#             'You are based on the GPT4 large language model. You are running at a temperature of ' + str(temperature) + '. '
#     }




### Get Telegram API token from file - file telegram_api_token in subdirectory files
telegram_api_token_file = './files/telegram_api_token'
# get path to directory of current script and join with file name
dir_path = os.path.dirname(os.path.realpath(__file__))
telegram_api_token_file = os.path.join(dir_path, telegram_api_token_file)
# read the token from the file
with open(telegram_api_token_file) as file:
    API_TOKEN = file.readline()

### Get OpenAI API key from file - file openai_api_key in subdirectory files
openai_api_key_file = './files/openai_api_key'
# get path to directory of current script and join with file name
openai_api_key_file = os.path.join(dir_path, openai_api_key_file)
# read the key from the file
with open(openai_api_key_file) as file:
    OPENAI_KEY = file.readline()

# put OPENAI_KEY into an environment variable OPENAI_API_KEY
os.environ['OPENAI_API_KEY'] = OPENAI_KEY

### Get system prompt from file - file system_prompt in subdirectory files
system_prompt_file = './files/system_prompt'
# get path to directory of current script and join with file name
system_prompt_file = os.path.join(dir_path, system_prompt_file)
# check if the file exists
if not os.path.exists(system_prompt_file):
    system_message = 'You are a helpful assitant in a Telegram chat.'
else:
    # read the prompt string from the file, using utf-8 encoding
    with open(system_prompt_file, encoding='utf-8') as file:
        system_message = file.read()
        if 'TEMPERATURE_VAL' in system_message:
            system_message = system_message.replace('TEMPERATURE_VAL', str(temperature))
        system_message = system_message.replace('\n', '')


# convert the system message into a compatible dict
system_message = {
        'role': 'system',
        'content': system_message
    }



### Initialize OpenAI client and chats dict
chats = {}
client = openai.OpenAI()

def main():
    application = ApplicationBuilder().token(API_TOKEN).build()
    
    start_handler = CommandHandler('start', start_restart_command)
    application.add_handler(start_handler)
    
    restart_handler = CommandHandler('restart', start_restart_command)
    application.add_handler(restart_handler)

    debug_handler = CommandHandler('debug', debug_to_chat_onoff_command)
    application.add_handler(debug_handler)
    
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), text_function)
    application.add_handler(text_handler)
    
    voice_handler = MessageHandler(filters.VOICE, voice_function)
    application.add_handler(voice_handler)

    file_handler = MessageHandler(filters.ATTACHMENT & (~filters.PHOTO), file_function)
    application.add_handler(file_handler)

    image_handler = MessageHandler(filters.PHOTO, image_function)
    application.add_handler(image_handler)
    
    application.run_polling()

    # message_list = [] # instead of a list, create a dict of lists - keyed according to chat IDs so that multiple conversations are orthogonal

async def image_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    user_id = str(update.effective_user.id)
    # save the attachment to a temp file
    print('image message received')
    try:
        os.remove(user_id+'_chatbot_image')
    except Exception: pass

    # opus_cmd = 'ffmpeg -i chatbot_voice_message_file.opus -ac 2 -b:a 192k chatbot_voice_message_file.mp3'
    
    # API_TOKEN = "6029468850:AAHF8-gCoWHc_gSit6BfVIifSg_UQFQuVmE"
    # print(update.message.photo)
    fid = update.message.photo[-1].file_id
    image_file = await context.bot.get_file(fid)
    image_url = str(image_file.file_path)
    # path = user_id+'_chatbot_image'
    # # await image_file.download_to_drive(custom_path=path)
    # print(f'fid: {fid}')
    print(f'image url: {image_url}')

    s =  update.message.caption
    if s is None:
        s = ''
    print(f'caption: {s}')

    # message_to_append = {
    #     'role': 'user',
    #     'content': [
    #         s
    # }
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
    if not user_id in chats:
        chats.update({user_id: [system_message]})
    chats[user_id].append(message_to_append)

        # chats.update({chat_id: [message_to_append]})
    # message_list.append(message_to_append)
    try:
        tokens = num_tokens_from_messages(chats[user_id], default_gpt_model)
        print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}, Tokens: {tokens}')
    except Exception as e:
        print('error getting tokens: ',e)
        tokens = 0
    if debug_to_chat:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Got Message! Chat length: {len(chats[user_id])}, Tokens: {tokens}')
    if tokens>50000:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Warning, close to max tokens. Tokens: {tokens}')

    gpt_response = ''
    time_to_wait = 1
    while True:
        try:
            gpt_response = client.chat.completions.create(
                model=default_gpt_model,
                messages=chats[user_id],
                # n=1,
                # temperature = temperature,
                # stream = False
            )
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Got response from API!')

            gpt_response = gpt_response.choices[0].message.content
            print('GPT: '+gpt_response)
            break
        except openai.RateLimitError:
            print('limit error, trying again')
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='API rate limit error, trying again')
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2
        except openai.APIError as e:
            print(f'API error: {e}, trying again')
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='API timeout error, trying again')
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2

    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')
    message_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    # message_list.append(message_to_append)
    # print('chat length: ',len(message_list))
    chats[user_id].append(message_to_append)

        # chats.update({chat_id: [message_to_append]})
    # message_list.append(message_to_append)
    print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}')


async def file_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    # save the attachment to a temp file
    print('file message received')
    try:
        os.remove(user_id+'_chatbot_file')
    except Exception: pass

    # opus_cmd = 'ffmpeg -i chatbot_voice_message_file.opus -ac 2 -b:a 192k chatbot_voice_message_file.mp3'
    
    # API_TOKEN = "6029468850:AAHF8-gCoWHc_gSit6BfVIifSg_UQFQuVmE"
    fid = update.message.document.file_id
    doc_file = await context.bot.get_file(fid)
    path = user_id+'_chatbot_file'
    await doc_file.download_to_drive(custom_path=path)
    # try to read file to string
    try:
        with open(path) as file:
            s = file.read()
    except Exception as e:
        print('error reading file: ',e)
        s = 'A file was attached to this message but there was an error reading it, this is the error message.'
    # add the caption to the string with line break
    if update.message.caption:
        s =  update.message.caption + '\n' + s
    
    print(s)


    message_to_append = {
        'role': 'user',
        'content': s
    }
    if not user_id in chats:
        chats.update({user_id: [system_message]})
    chats[user_id].append(message_to_append)

    # try:
        # tokens = num_tokens_from_messages(chats[user_id], default_gpt_model)
        # print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}, Tokens: {tokens}')
    # except Exception as e:
    #     print('error getting tokens: ',e)
    #     tokens = 0
    # if debug_to_chat:
    #     await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Got Message! Chat length: {len(chats[user_id])}, Tokens: {tokens}')
    # if tokens>50000:
    #     await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Warning, close to max tokens. Tokens: {tokens}')

    gpt_response = ''
    time_to_wait = 1
    while True:
        try:
            gpt_response = client.chat.completions.create(model=default_gpt_model,messages=chats[user_id],n=1,temperature = temperature,stream = False)
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Got response from API!')

            gpt_response = gpt_response.choices[0].message.content
            print('GPT: '+gpt_response)
            break
        except openai.RateLimitError:
            print('limit error, trying again')
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='API rate limit error, trying again')
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2
        except openai.APIError as e:
            print(f'API error: {e}, trying again')
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='API timeout error, trying again')
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2

    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')
    message_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    # message_list.append(message_to_append)
    # print('chat length: ',len(message_list))
    chats[user_id].append(message_to_append)

        # chats.update({chat_id: [message_to_append]})
    # message_list.append(message_to_append)
    print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}')

def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
        }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens



def transcribe(mp3_filename):
    # make sure that file exists
    if not os.path.exists(mp3_filename):
        raise FileNotFoundError(f"File {mp3_filename} not found. Make sure that ffmpeg is installed and in the system path.") from None
    file_stats = os.stat(mp3_filename)
    print(file_stats.st_size, type(file_stats.st_size))
    if file_stats.st_size >= 25*1024*1024:
        return ('DID NOT TRANSCRIBE. FILE IS TOO BIG')
# openai.api_key = os.getenv('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')
    audio_file = open(mp3_filename, "rb")
    # transcript = openai.Audio.transcribe("whisper-1", audio_file,api_key = OPENAI_KEY,response_format='text')
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    audio_file.close()
    # print(type(transcript))
    # print(transcript)
    # print(str(transcript))
    # model = whisper.load_model('small')
    # result = model.transcribe(mp3_filename)
    # print('local whisper output: ',result["text"])
    # return str(result["text"])
    return str(transcript.text)


# def transcribe(mp3_filename):
#     file_stats = os.stat(mp3_filename)
#     print(file_stats.st_size, type(file_stats.st_size))
#     if file_stats.st_size >= 20*1024*1024:
#         return ('DID NOT TRANSCRIBE. FILE IS TOO BIG')
#     audio_file = open(mp3_filename, "rb")
#     transcript = openai.Audio.transcribe("whisper-1", audio_file,response_format='text')
#     audio_file.close()

#     return str(transcript)


async def voice_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    print('voice message received')
    try:
        os.remove(user_id+'_chatbot.mp3')
    except: pass
    try:
        os.remove(user_id+'_chatbot.opus')
    except: pass
    # opus_cmd = 'ffmpeg -i chatbot_voice_message_file.opus -ac 2 -b:a 192k chatbot_voice_message_file.mp3'
    
    # API_TOKEN = "6029468850:AAHF8-gCoWHc_gSit6BfVIifSg_UQFQuVmE"
    fid = update.message.voice.file_id
    voice_file = await context.bot.get_file(fid)
    path = user_id+'_chatbot.opus'
    await voice_file.download_to_drive(custom_path=path)
    try:
        os.system('ffmpeg -i '+path+' -ac 2 -b:a 192k '+user_id+'_chatbot.mp3')
    except Exception as e:
        print('error converting voice file: ',e)
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Error converting voice message to text')
        return
    # s = transcribe('chatbot_voice_message_file.mp3')
    s = transcribe(user_id+'_chatbot.mp3')


    await context.bot.send_message(chat_id=update.effective_chat.id, text='transcripted voice message:\n'+s, parse_mode='Markdown')
    print('transcripted voice message:\n'+s)
    os.remove(user_id+'_chatbot.mp3')
    os.remove(user_id+'_chatbot.opus')
    print('voice message processed')
        # TODO transition to global dict of lists instead of global list
    print('User: '+s)
    message_to_append = {
        'role': 'user',
        'content': s
    }
    # message_list.append(message_to_append)
    # print('chat length: ',len(message_list))


    print(f'user id: {user_id}  type: {type(user_id)}')

    print(f'Chat id: {user_id} User: {update.message.text}')
    # message_to_append = {
    #     'role': 'user',
    #     'content': update.message.text
    # }
    if not user_id in chats:
        chats.update({user_id: [system_message]})
    chats[user_id].append(message_to_append)

        # chats.update({chat_id: [message_to_append]})
    # message_list.append(message_to_append)
    print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}')

    gpt_response = ''
    while True:
        try:
            gpt_response = client.chat.completions.create(
                model=default_gpt_model,
                messages=chats[user_id],
                n=1,
                temperature = temperature,
                stream = False)
            gpt_response = gpt_response.choices[0].message.content
            print('GPT: '+gpt_response)
            break
        except openai.RateLimitError:
            print('limit error, trying again')
            time.sleep(1)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')
    message_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    if not user_id in chats:
        chats.update({user_id: [system_message]})
    chats[user_id].append(message_to_append)
    print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}')




async def debug_to_chat_onoff_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global debug_to_chat
    if update.message.text == '/debug on':
        debug_to_chat = True
        await context.bot.send_message(chat_id=update.effective_chat.id, text='debug set to True')

    elif update.message.text == '/debug off':
        debug_to_chat = False
        await context.bot.send_message(chat_id=update.effective_chat.id, text='debug set to False')


async def start_restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO initialize a message list and add it to global dict
    # message_list=[]
    user_id = str(update.effective_user.id)
    print(update.message.text)
    chats.pop(user_id,None)
    # chats[user_id].append(message_to_append)
    # string_to_output = 'Hi!'
    # await context.bot.send_message(chat_id=update.effective_chat.id, text=string_to_output)
    # message_to_append = {
    #     'role': 'assistant',
    #     'content': string_to_output
    # }
    # message_list.append(message_to_append)
    # print('chat length: ',len(message_list))
    


async def text_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # TODO transition to global dict of lists instead of global list
    # print(update.message.contact)
    # print(update.chat_member)
    # print(update.effective_user.id)
    # chat_id = update.effective_chat.id
    user_id = str(update.effective_user.id)
    print(f'Got text message: {update.message.text} from user id: {user_id}')

    message_to_append = {
        'role': 'user',
        'content': update.message.text
    }
    if not user_id in chats:
        chats.update({user_id: [system_message]})
    chats[user_id].append(message_to_append)
    print('chat dict:')
    pprint.pprint(chats)

    # try:
    #     tokens = num_tokens_from_messages(chats[user_id], default_gpt_model)
    #     print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}, Tokens: {tokens}')
    # except Exception as e:
    #     print('error getting tokens: ',e)
    #     tokens = 0
    # if debug_to_chat:
    #     await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Got Message! Chat length: {len(chats[user_id])}, Tokens: {tokens}')
    # if tokens>50000:
    #     await context.bot.send_message(chat_id=update.effective_chat.id, text=f'Warning, close to max tokens. Tokens: {tokens}')

    gpt_response = ''
    time_to_wait = 1
    while True:
        try:
            gpt_response = client.chat.completions.create(model=default_gpt_model,messages=chats[user_id],n=1,temperature = temperature,stream = False)
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='Got response from API!')

            gpt_response = gpt_response.choices[0].message.content
            print('GPT: '+gpt_response)
            break
        except openai.RateLimitError:
            print('limit error, trying again')
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='API rate limit error, trying again')
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2
        except openai.APIError as e:
            # print(e.message)
            print(f'API error: {e}, trying again')
            if debug_to_chat:
                await context.bot.send_message(chat_id=update.effective_chat.id, text='API timeout error, trying again')
            time.sleep(time_to_wait)
            time_to_wait = time_to_wait*2

    await context.bot.send_message(chat_id=update.effective_chat.id, text=gpt_response, parse_mode='Markdown')
    message_to_append = {
        'role': 'assistant',
        'content': gpt_response
    }
    # message_list.append(message_to_append)
    # print('chat length: ',len(message_list))
    chats[user_id].append(message_to_append)

        # chats.update({chat_id: [message_to_append]})
    # message_list.append(message_to_append)
    print(f'Chat id: {user_id} Chat length: {len(chats[user_id])}')





if __name__ == '__main__':
    main()
    

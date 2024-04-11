import os
import json
import ydb
import ydb.iam
import requests
from random import randint
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot import types
#from dotenv import load_dotenv #remove in YC

#load_dotenv() #remove in YC

ydb_endpoint=os.getenv('YDB_ENDPOINT')
ydb_database=os.getenv('YDB_DATABASE')
#ydb_token=os.getenv('YDB_TOKEN') #remove in YC

#speechkit_token=os.getenv('SPEECHKIT_TOKEN')#remove in YC
speechkit_token = '' #use in YC

speechkit_folder_id = os.getenv('SPEECHKIT_FOLDER_ID')

tg_token = os.getenv('TG_TOKEN')

# Create driver in global space.
driver = ydb.Driver(
  endpoint=ydb_endpoint,
  database=ydb_database,
  #credentials=ydb.AccessTokenCredentials(ydb_token) #remove in YC
  credentials=ydb.iam.MetadataUrlCredentials() #use in YC
)
# Wait for the driver to become active for requests.
driver.wait(fail_fast=True, timeout=5)
session = driver.table_client.session().create()

bot = telebot.TeleBot(tg_token)

start_text = 'этот бот поможет тебе озвучить любой текст.\nразными языками и разными голосами.\n\n' \
        'доступны мужские и женские голоса, в разных амплуа.\n\nподдерживается несколько языков:\n' \
        '🇷🇺 русский\n🇬🇧 английский\n🇩🇪 немецкий\n🇰🇿 казахский\n🇺🇿 узбекский\n\n' \
        'перечень голосов, языков, и прочих возможностей будет расширяться.\n\n' \
        'бот временно бесплатный. ограничение: 300 символов на один запрос.\n\n' \
        'создатель/по всем вопросам @konstela\nприсоединяйся: @zhukov_tech'

faq_text = 'для правильй постановки ударения используй «+» перед ударной гласной. например: б+ольшая, больш+ая.\n' \
        'для создания пауз используй тире «-». например: мы - лучшие.\n\n' \
        'знаком ⚡️ отмечены наилучшие по тембру, эмоциям, интонациям и качеству звучания голоса.\n\n' \
        'так как качественный речевой синтез удовольствие недешевое - мне пришлось ограничить объем текста до 300 символов.'

about_text = 'данный бот преобразует текст в речь с помощью нейросетевой технологии синтеза речи.\n' \
'на данный момент для синтеза речи доступны голоса на русском, английском, казахском и узбекском языках, включая разный пол и разные амплуа.\n\n' \
'бот временно функционирует бесплатно, в тестовом режиме.\n\n' \
'бот создан и поддерживается с помощью облачных технологий.\n\n' \
'создатель/по всем вопросам: @konstela\nприсоединяйся: @zhukov_tech\n\n' \

send_text = 'вышли текст для озвучки. напоминаю, принимается текст объемом до 300 знаков.'

def check_spot(session, from_id): #проверяем в каком меню находится пользователь
    result_sets = session.transaction().execute(
        f'select spot from user where id == {from_id}',
        commit_tx=True,
    )
    if not result_sets[0].rows: #если ответ пустой, значит пользователя в базе нет: добавляем
        session.transaction().execute(f'upsert into user (id, spot) values ({userid}))', commit_tx=True)
        return 0
    else: #иначе если ответ есть
      for row in result_sets[0].rows:
        user_spot = row.spot
        return user_spot
      
def update_spot(session, from_id, spot):
    session.transaction().execute(
        f'upsert into user (id, spot) values ({from_id}, {spot})', 
        commit_tx=True,
        )
    
def keyboard(key_type="start_menu"):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup = types.ReplyKeyboardMarkup(row_width=1)
    if key_type == "start_menu":
        markup.add(KeyboardButton("примеры голосов"),KeyboardButton("озвучить текст"),KeyboardButton("faq"),KeyboardButton("о боте"))
    elif key_type == "voice_menu":
        markup.add(KeyboardButton("🇷🇺 RU: Алёна ⚡️"),
                   KeyboardButton("🇷🇺 RU: Женя"),
                   KeyboardButton("🇷🇺 RU: Женя (добрый) ⚡️"),
                   KeyboardButton("🇷🇺 RU: Марина"),
                   KeyboardButton("🇷🇺 RU: Марина (раздраженный) ⚡️"),
                   KeyboardButton("🇷🇺 RU: Ермил ⚡️"),
                   KeyboardButton("🇷🇺 RU: Филипп"),
                   KeyboardButton("🇷🇺 RU: Захар"),
                   KeyboardButton("🇷🇺 RU: Руслан"),
                   KeyboardButton("🇩🇪 DE: Лея"),
                   KeyboardButton("🇬🇧 EN: Джон"),
                   KeyboardButton("🇰🇿 KZ: Мади"),
                   KeyboardButton("🇰🇿 KZ: Амира"),
                   KeyboardButton("🇺🇿 UZ: Нигора"),
                   KeyboardButton("назад")
                   )
    else:
        markup.add(KeyboardButton("примеры голосов"),KeyboardButton("озвучить текст"),KeyboardButton("faq"),KeyboardButton("о боте"))
    return markup

def speechkit_synth(speechkit_token, text, lang, voice, emotion=None):
   url = 'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize'
   headers = {
       'Authorization': 'Bearer ' + speechkit_token,
   }

   data = {
       'text': text,
       'lang': lang,
       'voice': voice,
       'emotion': emotion,
       'format': 'mp3',
       'folderId': speechkit_folder_id
   }

   with requests.post(url, headers=headers, data=data, stream=True) as resp:
       if resp.status_code != 200:
           raise RuntimeError("Invalid response received: code: %d, message: %s" % (resp.status_code, resp.text))

       for chunk in resp.iter_content(chunk_size=None):
           yield chunk

def synth(chat_id, text, lang, voice, emotion=None):
    random_numb = randint(0, 10000000)
    lenght = len(text)
    if lenght < 300:
        with open(f'/tmp/{random_numb}_zhukov_speech.mp3', "wb") as f:
            for audio_content in speechkit_synth(speechkit_token, text, lang, voice, emotion):
                f.write(audio_content)
        bot.send_document(chat_id, open(f'/tmp/{random_numb}_zhukov_speech.mp3', 'rb'))
        update_spot(session, chat_id, 0)
        bot.send_message(chat_id,"подписывайся: @zhukov_tech",reply_markup=keyboard("start_menu"))
    else:
        bot.send_message(chat_id, f'слишком много символов. у тебя - {lenght}, нужно менее 300.')

@bot.message_handler(commands=["start"]) #если юзер запускает бота
def start_message(message):
    if message.from_user.id != 321588402:
        bot.send_message(message.from_user.id,"бот в разработке.\n\nподписывайся: @zhukov_tech")
        return
    spot = 0 #находится в меню 0
    session.transaction().execute(
     f'upsert into user (id, spot) values ({message.from_user.id}, {spot})', 
     commit_tx=True,
     ) #добавляем юзера в базу
    bot.send_message(message.chat.id, start_text, reply_markup=keyboard())

@bot.message_handler(func=lambda message:True)
def all_messages(message):
    if message.from_user.id != 321588402:
        bot.send_message(message.from_user.id,"бот в разработке.\n\nподписывайся: @zhukov_tech")
        return
    spot = check_spot(session, message.from_user.id)
    if message.text == "назад":
        update_spot(session, message.from_user.id, 0) #spot 0 (главное меню)
        bot.send_message(message.from_user.id,"подписывайся: @zhukov_tech",reply_markup=keyboard("start_menu"))
        return
    if spot == 0:    
        if message.text == "примеры голосов":
            update_spot(session, message.from_user.id, 1) #spot 1 (меню со списком для прослушивания)
            bot.send_message(message.from_user.id, "выбери голос для прослушивания\n\n⚡️ - наилучшие голоса",reply_markup=keyboard("voice_menu"))
            return
        elif message.text == "озвучить текст":
            update_spot(session, message.from_user.id, 2) #spot 2 (меню со списком для озвучивания)
            bot.send_message(message.from_user.id, "выбери голос, который будет озвучивать твой текст\n\n⚡️ - наилучшие голоса",reply_markup=keyboard("voice_menu"))
            return
        elif message.text == "faq":
            bot.send_message(message.from_user.id, faq_text)
            return
        elif message.text == "о боте":
            bot.send_message(message.from_user.id, about_text)
            return
    elif spot == 1 or spot == 2:
        if message.text == "🇷🇺 RU: Алёна ⚡️":
            if spot == 1: 
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Алёна')
                return
            else:
                update_spot(session, message.from_user.id, 3) #spot 3 (голос Алёна)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Женя":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Джейн')
                return
            else:
                update_spot(session, message.from_user.id, 4) #spot 4 (голос Джейн)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Женя (добрый) ⚡️":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример доброго голоса Джейн')
                return
            else:
                update_spot(session, message.from_user.id, 5) #spot 5 (добрый голос Джейн)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Марина":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Марина')
                return
            else:
                update_spot(session, message.from_user.id, 6) #spot 6 (голос Омаж)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Марина (раздраженный) ⚡️":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример раздраженного голоса Марина')
                return
            else:
                update_spot(session, message.from_user.id, 7) #spot 7 (раздраженный голос Омаж)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Ермил ⚡️":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример доброго голоса Ермил')
                return
            else:
                update_spot(session, message.from_user.id, 8) #spot 8 (голос Ермил)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Филипп":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Филипп')
                return
            else:
                update_spot(session, message.from_user.id, 9) #spot 9 (голос Филипп)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Захар":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Захар')
                return
            else:
                update_spot(session, message.from_user.id, 10) #spot 10 (голос Захар)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇷🇺 RU: Руслан":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Руслан')
                return
            else:
                update_spot(session, message.from_user.id, 11) #spot 11 (голос Мадирус)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇩🇪 DE: Лея":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Лея')
                return
            else:
                update_spot(session, message.from_user.id, 12) #spot 12 (голос Лея)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇬🇧 EN: Джон":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Джон')
                return
            else:
                update_spot(session, message.from_user.id, 13) #spot 13 (голос Джон)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇰🇿 KZ: Мади":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Мади')
                return
            else:
                update_spot(session, message.from_user.id, 14) #spot 14 (голос Мади)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇰🇿 KZ: Амира":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Амира')
                return
            else:
                update_spot(session, message.from_user.id, 15) #spot 15(голос Амира)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
        elif message.text == "🇺🇿 UZ: Нигора":
            if spot == 1:
                bot.send_message(message.from_user.id, 'здесь будет пример голоса Нигора')
                return
            else:
                update_spot(session, message.from_user.id, 16) #spot 16 (голос Нигора)
                bot.send_message(message.from_user.id, send_text, reply_markup=types.ReplyKeyboardRemove(selective=False))
                return
    elif spot == 3:
        synth(message.from_user.id, message.text, 'ru-RU', 'alena')
        return
    elif spot == 4:
        synth(message.from_user.id, message.text, 'ru-RU', 'jane')
        return
    elif spot == 5:
        synth(message.from_user.id, message.text, 'ru-RU', 'jane', 'good')
        return
    elif spot == 6:
        synth(message.from_user.id, message.text, 'ru-RU', 'omazh')
        return
    elif spot == 7:
        synth(message.from_user.id, message.text, 'ru-RU', 'omazh', 'evil')
        return
    elif spot == 8:
        synth(message.from_user.id, message.text, 'ru-RU', 'ermil')
        return
    elif spot == 9:
        synth(message.from_user.id, message.text, 'ru-RU', 'filipp')
        return
    elif spot == 10:
        synth(message.from_user.id, message.text, 'ru-RU', 'zahar')
        return
    elif spot == 11:
        synth(message.from_user.id, message.text, 'ru-RU', 'madirus')
        return
    elif spot == 12:
        synth(message.from_user.id, message.text, 'de-DE', 'lea')
        return
    elif spot == 13:
        synth(message.from_user.id, message.text, 'en-US', 'john')
        return
    elif spot == 14:
        synth(message.from_user.id, message.text, 'kk-KK', 'madi')
        return
    elif spot == 15:
        synth(message.from_user.id, message.text, 'kk-KK', 'amira')
        return
    elif spot == 16:
        synth(message.from_user.id, message.text, 'uz-UZ', 'nigora')
        return
    
#bot.infinity_polling() #remove in YC

# Cloud Function Handler
def handler(event,context):
    global speechkit_token
    speechkit_token = context.token["access_token"]
    body = json.loads(event['body'])
    update = telebot.types.Update.de_json(body)
    bot.process_new_updates([update])
    return {
    'statusCode': 200,
    'body': 'ok',
    }

# -*- coding: utf-8 -*-
import os

import telebot
from flask import Flask, request
import psycopg2

import time
import atexit

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from lxml import html
import requests


TOKEN = 'Your telegram bot token'
SOURCE_SITE_URL = 'https://coinmarketcap.com/new/'
bot = telebot.TeleBot(TOKEN)
DATABASE_URL = 'Database url'
server = Flask(__name__)
scheduler = BackgroundScheduler()
atexit.register(lambda: scheduler.shutdown())

@bot.message_handler(commands=['start'])
def start(message):
    #bot.reply_to(message, 'Hello, ' + message.from_user.first_name + '. I will send you new cryptocurrencies added to coinmarketcap.com')
    bot.send_message(message.chat.id, 'Hello, ' + message.from_user.first_name + '. I will send you new cryptocurrencies added to coinmarketcap.com')
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats_info(chat_id) values(%s);",(message.chat.id,))
    conn.commit()
    cursor.close()
    conn.close()


#@bot.message_handler(func=lambda message: True, content_types=['text'])
#def echo_message(message):
#    bot.reply_to(message, message.text)


@server.route('/' + TOKEN, methods=['POST'])
def getMessage():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "!", 200


@server.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook(url='https://coinmarketbot.herokuapp.com/' + TOKEN)
    return "!", 200

def check_new_crypto():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM currencies")
    old_list = [item[0] for item in cursor.fetchall()]
    tree = html.fromstring(requests.get(SOURCE_SITE_URL).text)
    a_tags =  tree.xpath("//table [@id='trending-recently-added']//td[contains(@class, 'currency-name')]/a")
    new_list = []
    for a in a_tags:
        new_list.append(a.xpath("text()")[0])
    new_items = [item for item in new_list if item not in old_list]
    if len(new_items):
        for item in new_items:
            cursor.execute("INSERT INTO currencies(name) VALUES(%s);",(item,))
        conn.commit()
        cursor.execute("SELECT chat_id FROM chats_info")
        for chat_id in cursor.fetchall():
            bot.send_message(chat_id[0],'\n'.join(new_items))
    cursor.close()
    conn.close()
if __name__ == "__main__":
    scheduler.start()
    scheduler.add_job(func=check_new_crypto,trigger=IntervalTrigger(seconds=300),id='check_new_crypto_job',name='Looking for new crypto currency in the table',replace_existing=True)
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))




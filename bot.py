#!/usr/bin/env python
# -*- coding: utf-8 -*-
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler
from bs4 import BeautifulSoup as bs
import os,time
import logging
import requests
import threading
import json
import pymongo
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
# Connection to MongoDB Server
myclient = pymongo.MongoClient("mongodb+srv://bot:bot@motor.4ilok.mongodb.net")
mydb = myclient["motor"]
status = mydb["status"]
logger = logging.getLogger(__name__)

os.environ['TZ'] = 'Asia/Kolkata'
time.tzset()
# Stages
FIRST= range(1)
# Callback data
MOIST, EXIT, BACK, MOTOR, ON, OFF, RFRH, HUM, TEMP, RAIN, COMP = range(11)
# function to interact with mongodb
def mongo(data,met,user='ML Prediction'):
    if met==0: # Initialize MongoDB
        print("MongoDB init")
        timedat = time.strftime('%X %x %Z')
        temp = {"_id":"0","status": data,"time":timedat,"lastread":"0","by":user}
        status.insert_one(temp)
        return timedat
    elif met==1: #Updating previous data
        print("MongoDB Update Process")
        timedat = time.strftime('%X %x %Z')
        temp = {"_id":"0"}
        newtemp = {"$set":{"status": data,"time":timedat,"by":user}}
        status.update_one(temp,newtemp)
        return timedat
    elif met==2: # Reading the available data
        print("MongoDB Reading")
        for x in status.find({},{ "_id": 0, "status": 1,"time":1,"lastread":1,"by":1}):
            temp=x
        timedat = time.strftime('%X %x %Z')
        id = {"_id":"0"}
        up = {"$set":{"lastread":timedat}}
        status.update_one(id,up)
        msg=int(temp['status'])
        timed=temp['time']
        last=temp['lastread']
        by=str(temp['by'])
        return msg,timed,last,by
    else:
        print("Method not specified or invalid method")
        return -1,-1

def thingspeakpost(Field_id,val,API='C8QRPW8NKUI9XATP'):
    URl='https://api.thingspeak.com/update?api_key='
    KEY=API
    ZONE='&timezone=Asia%2FKolkata'
    HEADER='&field'+str(Field_id)+'={}'.format(val)
    NEW_URL=URl+KEY+ZONE+HEADER
    print(NEW_URL)
    request = requests.get(NEW_URL)
    soup = bs(request.text,"lxml")
    allLines = soup.text
    status=int(allLines)
    return status

def readthingspeak(Field_id,API='GGAS9S9IXEW7Y0S2',ch='1193476'):
    URL='https://api.thingspeak.com/'
    CHA='channels/'+ch+'/fields/'
    F_ID=str(Field_id)+'/last.json?api_key='
    KEY=API
    ZONE='&timezone=Asia%2FKolkata'
    NEW_URL=URL+CHA+F_ID+KEY+ZONE
    print(NEW_URL)
    get_data=requests.get(NEW_URL).json()
    #print(get_data)
    msg=[]
    mst=str(get_data['field'+str(Field_id)])
    time=str(get_data['created_at'])
    msg=[mst,time]
    #print(feild_1)
    return msg

def readthingspeakall(n,API='GGAS9S9IXEW7Y0S2',ch='1193476'):
    URL='https://api.thingspeak.com/'
    CHA='channels/'+ch+'/feeds/last.json?api_key='
    KEY=API
    ZONE='&timezone=Asia%2FKolkata'
    NEW_URL=URL+CHA+KEY+ZONE
    print(NEW_URL)
    get_data=requests.get(NEW_URL).json()
    #print(get_data)
    time=str(get_data['created_at'])
    msg=[]*5
    for i in range(n):
        msg.append(str(get_data['field'+str(i+1)]))
    return msg,time

def statuscheck(Field_id,API='GGAS9S9IXEW7Y0S2',ch='1193476'):
    URL='https://api.thingspeak.com/'
    CHA='channels/'+ch+'/fields/'
    F_ID=str(Field_id)+'/last.json?api_key='
    KEY=API
    ZONE='&timezone=Asia%2FKolkata'
    NEW_URL=URL+CHA+F_ID+KEY+ZONE
    print(NEW_URL)
    get_data=requests.get(NEW_URL)
    statuscode=int(get_data.status_code)
    if statuscode == 200:
        msg = get_data.json()
        mst=int(msg['field'+str(Field_id)])
        return mst
    elif statuscode in [405,409,429,500,502,503]:
        return -1
    else:
        return 99

def start(update, context):
    """Send message on `/start`. https://api.thingspeak.com/channels/1193476/fields/1/last.txt?api_key=GGAS9S9IXEW7Y0S2"""
    # Get user that sent /start and log his name
    user = update.message.from_user
    logger.info("User %s started the conversation.", user.username)
    # Build InlineKeyboard where each button has a displayed text
    # and a string as callback_data
    # The keyboard is a list of button rows, where each row is in turn
    # a list (hence `[[...]]`).
    keyboard = [
        [
            InlineKeyboardButton("💧 Moisture", callback_data=str(MOIST)),
            InlineKeyboardButton("⛅ Humidity", callback_data=str(HUM)),
        ],
        [
            InlineKeyboardButton("🌡️ Temparature", callback_data=str(TEMP)),
            InlineKeyboardButton("🌧️ Rainfall Status", callback_data=str(RAIN)),
        ],
        [InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))],
        [InlineKeyboardButton("✔️ Complete info", callback_data=str(COMP))],
        [InlineKeyboardButton("🛑 Quit", callback_data=str(EXIT))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Send message with text and appended InlineKeyboard
    update.message.reply_text(text='Hello @{}\nYou can Check Your Field Status here'.format(user.username))
    update.message.reply_text(text='🖥 Main Menu 🖥', reply_markup=reply_markup)
    # Tell ConversationHandler that we're in state `FIRST` now
    return FIRST

def start_over(update, context):
    """Prompt same text & keyboard as `start` does but not as new message"""
    # Get CallbackQuery from Update
    query = update.callback_query
    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("💧 Moisture", callback_data=str(MOIST)),
            InlineKeyboardButton("⛅ Humidity", callback_data=str(HUM)),
        ],
        [
            InlineKeyboardButton("🌡️ Temparature", callback_data=str(TEMP)),
            InlineKeyboardButton("🌧️ Rainfall Status", callback_data=str(RAIN)),
        ],
        [InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))],
        [InlineKeyboardButton("✔️ Complete info", callback_data=str(COMP))],
        [InlineKeyboardButton("🛑 Quit", callback_data=str(EXIT))],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Instead of sending a new message, edit the message that
    # originated the CallbackQuery. This gives the feeling of an
    # interactive menu.
    query.edit_message_text(text="🖥 Main Menu 🖥", reply_markup=reply_markup)
    return FIRST

def moisture(update, context):
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("🚰 Pump Settings", callback_data=str(MOTOR))
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    a=readthingspeak(1)
    moi='Moisture 💧 in the Soil : {}%'.format(a[0])+'\nLast Updated on : '+a[1]
    query.edit_message_text(
        text=moi,reply_markup=reply_markup
    )
    return FIRST

def raincheck(update, context):
    """Show new choice of buttons"""
    a=statuscheck(2)
    if a==1:
        query = update.callback_query
        query.answer()
        keyboard = [
            [
                InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data=str(BACK))
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        moi="It's raining 🌧️ out there"+"\n"+'Last Updated on : '
        query.edit_message_text(text=moi,reply_markup=reply_markup)
        return FIRST
    else:
        query = update.callback_query
        query.answer()
        keyboard = [
            [
                InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))
            ],
            [
                InlineKeyboardButton("🔙 Back", callback_data=str(BACK))
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        moi="It's not raining 🌞"+"\n"+'Last Updated on : '
        query.edit_message_text(text=moi,reply_markup=reply_markup)
        return FIRST

def temparature(update, context):
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    a=readthingspeak(1)
    moi='Temparature 🌡️ in the Field : {}°C'.format(a[0])+'\nLast Updated on : '+a[1]
    query.edit_message_text(
        text=moi,reply_markup=reply_markup
    )

def humidity(update, context):
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    a=readthingspeak(1)
    moi='Humidity ⛅ in the Field : {}%'.format(a[0])+'\nLast Updated on : '+a[1]
    query.edit_message_text(
        text=moi,reply_markup=reply_markup
    )

def getall(update, context):
    """Show new choice of buttons"""
    query = update.callback_query
    query.answer()
    keyboard = [
        [
            InlineKeyboardButton("🚰 Pump Status", callback_data=str(MOTOR))
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    a,time=readthingspeakall(5)
    if a[2] == 1:
        rain='True'
    else:
        rain='False'
    moi='⛅ Humidity : {}%'.format(a[3])+"\n"+'🌡️ Temparature : {}°C'.format(a[4])+"\n"+'💧 Moisture : {}%'.format(a[0])+"\n"+'🌧️ Is Raining : '+rain+"\n"+'⌚ Last Updated  : '+time
    query.edit_message_text(
        text=moi,reply_markup=reply_markup
    )

def motoron(update, context):
    user = update.effective_message.chat.username
    stat = mongo(1,1,user)
    query = update.callback_query
    query.answer()
    keyboard = [
    [
            InlineKeyboardButton("🔙 Back", callback_data=str(MOTOR))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text='✔️ Running Status Changed\nSwitched ON by @'+user+' at : '+stat,reply_markup=reply_markup)
    return FIRST
def motoroff(update, context):
    user = update.effective_message.chat.username
    stat = mongo(0,1,user)
    query = update.callback_query
    query.answer()
    keyboard = [
    [
            InlineKeyboardButton("🔙 Back", callback_data=str(MOTOR))
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text='✔️ Running Status Changed\nSwitched OFF by @'+user+' at : '+stat,reply_markup=reply_markup)
    return FIRST

def refreshstat(update, context):
    a,b,c,d=mongo(0,2)
    motor(update, context, c)
    return FIRST

def motor(update, context, rfrh=''):
    """Show new choice of buttons"""
    a,b,c,d=mongo(0,2)
    if a == 1:
        query = update.callback_query
        query.answer()
        keyboard = [
            [
            InlineKeyboardButton("🛑 Switch OFF", callback_data=str(OFF)),
            InlineKeyboardButton("🔄 Refresh Status", callback_data=str(RFRH)),
            ],
            [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK)),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if d=='ML Prediction':
            if rfrh == '':
                moi='The Pump is Already Running\nSwitched ON by '+d+' at : '+b
            else:
                moi='The Pump is Already Running\nSwitched ON by '+d+' at : '+b+'\nLast Check : '+rfrh
        else:
            if rfrh == '':
                moi='The Pump is Already Running\nSwitched ON by @'+d+' at : '+b
            else:
                moi='The Pump is Already Running\nSwitched ON by @'+d+' at : '+b+'\nLast Check : '+rfrh
        query.edit_message_text(text=moi,reply_markup=reply_markup)
        return FIRST
    elif a == 0:
        query = update.callback_query
        query.answer()
        keyboard = [
            [
            InlineKeyboardButton("✅ Switch ON", callback_data=str(ON)),
            InlineKeyboardButton("🔄 Refresh Status", callback_data=str(RFRH)),
            ],
            [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK)),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        if d=='ML Prediction':
            if rfrh == '':
                moi='The Pump is OFF\nSwitched OFF Using '+d+' at : '+b
            else:
                moi='The Pump is OFF\nSwitched OFF Using '+d+' at : '+b+'\nLast Check : '+rfrh
        else:
            if rfrh == '':
                moi='The Pump is OFF\nSwitched OFF by @'+d+' at : '+b
            else:
                moi='The Pump is OFF\nSwitched OFF by @'+d+' at : '+b+'\nLast Check : '+rfrh
        query.edit_message_text(text=moi,reply_markup=reply_markup)
        return FIRST
    else:
        query = update.callback_query
        query.answer()
        keyboard = [
            [
            InlineKeyboardButton("✅ Switch ON", callback_data=str(ON)),
            InlineKeyboardButton("🛑 Switch OFF", callback_data=str(OFF)),
            InlineKeyboardButton("🔄 Refresh Status", callback_data=str(RFRH)),
            ],
            [
            InlineKeyboardButton("🔙 Back", callback_data=str(BACK)),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        moi=rfrh+'❌ Unknown Error Occured\nCould Not Retrive the Current Running Status of Motor'
        query.edit_message_text(text=moi,reply_markup=reply_markup)
        return FIRST

def end(update, context):
    """Returns `ConversationHandler.END`, which tells the
    ConversationHandler that the conversation is over"""
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="See you next time!")
    return ConversationHandler.END


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater("1157845506:AAE_9ok6uazi1iVIPxpQnrcY6YA2ai7NCd0", use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Setup conversation handler with the states FIRST and SECOND
    # Use the pattern parameter to pass CallbackQueries with specific
    # data pattern to the corresponding handlers.
    # ^ means "start of line/string"
    # $ means "end of line/string"
    # So ^ABC$ will only allow 'ABC'
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            FIRST: [
                CallbackQueryHandler(moisture, pattern='^' + str(MOIST) + '$'),
                CallbackQueryHandler(end, pattern='^' + str(EXIT) + '$'),
                CallbackQueryHandler(start_over, pattern='^' + str(BACK) + '$'),
                CallbackQueryHandler(motor, pattern='^' + str(MOTOR) + '$'),
                CallbackQueryHandler(motoroff, pattern='^' + str(OFF) + '$'),
                CallbackQueryHandler(motoron, pattern='^' + str(ON) + '$'),
                CallbackQueryHandler(refreshstat, pattern='^' + str(RFRH) + '$'),
                CallbackQueryHandler(temparature, pattern='^' + str(TEMP) + '$'),
                CallbackQueryHandler(humidity, pattern='^' + str(HUM) + '$'),
                CallbackQueryHandler(getall, pattern='^' + str(COMP) + '$'),
                CallbackQueryHandler(raincheck, pattern='^' + str(RAIN) + '$'),
            ]
        },
        fallbacks=[CommandHandler('start', start)],
    )

    # Add ConversationHandler to dispatcher that will be used for handling
    # updates
    dp.add_handler(conv_handler)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()

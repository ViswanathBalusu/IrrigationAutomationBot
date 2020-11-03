#!/usr/bin/env python
# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup as bs
import os,time
import logging
import requests
import json
import pymongo
import RPi.GPIO as GPIO
import numpy as np
import joblib


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
SWITCH = 17
GPIO.setup(SWITCH,GPIO.OUT)
myclient = pymongo.MongoClient("mongodb+srv://bot:bot@motor.4ilok.mongodb.net")
mydb = myclient["motor"]
status = mydb["status"]
os.environ['TZ'] = 'Asia/Kolkata'
time.tzset()
loaded_model = joblib.load('model.sav')

def mongo(data,met,user='ML Prediction'):
    if met==0: # Initialize MongoDB
        print("MongoDB init")
        timedat = time.strftime('%X %x %Z')
        temp = {"_id":"0","status": data,"time":timedat,"lastread":"0","MLread":"0","by":user}
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
        for x in status.find({},{ "_id": 0, "status": 1, "by":1}):
            temp=x
        timedat = time.strftime('%X %x %Z')
        id = {"_id":"0"}
        up = {"$set":{"MLread":timedat}}
        status.update_one(id,up)
        msg=int(temp['status'])
        by=str(temp['by'])
        return msg,by
    else:
        print("Method not specified or invalid method")
        return -1,-1

def readthingspeakall(n,API='VTXPIEW9CIOSWPQS',ch='1214586'):
    URL='https://api.thingspeak.com/'
    CHA='channels/'+ch+'/feeds/last.json?api_key='
    KEY=API
    ZONE='&timezone=Asia%2FKolkata'
    NEW_URL=URL+CHA+KEY+ZONE
    print(NEW_URL)
    get_data=requests.get(NEW_URL).json()
    msg=[]*n
    for i in range(n):
        msg.append(str(get_data['field'+str(i+1)]))
    return msg
def predict():
    a=readthingspeakall(4)
    test_vals=np.array([[int(a[2]),int(a[0]),int(a[1])]])
    pred=loaded_model.predict(test_vals)
    stat,by=mongo(0,2) #reading mongo
    if by=='ML Prediction':
        if pred == 1: #Pediction =1
            if a[3] == 1: # Rain status
                if stat==1: # checking motor status
                    temp=mongo(0,1) # if turned on ML Will be switched off
                    return -2,''
                else:
                    print("It's raining already, So no need of Pump") # Not turned on
                    return -1,''
            else:
                stat=mongo(1,1) # Rain Status 0
                return 1,''
        else:
            stat=mongo(0,1)
            return 0,''
    else:
        if stat==1:
            return 2,by
        else:
            return 3,by

def main():
    while True:
        a,by=predict()
        if a==1:
            GPIO.output(SWITCH, 0)
            print('Switched on by ML Prediction')
        elif a==0:
            GPIO.output(SWITCH, 1)
            print('Switched off by ML Prediction')
        elif a==-2:
            GPIO.output(SWITCH, 1)
            print('Switched off by ML Prediction because its Raining dude')
        elif a==2:
            GPIO.output(SWITCH, 0)
            print('Switched on by '+by)
        elif a==3:
            GPIO.output(SWITCH, 1)
            print('Switched off by '+by)
        else:
            print("Cannot Retrieve Current Status")


if __name__ == '__main__':
    main()

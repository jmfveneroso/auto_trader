#!/usr/bin/env python
# coding=UTF-8

import time
import os
from poloniex import Poloniex
from database_client import DatabaseClient
from bottle import route, run, template
from trade_bot import TradeBot

poloniex = Poloniex()
bot = TradeBot()
db = DatabaseClient(bot)

@route('/clear/<currency>')
def clear(currency):
  return bot.clear(currency)

@route('/force_buy/<currency>')
def update(currency):
  return bot.force(currency, 'Buy')

@route('/force_sell/<currency>')
def update(currency):
  return bot.force(currency, 'Sell')

@route('/update.json')
def update():
  return db.get_candlesticks()

@route('/gui.css')
def css():
  f = open("gui/gui.css")
  return f.read()

@route('/gui.js')
def js():
  f = open("gui/gui.js")
  return f.read()

@route('/')
def index():
  f = open("gui/gui.html")
  return f.read()

if __name__ == "__main__":
  db.start()
  run(host='localhost', port=8082)
  db.stop()

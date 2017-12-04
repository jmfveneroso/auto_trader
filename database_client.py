#!/usr/bin/env python
# coding=UTF-8

import os
import datetime
import time
import logging
from pymongo import MongoClient
from bson.json_util import dumps
from multiprocessing.dummy import Process as Thread
from threading import Lock
from classifier import TradeClassifier
from poloniex import Poloniex
import json

logger = logging.getLogger(__name__)
logging.basicConfig()

api = Poloniex()
mutex = Lock()

def str_to_datetime(timestamp):
  return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') 

def datetime_to_str(dt):
  return '{:%Y-%m-%d %H:%M:%S}'.format(dt)

class TradeBot:
  def __init__(self):
    self.ticker = None
    self.state = {
      'usdt_btc': {}, 'usdt_zec': {}, 'usdt_xrp': {}, 
      'usdt_dash': {}, 'usdt_eth': {}
    } 
    self.load_bot_state()

  def load_bot_state(self):
    f = open('bot_state.json', 'r')
    text = f.read()

    if len(text) > 0:
      self.state = json.loads(text)
    f.close()

  def save_bot_state(self):
    f = open('bot_state.json', 'w')
    f.write(json.dumps(self.state))
    f.close()

  def set_classifier_info(self, currency, prediction, accuracy, std_deviation):
    self.state[currency]['prediction'] = prediction
    self.state[currency]['accuracy'] = accuracy
    self.state[currency]['std_deviation'] = std_deviation

  def buy(self, currency):
    state = self.state[currency]
    lowest_ask = float(self.ticker[currency]['lowestAsk'])
    highest_bid = float(self.ticker[currency]['highestBid'])

    price = lowest_ask * 1.05
    amount = float(state['balance']) / lowest_ask

    result = api.buy(currency.upper(), price, amount)

    total = 0
    for trade in result['resultingTrades']:
      price = float(trade['rate'])
      total = float(trade['total'])
    print 'BUY:', result

    state['balance'] -= float(total)
    state['status'] = 'Holding'
    state['stop_gain'] = 1.03 * price
    state['stop_loss'] = 0.99 * price
    print state['stop_gain'], state['stop_loss']
    if not 'trades' in state: state['trades'] = []

    state['trades'].append({
      'type': 'Buy',
      'date': datetime_to_str(datetime.datetime.now()),
      'price': lowest_ask,
      'balance': state['balance'],
      'volume': amount,
      'tax': 0.25
    })

  def sell(self, currency):
    return
    state = self.state[currency]
    lowest_ask = float(self.ticker[currency]['lowestAsk'])
    highest_bid = float(self.ticker[currency]['highestBid'])

    price = 0.2 * highest_bid + 0.2 * lowest_ask

    # check if order already exists
    # if it exists check if it has been executed
    # if yes
    # log sell
    # remove stops
    # update state to idle
    # update balance

    # else
    # call polo api sell method, store order number

  def check_stops(self, currency):
    state = self.state[currency]
    current_price = float(self.ticker[currency]['last'])
    if current_price > state['stop_gain']:
      state['status'] = 'Sell'
    if current_price < state['stop_loss']:
      state['status'] = 'Sell'

  def update(self, ticker):
    mutex.acquire()
    self.ticker = ticker
    for currency in self.state: 
      self.state[currency]['lowest_ask'] = float(self.ticker[currency]['lowestAsk'])
      self.state[currency]['highest_bid'] = float(self.ticker[currency]['highestBid'])
      self.state[currency]['last_price'] = float(self.ticker[currency]['last'])

      if self.state[currency]['status'] == 'Holding':
        self.check_stops(currency)
      elif self.state[currency]['status'] == 'Buy':
        self.buy(currency)
      elif self.state[currency]['status'] == 'Sell':
        self.sell(currency)
      else: # idle.
        self.state[currency]['status'] = 'Idle'
    self.save_bot_state()
    mutex.release()

  def force(self, currency, status):
    self.state[currency]['status'] = status

  def end_of_candle_update(self):
    mutex.acquire()
    for currency in self.state: 
      state = self.state[currency]
      if state['status'] == 'idle':
        print 'idle'
    mutex.release()
    # self.update_currency_state(currency)

trade_bot = TradeBot()

classifier = TradeClassifier()

class DatabaseClient:
  def __init__(self):
    self.candles = {
     'usdt_btc':  [], 'usdt_eth': [], 'usdt_bch': [], 'usdt_ltc': [], 
     'usdt_xrp':  [], 'usdt_zec': [], 'usdt_etc': [], 'usdt_str': [], 
     'usdt_dash': [], 'usdt_nxt': [], 'usdt_xmr': [], 'usdt_rep': []
    }
    self.client = MongoClient('184.72.201.187')
    self.db = self.client.poloniex
    self.last_update = None
    self.most_recent_candle = datetime.datetime.min
    self.time_to_candle_end = None

  def merge_candles(self, currency, new_candles):
    # Delete old candles.
    oldest = datetime.datetime.now() - datetime.timedelta(days=5)
    i = 0
    while i < len(self.candles[currency]):
      if str_to_datetime(self.candles[currency][i]['date']) >= oldest:
        break 
    self.candles[currency] = self.candles[currency][i:]

    new_candles = [c for c in new_candles if c['currency_pair'] == currency]
    if len(new_candles) == 0:
      return

    # Replace from that date onwards.
    first_date = new_candles[0]['date']

    i = len(self.candles[currency]) - 1
    while i >= 0:
      if str_to_datetime(self.candles[currency][i]['date']) < first_date:
        break 
      i -= 1
      self.candles[currency][i]

    self.candles[currency] = self.candles[currency][:i+1]

    for c in new_candles:
      c['date'] = datetime_to_str(c['date'])
    self.candles[currency] += new_candles

  def get_candlesticks(self):
    mutex.acquire()
    self.data = {}
    self.data['candles'] = self.candles
    self.data['state'] = trade_bot.state
    self.data['time_to_candle_end'] = str(self.time_to_candle_end)
    mutex.release()
    return dumps(self.data)

  def force(self, currency, status):
    trade_bot.force(currency, status)

  def update_candles(self):
    after = datetime.datetime.min 
    if not self.last_update is None:
      after = self.last_update - datetime.timedelta(minutes=30)

    new_candles = list(self.db['candle_cache'].find(
      { 'date': { '$gt': after } }, 
      { '_id': 0, 'temp': 0 }
    ).sort('date', 1))

    for currency in self.candles:
      self.merge_candles(currency.lower(), new_candles)

    self.last_update = datetime.datetime.now()
    self.most_recent_candle = str_to_datetime(self.candles['usdt_btc'][-1]['date'])

  def train_classifiers(self):
    for currency in ['usdt_btc', 'usdt_zec', 'usdt_xrp', 'usdt_dash', 'usdt_eth']:
      prediction, accuracy, std_deviation = classifier.fit(self.candles, currency)
      trade_bot.set_classifier_info(currency, prediction, accuracy, std_deviation)

  def trigger_candle_end(self):
    print 'End of candle'
    self.train_classifiers()
    candle_ended = True
    trade_bot.end_of_candle_update()

  def get_ticker(self):
    ticker = {}
    for row in self.db['ticker'].find():
      ticker[row['_id'].lower()] = row
    return ticker

  def update_thread(self):
    self.update_candles()
    self.train_classifiers()

    candle_ended = False
    self.running = True
    while self.running:
      # try:
      ticker = self.get_ticker()

      self.update_candles()
      trade_bot.update(ticker)

      minutes_to_candle_end = self.most_recent_candle - datetime.datetime.now()
      self.time_to_candle_end = minutes_to_candle_end
      print 'Minutes to candle end:', minutes_to_candle_end
      if minutes_to_candle_end < datetime.timedelta(minutes=1):
        if not candle_ended:
          self.trigger_candle_end()
      elif minutes_to_candle_end > datetime.timedelta(minutes=10):
        candle_ended = False
      # except Exception as e:
      #   logger.error('Exception during main loop: ' + str(e))
      time.sleep(10)

  def start(self):
    self.thread = Thread(target=self.update_thread)
    self.thread.daemon = True
    self.thread.start()
    logger.info('Updater started')

  def stop(self):
    self.running = False
    self.thread.join()
    logger.info('Updater stopped')

if __name__ == "__main__":
  db = DatabaseClient()
  print db.get_candlesticks()

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
from misc import str_to_datetime, datetime_to_str
from trade_bot import TradeBot

logger = logging.getLogger(__name__)
logging.basicConfig()

api = Poloniex()
mutex = Lock()

classifier = TradeClassifier()

class DatabaseClient:
  currencies = ['usdt_btc', 'usdt_zec', 'usdt_xrp', 'usdt_dash', 'usdt_eth']

  def __init__(self, trade_bot):
    self.candles = {
     'usdt_btc':  [], 'usdt_eth': [], 'usdt_bch': [], 'usdt_ltc': [], 
     'usdt_xrp':  [], 'usdt_zec': [], 'usdt_etc': [], 'usdt_str': [], 
     'usdt_dash': [], 'usdt_nxt': [], 'usdt_xmr': [], 'usdt_rep': []
    }
    self.client = MongoClient('54.89.212.196')
    self.db = self.client.poloniex
    self.last_update = None
    self.last_candle = datetime.datetime.min
    self.predictions = {}
    self.trade_bot = trade_bot

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
    self.data['state'] = self.trade_bot.state
    mutex.release()
    return dumps(self.data)

  def update_candles(self):
    after = datetime.datetime.now() - datetime.timedelta(days=5)
    if not self.last_update is None:
      after = self.last_update - datetime.timedelta(minutes=30)

    new_candles = list(self.db['candle_cache'].find(
      { 'date': { '$gt': after } }, 
      { '_id': 0, 'temp': 0 }
    ).sort('date', 1))

    for currency in self.candles:
      self.merge_candles(currency.lower(), new_candles)

    # Train classifiers when the next candle begins.
    self.last_update = datetime.datetime.now()
    last_candle = str_to_datetime(self.candles['usdt_btc'][-1]['date'])
    if (last_candle > self.last_candle):
      self.last_candle = last_candle
    #   for currency in DatabaseClient.currencies:
    #     # We take out the last candle because it is still being formed.
    #     self.predictions[currency] = classifier.fit(self.candles[currency][:-1], currency)

  def test_classifier(self):
    candles = self.candles['usdt_btc']
    # prediction = classifier.fit(candles, 'usdt_btc')
    # return
    volume = float(1)
    price = float(0)
    holding = False

    trades = [0, 0]
    for i in range(192, len(candles)):
      if holding:
        if float(candles[i]['min']) < (1 - TradeClassifier.sell_loss) * price:
          print 'Sold', volume, 'at', candles[i]['date'], 'for $', candles[i]['min']
          volume = (1 - TradeClassifier.sell_loss) * volume
          print 'Yield:', volume
          trades[0] += 1
          holding = False
        elif float(candles[i]['max']) > (1 + TradeClassifier.sell_gain) * price:
          print 'Sold', volume, 'at', candles[i]['date'], 'for $', candles[i]['max']
          volume = (1 + TradeClassifier.sell_gain) * volume
          print 'Yield:', volume
          trades[1] += 1
          holding = False
        continue

      prediction = classifier.fit(candles[i-192:i], 'usdt_btc')
      # prediction = classifier.fit(candles[:i], 'usdt_btc')
      if prediction[0] == 1: # Buy
        holding = True
        price = float(candles[i]['close'])
        print 'Bought', volume, 'at', candles[i]['date'], 'for $', price
      print candles[i]['date'], trades

  def update_thread(self):
    # self.update_candles()


    f = open('candles_06_12_2017_11_28.json', 'r')
    self.candles = json.loads(f.read())
    self.test_classifier()
    return

    candle_ended = False
    self.running = True
    while self.running:
      ticker = {}
      for row in self.db['ticker'].find():
        if row['_id'].lower() in DatabaseClient.currencies:
          ticker[row['_id'].lower()] = row

      self.update_candles()
      self.trade_bot.update(ticker, self.predictions)

      time.sleep(4)

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

#!/usr/bin/env python
# coding=UTF-8

import os
import datetime
import time
import logging
from multiprocessing.dummy import Process as Thread
from pymongo import MongoClient
from poloniex import Poloniex

logger = logging.getLogger(__name__)

class DatabaseServer:
  # Time length of our request to the trade record API.
  timeskip = datetime.timedelta(hours=1)

  # The amount of trade history we are storing.
  lifespan = datetime.timedelta(days=5)

  # The candle size.
  candle_span = datetime.timedelta(minutes=15)

  currencies = [
   'USDT_BTC', 'USDT_ETH', 'USDT_BCH', 'USDT_LTC', 'USDT_XRP', 'USDT_ZEC', 
   'USDT_ETC', 'USDT_STR', 'USDT_DASH', 'USDT_NXT', 'USDT_XMR', 'USDT_REP'
  ]

  def __init__(self, poloniex, remote=False):
    self.poloniex = poloniex
    self.remote = remote
    self.running = False
    self.client = MongoClient()
    self.db = self.client.poloniex

  def now (self):
    return datetime.datetime.now()

  def get_candle_time(self, time):
    next_candle = time.replace(minute=0, second=0, microsecond=0)
    while next_candle < time:
      next_candle += DatabaseServer.candle_span
    return next_candle

  def add_to_candle(self, candles, currency_pair, date, price, volume, temp):
    price = float(price)
    candle_time = self.get_candle_time(date)
    if len(candles) == 0 or candle_time > candles[-1]['date']:
      candles.append({
        'date': candle_time, 'open': price, 'close': price, 
        'min': price, 'max': price, 'volume': float(volume),
        'temp': temp, 'currency_pair': currency_pair.lower()
      })
    elif candle_time == candles[-1]['date']:
      if price < float(candles[-1]['min']): candles[-1]['min'] = price
      if price > float(candles[-1]['max']): candles[-1]['max'] = price
      candles[-1]['close'] = price
      candles[-1]['volume'] += float(volume)
      candles[-1]['temp'] = temp
    else:
      assert False

  def update_candlesticks(self):
    for cp in DatabaseServer.currencies:
      cp = cp.lower()

      start = self.now() - DatabaseServer.lifespan
      candles = list(self.db['candle_cache'].find({ 
        'currency_pair': cp,
        'date': { '$gt': start },
        'temp': 0
      }).sort('date', 1))
      self.db['candle_cache'].remove({ 'currency_pair': cp })

      if len(candles) > 0:
        start = candles[-1]['date']
       
      trades = self.db[cp].find({ 'date': { '$gt': start } }).sort("date", 1)
      for t in trades:
        self.add_to_candle(candles, cp, t['date'], t['rate'], t['amount'], 0)
      candles[-1]['temp'] = True

      # ticks = self.db['ticker_buffer'].find().sort("date", 1)
      ticks = self.db['ticker_buffer'].find({ 'date': { '$gt': start } }).sort("date", 1)
      for t in ticks:
        self.add_to_candle(candles, cp, t['date'], t[cp.upper()]['last'], 0, 1)

      ticks = self.db['candle_cache'].insert(candles)
     
  def update_trade_records(self):
    for currency_pair in DatabaseServer.currencies:
      collection = self.db[currency_pair.lower()]

      # Remove old records.
      oldest = self.now() - DatabaseServer.lifespan
      cursor = collection.remove({ 'date':{ '$lt': oldest } })

      # Get newest trade record and update from that point onwards.
      start = oldest
      cursor = collection.find().sort("date", -1).limit(1)
      if cursor.count() > 0:
        start = cursor[0]['date']

      while True:
        end = start + DatabaseServer.timeskip
        trades = self.poloniex.return_market_trade_history(
          currency_pair.upper(), start, end
        )

        if len(trades) == 0:
          end -= DatabaseServer.timeskip
          continue

        for t in trades:
          t['_id'] = t['globalTradeID']
          del t['globalTradeID']

          # Check if trade record with this id already exists.
          if not collection.find({ '_id': t['_id'] }).count() > 0:
            collection.insert_one(t)

        logger.info('Added ' + str(len(trades)) + ' trades from ' + str(start) + ' to ' + str(end))
        logger.info('Total trade records: ' + str(collection.find().count()))

        if end > self.now():
          break

        time.sleep(5)
        start += DatabaseServer.timeskip
      logger.info('Updated ' + str(currency_pair))
    self.db['ticker_buffer'].remove({})

  def update_ticker(self):
    tick = self.poloniex.return_ticker()
    for market in tick:
      self.db['ticker'].update_one(
        {'_id': market},
        {'$set': tick[market]},
        upsert=True
      )
    
    tick['date'] = self.now() 
    self.db['ticker_buffer'].insert_one(tick)
    self.update_candlesticks()
    logger.info('Ticker updated')

  def initialize(self):
    logger.info('Started database server')
    self.db['candle_cache'].remove({})
    self.update_trade_records()
    self.update_candlesticks()

  def auto_update(self):
    counter = 0
    self.running = True
    while self.running:
      if counter % 30 == 0:
        self.update_trade_records()
      else:
        self.update_ticker()
      time.sleep(10)
      counter += 1

  def start(self):
    self.thread = Thread(target=self.auto_update)
    self.thread.daemon = True
    self.thread.start()
    logger.info('Updater started')

  def stop(self):
    self.running = False
    self.thread.join()
    logger.info('Updater stopped')

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO)
  db = DatabaseServer(Poloniex())
  db.initialize()
  db.start()

  time.sleep(1)
  while db.running:
    try:
      time.sleep(1)
    except:
      db.stop()

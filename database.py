#!/usr/bin/env python
# coding=UTF-8

import os
import datetime
import time
import logging
from multiprocessing.dummy import Process as Thread
from pymongo import MongoClient
from poloniex import Poloniex
from sshtunnel import SSHTunnelForwarder

logger = logging.getLogger(__name__)

class DB:
  timeskip = datetime.timedelta(hours=1)
  lifespan = datetime.timedelta(days=5)
  candle_span = datetime.timedelta(minutes=15)
  candle_start = datetime.timedelta(hours=12)

  def __init__(self, poloniex, ssh_forwarding=False):
    self.ssh_forwarding = ssh_forwarding
    if ssh_forwarding:
      self.server = SSHTunnelForwarder(
        'visconde.latin.dcc.ufmg.br',
        ssh_username='joao',
        ssh_pkey="/Users/joaomateusdefreitasveneroso/.ssh/id_rsa",
        remote_bind_address=('127.0.0.1', 27017)
      )
      self.server.start()
      self.client = MongoClient('127.0.0.1', self.server.local_bind_port) 
    else:
      self.client = MongoClient()

    self.db = self.client.poloniex
    self.poloniex = poloniex
    self.last_candles = {}

  def close(self):
    if self.ssh_forwarding:
      self.server.stop()

  def str_to_datetime(self, timestamp):
    return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') 

  def datetime_to_str(self, dt):
    return '{:%Y-%m-%d %H:%M:%S}'.format(dt)

  def add_trades(self, collection, trades):
    for t in trades:
      t['_id'] = t['globalTradeID']
      del t['globalTradeID']

      # Check if trade records with this id already exists.
      if not collection.find({ '_id': t['_id'] }).count() > 0:
        collection.insert_one(t)

  '''
  Removes trade records that are older than the determined
  lifespan.
  '''
  def clean_old_records(self, currency_pair):
    collection = self.db[currency_pair.lower()]
    threshold = datetime.datetime.now() - DB.lifespan
    cursor = collection.remove({ 'date':{ '$lt': threshold } })

  '''
  Updates trade records for a single currency pair from the
  determined lifespan up to now.
  '''
  def update_trade_records(self, currency_pair):
    collection = self.db[currency_pair.lower()]

    start = datetime.datetime.now() - DB.lifespan

    # Get newest trade record and update from that point.
    cursor = collection.find().sort("date", -1).limit(1)
    if cursor.count() > 0:
      start = cursor[0]['date']

    while True:
      end = start + DB.timeskip
      trades = self.poloniex.return_market_trade_history(
        currency_pair.upper(), start, end
      )

      if len(trades) == 0:
        end -= DB.timeskip
        continue

      self.add_trades(collection, trades)
      logger.info('Added ' + str(len(trades)) + ' trades from ' + str(start) + ' to ' + str(end))
      logger.info('Total trade records: ' + str(collection.find().count()))

      if end > datetime.datetime.now():
        break

      time.sleep(5)
      start += DB.timeskip
    logger.info('Finished updating ' + str(currency_pair))

  '''
  Update forward all currencies USD tethered.
  '''
  def update_all_currencies(self):
    currencies = [
     'USDT_BTC', 'USDT_ETH', 'USDT_BCH', 'USDT_LTC', 'USDT_XRP', 'USDT_ZEC', 
     'USDT_ETC', 'USDT_STR', 'USDT_DASH', 'USDT_NXT', 'USDT_XMR', 'USDT_REP'
    ]

    for currency_pair in currencies:
      logger.info('Updating ' + str(currency_pair))
      self.clean_old_records(currency_pair)
      self.update_trade_records(currency_pair)

    self.db['ticker_buffer'].remove({})

  def get_next_candle_time(self, time):
    next_candle = time.replace(minute=0, second=0)
    while next_candle < time:
      next_candle += DB.candle_span
    return next_candle

  def get_candlesticks(self, currency_pair):
    collection = self.db[currency_pair.lower()]
    candles = []

    open_p, close_p, high, low = 0, 0, 0, 0
    current_timestamp = None

    threshold = datetime.datetime.now() - DB.candle_start
    cursor = collection.find({ 'date':{ '$gt': threshold } })
    # cursor = collection.find().sort("date", 1)

    for trade in cursor:
      price = trade['rate']
      candle_time = self.get_next_candle_time(trade['date'])
      if candle_time == current_timestamp:
        if price < low:  low = price
        if price > high: high = price
        close_p = price
      else:
        if current_timestamp != None:
          candles.append((self.datetime_to_str(current_timestamp), open_p, close_p, high, low))
        open_p, close_p, high, low = price, price, price, price
        current_timestamp = candle_time

    cursor = self.db['ticker_buffer'].find().sort("time", 1)
    for ticker in cursor:
      price = ticker[currency_pair.upper()]['last']
      candle_time = self.get_next_candle_time(trade['date'])
      if candle_time == current_timestamp:
        if price < low:  low = price
        if price > high: high = price
        close_p = price
      elif candle_time > current_timestamp:
        if current_timestamp != None:
          candles.append((self.datetime_to_str(current_timestamp), open_p, close_p, high, low))
        open_p, close_p, high, low = price, price, price, price
        current_timestamp = candle_time

    candles.append((self.datetime_to_str(current_timestamp), open_p, close_p, high, low))
    return candles

class Ticker(object):
  def __init__(self, db, api, interval=10):
    self.api = api
    self.db = db
    self.mongo = MongoClient().poloniex
    self.interval = interval

  def updateTicker(self):
    tick = self.api.returnTicker()
    for market in tick:
      self.mongo['ticker'].update_one(
        {'_id': market},
        {'$set': tick[market]},
        upsert=True
      )
     
    tick['time'] = datetime.datetime.now()
    self.mongo['ticker_buffer'].insert_one(tick)
    logger.info('Ticker updated')

    return list(self.mongo['ticker'].find())

  def run(self):
    self._running = True
    self.counter = 0
    while self._running:
      self.updateTicker()
      if self.counter % 100 == 0:
        logger.info('Updating currencies')

        # Update trade history every 1000 seconds.
        self.db.update_all_currencies()
      time.sleep(self.interval)
      self.counter += 1

  def start(self):
    self._thread = Thread(target=self.run)
    self._thread.daemon = True
    self._thread.start()
    logger.info('Ticker started')

  def stop(self):
    self._running = False
    self._thread.join()
    logger.info('Ticker stopped')

if __name__ == "__main__":
  if not os.path.isfile("key.txt"):
    sys.exit('No key.txt file!')
  
  f = open("key.txt", "r")
  key, secret = tuple(f.readline().split(','))
  
  poloniex = Poloniex(key, secret)
  db = DB(poloniex)

  logging.basicConfig(level=logging.INFO)
  t = Ticker(db, poloniex)
  t.start()

  time.sleep(10)
  while t._running:
    try:
      time.sleep(10)
    except:
      t.stop()

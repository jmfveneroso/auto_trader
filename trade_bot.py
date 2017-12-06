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
import classifier

logger = logging.getLogger(__name__)
logging.basicConfig()

api = Poloniex()

class TradeBot:
  def __init__(self):
    self.ticker = None
    self.state = {
      'usdt_btc': {}, 'usdt_zec': {}, 'usdt_xrp': {}, 
      'usdt_dash': {}, 'usdt_eth': {}
    } 
    self.load()

  def load(self):
    f = open('bot_state.json', 'r')
    text = f.read()

    if len(text) > 0:
      self.state = json.loads(text)
    f.close()

    for currency in self.state: 
      s = self.state[currency]
      s['prediction'   ] = 0
      s['accuracy'     ] = 0
      s['std_deviation'] = 0

  def save(self):
    f = open('bot_state.json', 'w')
    f.write(json.dumps(self.state))
    f.close()

  def set_order(self, currency, order_type):
    s = self.state[currency]

    if order_type == 'Buy':
      price = s['lowest_ask'] * 0.9999
      amount = (float(s['balance']) - 0.0001) / price
      result = api.buy(currency.upper(), price, amount)
    else:
      price = s['highest_bid'] * 1.0001
      amount = float(s['invested']) * 0.999
      print 'Sell', amount, currency, 'at price', price
      result = api.sell(currency.upper(), price, amount)

    print result
    if 'error' in result:
      return
    s['order_number'] = result['orderNumber']

    for trade in result['resultingTrades']:
      price = float(trade['rate'])
      quantity = float(trade['amount'])
      s['incomplete_trades'].append((quantity, price, 0.0025))
      if order_type == 'Buy':
        s['balance'] -= float(trade['total'])
        s['invested'] += quantity * (1 - 0.0025)
      else:
        s['balance'] += float(trade['total']) * (1 - 0.0025)
        s['invested'] -= quantity


  def buy(self, currency):
    s = self.state[currency]

    # Finished trade.
    if s['balance'] < 0.01:
      # Log trade.
      if not 'trades' in s: s['trades'] = []

      price = 0
      volume = 0 # In dollars.
      fee = 0 
      for trade in s['incomplete_trades']:
        price += trade[1] * trade[0]
        fee += trade[2] * trade[0]
        volume += trade[1] * trade[0] * (1 - trade[2])

      quantity = sum([float(t[0]) for t in s['incomplete_trades']])
      fee = float(fee) / quantity
      price = float(price) / quantity
      s['trades'].append({
        'type': 'Buy',
        'date': datetime_to_str(datetime.datetime.now()),
        'price': price,
        'balance': s['prev_balance'],
        'volume': volume,
        'tax': fee
      }) 
      s['status'] = 'Holding'
      s['stop_loss'] = price * (1 - TradeClassifier.sell_loss)
      s['stop_gain'] = price * (1 + TradeClassifier.sell_gain)
       
    elif s['order_number'] == 0:
      self.set_order(currency, 'Buy')
    else:
      result = api.return_order_trades(s['order_number'])
      print s['order_number']
      print result

      # Cancel old order because we are going to update it anyway.
      err = None
      try:
        err = api.cancel(currency.upper(), s['order_number'])
      except:
        # Do nothing.      
        print 'Could not cancel:', err

      if 'error' in result:
        # Could not buy at the desired price. Try again.
        self.set_order(currency, 'Buy')
      else:
        for trade in result:
          price = float(trade['rate'])
          quantity = float(trade['amount'])
          fee = float(trade['fee'])
          s['incomplete_trades'].append((quantity, price, fee))
          s['balance'] -= float(trade['total'])
          s['invested'] += quantity * (1 - float(trade['fee']))
        s['order_number'] = 0

  def sell(self, currency):
    s = self.state[currency]

    # Finished trade.
    if float(s['invested'] * s['last_price']) < 0.01:
      # Log trade.
      if not 'trades' in s: s['trades'] = []

      price = 0
      volume = 0 # In dollars.
      fee = 0 
      for trade in s['incomplete_trades']:
        price += trade[1] * trade[0]
        fee += trade[2] * trade[0]
        volume += trade[1] * trade[0] * (1 - trade[2])

      quantity = sum([float(t[0]) for t in s['incomplete_trades']])
      fee = float(fee) / quantity
      price = float(price) / quantity
      s['trades'].append({
        'type': 'Sell',
        'date': datetime_to_str(datetime.datetime.now()),
        'price': price,
        'balance': s['balance'],
        'volume': volume,
        'tax': fee
      }) 
      s['status'] = 'Idle'
      s['stop_loss'] = 0
      s['stop_gain'] = 0
       
    elif s['order_number'] == 0:
      self.set_order(currency, 'Sell')
    else:
      result = api.return_order_trades(s['order_number'])
      print result

      # Cancel old order because we are going to update anyway.
      err = None
      try:
        err = api.cancel(currency, s['order_number'])
      except:
        # Do nothing.      
        print 'Could not cancel:', err

      if 'error' in result:
        # Could not buy at the desired price. Try again.
        self.set_order(currency, 'Sell')
      else:
        for trade in result:
          price = float(trade['rate'])
          quantity = float(trade['amount'])
          fee = float(trade['fee'])
          s['incomplete_trades'].append((quantity, price, fee))
          s['balance'] += float(trade['total']) * (1 - float(trade['fee']))
          s['invested'] -= quantity
        s['order_number'] = 0

  def check_stops(self, currency):
    s = self.state[currency]
    price = float(self.ticker[currency]['last'])
    if price > s['stop_gain']:
      s['status'] = 'Start Selling'
    if price < s['stop_loss']:
      s['status'] = 'Start Selling'

  def update(self, ticker, predictions):
    self.ticker = ticker
    for currency in self.state: 
      s = self.state[currency]
      if currency in predictions:
        s['prediction'   ] = predictions[currency][0]
        s['accuracy'     ] = predictions[currency][1]
        s['std_deviation'] = predictions[currency][2]
        s['prediction_date'] = predictions[currency][3]

      s['lowest_ask'   ] = float(self.ticker[currency]['lowestAsk'])
      s['highest_bid'  ] = float(self.ticker[currency]['highestBid'])
      s['last_price'   ] = float(self.ticker[currency]['last'])

      if s['status'] == 'Holding':
        self.check_stops(currency)
      elif s['status'] == 'Start Buying':
        s['prev_balance'] = s['balance']
        s['order_number'] = 0
        s['incomplete_trades'] = []
        s['status'] = 'Buy'
      elif s['status'] == 'Start Selling':
        s['prev_balance'] = s['balance']
        s['order_number'] = 0
        s['incomplete_trades'] = []
        s['status'] = 'Sell'
      elif s['status'] == 'Buy':
        self.buy(currency)
      elif s['status'] == 'Sell':
        self.sell(currency)
      else: # idle.
        s['status'] = 'Idle'
        # if s['prediction'] == 1:
        #   s['status'] = 'Start Buying'
    self.save()

  def force(self, currency, status):
    if status == 'Buy':
      if self.state[currency]['balance'] >= 0.01:
        self.state[currency]['status'] = 'Start Buying'
    elif status == 'Sell':
      if float(self.state[currency]['invested']) >= 0.0000001:
        self.state[currency]['status'] = 'Start Selling'

  def clear(self, currency):
    self.state[currency]['balance'] = 1.0
    self.state[currency]['stop_gain'] = 0
    self.state[currency]['stop_loss'] = 0
    self.state[currency]['status'] = 'Idle'
    self.state[currency]['trades'] = []
    self.state[currency]['invested'] = 0

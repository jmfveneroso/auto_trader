#!/usr/bin/env python
# coding=UTF-8

import urllib
import urllib2
import httplib
import json
import time
import os
import threading
import datetime
import hmac,hashlib
from sklearn import datasets
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import calibration_curve
from sklearn.externals import joblib
from sklearn.model_selection import cross_val_score

def create_timestamp(datestr, format="%Y-%m-%d %H:%M:%S"):
  return time.mktime(time.strptime(datestr, format))

class Poloniex:
  def __init__(self):
    if not os.path.isfile("key.txt"):
      sys.exit('No key.txt file!')
    
    f = open("key.txt", "r")
    key, secret = tuple(f.readline().strip().split(','))
    self.APIKey = key
    self.Secret = secret
 
  def post_process(self, before):
    after = before
 
    # Add timestamps if there isnt one but is a datetime
    if('return' in after):
      if(isinstance(after['return'], list)):
        for x in xrange(0, len(after['return'])):
          if(isinstance(after['return'][x], dict)):
            if('datetime' in after['return'][x] and 'timestamp' not in after['return'][x]):
              after['return'][x]['timestamp'] = float(create_timestamp(after['return'][x]['datetime']))
               
    return after
 
  def api_query(self, command, req={}):
 
    if(command == "returnTicker" or command == "return24Volume"):
      ret = urllib2.urlopen(urllib2.Request('https://poloniex.com/public?command=' + command))
      return json.loads(ret.read())
    elif(command == "returnOrderBook"):
      ret = urllib2.urlopen(urllib2.Request('https://poloniex.com/public?command=' + command + '&currencyPair=' + str(req['currencyPair'])))
      return json.loads(ret.read())
    else:
      req['command'] = command
      req['nonce'] = int(time.time()*1000)
      post_data = urllib.urlencode(req)
 
      sign = hmac.new(self.Secret, post_data, hashlib.sha512).hexdigest()
      headers = {
        'Sign': sign,
        'Key': self.APIKey
      }

      ret = None
      try: 
        ret = urllib2.urlopen(urllib2.Request('https://poloniex.com/tradingApi', post_data, headers))
        ret = ret.read()
      except httplib.IncompleteRead, e:
        ret = e.partial

      jsonRet = json.loads(ret)
      return self.post_process(jsonRet)
 
 
  def return_ticker(self):
    return self.api_query("returnTicker")
 
  def return24Volume(self):
    return self.api_query("return24Volume")
 
  def returnOrderBook (self, currencyPair):
    return self.api_query("returnOrderBook", {'currencyPair': currencyPair})
 
  def return_market_trade_history (self, currencyPair, start, end):
    query = 'https://poloniex.com/public?command=returnTradeHistory'
    query += '&currencyPair=' + currencyPair

    end = int(end.strftime("%s"))
    start = int(start.strftime("%s"))
    query += '&start=' + str(start)
    query += '&end=' + str(end)

    ret = None
    try: 
      req = urllib2.Request(query)
      ret = urllib2.urlopen(req)
      ret = ret.read()
    except httplib.IncompleteRead, e:
      return []

    trades = json.loads(ret)
    for trade in trades:
      trade['date'] = datetime.datetime.strptime(trade['date'], '%Y-%m-%d %H:%M:%S') 
      trade['date'] += datetime.timedelta(hours = -2)
      # trade['date'] = '{:%Y-%m-%d %H:%M:%S}'.format(trade['date'])

    return trades
 
 
  # Returns all of your balances.
  # Outputs:
  # {"BTC":"0.59098578","LTC":"3.31117268", ... }
  def returnBalances(self):
    return self.api_query('returnBalances')
 
  # Returns your open orders for a given market, specified by the "currencyPair" POST parameter, e.g. "BTC_XCP"
  # Inputs:
  # currencyPair  The currency pair e.g. "BTC_XCP"
  # Outputs:
  # orderNumber   The order number
  # type      sell or buy
  # rate      Price the order is selling or buying at
  # Amount    Quantity of order
  # total     Total value of order (price * quantity)
  def returnOpenOrders(self,currencyPair):
    return self.api_query('returnOpenOrders',{"currencyPair":currencyPair})
 
 
  # Returns your trade history for a given market, specified by the "currencyPair" POST parameter
  # Inputs:
  # currencyPair  The currency pair e.g. "BTC_XCP"
  # Outputs:
  # date      Date in the form: "2014-02-19 03:44:59"
  # rate      Price the order is selling or buying at
  # amount    Quantity of order
  # total     Total value of order (price * quantity)
  # type      sell or buy
  def returnTradeHistory(self,currencyPair):
    return self.api_query('returnTradeHistory',{"currencyPair":currencyPair})
 
  # Places a buy order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
  # Inputs:
  # currencyPair  The curreny pair
  # rate      price the order is buying at
  # amount    Amount of coins to buy
  # Outputs:
  # orderNumber   The order number
  def buy(self,currencyPair,rate,amount):
    return self.api_query('buy',{"currencyPair":currencyPair,"rate":rate,"amount":amount})
 
  # Places a sell order in a given market. Required POST parameters are "currencyPair", "rate", and "amount". If successful, the method will return the order number.
  # Inputs:
  # currencyPair  The curreny pair
  # rate      price the order is selling at
  # amount    Amount of coins to sell
  # Outputs:
  # orderNumber   The order number
  def sell(self,currencyPair,rate,amount):
    return self.api_query('sell',{"currencyPair":currencyPair,"rate":rate,"amount":amount})
 
  # Cancels an order you have placed in a given market. Required POST parameters are "currencyPair" and "orderNumber".
  # Inputs:
  # currencyPair  The curreny pair
  # orderNumber   The order number to cancel
  # Outputs:
  # succes    1 or 0
  def cancel(self,currencyPair,orderNumber):
    return self.api_query('cancelOrder',{"currencyPair":currencyPair,"orderNumber":orderNumber})

  def return_order_trades(self, orderNumber):
    return self.api_query('returnOrderTrades',{"orderNumber":orderNumber})

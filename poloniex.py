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
    key, secret = tuple(f.readline().split(','))
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

  # def get_inverting_points(self, quotes):
  #   good_candles, bad_candles = [], []
  #   for i in range(0, len(quotes)):
  #     current_price = float(quotes[i][2])
  #     max_price, min_price = 0, 99999999
  #     keep_buying, keep_selling = True, True

  #     for j in range(i + 1, len(quotes)):
  #       next_price = float(quotes[j][2])

  #       if keep_buying and next_price > max_price:
  #         max_price = next_price

  #       if keep_selling and next_price < min_price:
  #         min_price = next_price

  #       # Price can reduce at most 10%.
  #       if next_price < 0.99 * current_price:
  #         keep_buying = False

  #       # Price can reduce at most 10%.
  #       if next_price > 1.02 * current_price:
  #         keep_selling = False

  #     if float(min_price) / current_price < 0.99:
  #       quotes[i] = (quotes[i], 0)
  #     elif float(max_price) / current_price > 1.02:
  #       quotes[i] = (quotes[i], 1)
  #     else:
  #       quotes[i] = (quotes[i], 2)

  #   return quotes

  # def get_features(self, quotes, i):
  #   features = {}

  #   mean = sum([q[0][2] for q in quotes[:i]]) / (i + 1)
  #   resistances = [q[0] for q in quotes[:i] if q[1] == 0]
  #   supports    = [q[0] for q in quotes[:i] if q[1] == 1]
  #   # features['open_price'        ] = quotes[i][0][1]
  #   # features['close_price'       ] = quotes[i][0][2]
  #   # features['close_price'       ] = quotes[i][0][2]
  #   # features['high_price'        ] = quotes[i][0][3]

  #   if len(resistances) > 2:
  #     features['last_resistance'   ] = resistances[-1][2]
  #     features['last_resistance_2'   ] = resistances[-2][2]
  #     # features['last_resistance_3'   ] = resistances[-3][2]
  #   else:
  #     features['last_resistance'   ] = quotes[i][0][2]
  #     features['last_resistance_2'   ] = quotes[i][0][2]
  #     # features['last_resistance_3'   ] = quotes[i][0][2]

  #   if len(supports) > 2:
  #     features['last_support'      ] = supports[-1][2]
  #     features['last_support_2'      ] = supports[-2][2]
  #     # features['last_support_3'      ] = supports[-3][2]
  #   else:
  #     features['last_support'   ] = quotes[i][0][2]
  #     features['last_support_2' ] = quotes[i][0][2]
  #     # features['last_support_3' ] = quotes[i][0][2]

  #   features['close_price_higher_than_last_price' ] = quotes[i][0][2] > quotes[i-1][0][2]
  #   # features['close_price_higher_than_2_prices' ]   = quotes[i][0][2] > quotes[i-1][0][2] and quotes[i][0][2] > quotes[i-2][0][2]
  #   # features['close_price_higher_than_last_price_2' ] = quotes[i-1][0][2] > quotes[i-2][0][2]
  #   # features['close_price_higher_than_last_price_3' ] = quotes[i-2][0][2] > quotes[i-3][0][2]
  #   # features['close_price_higher_than_last_price_4' ] = quotes[i-3][0][2] > quotes[i-4][0][2]
  #   features['close_price_higher_than_resistance' ] = quotes[i][0][2] > features['last_resistance'] 
  #   features['close_price_lower_than_support'     ] = quotes[i][0][2] < features['last_support'   ] 
  #   features['close_price_higher_than_resistance_2' ] = quotes[i][0][2] > features['last_resistance_2'] 
  #   features['close_price_lower_than_support_2'     ] = quotes[i][0][2] < features['last_support_2'   ] 
  #   features['low_price_higher_than_resistance' ]   = quotes[i][0][4] > features['last_resistance'] 
  #   features['low_price_lower_than_support'     ]   = quotes[i][0][4] < features['last_support'   ] 
  #   features['1_red_candle'     ] = quotes[i][0][2] < quotes[i][0][1]
  #   features['2_red_candles'     ] = quotes[i][0][2] < quotes[i][0][1] and quotes[i-1][0][2] < quotes[i-1][0][1]
  #   features['3_red_candles'     ] = quotes[i][0][2] < quotes[i][0][1] and quotes[i-1][0][2] < quotes[i-1][0][1] and quotes[i-2][0][2] < quotes[i-2][0][1]
  #   # features['close_price_much_lower_than_support' ] = float(features['last_support']) / quotes[i][0][2] < 0.99
  #   # features['close_price_higher_than_mean'       ] = quotes[i][0][2] > mean

  #   features['prev_price_1_lower'] = quotes[i-1][0][2] < quotes[i][0][2]
  #   features['prev_price_2_lower'] = quotes[i-2][0][2] < quotes[i][0][2]
  #   features['prev_price_3_lower'] = quotes[i-3][0][2] < quotes[i][0][2]
  #   features['prev_price_4_lower'] = quotes[i-4][0][2] < quotes[i][0][2]
  #   features['prev_high_price_1_lower'] = quotes[i-1][0][3] < quotes[i][0][2]
  #   features['prev_high_price_2_lower'] = quotes[i-2][0][3] < quotes[i][0][2]
  #   features['prev_high_price_3_lower'] = quotes[i-3][0][3] < quotes[i][0][2]
  #   features['prev_high_price_4_lower'] = quotes[i-4][0][3] < quotes[i][0][2]


  #   # features['close_price_prev_1'] = quotes[i-1][0][2]
  #   # features['close_price_prev_2'] = quotes[i-2][0][2]
  #   # features['close_price_prev_3'] = quotes[i-3][0][2]
  #   # features['close_price_prev_4'] = quotes[i-4][0][2]
  #   # features['high_price_prev_1' ] = quotes[i-1][0][3]
  #   # features['high_price_prev_2' ] = quotes[i-2][0][3]
  #   # features['high_price_prev_3' ] = quotes[i-3][0][3]
  #   # features['high_price_prev_4' ] = quotes[i-4][0][3]
  #   return features

  # def create_feature_vectors(self, quotes):
  #   feature_vectors = []
  #   for i in range(4, len(quotes)):
  #     feature_vectors.append(self.get_features(quotes, i))
  #      
  #   return feature_vectors 

  # def plot_candlesticks(self):
  #   quotes = self.get_candlesticks(datetime.timedelta(minutes=10))
  #   quotes = self.get_inverting_points(quotes)
  #   x = self.create_feature_vectors(quotes)
  #   y = [q[1] for q in quotes[4:]]

  #   x = [[e[1] for e in el.items()] for el in x]

  #   # m = GaussianNB()
  #   m = LogisticRegression()
  #   # m = LinearSVC(C=1.0)
  #   # m = RandomForestClassifier(n_estimators=100)

  #   m = m.fit(x[:-10], y[:-10])
  #   predicted = m.predict(x)

  #   scores = cross_val_score(m, x, y, cv=5)
  #   print("Accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

  #   fig, ax = plt.subplots()
  #   fig.subplots_adjust(bottom=0.2)
  #   
  #   candlestick(ax, [q[0] for q in quotes], width=0.005)
  #   good_candles = [c[0] for c in quotes if c[1] == 1]

  #   buy_candles_x = [quotes[i][0][0] for i in range(4, len(quotes)) if predicted[i-4] == 1]
  #   buy_candles_y = [quotes[i][0][2] for i in range(4, len(quotes)) if predicted[i-4] == 1]
  #   # ax.scatter([p[0] for p in good_candles], [p[2] for p in good_candles], color='g')
  #   ax.scatter(buy_candles_x, buy_candles_y, color='y')
  #   # ax.scatter([p[0] for p in bad_candles], [p[2] for p in bad_candles], color='y')

  #   locator = HourLocator()
  #   formatter = DateFormatter('%d/%m %H:%M')
  #   ax.xaxis.set_major_locator(locator)
  #   ax.xaxis.set_major_formatter(formatter)
  #  
  #   # circle1 = Ellipse((date2num(datetime.datetime.now() + datetime.timedelta(hours=-5)), 7800), 0.013, 10, color='b')
  #   # ax.add_artist(circle1)
  #   ax.xaxis_date()
  #   # ax.axis('equal')
  #   ax.autoscale_view()
  #   plt.setp(plt.gca().get_xticklabels(), rotation=45, horizontalalignment='right')
  #   fig.savefig('data/graph.png')
  #   # plt.show()
  #   plt.close()

  #   return predicted[-1]

  # def create_dataset(self, dataset, window_size=20, distance=4):
  #   dataX, dataY = [], []
  #   for i in range(len(dataset) - window_size - distance - 1):
  #     # a = dataset[i:(i+look_back), 0]
  #     a = dataset[i:i + window_size, 0]
  #     # a = a.flatten()
  #     dataX.append(a)
  #     dataY.append(dataset[i + window_size + distance, 0])
  #   return numpy.array(dataX), numpy.array(dataY)

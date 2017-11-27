#!/usr/bin/env python

import urllib
import urllib2
import json
import time
import os
import threading
import datetime
import hmac,hashlib
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
from matplotlib.dates import DateFormatter, WeekdayLocator, DayLocator, HourLocator, MinuteLocator, MONDAY, AutoDateLocator, AutoDateFormatter
from matplotlib.finance import candlestick
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from matplotlib.patches import Ellipse, Circle
from sklearn import datasets
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import calibration_curve
from sklearn.externals import joblib
from sklearn.model_selection import cross_val_score
from poloniex import Poloniex

# import numpy
# import pandas
# import math
# from keras.models import Sequential
# from keras.layers import Dense
# from keras.layers import LSTM
# from sklearn.preprocessing import MinMaxScaler
# from sklearn.metrics import mean_squared_error
prediction_list = []
 
predicted = 'do nothing'
balances = None
class GetHandler(BaseHTTPRequestHandler):
  def do_GET(self):
    self.send_response(200)
    if self.path.endswith(".png"):
      f = open(self.path[1:])
      self.send_header('Content-type', 'image/png')
      self.end_headers()
      self.wfile.write(f.read())
      f.close()
    else:
      self.end_headers()
      html = '<html><body><img width="800" height="600" src="data/graph.png">' 
      html += '<div>' + str(prediction_list) + '</div>'

      if balances != None:
        for coin in balances:
          html += '<div>' + coin + ', ' + str(balances[coin]) + '</div>'
      html += '</body></html>' 

      self.wfile.write(html)

  def log_message(self, format, *args):
    return

def serve():
  server = HTTPServer(('localhost', 8080), GetHandler)
  server.serve_forever()
 
p = Poloniex(
  'GCRWWGGU-SXE53KFV-XEP9MPDZ-9LCDDV4K',
  '346fb5d4bd593d0a796ca24defa66bb1947da3cab31542048bba751ee700135285e4f3b008fdf830e672137634ccd5742118376cf499b7b5cb25667e564e5cb4'
)

def serve():
  server = HTTPServer(('localhost', 8080), GetHandler)
  server.serve_forever()

t1 = threading.Thread(target=serve)
t1.daemon = True
t1.start()

while True:
  p.update_records()
  predicted = p.plot_candlesticks()
  if (predicted == 0):
    predicted = 'sell'
  elif (predicted == 1):
    predicted = 'buy'
  else:
    predicted = 'do nothing'

  prediction_list.append(predicted)
  time.sleep(5)
  balances = p.returnBalances()

  time.sleep(30)

# print p.returnOpenOrders('USDT_BCH')
# print p.sell('USDT_BCH', 1300.00, 0.001)
# print p.cancel('USDT_BCH', 18217952003)

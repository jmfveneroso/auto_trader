#!/usr/bin/env python

import os
from database import DB
from poloniex import Poloniex

if not os.path.isfile("key.txt"):
  sys.exit('No key.txt file!')

f = open("key.txt", "r")
key, secret = tuple(f.readline().split(','))

api = Poloniex(key, secret)
db = DB(api)
print db.get_candlesticks('USDT_BTC')

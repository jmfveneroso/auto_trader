#!/usr/bin/env python
# coding=UTF-8

import os
import datetime
import time
import logging
from pymongo import MongoClient
from bson.json_util import dumps

logger = logging.getLogger(__name__)

def str_to_datetime(timestamp):
  return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') 

def datetime_to_str(dt):
  return '{:%Y-%m-%d %H:%M:%S}'.format(dt)

class DatabaseClient:
  def __init__(self):
    # self.client = MongoClient('54.167.109.34')
    self.client = MongoClient()
    self.db = self.client.poloniex

  def get_candlesticks(self, after=None):
    if after is None:
      after = datetime.datetime.min
    else:
      after = str_to_datetime(after)

    candles = list(self.db['candle_cache'].find(
      { 'date': { '$gt': after } }, 
      { '_id': 0, 'temp': 0 }
    ))

    for c in candles:
      c['date'] = datetime_to_str(c['date'])
 
    return dumps(candles)

if __name__ == "__main__":
  db = DatabaseClient()
  print db.get_candlesticks()

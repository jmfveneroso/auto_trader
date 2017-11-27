# dumbticker.py requires pymongo (and pandas)
# it saves the data returned from Poloniex.returnTicker() 
# in a mongodb collection at a set interval within a thread.
from pymongo import MongoClient


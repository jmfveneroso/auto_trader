#!/usr/bin/env python
# coding=UTF-8

import time
import os
from poloniex import Poloniex
from database_client import DatabaseClient
from bottle import route, run, template

poloniex = Poloniex()
db = DatabaseClient()

@route('/update/<timestamp>')
def update(timestamp):
  return db.get_candlesticks(timestamp)

@route('/gui.css')
def css():
  f = open("gui/gui.html")
  return f.read()

@route('/gui.js')
def js():
  f = open("gui/gui.js")
  return f.read()

@route('/')
def index():
  f = open("gui/gui.html")
  return f.read()

if __name__ == "__main__":
  run(host='localhost', port=8080)

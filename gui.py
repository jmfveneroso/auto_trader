#!/usr/bin/env python
# coding=UTF-8

import urllib
import urllib2
import json
import time
import os
import threading
from BaseHTTPServer import BaseHTTPRequestHandler
from BaseHTTPServer import HTTPServer
from poloniex import Poloniex
from database import DB

class GetHandler(BaseHTTPRequestHandler):
  def send_file(self, f):
    self.end_headers()
    self.wfile.write(f.read())
    f.close()

  def get_update_json(self):
    return json.dumps(db.get_candlesticks('USDT_BCH'))

  def do_GET(self):
    self.send_response(200)

    print self.path
    if self.path.endswith(".css"):
      f = open('gui/gui.css')
      self.send_header('Content-type', 'text/css')
      self.send_file(f)
    elif self.path.endswith(".js"):
      f = open('gui/gui.js')
      self.send_header('Content-type', 'text/javascript')
      self.send_file(f)
    elif self.path == '/update.json':
      self.end_headers()
      json = self.get_update_json()
      self.wfile.write(json)
    else:
      f = open("gui/gui.html")
      self.send_header('Content-type', 'text/html')
      self.send_file(f)


  def log_message(self, format, *args):
    return

def serve():
  server = HTTPServer(('localhost', 8082), GetHandler)
  server.serve_forever()

if __name__ == "__main__":
  f = open("key.txt", "r")
  key, secret = tuple(f.readline().split(','))
  global poloniex
  global db
  poloniex = Poloniex(key, secret)
  db = DB(poloniex, ssh_forwarding=True)

  serve()
  t1 = threading.Thread(target=serve)
  t1.daemon = True
  t1.start()
 
  try: 
    while True:
      time.sleep(5)
  except:
    db.close()

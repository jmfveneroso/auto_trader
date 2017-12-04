#!/usr/bin/env python
# coding=UTF-8

import datetime

def str_to_datetime(timestamp):
  return datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S') 

def datetime_to_str(dt):
  return '{:%Y-%m-%d %H:%M:%S}'.format(dt)

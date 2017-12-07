#!/usr/bin/env python
# coding=UTF-8

import json
import time
import os
import datetime
import hmac,hashlib
from sklearn import datasets
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.ensemble import AdaBoostClassifier
from sklearn.svm import LinearSVC
from sklearn.calibration import calibration_curve
from sklearn.externals import joblib
from sklearn.model_selection import cross_val_score
from sklearn.feature_extraction import DictVectorizer
from random import shuffle
import math
from misc import str_to_datetime, datetime_to_str

class TradeClassifier:
  sell_gain = 0.045
  sell_loss = 0.015
  window = 6

  def __init__(self):
    pass

  def classify_dataset(self, candles):
    for i in range(0, len(candles)):
      current_price = float(candles[i]['close'])
      gain_stop = current_price * (1 + TradeClassifier.sell_gain)
      loss_stop = current_price * (1 - TradeClassifier.sell_loss)

      buy = False
      for j in range(i + 1, len(candles)):
        min_price = float(candles[j]['min'])
        max_price = float(candles[j]['max'])
        
        if min_price < loss_stop:
          break 

        if max_price > gain_stop:
          buy = True
          break

      is_support = False
      is_resistance = False
      if i > 4 and i + 11 < len(candles):
        is_support = True
        is_resistance = True
        for j in range(i - 4, i + 7):
          if j == i: continue
          if candles[j]['close'] < current_price:
            is_support = False
          if candles[j]['close'] > current_price:
            is_resistance = False
          
      candles[i]['support']    = 1 if is_support else 0
      candles[i]['resistance'] = 1 if is_resistance else 0
      candles[i]['buy'] = 1 if buy else 0
    return candles

  def to_relative_price(self, reference_price, price):
    # return float(price) / reference_price
    return price

  def get_features(self, candles, i):
    features = {}

    avg = sum([c['close'] for c in candles[i-50:i]]) / float(len(candles[:i]))
    ref_price = candles[i - TradeClassifier.window]['min']
    resistances   = [c['close'] for c in candles[:i] if c['resistance'] == 1]
    supports      = [c['close'] for c in candles[:i] if c['support'] == 1]
    buying_points = [c['close'] for c in candles[:i] if c['buy'] == 1]

    green_candle = candles[i]['close'] > candles[i]['open']

    lower_shadow = candles[i]['close'] - candles[i]['min'] 
    if green_candle:
      lower_shadow = candles[i]['open'] - candles[i]['min'] 

    # features['upper_shadow'] = candles[i]['max'] - candles[i]['close'] 

    features['open']  = self.to_relative_price(ref_price, candles[i]['open' ])
    features['close'] = self.to_relative_price(ref_price, candles[i]['close'])
    features['min']   = self.to_relative_price(ref_price, candles[i]['min'  ])
    features['max']   = self.to_relative_price(ref_price, candles[i]['max'  ])
    features['relative_to_avg']   =  self.to_relative_price(ref_price, candles[i]['close']) - avg

    red_candles = 0
    for j in range(i, 0, -1):
      if candles[i]['close'] < candles[i]['open']:
        red_candles += 1
      else:
        break

    features['red_candles']  = red_candles
    features['relative_to_avg']  =  self.to_relative_price(ref_price, candles[i]['close']) - avg

    for j in range(i - TradeClassifier.window, i):
      features[str(j - (i - TradeClassifier.window)) + '_open']  = self.to_relative_price(ref_price, candles[j]['open' ])
      features[str(j - (i - TradeClassifier.window)) + '_close'] = self.to_relative_price(ref_price, candles[j]['close'])
      features[str(j - (i - TradeClassifier.window)) + '_candle_size'] = candles[j]['close'] - candles[j]['open']
      features[str(j - (i - TradeClassifier.window)) + '_min']   = self.to_relative_price(ref_price, candles[j]['min'  ])
      features[str(j - (i - TradeClassifier.window)) + '_max']   = self.to_relative_price(ref_price, candles[j]['max'  ])

    features['candle_length'] = candles[i]['close'] - candles[i]['open']
    features['variance']  = candles[i]['max'] - candles[i]['min']
    # features['green_candle_1'] = candles[i]['close'] > candles[i]['open']
    # features['green_candle_2'] = features['green_candle_1'] and candles[i-1]['close'] > candles[i-1]['open']
    # features['green_candle_3'] = features['green_candle_2'] and candles[i-2]['close'] > candles[i-2]['open']
    # features['big_lower_shadow'] = lower_shadow > candle_size

    for k in range(1, 5):
      if len(resistances) > k:
        features['higher_than_resistance_' + str(k)] = candles[i]['close'] - resistances[-k]
        features['resistance_' + str(k)] = self.to_relative_price(ref_price, resistances[-k])
      else:
        features['higher_than_resistance_' + str(k)] = 0
        features['resistance_' + str(k)] = 0

    for k in range(1, 5):
      if len(supports) > k:
        features['higher_than_support_' + str(k)] = candles[i]['close'] - supports[-k]
        features['support_' + str(k)] = self.to_relative_price(ref_price, supports[-k])
      else:
        features['higher_than_support_' + str(k)] = 0
        features['support_' + str(k)] = 0

    for k in range(1, 5):
      if len(buying_points) > k:
        features['higher_than_buying_point_' + str(k)] = candles[i]['close'] - buying_points[-k]
        features['buying_point_' + str(k)] = self.to_relative_price(ref_price, buying_points[-k])
      else:
        features['higher_than_buying_point_' + str(k)] = 0
        features['buying_point_' + str(k)] = 0

    return (features, candles[i]['buy'], candles[i])

  def create_feature_vectors(self, dataset):
    feature_vectors = []
    for i in range(TradeClassifier.window, len(dataset)):
      feature_vectors.append(self.get_features(dataset, i))
    return feature_vectors 

  def fit(self, candles, currency):
    self.classify_dataset(candles)
    feature_vectors = self.create_feature_vectors(candles)
    shuffle(feature_vectors)
    # feature_vectors = feature_vectors[::-1]

    test = feature_vectors[-10:]
    feature_vectors = feature_vectors[:-10]
    feature_dicts = [v[0] for v in feature_vectors]
    # vectorizer = DictVectorizer(sparse=False)
    # x = vectorizer.fit_transform(feature_dicts)
    x = [v[0].values() for v in feature_vectors]
    y = [v[1] for v in feature_vectors]

    # model_ = GaussianNB()
    # model_ = LinearSVC(C=1.0)
    # model_ = RandomForestClassifier(n_estimators=100)
    model_ = LogisticRegression()
    # model_ = AdaBoostClassifier(n_estimators=200)

    scores = cross_val_score(model_, x, y, cv=5)
    # print scores
    # print(currency + " accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

    # predicted = model.predict(x[:-10])
    # for i in range(0, len(predicted)):
    #   candles[4 + i]['prediction'] = predicted[i]

    right = 0
    wrong = 0
    model = model_.fit(x[:-100], y[:-100])
    predicted = model.predict(x[-100:-10])
    expected = y[-100:-10]
    for i in range(0, len(predicted)):
      if predicted[i] == 1:
        if expected[i] == 1: right += 1
        else: wrong += 1
      feature_vectors[-100 + i][2]['prediction'] = predicted[i]
    # print 'right: ', right, 'wrong:', wrong, 'accuracy:', float(right) / (right + wrong)

    # model = RandomForestClassifier(n_estimators=200)
    model = model_.fit(x, y)
    joblib.dump(model, 'classifiers/' + currency + '.pkl') 

    # bla = model.feature_importances_
    # for i in range(0, len(feature_dicts[0])):
    #   print feature_dicts[0].keys()[i], bla[i]

    x = [v[0].values() for v in test]
    # x = vectorizer.fit_transform(feature_dicts)
    predicted = model.predict(x)
    for i in range(0, len(predicted)):
      test[i][2]['prediction'] = predicted[i]

    date = datetime_to_str(datetime.datetime.now())
    return (predicted[-1], scores.mean(), scores.std(), date)

  def predict(self, candles, currency):
    model = joblib.load('classifiers/' + currency + '.pkl') 

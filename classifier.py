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
from sklearn.svm import LinearSVC
from sklearn.calibration import calibration_curve
from sklearn.externals import joblib
from sklearn.model_selection import cross_val_score
from sklearn.feature_extraction import DictVectorizer
from random import shuffle
import math

class TradeClassifier:
  sell_gain = 0.03
  sell_loss = 0.01

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

  def get_features(self, candles, i):
    features = {}

    resistances   = [c['close'] for c in candles[:i] if c['resistance'] == 0]
    supports      = [c['close'] for c in candles[:i] if c['support'] == 1]
    buying_points = [c['close'] for c in candles[:i] if c['buy'] == 1]

    green_candle = candles[i]['close'] > candles[i]['open']

    lower_shadow = candles[i]['close'] - candles[i]['min'] 
    if green_candle:
      lower_shadow = candles[i]['open'] - candles[i]['min'] 

    candle_size = math.fabs(candles[i]['close'] - candles[i]['open'])

    features['open'] = candles[i]['open']
    features['close'] = candles[i]['close']
    features['min'] = candles[i]['min']
    features['max'] = candles[i]['max']

    window = 4
    for j in range(i - window, i):
      features[str(j - (i - window)) + '_open']  = candles[j]['open']
      features[str(j - (i - window)) + '_close'] = candles[j]['close']
      features[str(j - (i - window)) + '_min']   = candles[j]['min']
      features[str(j - (i - window)) + '_max']   = candles[j]['max']

    features['candle_length']  = candle_size
    features['variance']  = candles[i]['max'] - candles[i]['min']
    features['green_candle_1'] = candles[i]['close'] > candles[i]['open']
    features['green_candle_2'] = features['green_candle_1'] and candles[i-1]['close'] > candles[i-1]['open']
    features['green_candle_3'] = features['green_candle_2'] and candles[i-2]['close'] > candles[i-2]['open']
    features['big_lower_shadow'] = lower_shadow > candle_size

    if len(resistances) > 3:
      features['resistance_1'   ] = resistances[-1]
      features['resistance_2'   ] = resistances[-2]
      features['resistance_3'   ] = resistances[-3]
      features['higher_than_resistance_1'   ] = candles[i]['close'] > resistances[-1]
      features['higher_than_resistance_2'   ] = candles[i]['close'] > resistances[-2]
      features['higher_than_resistance_3'   ] = candles[i]['close'] > resistances[-3]
    else:
      features['resistance_1'               ] = 0 
      features['resistance_2'               ] = 0
      features['resistance_3'               ] = 0
      features['higher_than_resistance_1'   ] = False
      features['higher_than_resistance_2'   ] = False
      features['higher_than_resistance_3'   ] = False

    if len(supports) > 3:
      features['support_1'       ] = supports[-1]
      features['support_2'       ] = supports[-2]
      features['support_3'       ] = supports[-3]
      features['lower_than_support_1'       ] = candles[i]['close'] < supports[-1]
      features['lower_than_support_2'       ] = candles[i]['close'] < supports[-2]
      features['lower_than_support_3'       ] = candles[i]['close'] < supports[-3]
    else:
      features['support_1'                  ] = 0 
      features['support_2'                  ] = 0
      features['support_3'                  ] = 0
      features['lower_than_support_1'       ] = False
      features['lower_than_support_2'       ] = False
      features['lower_than_support_3'       ] = False

    if len(buying_points) > 3:
      features['buying_point_1'] = buying_points[-1]
      features['buying_point_2'] = buying_points[-2]
      features['buying_point_3'] = buying_points[-3]
    else:
      features['buying_point_1'] = 0
      features['buying_point_2'] = 0
      features['buying_point_3'] = 0

    return (features, candles[i]['buy'], candles[i])

  def create_feature_vectors(self, dataset, window=4):
    feature_vectors = []
    for i in range(window, len(dataset)):
      feature_vectors.append(self.get_features(dataset, i))
    return feature_vectors 

  def fit(self, candles, currency):
    candles = candles[currency]
    self.classify_dataset(candles)
    feature_vectors = self.create_feature_vectors(candles)
    shuffle(feature_vectors)
    # feature_vectors = feature_vectors[::-1]

    test = feature_vectors[-10:]
    feature_vectors = feature_vectors[:-10]
    feature_dicts = [v[0] for v in feature_vectors]
    vectorizer = DictVectorizer(sparse=False)
    x = vectorizer.fit_transform(feature_dicts)
    y = [v[1] for v in feature_vectors]

    # model = GaussianNB()
    # model = LinearSVC(C=1.0)
    model = RandomForestClassifier(n_estimators=200)
    # model = LogisticRegression()

    scores = cross_val_score(model, x, y, cv=5)
    print scores
    print(currency + " accuracy: %0.2f (+/- %0.2f)" % (scores.mean(), scores.std() * 2))

    # predicted = model.predict(x[:-10])
    # for i in range(0, len(predicted)):
    #   candles[4 + i]['prediction'] = predicted[i]

    right = 0
    wrong = 0
    model = model.fit(x[:-100], y[:-100])
    predicted = model.predict(x[-100:-10])
    expected = y[-100:-10]
    for i in range(0, len(predicted)):
      if predicted[i] == 1:
        if expected[i] == 1: right += 1
        else: wrong += 1
      feature_vectors[-100 + i][2]['prediction'] = predicted[i]
    print 'right: ', right, 'wrong:', wrong, 'accuracy:', float(right) / (right + wrong)

    model = model.fit(x, y)
    joblib.dump(model, 'classifiers/' + currency + '.pkl') 

    feature_dicts = [v[0] for v in test]
    x = vectorizer.fit_transform(feature_dicts)
    predicted = model.predict(x)
    for i in range(0, len(predicted)):
      test[i][2]['prediction'] = predicted[i]

    return predicted[-1], scores.mean(), scores.std()

  def predict(self, candles, currency):
    model = joblib.load('classifiers/' + currency + '.pkl') 

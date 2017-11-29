(function () {

width = 600;
height = 400;

candles = {}

function draw_shadows(ctx, x, min, max, candle_size) {
  ctx.moveTo(x * (candle_size + 4) + candle_size / 2, height - max);
  ctx.lineTo(x * (candle_size + 4) + candle_size / 2, height - min);
  ctx.stroke();
}

function draw_candle(ctx, x, open, close, candle_size) {
  length = Math.abs(open - close);
  if (length < 2) length = 2;
  y = (open > close) ? open : close;

  if (open < close)
    ctx.fillStyle = "#00FF00";
  else 
    ctx.fillStyle = "#FF0000";

  ctx.fillRect(x * (candle_size + 4), height - y, candle_size, length);
}

function plot_candlesticks(candles, currency) {
  var c = document.getElementById(currency);
  var ctx = c.getContext("2d");

  data = []
  for (var i = 0; i < candles.length; i++) {
    if (candles[i]['currency_pair'] == 'usdt_' + currency) 
      data.push(candles[i])
  }
 
  min = 99999999.0
  max = 0.0
  for (var i = 0; i < data.length; i++) {
    if (parseFloat(data[i]['max']) > max) max = parseFloat(data[i]['max'])
    if (parseFloat(data[i]['min']) < min) min = parseFloat(data[i]['min'])
  }

  candle_size = parseInt(800 / data.length) - 4
  for (var i = 0; i < data.length; i++) {
    min_ = ((parseFloat(data[i]['min']) - min) / (max - min)) * height
    max_ = ((parseFloat(data[i]['max']) - min) / (max - min)) * height
    console.log('min: ' + min_ + ' max: ' + max_)
    draw_shadows(ctx, i, min_, max_, candle_size);
  }

  for (var i = 0; i < data.length; i++) {
    console.log(data[i])
    open  = ((parseFloat(data[i]['open']) - min) / (max - min)) * height 
    close = ((parseFloat(data[i]['close']) - min) / (max - min)) * height 
    // draw_candle(ctx, i, open, close, candle_size);
  }
}

function update_candlesticks() {
  $.get("/update/2012-12-12 00:00:00", function(data) {
    candles = JSON.parse(data)
  }).done(function (data) {
    candles = JSON.parse(data);
    candles.sort(function (x, y) {
      return Date(x['date']) < Date(y['date']);
    })

    currencies = [
     "btc", "eth", "bch", "ltc", "xrp", "zec", "etc", "str", "dash", "nxt", "xmr", "rep"
    ];

    for (var i = 0; i < currencies.length; i++) {
      plot_candlesticks(candles, currencies[i]);
    }
    
  });
}

$(document).ready(function() {
  update_candlesticks()
});

}())

(function () {

width = 1000;
height = 400;
margin_x = 68;
margin_y = 80;

last_update = new Date('1970-01-01 00:00:00')
candles = {}

function date_to_str(d) {
  function two(num) {
    return ("0" + num).slice(-2)
  }

  return d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate()) + ' ' +
         two(d.getHours()) + ':' + two(d.getMinutes()) + ':' + two(d.getSeconds());
}

function date_to_simple_str(d) {
  function two(num) {
    return ("0" + num).slice(-2)
  }

  return [two(d.getDate()) + '/' + two(d.getMonth() + 1),
         two(d.getHours()) + ':' + two(d.getMinutes())]
}

function draw_shadows(ctx, x, min, max, candle_size, skip_size) {
  ctx.beginPath();
  ctx.strokeStyle = "#aaaaaa";
  ctx.lineWidth = 1;
  ctx.moveTo(margin_x + x * (candle_size + skip_size) + candle_size / 2, margin_y + height - max);
  ctx.lineTo(margin_x + x * (candle_size + skip_size) + candle_size / 2, margin_y + height - min);
  ctx.stroke();
  ctx.strokeStyle = "#000000";
  ctx.closePath();
}

function draw_date_scale(ctx, x, candle_size, skip_size, date) {
  arr = date_to_simple_str(date);
  ctx.fillStyle = "#000000";
  ctx.fillText(arr[0], margin_x + x * (candle_size + skip_size) - 12, margin_y + height + 30);
  ctx.fillText(arr[1], margin_x + x * (candle_size + skip_size) - 12, margin_y + height + 42);

  ctx.strokeStyle = "#eeeeee";
  ctx.lineWidth = 1;
  ctx.moveTo(margin_x + x * (candle_size + skip_size), margin_y);
  ctx.lineTo(margin_x + x * (candle_size + skip_size), margin_y + height);
  ctx.stroke();
}

function draw_candle(ctx, x, open, close, candle_size, skip_size) {
  length = Math.abs(open - close);
  if (length < 2) length = 2;
  y = (open > close) ? open : close;

  ctx.beginPath();

  if (open < close)
    ctx.fillStyle = "#00FF00";
  else 
    ctx.fillStyle = "#FF0000";

  ctx.fillRect(margin_x + x * (candle_size + skip_size), height - y + margin_y, candle_size, length);

  ctx.closePath();
}

function minutes_between(date1, date2) {
  // Get 1 minute in milliseconds.
  var one_minute=1000*60;

  // Convert both dates to milliseconds.
  var date1_ms = date1.getTime();
  var date2_ms = date2.getTime();

  // Calculate the difference in milliseconds.
  var difference_ms = date2_ms - date1_ms;
    
  // Convert back to days and return
  return Math.round(difference_ms/one_minute); 
}

function draw_scale(ctx, min, max, min_date, max_date, candles) {
  ctx.beginPath();
  ctx.fillStyle = "#000000";

  step = (max - min) / 10;
  value = max;
  for (var i = 0; i < 11; i ++) {
    ctx.strokeStyle = "#eeeeee";
    ctx.lineWidth = 1;
    ctx.moveTo(margin_x - 10, margin_y + 40 * i);
    ctx.lineTo(margin_x + width + 10, margin_y + 40 * i);
    ctx.stroke();

    ctx.fillText(String(value.toFixed(4)), margin_x + width + 20, margin_y + 40 * i + 2);
    value -= step;
  }

  ctx.closePath();
  ctx.strokeStyle = "#000000";
}

function plot_candlesticks(new_candles, currency) {
  var c = document.getElementById(currency);
  var ctx = c.getContext("2d");
  ctx.clearRect(0, 0 , 1200, 600);

  currency_candles = []
  for (var i = 0; i < new_candles.length; i++) {
    if (new_candles[i]['currency_pair'] == 'usdt_' + currency) 
      currency_candles.push(new_candles[i])
  }

  if (candles[currency] === undefined) {
    candles[currency] = currency_candles;
  } else {
    last_candle = candles[currency][candles[currency].length - 1];
    last_candle_date = (new Date(last_candle['date'])).getTime();
    cmp = (new Date(currency_candles[0]['date']).getTime()) - last_candle_date

    if (cmp == 0) {
      candles[currency][candles[currency].length - 1] = currency_candles[0];
    } else if (cmp > 0) {
      candles[currency].shift();
      candles[currency].push(currency_candles[0]);
    }
  }

  data = candles[currency]
  console.log(data);
 
  min = 99999999.0
  max = 0.0
  for (var i = 0; i < data.length; i++) {
    if (parseFloat(data[i]['max']) > max) max = parseFloat(data[i]['max'])
    if (parseFloat(data[i]['min']) < min) min = parseFloat(data[i]['min'])
  }
  draw_scale(ctx, min, max, new Date(data[0]['date']), new Date(data[data.length - 1]['date']), data);

  skip_size = 1;
  candle_size = parseInt(((600 - (data.length - 1)) * skip_size) / data.length);
  candle_size = (candle_size > 0) ? candle_size : 1;
  for (var i = 0; i < data.length; i++) {
    min_ = ((parseFloat(data[i]['min']) - min) / (max - min)) * height
    max_ = ((parseFloat(data[i]['max']) - min) / (max - min)) * height
    draw_shadows(ctx, i, min_, max_, candle_size, skip_size);
  }

  last_date = null;
  var i = 0;
  for (; i < data.length; i++) {
    open  = ((parseFloat(data[i]['open']) - min) / (max - min)) * height 
    close = ((parseFloat(data[i]['close']) - min) / (max - min)) * height 
    draw_candle(ctx, i, open, close, candle_size, skip_size);
    if (i % 30 == 0)
      draw_date_scale(ctx, i, candle_size, skip_size, new Date(data[i]['date']));
    last_date = new Date(data[i]['date']);
  }

  remaining = (30 - (i % 30));
  i = i + remaining;
  last_date = new Date(last_date.getTime() + 15 * 60 * 1000 * remaining);
  draw_date_scale(ctx, i, candle_size, skip_size, last_date);

}

function update_plots() {
  for (var i = 0; i < currencies.length; i++) {
    plot_candlesticks(candles, currencies[i]);
  }
}

function update_candlesticks() {
  $.get("/update/" + date_to_str(last_update)).done(function (data) {
    // Have to add 2 hours because of time zones.
    // last_update = new Date((new Date()).getTime() + 2 * 60 * 60 * 1000);
    last_update = new Date()

    new_candles = JSON.parse(data);
    new_candles = new_candles.sort(function (x, y) {
      return (new Date(x['date']).getTime()) - (new Date(y['date'])).getTime();
    });

    if (new_candles.length == 0) return;

    currencies = [
    //   "btc", "eth", "bch", "ltc", "xrp", "zec", 
    //   "etc", "str", "dash", "nxt", "xmr", "rep"
    "btc"
    ];

    for (var i = 0; i < currencies.length; i++) {
      plot_candlesticks(new_candles, currencies[i]);
    }
  });
}

$(document).ready(function() {
  setInterval(function () {
    update_candlesticks();
  }, 5000);
});

}())

(function () {

width = 1000;
height = 400;
margin_x = 38;
margin_y = 34

candles = {}
states = {}

currencies = [
  // "btc", "eth", "bch", "ltc", "xrp", "zec", 
  // "etc", "str", "dash", "nxt", "xmr", "rep"
  'btc', 'zec', 'xrp', 'dash', 'eth'
];

function buy(event) {
  id = event.target.id;
  currency = id.substr(0, id.length - 4);
  $.get("/force_buy/usdt_" + currency);
}

function sell(event) {
  id = event.target.id;
  currency = id.substr(0, id.length - 5);
  $.get("/force_sell/usdt_" + currency);
}

function clear(event) {
  id = event.target.id;
  currency = id.substr(0, id.length - 6);
  $.get("/clear/usdt_" + currency);
}

function to_percentage(num) {
  return parseFloat(num * 100).toFixed(2)
}

function crop_num(num) {
  return parseFloat(num).toFixed(4)
}

function update_trades(currency, trades) {
  $('#' + currency + '_order_table').html('');
  if (trades == undefined) return;

  html = '';
  trades.reverse();
  for (var i = 0; i < trades.length; i++) {
    t = trades[i];
    html += '<tr><td>' + t['date']  + '</td><td>' + t['type']   + '</td><td>'
                       + crop_num(t['price']) + '</td><td>' + crop_num(t['volume']) + '</td><td>'
                       + crop_num(t['tax'])   + '</td><td>' + crop_num(t['balance'])   + '</td>';
  }
  $('#' + currency + '_order_table').html(html);
}

function update_info(data) {
  states = data['state'];

  for (var i = 0; i < currencies.length; i++) {
    state = states['usdt_' + currencies[i]];
    $('#' + currencies[i] + '_accuracy').text(
      to_percentage(state['accuracy']) + 
      '% (' + to_percentage(state['std_deviation']) + '%)'
    );

    $('#' + currencies[i] + '_status'     ).text(state['status']               );
    $('#' + currencies[i] + '_prediction' ).text(state['prediction']           );
    $('#' + currencies[i] + '_highest_bid').text(crop_num(state['highest_bid']));
    $('#' + currencies[i] + '_lowest_ask' ).text(crop_num(state['lowest_ask'] ));
    $('#' + currencies[i] + '_last_price' ).text(crop_num(state['last_price'] ));
    $('#' + currencies[i] + '_balance'    ).text(crop_num(state['balance']    ));
    $('#' + currencies[i] + '_invested'   ).text(crop_num(state['invested']   ));
    $('#' + currencies[i] + '_stop_gain'  ).text(crop_num(state['stop_gain']  ));
    $('#' + currencies[i] + '_stop_loss'  ).text(crop_num(state['stop_loss']  ));

    $('#' + currencies[i] + '_buy').unbind().click(buy);
    $('#' + currencies[i] + '_sell').unbind().click(sell);
    $('#' + currencies[i] + '_clear').unbind().click(clear);
    update_trades(currencies[i], state['trades']);
  }
}

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

function draw_candle(ctx, x, open, close, candle_size, skip_size, buy, prediction, candle) {
  length = Math.abs(open - close);
  if (length < 2) length = 2;
  y = (open > close) ? open : close;

  ctx.beginPath();

  if (buy == '1' && prediction == '1')
    ctx.fillStyle = "#0000FF";
  else if (buy == '1')
    ctx.fillStyle = "#00FFFF";
  else if (prediction == '1')
    ctx.fillStyle = "#000000";

  // if (candle['support'])
  //   ctx.fillStyle = "#0000FF";
  // else if (candle['resistance'])
  //   ctx.fillStyle = "#000000";
  else if (open < close)
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

function plot_trade(ctx, trade, open_date, min, max) {
  trade_date = (new Date(trade['date'])).getTime();
  date = parseInt(open_date.getTime());

  var x = 0;
  for (; date < trade_date; date += (15 * 60000)) {
    x++; 
  }
  x--;

  y = ((parseFloat(trade['price']) - min) / (max - min)) * height 

  ctx.beginPath();
  ctx.fillStyle = '#888';
  ctx.fillRect(margin_x + 2 * x - 2, height - y - 2 + margin_y, 5, 5);
  ctx.fillStyle = (trade['type'] == 'Buy') ? "#00FF00" : '#FF0000';
  ctx.fillRect(margin_x + 2 * x - 1, height - y - 1 + margin_y, 3, 3);
  ctx.closePath();
}

function plot_candlesticks(new_candles, currency) {
  var c = document.getElementById(currency);
  var ctx = c.getContext("2d");
  ctx.clearRect(0, 0 , 1200, 600);

  data = new_candles['usdt_' + currency]
 
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
    draw_candle(ctx, i, open, close, candle_size, skip_size, data[i]['buy'], data[i]['prediction'], data[i]);
    if (i % 30 == 0)
      draw_date_scale(ctx, i, candle_size, skip_size, new Date(data[i]['date']));
    last_date = new Date(data[i]['date']);
  }

  remaining = (30 - (i % 30));
  i = i + remaining;
  last_date = new Date(last_date.getTime() + 15 * 60 * 1000 * (remaining + 1));
  draw_date_scale(ctx, i, candle_size, skip_size, last_date);

  // Draw stop gain and loss.
  if (states['usdt_' + currency]) {
    if (states['usdt_' + currency]['stop_loss']) {
      ctx.beginPath();
      stop_loss = states['usdt_' + currency]['stop_loss'];

      ctx.strokeStyle = "#aa0000";
      ctx.lineWidth = 1;

      y = ((stop_loss - min) / (max - min)) * height
      ctx.moveTo(margin_x - 10, height + margin_y - y);
      ctx.lineTo(margin_x + width + 10, height + margin_y - y);
      ctx.stroke();
      ctx.closePath();
    }

    if (states['usdt_' + currency]['stop_gain']) {
      ctx.beginPath();
      stop_loss = states['usdt_' + currency]['stop_gain'];

      ctx.strokeStyle = "#00aa00";
      ctx.lineWidth = 1;

      y = ((stop_loss - min) / (max - min)) * height
      ctx.moveTo(margin_x - 10, height + margin_y - y);
      ctx.lineTo(margin_x + width + 10, height + margin_y - y);
      ctx.stroke();
      ctx.closePath();
    }

    trades =states['usdt_' + currency]['trades'] || [];

    for (var i = 0; i < trades.length; i++) {
      plot_trade(ctx, trades[i], new Date(data[0]['date']), min, max);
    }
  }
}

function update_candlesticks() {
  $.get("/update.json").done(function (data) {
    data = JSON.parse(data);
    update_info(data);
    new_candles = data['candles'];
    if (new_candles.length == 0) return;

    for (var i = 0; i < currencies.length; i++)
      plot_candlesticks(new_candles, currencies[i]);
  });
}

$(document).ready(function() {
  setInterval(function () {
    update_candlesticks();
  }, 5000);
});

}())

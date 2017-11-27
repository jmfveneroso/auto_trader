(function () {

width = 600;
height = 400;

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

function draw_candlesticks(currency) {
  $.get("/update.json", function(data) {
    // console.log(data);

    var c = document.getElementById(currency);
    var ctx = c.getContext("2d");

    data = JSON.parse(data);

    min = 99999999
    max = 0
    for (var i = 0; i < data.length; i++) {
      if (data[i][3] > max) max = data[i][3]
      if (data[i][4] < min) min = data[i][4]
    }

    candle_size = parseInt(800 / data.length) - 4
    console.log(max)
    console.log(min)
    for (var i = 0; i < data.length; i++) {
      min_ = ((parseFloat(data[i][4]) - min) / (max - min)) * height
      max_ = ((parseFloat(data[i][3]) - min) / (max - min)) * height
      draw_shadows(ctx, i, min_, max_, candle_size);
    }
    for (var i = 0; i < data.length; i++) {
      open  = ((parseFloat(data[i][1]) - min) / (max - min)) * height 
      close = ((parseFloat(data[i][2]) - min) / (max - min)) * height 
      draw_candle(ctx, i, open, close, candle_size);
    }
  });
}

$(document).ready(function() {
  draw_candlesticks('bch');
});

}())

/* Theme toggle and the two charts. Colours come from the CSS tokens. */
(function () {
  var root = document.documentElement;
  var toggle = document.getElementById("theme-toggle");
  var charts = [];

  function isDark() {
    if (root.dataset.theme) return root.dataset.theme === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  function token(name) {
    return getComputedStyle(root).getPropertyValue(name).trim();
  }

  function label() {
    toggle.textContent = isDark() ? "Light mode" : "Dark mode";
  }

  function data(id) {
    var el = document.getElementById(id);
    return el ? JSON.parse(el.textContent) : null;
  }

  function compact(value) {
    return value >= 1000000 ? (value / 1000000).toFixed(1) + "M" : Math.round(value / 1000) + "K";
  }

  function spaced(value) {
    return String(value).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  }

  function base() {
    Chart.defaults.color = token("--muted");
    Chart.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", sans-serif';
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: token("--surface"),
          titleColor: token("--ink"),
          bodyColor: token("--ink-2"),
          borderColor: token("--border"),
          borderWidth: 1,
          displayColors: false,
          padding: 10,
          callbacks: { label: function (c) { return "NOK " + spaced(c.raw); } }
        }
      }
    };
  }

  /* Prints the value at the tip of each bar. */
  var barLabels = {
    id: "barLabels",
    afterDatasetsDraw: function (chart) {
      var ctx = chart.ctx;
      ctx.save();
      ctx.fillStyle = token("--ink");
      ctx.font = '500 13px system-ui, -apple-system, "Segoe UI", sans-serif';
      ctx.textBaseline = "middle";
      chart.getDatasetMeta(0).data.forEach(function (bar, i) {
        ctx.fillText(compact(chart.data.datasets[0].data[i]), bar.x + 8, bar.y);
      });
      ctx.restore();
    }
  };

  /* Vertical hairline under the tooltip. */
  var crosshair = {
    id: "crosshair",
    beforeDatasetsDraw: function (chart) {
      var active = chart.tooltip && chart.tooltip.getActiveElements();
      if (!active || !active.length) return;
      var ctx = chart.ctx;
      var x = active[0].element.x;
      ctx.save();
      ctx.strokeStyle = token("--axis");
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, chart.chartArea.top);
      ctx.lineTo(x, chart.chartArea.bottom);
      ctx.stroke();
      ctx.restore();
    }
  };

  /* Prints the latest value beside the end of the line. */
  var endLabel = {
    id: "endLabel",
    afterDatasetsDraw: function (chart) {
      var points = chart.getDatasetMeta(0).data;
      var last = points[points.length - 1];
      var values = chart.data.datasets[0].data;
      var ctx = chart.ctx;
      ctx.save();
      ctx.fillStyle = token("--ink");
      ctx.font = '500 13px system-ui, -apple-system, "Segoe UI", sans-serif';
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(compact(values[values.length - 1]), last.x + 10, last.y);
      ctx.restore();
    }
  };

  function segments() {
    var rows = data("segments-data");
    if (!rows) return;
    var options = base();
    options.indexAxis = "y";
    options.layout = { padding: { right: 48 } };
    options.scales = {
      x: { display: false, beginAtZero: true },
      y: { grid: { display: false }, border: { color: token("--axis") }, ticks: { color: token("--ink-2") } }
    };
    charts.push(new Chart(document.getElementById("segments"), {
      type: "bar",
      data: {
        labels: rows.map(function (r) { return r.label; }),
        datasets: [{
          data: rows.map(function (r) { return r.value; }),
          backgroundColor: token("--series"),
          maxBarThickness: 24,
          borderRadius: { topRight: 4, bottomRight: 4 },
          borderSkipped: false
        }]
      },
      options: options,
      plugins: [barLabels]
    }));
  }

  function orders() {
    var rows = data("orders-data");
    if (!rows) return;
    var options = base();
    options.layout = { padding: { right: 48, top: 8 } };
    options.interaction = { mode: "index", intersect: false };
    options.scales = {
      x: { grid: { display: false }, border: { color: token("--axis") }, ticks: { maxRotation: 0, autoSkipPadding: 16 } },
      y: {
        beginAtZero: true,
        grid: { color: token("--grid") },
        border: { display: false },
        ticks: { maxTicksLimit: 5, font: { variant: "tabular-nums" }, callback: compact }
      }
    };
    var lastPoint = rows.length - 1;
    charts.push(new Chart(document.getElementById("orders"), {
      type: "line",
      data: {
        labels: rows.map(function (r) { return r.label; }),
        datasets: [{
          data: rows.map(function (r) { return r.value; }),
          borderColor: token("--series"),
          borderWidth: 2,
          borderCapStyle: "round",
          borderJoinStyle: "round",
          tension: 0,
          pointRadius: function (c) { return c.dataIndex === lastPoint ? 4 : 0; },
          pointHoverRadius: 5,
          pointBackgroundColor: token("--series"),
          pointBorderColor: token("--surface"),
          pointBorderWidth: 2
        }]
      },
      options: options,
      plugins: [crosshair, endLabel]
    }));
  }

  function draw() {
    charts.forEach(function (c) { c.destroy(); });
    charts = [];
    segments();
    orders();
  }

  toggle.addEventListener("click", function () {
    var next = isDark() ? "light" : "dark";
    root.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch (e) {}
    label();
    draw();
  });

  label();
  draw();
})();

/* Shared chart defaults keep the dashboard consistent and readable. */
Chart.defaults.font.family = 'Inter, ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif';
Chart.defaults.font.size = 11;
Chart.defaults.color = '#718294';
Chart.defaults.borderColor = '#e9eff4';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.animation.duration = 650;

const palette = {
  navy: '#234e70',
  teal: '#19a995',
  aqua: '#77d5c1',
  green: '#58ae8d',
  gold: '#e5ad45',
  orange: '#de8f45',
  red: '#d85858',
  blue: '#6d9fce',
  slate: '#9aabba',
  grid: '#e9eff4'
};

function chart(id, cfg) {
  const el = document.getElementById(id);
  if (!el) return;
  const originalOptions = cfg.options || {};
  cfg.options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: { legend: { position: 'bottom' }, ...originalOptions.plugins },
    ...originalOptions,
  };
  if (cfg.options.scales) {
    Object.values(cfg.options.scales).forEach((axis) => {
      axis.grid = { color: palette.grid, drawBorder: false, ...axis.grid };
      axis.ticks = { color: '#718294', padding: 8, ...axis.ticks };
      axis.border = { display: false, ...axis.border };
    });
  }
  new Chart(el, cfg);
}

chart("churnTrend", {
  type: "line",
  data: {
    labels: churnTrend.map((r) => r.month),
    datasets: [
      {
        label: "Observed churn mix",
        data: churnTrend.map((r) => r.observed * 100),
        borderColor: palette.red,
        backgroundColor: 'rgba(216,88,88,.08)',
        borderWidth: 2.5,
        pointRadius: 2.5,
        pointHoverRadius: 5,
        pointBackgroundColor: palette.red,
        fill: true,
        tension: .36
      },
      {
        label: "Avg predicted probability",
        data: churnTrend.map((r) => r.predicted * 100),
        borderColor: palette.teal,
        backgroundColor: 'rgba(25,169,149,.08)',
        borderWidth: 2.5,
        pointRadius: 2.5,
        pointHoverRadius: 5,
        pointBackgroundColor: palette.teal,
        fill: true,
        tension: .36
      },
    ],
  },
  options: {
    scales: {
      x: { grid: { display: false } },
      y: { beginAtZero: true, ticks: { callback: (value) => value + '%' } }
    }
  },
});

chart("riskDist", {
  type: "doughnut",
  data: {
    labels: riskDist.map((r) => r.label),
    datasets: [{
      data: riskDist.map((r) => r.n),
      backgroundColor: [palette.green, palette.gold, palette.orange, palette.red],
      borderColor: '#fff',
      borderWidth: 4,
      hoverOffset: 7
    }],
  },
  options: { cutout: '72%', plugins: { legend: { position: 'bottom' } } },
});

chart("shiftTrend", {
  type: "bar",
  data: {
    labels: shiftTrend.map((r) => r.label),
    datasets: [{
      label: "Customers",
      data: shiftTrend.map((r) => r.n),
      backgroundColor: [palette.aqua, palette.blue, palette.orange, palette.red],
      borderRadius: 7,
      maxBarThickness: 46
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    scales: { x: { grid: { display: false } }, y: { beginAtZero: true } }
  },
});

chart("branchChurn", {
  type: "bar",
  data: {
    labels: branchChurn.map((r) => r.label),
    datasets: [{
      label: "Churn rate",
      data: branchChurn.map((r) => r.churn_rate * 100),
      backgroundColor: 'rgba(35,78,112,.82)',
      hoverBackgroundColor: palette.teal,
      borderRadius: 6,
      maxBarThickness: 25
    }],
  },
  options: {
    indexAxis: "y",
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true, ticks: { callback: (value) => value + '%' } }, y: { grid: { display: false } } }
  },
});

chart("reasons", {
  type: "bar",
  data: {
    labels: topReasons.map((r) => r[0]),
    datasets: [{
      label: "Importance",
      data: topReasons.map((r) => r[1]),
      backgroundColor: 'rgba(25,169,149,.78)',
      hoverBackgroundColor: palette.teal,
      borderRadius: 5,
      maxBarThickness: 22
    }],
  },
  options: {
    indexAxis: "y",
    plugins: { legend: { display: false } },
    scales: { x: { beginAtZero: true }, y: { grid: { display: false } } }
  },
});

chart("valueDist", {
  type: "bar",
  data: {
    labels: valueBins.map((r) => r.label),
    datasets: [{
      label: "Customers",
      data: valueBins.map((r) => r.n),
      backgroundColor: 'rgba(109,159,206,.8)',
      hoverBackgroundColor: palette.navy,
      borderRadius: 6,
      maxBarThickness: 35
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    scales: { x: { grid: { display: false } }, y: { beginAtZero: true } }
  },
});

chart("segments", {
  type: "doughnut",
  data: {
    labels: segments.map((r) => r.label),
    datasets: [{
      data: segments.map((r) => r.n),
      backgroundColor: [palette.navy, palette.teal, palette.gold, palette.orange, palette.blue, palette.slate],
      borderColor: '#fff',
      borderWidth: 4,
      hoverOffset: 6
    }],
  },
  options: { cutout: '58%', plugins: { legend: { position: 'bottom' } } },
});

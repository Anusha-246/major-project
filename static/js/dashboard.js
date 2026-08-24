function chart(id, cfg) {
  const el = document.getElementById(id);
  if (!el) return;
  new Chart(el, cfg);
}

chart("churnTrend", {
  type: "line",
  data: {
    labels: churnTrend.map((r) => r.month),
    datasets: [
      { label: "Observed churn mix", data: churnTrend.map((r) => r.observed * 100), borderColor: "#922b21", tension: 0.3 },
      { label: "Avg predicted probability", data: churnTrend.map((r) => r.predicted * 100), borderColor: "#1b4f72", tension: 0.3 },
    ],
  },
  options: { plugins: { legend: { position: "bottom" } } },
});

chart("riskDist", {
  type: "doughnut",
  data: {
    labels: riskDist.map((r) => r.label),
    datasets: [{ data: riskDist.map((r) => r.n), backgroundColor: ["#1e8449", "#f4d03f", "#e67e22", "#c0392b"] }],
  },
});

chart("shiftTrend", {
  type: "bar",
  data: {
    labels: shiftTrend.map((r) => r.label),
    datasets: [{ label: "Customers", data: shiftTrend.map((r) => r.n), backgroundColor: "#1b4f72" }],
  },
});

chart("branchChurn", {
  type: "bar",
  data: {
    labels: branchChurn.map((r) => r.label),
    datasets: [{ label: "Churn rate %", data: branchChurn.map((r) => r.churn_rate * 100), backgroundColor: "#c9a227" }],
  },
  options: { indexAxis: "y" },
});

chart("reasons", {
  type: "bar",
  data: {
    labels: topReasons.map((r) => r[0]),
    datasets: [{ label: "Count", data: topReasons.map((r) => r[1]), backgroundColor: "#12324d" }],
  },
  options: { indexAxis: "y" },
});

chart("valueDist", {
  type: "bar",
  data: {
    labels: valueBins.map((r) => r.label),
    datasets: [{ label: "Customers", data: valueBins.map((r) => r.n), backgroundColor: "#1b4f72" }],
  },
});

chart("segments", {
  type: "pie",
  data: {
    labels: segments.map((r) => r.label),
    datasets: [{ data: segments.map((r) => r.n), backgroundColor: ["#1b4f72", "#c9a227", "#1e8449", "#e67e22", "#5d6d7e"] }],
  },
});

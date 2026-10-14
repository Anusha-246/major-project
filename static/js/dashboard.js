
/* =========================================================
   PREMIUM BANKING ANALYTICS DASHBOARD
   Chart.js 4.x
   Seven dashboard visualizations
   ========================================================= */

"use strict";

/* ---------------------------------------------------------
   1. COLOUR PALETTE
   --------------------------------------------------------- */

const palette = {
  teal: "#38E0C2",
  tealDark: "#159F91",
  aqua: "#7AF3DE",

  blue: "#68B5FF",
  blueDark: "#377ED0",

  purple: "#B99AFF",
  gold: "#FFD166",
  orange: "#FF9F68",
  red: "#FF7185",
  green: "#65D6A5",

  slate: "#A9BCD5",
  text: "#DCE8F8",
  muted: "#A6B9D2",

  grid: "rgba(169, 194, 225, 0.12)",
  panel: "#111E32",
  tooltip: "#071323"
};

/* ---------------------------------------------------------
   2. GLOBAL CHART DEFAULTS
   --------------------------------------------------------- */

if (typeof Chart !== "undefined") {
  Chart.defaults.color = palette.text;

  Chart.defaults.font.family =
    "'Inter', 'Segoe UI', system-ui, sans-serif";

  Chart.defaults.font.size = 12;

  Chart.defaults.animation.duration = 850;
  Chart.defaults.animation.easing = "easeOutQuart";

  Chart.defaults.plugins.tooltip.backgroundColor =
    palette.tooltip;

  Chart.defaults.plugins.tooltip.titleColor = "#FFFFFF";
  Chart.defaults.plugins.tooltip.bodyColor = palette.text;

  Chart.defaults.plugins.tooltip.borderColor =
    "rgba(56, 224, 194, 0.65)";

  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.padding = 13;
  Chart.defaults.plugins.tooltip.cornerRadius = 10;
  Chart.defaults.plugins.tooltip.displayColors = true;

  Chart.defaults.plugins.tooltip.titleFont = {
    size: 12,
    weight: "600"
  };

  Chart.defaults.plugins.tooltip.bodyFont = {
    size: 12
  };

  Chart.defaults.plugins.legend.labels.color = palette.text;
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.pointStyle = "circle";
  Chart.defaults.plugins.legend.labels.padding = 16;
  Chart.defaults.plugins.legend.labels.boxWidth = 9;

  Chart.defaults.elements.line.borderWidth = 3;
  Chart.defaults.elements.line.tension = 0.38;

  Chart.defaults.elements.point.radius = 3;
  Chart.defaults.elements.point.hoverRadius = 7;
  Chart.defaults.elements.point.hitRadius = 10;

  Chart.defaults.elements.bar.borderRadius = 7;
  Chart.defaults.elements.bar.borderSkipped = false;

  Chart.defaults.elements.arc.hoverOffset = 8;
}

/* ---------------------------------------------------------
   3. CHART CONFIGURATION HELPER
   --------------------------------------------------------- */

function chart(id, config) {
  if (typeof Chart === "undefined") {
    console.error(
      "Chart.js is not loaded. Check the Chart.js script in your HTML."
    );
    return null;
  }

  const canvas = document.getElementById(id);

  if (!canvas) {
    console.warn(`Chart canvas not found: #${id}`);
    return null;
  }

  /*
   * Prevent duplicate chart instances when the dashboard
   * initialization function is executed more than once.
   */
  const existingChart = Chart.getChart(canvas);

  if (existingChart) {
    existingChart.destroy();
  }

  const originalOptions = config.options || {};

  const options = {
    responsive: true,
    maintainAspectRatio: false,

    animation: {
      duration: 850,
      easing: "easeOutQuart"
    },

    interaction: {
      intersect: false,
      mode: "index"
    },

    ...originalOptions,

    plugins: {
      ...originalOptions.plugins
    }
  };

  /*
   * Consistent legend placement and typography.
   */
  if (options.plugins.legend === undefined) {
    options.plugins.legend = {
      position: "bottom"
    };
  }

  if (options.plugins.legend.display !== false) {
    options.plugins.legend.labels = {
      color: palette.text,
      usePointStyle: true,
      pointStyle: "circle",
      padding: 16,
      boxWidth: 9,
      ...options.plugins.legend.labels
    };
  }

  /*
   * Apply common styling to chart axes without removing
   * chart-specific settings.
   */
  if (options.scales) {
    Object.entries(options.scales).forEach(([key, axis]) => {
      if (axis.display === false) return;

      axis.grid = {
        color: palette.grid,
        drawTicks: false,
        ...axis.grid
      };

      axis.ticks = {
        color: palette.muted,
        padding: 8,
        font: {
          size: 11
        },
        ...axis.ticks
      };

      axis.border = {
        display: false,
        ...axis.border
      };
    });
  }

  return new Chart(canvas, {
    ...config,
    options
  });
}

/* ---------------------------------------------------------
   4. CHURN TREND
   Observed churn mix vs predicted probability
   --------------------------------------------------------- */

chart("churnTrend", {
  type: "line",

  data: {
    labels: churnTrend.map(row => row.month),

    datasets: [
      {
        label: "Observed churn mix",

        data: churnTrend.map(row => row.observed * 100),

        borderColor: palette.red,
        backgroundColor: "rgba(255, 113, 133, 0.10)",

        pointBackgroundColor: palette.red,
        pointBorderColor: palette.panel,
        pointBorderWidth: 2,

        pointRadius: 4,
        pointHoverRadius: 7,

        borderWidth: 3,
        fill: true,
        tension: 0.38
      },

      {
        label: "Predicted probability",

        data: churnTrend.map(row => row.predicted * 100),

        borderColor: palette.teal,
        backgroundColor: "rgba(56, 224, 194, 0.08)",

        pointBackgroundColor: palette.teal,
        pointBorderColor: palette.panel,
        pointBorderWidth: 2,

        pointRadius: 4,
        pointHoverRadius: 7,

        borderWidth: 3,
        fill: true,
        tension: 0.38
      }
    ]
  },

  options: {
    plugins: {
      legend: {
        position: "bottom"
      },

      tooltip: {
        callbacks: {
          label: context =>
            `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
        }
      }
    },

    scales: {
      x: {
        grid: {
          display: false
        }
      },

      y: {
        beginAtZero: true,

        ticks: {
          callback: value => `${value}%`
        }
      }
    }
  }
});

/* ---------------------------------------------------------
   5. CUSTOMER RISK DISTRIBUTION
   --------------------------------------------------------- */

chart("riskDist", {
  type: "doughnut",

  data: {
    labels: riskDist.map(row => row.label),

    datasets: [
      {
        data: riskDist.map(row => row.n),

        backgroundColor: [
          palette.green,
          palette.gold,
          palette.orange,
          palette.red
        ],

        hoverBackgroundColor: [
          "#8BF0C3",
          "#FFE49A",
          "#FFBD91",
          "#FF9AAA"
        ],

        borderColor: palette.panel,
        borderWidth: 4,
        hoverOffset: 10,
        spacing: 3
      }
    ]
  },

  options: {
    cutout: "70%",

    plugins: {
      legend: {
        position: "bottom"
      },

      tooltip: {
        callbacks: {
          label: context => {
            const values = context.dataset.data;

            const total = values.reduce(
              (sum, value) => sum + value,
              0
            );

            const percentage = total
              ? ((context.parsed / total) * 100).toFixed(1)
              : "0.0";

            return (
              ` ${context.label}: ` +
              `${context.parsed.toLocaleString()} ` +
              `(${percentage}%)`
            );
          }
        }
      }
    }
  }
});

/* ---------------------------------------------------------
   6. BEHAVIOUR SHIFT CLASSES
   --------------------------------------------------------- */

chart("shiftTrend", {
  type: "bar",

  data: {
    labels: shiftTrend.map(row => row.label),

    datasets: [
      {
        label: "Customers",

        data: shiftTrend.map(row => row.n),

        backgroundColor: [
          palette.aqua,
          palette.blue,
          palette.orange,
          palette.red
        ],

        hoverBackgroundColor: [
          "#B0FFF0",
          "#9BCFFF",
          "#FFD0A8",
          "#FFACB8"
        ],

        borderRadius: 8,
        maxBarThickness: 48,

        categoryPercentage: 0.7,
        barPercentage: 0.82
      }
    ]
  },

  options: {
    plugins: {
      legend: {
        display: false
      },

      tooltip: {
        callbacks: {
          label: context =>
            ` Customers: ${context.parsed.y.toLocaleString()}`
        }
      }
    },

    scales: {
      x: {
        grid: {
          display: false
        }
      },

      y: {
        beginAtZero: true,

        ticks: {
          precision: 0
        }
      }
    }
  }
});

/* ---------------------------------------------------------
   7. BRANCH-WISE CHURN
   --------------------------------------------------------- */

chart("branchChurn", {
  type: "bar",

  data: {
    labels: branchChurn.map(row => row.label),

    datasets: [
      {
        label: "Churn rate",

        data: branchChurn.map(row => row.churn_rate * 100),

        backgroundColor: branchChurn.map(
          (_, index) =>
            index % 2 === 0
              ? palette.blue
              : palette.tealDark
        ),

        hoverBackgroundColor: palette.teal,

        borderRadius: 7,
        maxBarThickness: 24,

        categoryPercentage: 0.78,
        barPercentage: 0.88
      }
    ]
  },

  options: {
    indexAxis: "y",

    plugins: {
      legend: {
        display: false
      },

      tooltip: {
        callbacks: {
          label: context =>
            ` Churn rate: ${context.parsed.x.toFixed(1)}%`
        }
      }
    },

    scales: {
      x: {
        beginAtZero: true,

        ticks: {
          callback: value => `${value}%`
        }
      },

      y: {
        grid: {
          display: false
        },

        ticks: {
          autoSkip: false,
          font: {
            size: 10
          }
        }
      }
    }
  }
});

/* ---------------------------------------------------------
   8. TOP CHURN REASONS
   --------------------------------------------------------- */

chart("reasons", {
  type: "bar",

  data: {
    labels: topReasons.map(row => row[0]),

    datasets: [
      {
        label: "Importance",

        data: topReasons.map(row => row[1]),

        backgroundColor: [
          palette.teal,
          palette.blue,
          palette.purple,
          palette.gold,
          palette.orange,
          palette.green
        ],

        hoverBackgroundColor: palette.aqua,

        borderRadius: 7,
        maxBarThickness: 25,
        categoryPercentage: 0.75
      }
    ]
  },

  options: {
    indexAxis: "y",

    plugins: {
      legend: {
        display: false
      },

      tooltip: {
        callbacks: {
          label: context =>
            ` Importance: ${context.parsed.x.toLocaleString()}`
        }
      }
    },

    scales: {
      x: {
        beginAtZero: true
      },

      y: {
        grid: {
          display: false
        },

        ticks: {
          autoSkip: false,
          color: palette.text,

          font: {
            size: 10
          }
        }
      }
    }
  }
});

/* ---------------------------------------------------------
   9. CUSTOMER VALUE DISTRIBUTION
   --------------------------------------------------------- */

chart("valueDist", {
  type: "bar",

  data: {
    labels: valueBins.map(row => row.label),

    datasets: [
      {
        label: "Customers",

        data: valueBins.map(row => row.n),

        backgroundColor: [
          "rgba(104, 181, 255, 0.72)",
          "rgba(104, 181, 255, 0.84)",
          "rgba(56, 224, 194, 0.80)",
          "rgba(185, 154, 255, 0.84)",
          "rgba(255, 209, 102, 0.86)",
          "rgba(101, 214, 165, 0.88)"
        ],

        hoverBackgroundColor: palette.teal,

        borderRadius: 8,
        maxBarThickness: 40,

        categoryPercentage: 0.72,
        barPercentage: 0.84
      }
    ]
  },

  options: {
    plugins: {
      legend: {
        display: false
      },

      tooltip: {
        callbacks: {
          label: context =>
            ` Customers: ${context.parsed.y.toLocaleString()}`
        }
      }
    },

    scales: {
      x: {
        grid: {
          display: false
        },

        ticks: {
          color: palette.text,

          font: {
            size: 10
          }
        }
      },

      y: {
        beginAtZero: true,

        ticks: {
          precision: 0
        }
      }
    }
  }
});

/* ---------------------------------------------------------
   10. CUSTOMER SEGMENTS
   --------------------------------------------------------- */

chart("segments", {
  type: "doughnut",

  data: {
    labels: segments.map(row => row.label),

    datasets: [
      {
        data: segments.map(row => row.n),

        backgroundColor: [
          palette.blue,
          palette.teal,
          palette.purple,
          palette.gold,
          palette.orange,
          palette.green
        ],

        hoverBackgroundColor: [
          "#9DCEFF",
          "#82F7E3",
          "#D0BCFF",
          "#FFE6A0",
          "#FFC39C",
          "#A0F0C6"
        ],

        borderColor: palette.panel,
        borderWidth: 4,

        hoverOffset: 9,
        spacing: 3
      }
    ]
  },

  options: {
    cutout: "62%",

    plugins: {
      legend: {
        position: "bottom",

        labels: {
          padding: 13
        }
      },

      tooltip: {
        callbacks: {
          label: context => {
            const values = context.dataset.data;

            const total = values.reduce(
              (sum, value) => sum + value,
              0
            );

            const percentage = total
              ? ((context.parsed / total) * 100).toFixed(1)
              : "0.0";

            return (
              ` ${context.label}: ` +
              `${context.parsed.toLocaleString()} ` +
              `(${percentage}%)`
            );
          }
        }
      }
    }
  }
});

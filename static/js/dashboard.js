document.addEventListener("DOMContentLoaded", () => {
  const payload = window.EMOCARE_CHARTS || null;
  const trendCanvas = document.getElementById("moodTrend");
  const pieCanvas = document.getElementById("moodPie");

  if (trendCanvas && payload?.timeline) {
    new Chart(trendCanvas, {
      type: "line",
      data: {
        labels: payload.timeline.labels,
        datasets: payload.timeline.datasets,
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: true,
            labels: { usePointStyle: true },
          },
        },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  if (pieCanvas && payload?.distribution) {
    new Chart(pieCanvas, {
      type: "doughnut",
      data: {
        labels: payload.distribution.labels,
        datasets: [
          {
            data: payload.distribution.data,
            backgroundColor: payload.distribution.colors,
          },
        ],
      },
      options: {
        cutout: "70%",
        plugins: { legend: { position: "bottom" } },
      },
    });
  }
});

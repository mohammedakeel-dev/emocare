document.addEventListener("DOMContentLoaded", () => {
  const grid = document.getElementById("calendarGrid");
  if (!grid) return;

  const startDate = new Date(firstDay);
  const endDate = new Date(lastDay);
  const startDay = startDate.getDay();
  
  // Add empty cells for days before month starts
  for (let i = 0; i < startDay; i++) {
    const cell = document.createElement("div");
    cell.className = "calendar-day empty";
    grid.appendChild(cell);
  }

  // Add cells for each day of the month
  const currentDate = new Date(startDate);
  while (currentDate <= endDate) {
    const cell = document.createElement("div");
    cell.className = "calendar-day";
    const dateStr = currentDate.toISOString().split("T")[0];
    const dayData = calendarData[dateStr];

    if (dayData) {
      // If entries array exists, render a floating pill behind the date number
      // Use a multicolor linear-gradient so all emotions recorded that day are visible
      const entries = dayData.entries || [];
      const dominant = dayData.dominant || (entries[0] && entries[0].emotion) || dayData.emotion;
      const dominantIntensity = dayData.intensity || (entries[0] && entries[0].intensity) || 2;
      if (entries.length > 0 || dominant) {
        // build counts per emotion
        const counts = {};
        if (entries.length > 0) {
          entries.forEach((en) => { counts[en.emotion] = (counts[en.emotion] || 0) + 1; });
        } else {
          counts[dominant] = 1;
        }

        const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
        // order emotions by count desc for consistent visuals
        const ordered = Object.keys(counts).sort((a, b) => counts[b] - counts[a]);

        // cap number of segments to 6 to keep pill readable
        const maxSegments = 6;
        const used = ordered.slice(0, maxSegments);
        const stops = [];
        let cursor = 0;
        used.forEach((em, idx) => {
          const cnt = counts[em];
          const pct = Math.round((cnt / total) * 100);
          const start = cursor;
          // ensure final segment reaches 100
          const end = (idx === used.length - 1) ? 100 : Math.min(100, cursor + pct || 1);
          const color = emotionColors[em] || "#94a3b8";
          stops.push(`${color} ${start}% ${end}%`);
          cursor = end;
        });

        // If cursor < 100 (due to rounding), extend last stop
        if (stops.length && !stops[stops.length - 1].includes("100%")) {
          const last = stops.pop();
          const newLast = last.replace(/\d+%\s*$/, "100%");
          stops.push(newLast);
        }

        const gradient = `linear-gradient(90deg, ${stops.join(", ")})`;

        // Create a floating pill behind the date number to 'fill' the date visually
        const pill = document.createElement("div");
        pill.className = "calendar-day-pill";
        pill.style.background = gradient;
        pill.style.opacity = Math.min(1, 0.35 + (dominantIntensity / 5) * 0.65);
        // Title shows aggregated counts
        const titleParts = used.map((em) => `${em} x${counts[em]}`);
        pill.title = `${dominant} (${dominantIntensity}/5) — ${titleParts.join(", ")}`;
        cell.appendChild(pill);
        cell.classList.add("has-data");
      }

      // Build tooltip summary
      let titleParts = [];
      if (dayData.entries && dayData.entries.length > 0) {
        // aggregate counts by emotion
        const counts = {};
        dayData.entries.forEach((en) => { counts[en.emotion] = (counts[en.emotion] || 0) + 1; });
        for (const k in counts) {
          titleParts.push(`${k} x${counts[k]}`);
        }
      } else if (dayData.dominant) {
        titleParts.push(`${dayData.dominant} (${dayData.intensity}/5)`);
      }
      if (titleParts.length) {
        cell.title = `${dateStr}: ${titleParts.join(", ")}`;
        cell.classList.add("has-data");
      }
    }

    const dayNum = document.createElement("div");
    dayNum.className = "calendar-day-number";
    dayNum.textContent = currentDate.getDate();
    cell.appendChild(dayNum);
    grid.appendChild(cell);

    currentDate.setDate(currentDate.getDate() + 1);
  }
});


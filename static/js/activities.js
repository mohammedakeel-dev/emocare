/* Activity interactions: open modal, start timer, mark complete */
document.addEventListener("DOMContentLoaded", () => {
  const startButtons = document.querySelectorAll(".activity-start-btn");
  const modal = document.getElementById("activityModal");
  const overlay = document.getElementById("activityModalOverlay");
  const titleEl = document.getElementById("activityModalTitle");
  const subtitleEl = document.getElementById("activityModalSubtitle");
  const timerDisplay = document.getElementById("activityTimer");
  const startTimerBtn = document.getElementById("activityStartTimer");
  const markDoneBtn = document.getElementById("activityMarkDone");
  const closeBtn = document.getElementById("activityCloseBtn");

  let countdown = null;
  let remaining = 0; // seconds
  let currentActivityTitle = null;
  let currentActivitySubtitle = null;

  function openModal(title, subtitle, durationSeconds = 120) {
    titleEl.textContent = title;
    subtitleEl.textContent = subtitle;
    currentActivityTitle = title;
    currentActivitySubtitle = subtitle;
    remaining = durationSeconds;
    updateTimerDisplay();
    modal.classList.remove("hidden");
    overlay.classList.remove("hidden");
    startTimerBtn.disabled = false;
    startTimerBtn.textContent = "Start timer";
  }

  // Small confetti emoji burst on completion
  function burstConfetti() {
    const count = 18;
    for (let i = 0; i < count; i++) {
      const el = document.createElement('div');
      el.className = 'confetti-emoji';
      el.textContent = ['🎉','✨','💪','😊'][Math.floor(Math.random()*4)];
      el.style.left = (20 + Math.random()*60) + '%';
      el.style.top = (30 + Math.random()*30) + '%';
      el.style.fontSize = (12 + Math.random()*18) + 'px';
      el.style.position = 'fixed';
      el.style.zIndex = 9999;
      document.body.appendChild(el);
      setTimeout(()=> el.remove(), 1600 + Math.random()*800);
    }
  }

  function closeModal() {
    modal.classList.add("hidden");
    overlay.classList.add("hidden");
    stopCountdown();
  }

  function updateTimerDisplay() {
    const mins = Math.floor(remaining / 60);
    const secs = remaining % 60;
    timerDisplay.textContent = `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function startCountdown() {
    if (countdown) return;
    countdown = setInterval(() => {
      if (remaining <= 0) {
        stopCountdown();
        // mark complete, reward, and close
        if (currentActivityTitle) {
          markActivityDone(currentActivityTitle, currentActivitySubtitle);
        }
        incrementStreak();
        showNotification("Activity complete — well done!", "success");
        burstConfetti();
        // keep modal visible a short moment so user sees completion
        setTimeout(() => closeModal(), 900);
        return;
      }
      remaining -= 1;
      updateTimerDisplay();
    }, 1000);
  }

  function stopCountdown() {
    if (countdown) {
      clearInterval(countdown);
      countdown = null;
    }
  }

  function markActivityDone(title, subtitle) {
    const completed = JSON.parse(localStorage.getItem("completedActivities") || "[]");
    completed.push({ title, subtitle, timestamp: new Date().toISOString() });
    localStorage.setItem("completedActivities", JSON.stringify(completed));
    showNotification(`Marked done: ${title}`, "success");
  }

  // Simple streak tracker stored in localStorage
  function loadStreak() {
    return JSON.parse(localStorage.getItem('activityStreak') || '{"count":0,"lastDate":null}');
  }

  function saveStreak(streak) {
    localStorage.setItem('activityStreak', JSON.stringify(streak));
  }

  function updateStreakBadge() {
    const streak = loadStreak();
    let badge = document.querySelector('.streak-badge');
    if (!badge) {
      const header = document.querySelector('.activities-page h2');
      if (!header) return;
      badge = document.createElement('span');
      badge.className = 'streak-badge';
      header.appendChild(badge);
    }
    if (streak.count > 0) {
      badge.textContent = `🔥 Streak: ${streak.count}`;
      badge.title = `Last activity: ${streak.lastDate}`;
      badge.style.display = 'inline-block';
    } else {
      badge.style.display = 'none';
    }
  }

  function incrementStreak() {
    const today = new Date().toISOString().slice(0,10);
    const streak = loadStreak();
    if (streak.lastDate === today) {
      // already counted today
    } else {
      // check yesterday
      const yesterday = new Date(Date.now() - 24*60*60*1000).toISOString().slice(0,10);
      if (streak.lastDate === yesterday) {
        streak.count = (streak.count || 0) + 1;
      } else {
        streak.count = 1;
      }
      streak.lastDate = today;
      saveStreak(streak);
      updateStreakBadge();
    }
  }

  startButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      const li = btn.closest("li");
      const title = li.querySelector("strong")?.textContent || "Activity";
      const subtitle = li.querySelector("p")?.textContent || "";
      // optional data-duration attribute in seconds
      const durationAttr = btn.getAttribute("data-duration");
      const duration = durationAttr ? parseInt(durationAttr, 10) : 120;
      openModal(title, subtitle, duration);
    });
  });

  // Wire up watch video links to open in a lightweight popup and record click
  const watchButtons = document.querySelectorAll('.watch-video-btn');
  watchButtons.forEach((a) => {
    a.addEventListener('click', (e) => {
      // let anchor operate normally but also store a quick metric
      try {
        const href = a.href;
        const watched = JSON.parse(localStorage.getItem('watchedVideos') || '[]');
        watched.push({ href, timestamp: new Date().toISOString() });
        localStorage.setItem('watchedVideos', JSON.stringify(watched));
      } catch (err) {
        // ignore
      }
      // default behaviour (open in new tab) continues because anchor has target
    });
  });

  // overlay and close
  overlay.addEventListener("click", closeModal);
  closeBtn.addEventListener("click", closeModal);

  startTimerBtn.addEventListener("click", () => {
    startCountdown();
    startTimerBtn.disabled = true;
    startTimerBtn.textContent = "Running…";
  });

  markDoneBtn.addEventListener("click", () => {
    const title = titleEl.textContent;
    const subtitle = subtitleEl.textContent;
    markActivityDone(title, subtitle);
    incrementStreak();
    closeModal();
  });

  // render initial streak badge
  updateStreakBadge();
});

// Small notification helper
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.className = `flash flash-${type}`;
  notification.textContent = message;
  notification.style.position = "fixed";
  notification.style.top = "20px";
  notification.style.right = "20px";
  notification.style.zIndex = "9999";
  notification.style.padding = "1rem";
  notification.style.borderRadius = "8px";
  notification.style.maxWidth = "360px";
  document.body.appendChild(notification);
  setTimeout(() => notification.remove(), 3000);
}

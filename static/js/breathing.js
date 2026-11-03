// Breathing Exercises

let breathingInterval = null;
let breathingTimer = null;
let currentExercise = null;
let cycleCount = 0;
let sessionStartTime = null;
let isPaused = false;

const exercises = {
  box: {
    name: "Box Breathing",
    phases: [
      { name: "Inhale", duration: 4000 },
      { name: "Hold", duration: 4000 },
      { name: "Exhale", duration: 4000 },
      { name: "Hold", duration: 4000 }
    ]
  },
  "478": {
    name: "4-7-8 Breathing",
    phases: [
      { name: "Inhale", duration: 4000 },
      { name: "Hold", duration: 7000 },
      { name: "Exhale", duration: 8000 }
    ]
  },
  deep: {
    name: "Deep Breathing",
    phases: [
      { name: "Inhale", duration: 5000 },
      { name: "Exhale", duration: 5000 }
    ]
  }
};

function startBreathing(exerciseType) {
  currentExercise = exerciseType;
  cycleCount = 0;
  sessionStartTime = Date.now();
  isPaused = false;
  
  document.querySelector('.breathing-exercises').classList.add('hidden');
  document.getElementById('breathingSession').classList.remove('hidden');
  
  startSessionTimer();
  runBreathingCycle();
}

function runBreathingCycle() {
  if (isPaused) return;
  
  const exercise = exercises[currentExercise];
  let phaseIndex = 0;
  
  function executePhase() {
    if (isPaused) return;
    
    const phase = exercise.phases[phaseIndex];
    const circle = document.getElementById('breathingCircle');
    const instruction = document.getElementById('breathingInstruction');
    const countEl = document.getElementById('breathingCount');
    
    instruction.textContent = phase.name;
    
    if (phase.name === "Inhale") {
      circle.style.transform = 'scale(1.3)';
      circle.style.background = '#10b981';
      let count = Math.ceil(phase.duration / 1000);
      const countdown = setInterval(() => {
        if (isPaused) {
          clearInterval(countdown);
          return;
        }
        countEl.textContent = count;
        count--;
        if (count < 0) clearInterval(countdown);
      }, 1000);
    } else if (phase.name === "Exhale") {
      circle.style.transform = 'scale(1)';
      circle.style.background = '#ef4444';
      let count = Math.ceil(phase.duration / 1000);
      const countdown = setInterval(() => {
        if (isPaused) {
          clearInterval(countdown);
          return;
        }
        countEl.textContent = count;
        count--;
        if (count < 0) clearInterval(countdown);
      }, 1000);
    } else {
      circle.style.transform = 'scale(1.15)';
      circle.style.background = '#f59e0b';
      let count = Math.ceil(phase.duration / 1000);
      const countdown = setInterval(() => {
        if (isPaused) {
          clearInterval(countdown);
          return;
        }
        countEl.textContent = count;
        count--;
        if (count < 0) clearInterval(countdown);
      }, 1000);
    }
    
    phaseIndex++;
    if (phaseIndex >= exercise.phases.length) {
      phaseIndex = 0;
      cycleCount++;
      document.getElementById('cycleCount').textContent = cycleCount;
    }
    
    if (!isPaused) {
      setTimeout(executePhase, phase.duration);
    }
  }
  
  executePhase();
}

function pauseBreathing() {
  isPaused = !isPaused;
  const btn = document.getElementById('pauseBtn');
  btn.textContent = isPaused ? 'Resume' : 'Pause';
  
  if (!isPaused) {
    runBreathingCycle();
  }
}

function stopBreathing() {
  if (breathingInterval) clearInterval(breathingInterval);
  if (breathingTimer) clearInterval(breathingTimer);
  
  document.getElementById('breathingSession').classList.add('hidden');
  document.querySelector('.breathing-exercises').classList.remove('hidden');
  
  currentExercise = null;
  isPaused = false;
  
  // Save session
  if (cycleCount > 0) {
    fetch('/breathing', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `duration=${Math.floor((Date.now() - sessionStartTime) / 1000)}&type=${currentExercise}`
    });
  }
}

function startSessionTimer() {
  breathingTimer = setInterval(() => {
    if (!isPaused && sessionStartTime) {
      const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);
      const minutes = Math.floor(elapsed / 60);
      const seconds = elapsed % 60;
      document.getElementById('sessionTime').textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    }
  }, 1000);
}

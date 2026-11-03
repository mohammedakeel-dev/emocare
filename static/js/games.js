// EmoCare Games - Emotion-themed puzzle games

let currentGame = null;
let gameScore = 0;
let gameTimer = null;
let gameStartTime = null;

// Emotion data for games
const emotionData = {
  Happiness: {
    description: "A feeling of joy, pleasure, or contentment",
    keywords: ["joy", "pleasure", "contentment", "delight", "cheer"],
    emoji: "😊"
  },
  Calm: {
    description: "A state of peace and tranquility",
    keywords: ["peace", "tranquility", "serenity", "relaxation", "balance"],
    emoji: "😌"
  },
  Stress: {
    description: "Mental or emotional strain from demanding circumstances",
    keywords: ["pressure", "tension", "strain", "overwhelm", "burden"],
    emoji: "😩"
  },
  Anxiety: {
    description: "Worry or unease about an uncertain outcome",
    keywords: ["worry", "unease", "nervousness", "apprehension", "fear"],
    emoji: "😰"
  },
  Depression: {
    description: "Persistent feelings of sadness and loss of interest",
    keywords: ["sadness", "melancholy", "despair", "hopelessness", "gloom"],
    emoji: "😢"
  },
  Anger: {
    description: "Strong feeling of annoyance, displeasure, or hostility",
    keywords: ["rage", "fury", "irritation", "resentment", "hostility"],
    emoji: "😠"
  }
};

const emotions = Object.keys(emotionData);

// Initialize games
document.addEventListener('DOMContentLoaded', () => {
  // Games are initialized when selected
});

function startGame(gameType) {
  currentGame = gameType;
  gameScore = 0;
  gameStartTime = Date.now();
  
  document.getElementById('gameMenu').classList.add('hidden');
  document.getElementById('gameContainer').classList.remove('hidden');
  
  updateScore();
  startTimer();
  
  switch(gameType) {
    case 'matching':
      initMatchingGame();
      break;
    case 'wordsearch':
      initWordSearch();
      break;
    case 'memory':
      initMemoryGame();
      break;
    case 'crossword':
      initCrossword();
      break;
    case 'jigsaw':
      initJigsaw();
      break;
    case 'trivia':
      initTrivia();
      break;
    case 'snake':
      initSnake();
      break;
    case 'tictactoe':
      initTicTacToe();
      break;
    case 'reaction':
      initReaction();
      break;
    case 'colormatch':
      initColorMatch();
      break;
    case 'wheel':
      initWheel();
      break;
    case 'bubble':
      initBubble();
      break;
  }
}

function backToMenu() {
  stopTimer();
  document.getElementById('gameContainer').classList.add('hidden');
  document.getElementById('gameMenu').classList.remove('hidden');
  document.getElementById('gameArea').innerHTML = '';
  currentGame = null;
}

function updateScore() {
  document.getElementById('gameScore').textContent = `Score: ${gameScore}`;
}

function startTimer() {
  gameStartTime = Date.now();
  gameTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - gameStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    document.getElementById('gameTime').textContent = `Time: ${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, 1000);
}

function stopTimer() {
  if (gameTimer) {
    clearInterval(gameTimer);
    gameTimer = null;
  }
}

function addScore(points) {
  gameScore += points;
  updateScore();
}

// ==================== MATCHING GAME ====================
function initMatchingGame() {
  const gameArea = document.getElementById('gameArea');
  const shuffledEmotions = [...emotions].sort(() => Math.random() - 0.5);
  const selectedEmotions = shuffledEmotions.slice(0, 6);
  
  const descriptions = selectedEmotions.map(e => emotionData[e].description);
  const emotionNames = [...selectedEmotions];
  
  // Shuffle both arrays
  descriptions.sort(() => Math.random() - 0.5);
  emotionNames.sort(() => Math.random() - 0.5);
  
  let selectedCard = null;
  let matches = 0;
  const totalMatches = selectedEmotions.length;
  
  gameArea.innerHTML = `
    <div class="matching-game">
      <div class="matching-section">
        <h3>Emotions</h3>
        ${emotionNames.map((emotion, idx) => `
          <div class="matching-card" data-type="emotion" data-emotion="${emotion}" data-idx="${idx}">
            <strong>${emotion}</strong>
            <div style="font-size: 2rem; margin-top: 0.5rem;">${emotionData[emotion].emoji}</div>
          </div>
        `).join('')}
      </div>
      <div class="matching-section">
        <h3>Descriptions</h3>
        ${descriptions.map((desc, idx) => {
          const emotion = selectedEmotions.find(e => emotionData[e].description === desc);
          return `
            <div class="matching-card" data-type="description" data-emotion="${emotion}" data-idx="${idx}">
              ${desc}
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
  
  gameArea.querySelectorAll('.matching-card').forEach(card => {
    card.addEventListener('click', function() {
      if (this.classList.contains('matched')) return;
      
      if (!selectedCard) {
        selectedCard = this;
        this.classList.add('selected');
      } else {
        if (selectedCard === this) {
          this.classList.remove('selected');
          selectedCard = null;
          return;
        }
        
        const card1Emotion = selectedCard.dataset.emotion;
        const card2Emotion = this.dataset.emotion;
        
        if (card1Emotion === card2Emotion && 
            selectedCard.dataset.type !== this.dataset.type) {
          // Match!
          selectedCard.classList.remove('selected');
          selectedCard.classList.add('matched');
          this.classList.add('matched');
          matches++;
          addScore(10);
          
          if (matches === totalMatches) {
            setTimeout(() => {
              showGameComplete();
            }, 500);
          }
        } else {
          // No match
          selectedCard.classList.remove('selected');
          setTimeout(() => {
            this.classList.remove('selected');
          }, 1000);
        }
        
        selectedCard = null;
      }
    });
  });
}

// ==================== WORD SEARCH ====================
function initWordSearch() {
  const words = emotions.map(e => e.toUpperCase());
  const gridSize = 18; // Larger grid for better placement
  const grid = Array(gridSize).fill(null).map(() => Array(gridSize).fill(''));
  
  // Place words in grid with better algorithm
  const placedWords = [];
  
  // Sort words by length (longest first) for better placement
  const sortedWords = [...words].sort((a, b) => b.length - a.length);
  
  sortedWords.forEach((word, wordIdx) => {
    let placed = false;
    const directions = [
      { name: 'horizontal', rowInc: 0, colInc: 1 },
      { name: 'vertical', rowInc: 1, colInc: 0 },
      { name: 'diagonal', rowInc: 1, colInc: 1 }
    ];
    
    // First try random placement
    for (let attempt = 0; attempt < 100 && !placed; attempt++) {
      const direction = directions[Math.floor(Math.random() * directions.length)];
      const maxRow = gridSize - (word.length * Math.abs(direction.rowInc || 1));
      const maxCol = gridSize - (word.length * Math.abs(direction.colInc || 1));
      
      if (maxRow < 0 || maxCol < 0) continue;
      
      const row = Math.floor(Math.random() * (maxRow + 1));
      const col = Math.floor(Math.random() * (maxCol + 1));
      
      if (canPlaceWord(grid, word, row, col, direction, gridSize)) {
        placeWord(grid, word, row, col, direction);
        placedWords.push({word, row, col, direction: direction.name});
        placed = true;
      }
    }
    
    // If still not placed, force placement in specific rows
    if (!placed) {
      const startRow = (wordIdx * 2) % gridSize; // Distribute words across rows
      for (let r = startRow; r < gridSize && !placed; r++) {
        for (let c = 0; c <= gridSize - word.length && !placed; c++) {
          const dir = { name: 'horizontal', rowInc: 0, colInc: 1 };
          if (canPlaceWord(grid, word, r, c, dir, gridSize)) {
            placeWord(grid, word, r, c, dir);
            placedWords.push({word, row: r, col: c, direction: 'horizontal'});
            placed = true;
          }
        }
      }
    }
  });
  
  // Fill empty cells with random letters (weighted towards common letters)
  const commonLetters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZABCDEFGHIJKLMNOPQRSTUVWXYZAEIOUA';
  for (let i = 0; i < gridSize; i++) {
    for (let j = 0; j < gridSize; j++) {
      if (!grid[i][j]) {
        grid[i][j] = commonLetters[Math.floor(Math.random() * commonLetters.length)];
      }
    }
  }
  
  let foundWords = 0;
  let selectedCells = [];
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div class="wordsearch-container">
      <div class="wordsearch-words">
        ${words.map(word => `
          <span class="word-item" data-word="${word}">${word}</span>
        `).join('')}
      </div>
      <div class="wordsearch-grid" style="grid-template-columns: repeat(${gridSize}, 1fr);">
        ${grid.map((row, i) => row.map((cell, j) => `
          <div class="wordsearch-cell" data-row="${i}" data-col="${j}">${cell}</div>
        `).join('')).join('')}
      </div>
    </div>
  `;
  
  const cells = gameArea.querySelectorAll('.wordsearch-cell');
  let isSelecting = false;
  
  cells.forEach(cell => {
    cell.addEventListener('mousedown', (e) => {
      e.preventDefault();
      isSelecting = true;
      selectedCells = [cell];
      cell.classList.add('selected');
    });
    
    cell.addEventListener('mouseenter', () => {
      if (isSelecting && !selectedCells.includes(cell)) {
        selectedCells.push(cell);
        cell.classList.add('selected');
      }
    });
    
    cell.addEventListener('mouseup', () => {
      if (isSelecting) {
        checkWordSelection(selectedCells, placedWords, gridSize);
        cells.forEach(c => c.classList.remove('selected'));
        selectedCells = [];
        isSelecting = false;
      }
    });
  });
  
  document.addEventListener('mouseup', () => {
    isSelecting = false;
  });
  
  function checkWordSelection(selected, placedWords, size) {
    if (selected.length < 3) return;
    
    const word = selected.map(c => c.textContent).join('').trim();
    const reverseWord = word.split('').reverse().join('');
    
    placedWords.forEach(({word: targetWord}) => {
      if (word === targetWord || reverseWord === targetWord) {
        const wordItem = document.querySelector(`[data-word="${targetWord}"]`);
        if (wordItem && !wordItem.classList.contains('found')) {
          wordItem.classList.add('found');
          selected.forEach(c => c.classList.add('found'));
          foundWords++;
          addScore(15);
          
          if (foundWords === words.length) {
            setTimeout(() => showGameComplete(), 500);
          }
        }
      }
    });
  }
}

function canPlaceWord(grid, word, row, col, direction, size) {
  const len = word.length;
  for (let i = 0; i < len; i++) {
    const r = row + (direction.rowInc * i);
    const c = col + (direction.colInc * i);
    
    if (r < 0 || r >= size || c < 0 || c >= size) return false;
    if (grid[r][c] && grid[r][c] !== word[i]) return false;
  }
  return true;
}

function placeWord(grid, word, row, col, direction) {
  for (let i = 0; i < word.length; i++) {
    const r = row + (direction.rowInc * i);
    const c = col + (direction.colInc * i);
    grid[r][c] = word[i];
  }
}

// ==================== MEMORY GAME ====================
function initMemoryGame() {
  const selectedEmotions = [...emotions].sort(() => Math.random() - 0.5).slice(0, 8);
  const cards = [...selectedEmotions, ...selectedEmotions].sort(() => Math.random() - 0.5);
  
  let flippedCards = [];
  let matchedPairs = 0;
  const totalPairs = selectedEmotions.length;
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div class="memory-grid">
      ${cards.map((emotion, idx) => `
        <div class="memory-card" data-emotion="${emotion}" data-idx="${idx}">
          ?
        </div>
      `).join('')}
    </div>
  `;
  
  gameArea.querySelectorAll('.memory-card').forEach(card => {
    card.addEventListener('click', function() {
      if (this.classList.contains('flipped') || this.classList.contains('matched')) return;
      if (flippedCards.length >= 2) return;
      
      this.classList.add('flipped');
      this.textContent = emotionData[this.dataset.emotion].emoji;
      flippedCards.push(this);
      
      if (flippedCards.length === 2) {
        const [card1, card2] = flippedCards;
        if (card1.dataset.emotion === card2.dataset.emotion) {
          // Match!
          setTimeout(() => {
            card1.classList.add('matched');
            card2.classList.add('matched');
            matchedPairs++;
            addScore(20);
            
            if (matchedPairs === totalPairs) {
              setTimeout(() => showGameComplete(), 500);
            }
          }, 500);
        } else {
          // No match
          setTimeout(() => {
            card1.classList.remove('flipped');
            card1.textContent = '?';
            card2.classList.remove('flipped');
            card2.textContent = '?';
          }, 1000);
        }
        flippedCards = [];
      }
    });
  });
}

// ==================== CROSSWORD ====================
function initCrossword() {
  const clues = [
    { word: "HAPPINESS", clue: "A feeling of joy and contentment", row: 0, col: 0, direction: "across" },
    { word: "CALM", clue: "A state of peace and tranquility", row: 2, col: 0, direction: "across" },
    { word: "STRESS", clue: "Mental or emotional strain", row: 4, col: 0, direction: "across" },
    { word: "ANXIETY", clue: "Worry about uncertain outcomes", row: 6, col: 0, direction: "across" },
    { word: "ANGER", clue: "Strong feeling of annoyance", row: 0, col: 0, direction: "down" },
    { word: "DEPRESSION", clue: "Persistent feelings of sadness", row: 0, col: 4, direction: "down" }
  ];
  
  const gridSize = 10;
  const grid = Array(gridSize).fill(null).map(() => Array(gridSize).fill(null));
  
  // Simple crossword layout
  const layout = [
    "HAPPINESS  ",
    "A         ",
    "CALM      ",
    "L         ",
    "STRESS    ",
    "M         ",
    "ANXIETY   ",
    "          ",
    "          ",
    "          "
  ];
  
  const acrossClues = clues.filter(c => c.direction === "across");
  const downClues = clues.filter(c => c.direction === "down");
  
  let solvedCount = 0;
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div class="crossword-container">
      <div class="crossword-clues">
        <div class="clue-section">
          <h4>Across</h4>
          ${acrossClues.map((clue, idx) => `
            <div class="clue-item" data-word="${clue.word}" data-idx="${idx}">
              ${idx + 1}. ${clue.clue}
            </div>
          `).join('')}
        </div>
        <div class="clue-section">
          <h4>Down</h4>
          ${downClues.map((clue, idx) => `
            <div class="clue-item" data-word="${clue.word}" data-idx="${idx + acrossClues.length}">
              ${idx + acrossClues.length + 1}. ${clue.clue}
            </div>
          `).join('')}
        </div>
      </div>
      <div class="crossword-grid" style="grid-template-columns: repeat(${gridSize}, 1fr);">
        ${layout.map((row, i) => row.split('').map((cell, j) => {
          if (cell === ' ') {
            return `<div class="crossword-cell blocked"></div>`;
          } else {
            const clueNum = getClueNumber(i, j, clues);
            return `
              <div class="crossword-cell">
                ${clueNum ? `<span class="cell-number">${clueNum}</span>` : ''}
                <input type="text" maxlength="1" data-row="${i}" data-col="${j}" style="text-transform: uppercase;">
              </div>
            `;
          }
        }).join('')).join('')}
      </div>
    </div>
  `;
  
  const inputs = gameArea.querySelectorAll('.crossword-cell input');
  inputs.forEach(input => {
    input.addEventListener('input', function() {
      checkCrosswordProgress(clues, layout, gridSize);
    });
    
    input.addEventListener('keydown', function(e) {
      const row = parseInt(this.dataset.row);
      const col = parseInt(this.dataset.col);
      
      if (e.key === 'ArrowRight' && col < gridSize - 1) {
        const next = gameArea.querySelector(`[data-row="${row}"][data-col="${col + 1}"]`);
        if (next) next.focus();
      } else if (e.key === 'ArrowLeft' && col > 0) {
        const next = gameArea.querySelector(`[data-row="${row}"][data-col="${col - 1}"]`);
        if (next) next.focus();
      } else if (e.key === 'ArrowDown' && row < gridSize - 1) {
        const next = gameArea.querySelector(`[data-row="${row + 1}"][data-col="${col}"]`);
        if (next) next.focus();
      } else if (e.key === 'ArrowUp' && row > 0) {
        const next = gameArea.querySelector(`[data-row="${row - 1}"][data-col="${col}"]`);
        if (next) next.focus();
      }
    });
  });
  
  function checkCrosswordProgress(clues, layout, size) {
    clues.forEach(clue => {
      let word = '';
      const row = clue.row;
      const col = clue.col;
      
      for (let i = 0; i < clue.word.length; i++) {
        let r = row, c = col;
        if (clue.direction === "across") c += i;
        else r += i;
        
        if (r < size && c < size && layout[r] && layout[r][c] !== ' ') {
          const input = gameArea.querySelector(`[data-row="${r}"][data-col="${c}"]`);
          if (input) word += input.value.toUpperCase();
        }
      }
      
      if (word === clue.word) {
        const clueItem = gameArea.querySelector(`[data-word="${clue.word}"]`);
        if (clueItem && !clueItem.classList.contains('solved')) {
          clueItem.classList.add('solved');
          solvedCount++;
          addScore(25);
          
          if (solvedCount === clues.length) {
            setTimeout(() => showGameComplete(), 500);
          }
        }
      }
    });
  }
  
  function getClueNumber(row, col, clues) {
    for (let i = 0; i < clues.length; i++) {
      if (clues[i].row === row && clues[i].col === col) {
        return i + 1;
      }
    }
    return null;
  }
}

// ==================== JIGSAW PUZZLE ====================
function initJigsaw() {
  const gridSize = 3;
  const pieces = Array.from({length: gridSize * gridSize}, (_, i) => i + 1);
  pieces.sort(() => Math.random() - 0.5);
  
  let correctPositions = 0;
  const totalPieces = gridSize * gridSize;
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div class="jigsaw-container">
      <p>Drag and drop pieces to solve the puzzle. Arrange numbers 1-${totalPieces} in order.</p>
      <div class="jigsaw-puzzle" style="grid-template-columns: repeat(${gridSize}, 1fr);">
        ${pieces.map((num, idx) => {
          const correctRow = Math.floor((num - 1) / gridSize);
          const correctCol = (num - 1) % gridSize;
          return `
            <div class="jigsaw-piece" 
                 draggable="true" 
                 data-num="${num}" 
                 data-idx="${idx}"
                 data-correct-row="${correctRow}"
                 data-correct-col="${correctCol}">
              ${num}
            </div>
          `;
        }).join('')}
      </div>
    </div>
  `;
  
  const puzzle = gameArea.querySelector('.jigsaw-puzzle');
  let draggedElement = null;
  
  puzzle.querySelectorAll('.jigsaw-piece').forEach(piece => {
    piece.addEventListener('dragstart', function(e) {
      draggedElement = this;
      this.style.opacity = '0.5';
    });
    
    piece.addEventListener('dragend', function() {
      this.style.opacity = '1';
    });
    
    piece.addEventListener('dragover', function(e) {
      e.preventDefault();
    });
    
    piece.addEventListener('drop', function(e) {
      e.preventDefault();
      if (draggedElement && draggedElement !== this) {
        const tempNum = this.dataset.num;
        const tempIdx = this.dataset.idx;
        
        this.dataset.num = draggedElement.dataset.num;
        this.dataset.idx = draggedElement.dataset.idx;
        this.textContent = draggedElement.dataset.num;
        
        draggedElement.dataset.num = tempNum;
        draggedElement.dataset.idx = tempIdx;
        draggedElement.textContent = tempNum;
        
        checkJigsawProgress();
      }
    });
  });
  
  function checkJigsawProgress() {
    const pieces = Array.from(puzzle.querySelectorAll('.jigsaw-piece'));
    let correct = 0;
    
    pieces.forEach((piece, idx) => {
      const num = parseInt(piece.dataset.num);
      const correctRow = Math.floor((num - 1) / gridSize);
      const correctCol = (num - 1) % gridSize;
      const currentRow = Math.floor(idx / gridSize);
      const currentCol = idx % gridSize;
      
      if (currentRow === correctRow && currentCol === correctCol) {
        if (!piece.classList.contains('correct')) {
          piece.classList.add('correct');
          correct++;
        }
      } else {
        piece.classList.remove('correct');
      }
    });
    
    correctPositions = correct;
    
    if (correct === totalPieces) {
      setTimeout(() => showGameComplete(), 500);
    }
  }
  
  // Initial check
  setTimeout(checkJigsawProgress, 100);
}

// ==================== TRIVIA ====================
function initTrivia() {
  const questions = [
    {
      question: "Which emotion is characterized by feelings of joy and contentment?",
      options: ["Happiness", "Calm", "Stress", "Anxiety"],
      correct: 0
    },
    {
      question: "What is the primary characteristic of anxiety?",
      options: ["Joy", "Worry about uncertain outcomes", "Contentment", "Peace"],
      correct: 1
    },
    {
      question: "Which emotion involves persistent feelings of sadness?",
      options: ["Happiness", "Calm", "Depression", "Anger"],
      correct: 2
    },
    {
      question: "What helps reduce stress?",
      options: ["More work", "Breathing exercises", "Avoiding breaks", "Ignoring feelings"],
      correct: 1
    },
    {
      question: "Which emotion is associated with tranquility?",
      options: ["Anger", "Stress", "Calm", "Anxiety"],
      correct: 2
    }
  ];
  
  let currentQuestion = 0;
  let correctAnswers = 0;
  
  function showQuestion() {
    if (currentQuestion >= questions.length) {
      showTriviaComplete();
      return;
    }
    
    const q = questions[currentQuestion];
    const gameArea = document.getElementById('gameArea');
    gameArea.innerHTML = `
      <div class="trivia-container">
        <div class="trivia-question">
          <h3>Question ${currentQuestion + 1} of ${questions.length}</h3>
          <p>${q.question}</p>
        </div>
        <div class="trivia-options">
          ${q.options.map((opt, idx) => `
            <div class="trivia-option" data-option="${idx}">${opt}</div>
          `).join('')}
        </div>
      </div>
    `;
    
    gameArea.querySelectorAll('.trivia-option').forEach(option => {
      option.addEventListener('click', function() {
        if (this.classList.contains('selected')) return;
        
        const selectedIdx = parseInt(this.dataset.option);
        const allOptions = gameArea.querySelectorAll('.trivia-option');
        
        allOptions.forEach(opt => opt.classList.remove('selected'));
        this.classList.add('selected');
        
        setTimeout(() => {
          allOptions.forEach((opt, idx) => {
            if (idx === q.correct) {
              opt.classList.add('correct');
            } else if (idx === selectedIdx && idx !== q.correct) {
              opt.classList.add('incorrect');
            }
          });
          
          if (selectedIdx === q.correct) {
            correctAnswers++;
            addScore(30);
          }
          
          setTimeout(() => {
            currentQuestion++;
            showQuestion();
          }, 2000);
        }, 500);
      });
    });
  }
  
  function showTriviaComplete() {
    const gameArea = document.getElementById('gameArea');
    gameArea.innerHTML = `
      <div class="game-complete">
        <h3>Trivia Complete!</h3>
        <p>You got ${correctAnswers} out of ${questions.length} questions correct!</p>
        <div class="game-controls">
          <button class="button-link" onclick="startGame('trivia')">Play Again</button>
          <button class="button-link secondary" onclick="backToMenu()">Back to Menu</button>
        </div>
      </div>
    `;
  }
  
  showQuestion();
}

// ==================== SNAKE GAME ====================
function initSnake() {
  const canvas = document.createElement('canvas');
  canvas.width = 600;
  canvas.height = 600;
  canvas.style.border = '2px solid var(--border)';
  canvas.style.borderRadius = '8px';
  canvas.style.display = 'block';
  canvas.style.margin = '0 auto';
  
  const ctx = canvas.getContext('2d');
  const gridSize = 20;
  const tileCount = canvas.width / gridSize;
  
  let snake = [{x: 10, y: 10}];
  let food = {x: 15, y: 15};
  let dx = 0;
  let dy = 0;
  let score = 0;
  let gameLoop = null;
  let gameOver = false;
  
  const emotionColors = {
    'Happiness': '#fbbf24',
    'Calm': '#60a5fa',
    'Stress': '#f87171',
    'Anxiety': '#a78bfa',
    'Depression': '#64748b',
    'Anger': '#ef4444'
  };
  
  const currentEmotion = emotions[Math.floor(Math.random() * emotions.length)];
  const snakeColor = emotionColors[currentEmotion] || '#5b21b6';
  
  function drawGame() {
    clearCanvas();
    drawSnake();
    drawFood();
    if (gameOver) {
      drawGameOver();
    }
  }
  
  function clearCanvas() {
    ctx.fillStyle = '#f5f6fa';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  
  function drawSnake() {
    ctx.fillStyle = snakeColor;
    snake.forEach((segment, index) => {
      if (index === 0) {
        ctx.fillStyle = snakeColor;
      } else {
        ctx.fillStyle = snakeColor + '80';
      }
      ctx.fillRect(segment.x * gridSize, segment.y * gridSize, gridSize - 2, gridSize - 2);
    });
  }
  
  function drawFood() {
    ctx.fillStyle = '#10b981';
    ctx.beginPath();
    ctx.arc(food.x * gridSize + gridSize/2, food.y * gridSize + gridSize/2, gridSize/2 - 2, 0, 2 * Math.PI);
    ctx.fill();
  }
  
  function drawGameOver() {
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#ffffff';
    ctx.font = '30px Inter';
    ctx.textAlign = 'center';
    ctx.fillText('Game Over!', canvas.width/2, canvas.height/2 - 20);
    ctx.font = '20px Inter';
    ctx.fillText(`Score: ${score}`, canvas.width/2, canvas.height/2 + 20);
  }
  
  function moveSnake() {
    const head = {x: snake[0].x + dx, y: snake[0].y + dy};
    
    if (head.x < 0 || head.x >= tileCount || head.y < 0 || head.y >= tileCount) {
      endGame();
      return;
    }
    
    if (head.x === food.x && head.y === food.y) {
      score += 10;
      addScore(10);
      updateScore();
      generateFood();
    } else {
      snake.pop();
    }
    
    snake.unshift(head);
    
    for (let i = 1; i < snake.length; i++) {
      if (head.x === snake[i].x && head.y === snake[i].y) {
        endGame();
        return;
      }
    }
  }
  
  function generateFood() {
    food = {
      x: Math.floor(Math.random() * tileCount),
      y: Math.floor(Math.random() * tileCount)
    };
    for (let segment of snake) {
      if (segment.x === food.x && segment.y === food.y) {
        generateFood();
        return;
      }
    }
  }
  
  function endGame() {
    gameOver = true;
    if (gameLoop) clearInterval(gameLoop);
    setTimeout(() => {
      showGameComplete();
    }, 2000);
  }
  
  document.addEventListener('keydown', (e) => {
    if (gameOver) return;
    if (e.key === 'ArrowUp' && dy !== 1) { dx = 0; dy = -1; }
    if (e.key === 'ArrowDown' && dy !== -1) { dx = 0; dy = 1; }
    if (e.key === 'ArrowLeft' && dx !== 1) { dx = -1; dy = 0; }
    if (e.key === 'ArrowRight' && dx !== -1) { dx = 1; dy = 0; }
  });
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div style="text-align: center; margin-bottom: 1rem;">
      <h3>🐍 Emotion Snake - Use Arrow Keys</h3>
      <p>Current Emotion: ${currentEmotion} | Score: <span id="snakeScore">0</span></p>
    </div>
  `;
  gameArea.appendChild(canvas);
  
  const scoreDisplay = document.getElementById('snakeScore');
  
  function updateScore() {
    scoreDisplay.textContent = score;
  }
  
  gameLoop = setInterval(() => {
    if (!gameOver) {
      moveSnake();
      drawGame();
    }
  }, 150);
  
  drawGame();
}

// ==================== TIC-TAC-TOE ====================
function initTicTacToe() {
  let board = Array(9).fill('');
  let currentPlayer = 'X'; // User always goes first
  let gameOver = false;
  let isAITurn = false; // Flag to prevent user moves during AI turn
  let wins = { X: 0, O: 0 };
  
  const winPatterns = [
    [0,1,2], [3,4,5], [6,7,8],
    [0,3,6], [1,4,7], [2,5,8],
    [0,4,8], [2,4,6]
  ];
  
  function checkWinner() {
    for (let pattern of winPatterns) {
      const [a, b, c] = pattern;
      if (board[a] && board[a] === board[b] && board[a] === board[c]) {
        return board[a];
      }
    }
    if (board.every(cell => cell)) return 'tie';
    return null;
  }
  
  function aiMove() {
    if (gameOver) return;
    
    const available = board.map((cell, idx) => cell === '' ? idx : null).filter(x => x !== null);
    if (available.length === 0) return;
    
    // Try to win
    for (let idx of available) {
      board[idx] = 'O';
      if (checkWinner() === 'O') {
        renderBoard();
        return;
      }
      board[idx] = '';
    }
    
    // Block player
    for (let idx of available) {
      board[idx] = 'X';
      if (checkWinner() === 'X') {
        board[idx] = 'O';
        renderBoard();
        return;
      }
      board[idx] = '';
    }
    
    // Center
    if (board[4] === '') {
      board[4] = 'O';
      renderBoard();
      return;
    }
    
    // Random
    const random = available[Math.floor(Math.random() * available.length)];
    board[random] = 'O';
    renderBoard();
  }
  
  function makeMove(idx) {
    // Prevent moves if game is over, cell is taken, not user's turn, or AI is thinking
    if (board[idx] || gameOver || currentPlayer !== 'X' || isAITurn) return;
    
    board[idx] = 'X';
    renderBoard();
    
    const winner = checkWinner();
    if (winner) {
      gameOver = true;
      if (winner === 'X') {
        wins.X++;
        addScore(50);
        setTimeout(() => alert('You Win! 🎉'), 100);
      } else if (winner === 'O') {
        wins.O++;
        setTimeout(() => alert('AI Wins! 🤖'), 100);
      } else {
        setTimeout(() => alert('Tie Game! 🤝'), 100);
      }
      setTimeout(() => {
        board = Array(9).fill('');
        currentPlayer = 'X';
        gameOver = false;
        isAITurn = false;
        renderBoard();
      }, 2000);
      return;
    }
    
    // Switch to AI turn
    currentPlayer = 'O';
    isAITurn = true;
      setTimeout(() => {
        aiMove();
        currentPlayer = 'X';
        isAITurn = false;
        renderBoard(); // Re-enable cells after AI move
        
        // Check if AI won
        const aiWinner = checkWinner();
        if (aiWinner) {
          gameOver = true;
          renderBoard(); // Disable cells on game over
          if (aiWinner === 'O') {
            wins.O++;
            setTimeout(() => alert('AI Wins! 🤖'), 100);
          } else if (aiWinner === 'tie') {
            setTimeout(() => alert('Tie Game! 🤝'), 100);
          }
          setTimeout(() => {
            board = Array(9).fill('');
            currentPlayer = 'X';
            gameOver = false;
            isAITurn = false;
            renderBoard();
          }, 2000);
        }
      }, 500);
  }
  
  function renderBoard() {
    const boardEl = document.getElementById('tictactoe-board');
    if (!boardEl) return;
    const shouldDisable = gameOver || isAITurn;
    boardEl.innerHTML = board.map((cell, idx) => {
      const emoji = cell === 'X' ? '😊' : cell === 'O' ? '🤖' : '';
      const disabledClass = shouldDisable ? 'disabled' : '';
      const disabledStyle = shouldDisable ? 'style="pointer-events: none; opacity: 0.6;"' : '';
      return `<div class="ttt-cell ${disabledClass}" onclick="makeTTTMove(${idx})" ${disabledStyle}>${emoji}</div>`;
    }).join('');
  }
  
  window.makeTTTMove = makeMove;
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div style="text-align: center; margin-bottom: 1.5rem;">
      <h3>⭕ Emotion Tic-Tac-Toe</h3>
      <p>You: 😊 | AI: 🤖 | Wins - You: <span id="winsX">0</span> | AI: <span id="winsO">0</span></p>
    </div>
    <div id="tictactoe-board" class="ttt-board"></div>
    <div class="game-controls">
      <button class="button-link" onclick="initTicTacToe()">Reset</button>
    </div>
  `;
  
  renderBoard();
  
  setInterval(() => {
    document.getElementById('winsX').textContent = wins.X;
    document.getElementById('winsO').textContent = wins.O;
  }, 100);
}

// ==================== REACTION TIME ====================
function initReaction() {
  let rounds = 0;
  let totalTime = 0;
  let waiting = false;
  let startTime = null;
  let timeoutId = null;
  
  const emotionColors = {
    'Happiness': { bg: '#fef3c7', border: '#fbbf24', name: 'Happiness' },
    'Calm': { bg: '#dbeafe', border: '#60a5fa', name: 'Calm' },
    'Stress': { bg: '#fee2e2', border: '#f87171', name: 'Stress' },
    'Anxiety': { bg: '#ede9fe', border: '#a78bfa', name: 'Anxiety' },
    'Depression': { bg: '#e2e8f0', border: '#64748b', name: 'Depression' },
    'Anger': { bg: '#fee2e2', border: '#ef4444', name: 'Anger' }
  };
  
  function startRound() {
    waiting = true;
    const gameArea = document.getElementById('gameArea');
    const reactionBox = document.getElementById('reactionBox');
    reactionBox.style.background = '#f5f6fa';
    reactionBox.textContent = 'Wait for the color...';
    reactionBox.onclick = null;
    
    const delay = 1000 + Math.random() * 3000;
    timeoutId = setTimeout(() => {
      const emotion = emotions[Math.floor(Math.random() * emotions.length)];
      const color = emotionColors[emotion];
      reactionBox.style.background = color.bg;
      reactionBox.style.borderColor = color.border;
      reactionBox.textContent = `Click Now! (${color.name})`;
      startTime = Date.now();
      waiting = false;
      
      reactionBox.onclick = () => {
        if (!waiting && startTime) {
          const reactionTime = Date.now() - startTime;
          totalTime += reactionTime;
          rounds++;
          addScore(Math.max(0, 100 - Math.floor(reactionTime / 10)));
          
          const avgTime = Math.round(totalTime / rounds);
          document.getElementById('avgTime').textContent = avgTime;
          document.getElementById('rounds').textContent = rounds;
          
          if (rounds >= 5) {
            setTimeout(() => {
              showGameComplete();
            }, 1000);
          } else {
            setTimeout(startRound, 1000);
          }
        }
      };
    }, delay);
  }
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div style="text-align: center;">
      <h3>⚡ Reaction Time Test</h3>
      <p>Click as fast as you can when the color appears!</p>
      <p>Rounds: <span id="rounds">0</span>/5 | Avg: <span id="avgTime">0</span>ms</p>
      <div id="reactionBox" style="width: 400px; height: 400px; margin: 2rem auto; border: 4px solid var(--border); border-radius: 16px; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; font-weight: bold; cursor: pointer; transition: all 0.3s;"></div>
      <button class="button-link" onclick="startReactionRound()">Start</button>
    </div>
  `;
  
  window.startReactionRound = () => {
    rounds = 0;
    totalTime = 0;
    startRound();
  };
}

// ==================== COLOR MATCH ====================
function initColorMatch() {
  let level = 1;
  let sequence = [];
  let playerSequence = [];
  let playing = false;
  
  const colors = ['#ef4444', '#f59e0b', '#10b981', '#3b82f6', '#8b5cf6', '#ec4899'];
  const colorNames = ['Red', 'Orange', 'Green', 'Blue', 'Purple', 'Pink'];
  
  function generateSequence(length) {
    return Array.from({length}, () => Math.floor(Math.random() * colors.length));
  }
  
  function playSequence() {
    playing = true;
    let i = 0;
    const interval = setInterval(() => {
      highlightColor(sequence[i]);
      i++;
      if (i >= sequence.length) {
        clearInterval(interval);
        playing = false;
        playerSequence = [];
      }
    }, 600);
  }
  
  function highlightColor(idx) {
    const cells = document.querySelectorAll('.colormatch-cell');
    cells[idx].style.transform = 'scale(1.2)';
    cells[idx].style.opacity = '0.8';
    setTimeout(() => {
      cells[idx].style.transform = 'scale(1)';
      cells[idx].style.opacity = '1';
    }, 300);
  }
  
  function checkSequence() {
    for (let i = 0; i < playerSequence.length; i++) {
      if (playerSequence[i] !== sequence[i]) {
        return false;
      }
    }
    return true;
  }
  
  function nextLevel() {
    level++;
    sequence = generateSequence(level + 2);
    addScore(level * 10);
    document.getElementById('colorLevel').textContent = level;
    setTimeout(() => playSequence(), 1000);
  }
  
  function makeMove(idx) {
    if (playing) return;
    
    highlightColor(idx);
    playerSequence.push(idx);
    
    if (!checkSequence()) {
      setTimeout(() => {
        alert(`Game Over! Reached Level ${level}`);
        showGameComplete();
      }, 500);
      return;
    }
    
    if (playerSequence.length === sequence.length) {
      nextLevel();
    }
  }
  
  function startGame() {
    level = 1;
    sequence = generateSequence(3);
    const gameArea = document.getElementById('gameArea');
    gameArea.innerHTML = `
      <div style="text-align: center; margin-bottom: 1.5rem;">
        <h3>🎨 Color Match Game</h3>
        <p>Level: <span id="colorLevel">1</span> | Watch and repeat the sequence!</p>
      </div>
      <div class="colormatch-grid">
        ${colors.map((color, idx) => `
          <div class="colormatch-cell" style="background: ${color};" onclick="makeColorMove(${idx})"></div>
        `).join('')}
      </div>
      <div class="game-controls">
        <button class="button-link" onclick="startColorGame()">Restart</button>
      </div>
    `;
    
    window.makeColorMove = makeMove;
    window.startColorGame = startGame;
    
    setTimeout(() => playSequence(), 1000);
  }
  
  startGame();
}

// ==================== EMOTION WHEEL ====================
function initWheel() {
  let spinning = false;
  let currentRotation = 0;
  
  const wheelEmotions = emotions.map((emotion, idx) => ({
    emotion,
    emoji: emotionData[emotion].emoji,
    color: ['#fbbf24', '#60a5fa', '#f87171', '#a78bfa', '#64748b', '#ef4444'][idx],
    angle: (360 / emotions.length) * idx
  }));
  
  function spin() {
    if (spinning) return;
    spinning = true;
    
    const spins = 5 + Math.random() * 3;
    const randomAngle = Math.random() * 360;
    const totalRotation = currentRotation + (spins * 360) + randomAngle;
    currentRotation = totalRotation % 360;
    
    const wheel = document.getElementById('emotionWheel');
    wheel.style.transform = `rotate(${totalRotation}deg)`;
    wheel.style.transition = 'transform 3s cubic-bezier(0.4, 0, 0.2, 1)';
    
    setTimeout(() => {
      const normalizedAngle = (360 - (currentRotation % 360)) % 360;
      const segmentAngle = 360 / emotions.length;
      const selectedIndex = Math.floor(normalizedAngle / segmentAngle);
      const selected = wheelEmotions[selectedIndex];
      
      document.getElementById('wheelResult').innerHTML = `
        <h3>${selected.emoji} ${selected.emotion}!</h3>
        <p>${emotionData[selected.emotion].description}</p>
      `;
      
      addScore(20);
      spinning = false;
    }, 3000);
  }
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div style="text-align: center;">
      <h3>🎡 Emotion Wheel</h3>
      <p>Spin to discover your emotion!</p>
      <div style="position: relative; width: 400px; height: 400px; margin: 2rem auto;">
        <div id="emotionWheel" style="width: 100%; height: 100%; border-radius: 50%; position: relative; transition: transform 3s;">
          ${wheelEmotions.map((item, idx) => {
            const angle = (360 / emotions.length) * idx;
            const nextAngle = (360 / emotions.length) * (idx + 1);
            return `
              <div style="position: absolute; width: 50%; height: 50%; left: 50%; top: 0; transform-origin: 0 100%; transform: rotate(${angle}deg); clip-path: polygon(0 0, 100% 0, 100% 100%); background: ${item.color};">
                <div style="transform: rotate(${(angle + nextAngle) / 2 - angle}deg); padding-top: 20px; padding-left: 40px; font-size: 1.5rem;">
                  ${item.emoji}<br><small>${item.emotion}</small>
                </div>
              </div>
            `;
          }).join('')}
        </div>
        <div style="position: absolute; top: -10px; left: 50%; transform: translateX(-50%); width: 0; height: 0; border-left: 15px solid transparent; border-right: 15px solid transparent; border-top: 30px solid var(--text);"></div>
      </div>
      <div id="wheelResult" style="margin-top: 2rem; padding: 1.5rem; background: var(--bg); border-radius: 12px;"></div>
      <button class="button-link" onclick="spinWheel()" style="margin-top: 1rem;">Spin Again!</button>
    </div>
  `;
  
  window.spinWheel = spin;
  spin();
}

// ==================== BUBBLE POP ====================
function initBubble() {
  let score = 0;
  let timeLeft = 30;
  let bubbles = [];
  let gameInterval = null;
  let timerInterval = null;
  
  const emotionEmojis = emotions.map(e => emotionData[e].emoji);
  
  function createBubble() {
    const bubble = {
      id: Date.now() + Math.random(),
      emoji: emotionEmojis[Math.floor(Math.random() * emotionEmojis.length)],
      x: Math.random() * 80 + 10,
      y: 100,
      speed: 0.5 + Math.random() * 0.5,
      size: 50 + Math.random() * 30
    };
    bubbles.push(bubble);
    renderBubbles();
  }
  
  function updateBubbles() {
    bubbles = bubbles.filter(bubble => {
      bubble.y -= bubble.speed;
      return bubble.y > -10;
    });
    renderBubbles();
    
    if (bubbles.length > 20) {
      endBubbleGame();
    }
  }
  
  function popBubble(bubbleId) {
    bubbles = bubbles.filter(b => b.id !== bubbleId);
    score += 10;
    addScore(10);
    document.getElementById('bubbleScore').textContent = score;
    renderBubbles();
  }
  
  function renderBubbles() {
    const container = document.getElementById('bubbleContainer');
    container.innerHTML = bubbles.map(bubble => `
      <div class="bubble" style="
        position: absolute;
        left: ${bubble.x}%;
        top: ${bubble.y}%;
        width: ${bubble.size}px;
        height: ${bubble.size}px;
        font-size: ${bubble.size * 0.6}px;
        cursor: pointer;
        transition: transform 0.1s;
      " onclick="popBubbleById('${bubble.id}')">${bubble.emoji}</div>
    `).join('');
  }
  
  function endBubbleGame() {
    clearInterval(gameInterval);
    clearInterval(timerInterval);
    setTimeout(() => showGameComplete(), 1000);
  }
  
  window.popBubbleById = (id) => {
    popBubble(id);
  };
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div style="text-align: center; margin-bottom: 1rem;">
      <h3>🫧 Bubble Pop</h3>
      <p>Score: <span id="bubbleScore">0</span> | Time: <span id="bubbleTime">30</span>s</p>
    </div>
    <div id="bubbleContainer" style="position: relative; width: 100%; height: 500px; background: linear-gradient(to bottom, #dbeafe, #fef3c7); border-radius: 12px; overflow: hidden;"></div>
  `;
  
  gameInterval = setInterval(() => {
    createBubble();
    updateBubbles();
  }, 800);
  
  timerInterval = setInterval(() => {
    timeLeft--;
    document.getElementById('bubbleTime').textContent = timeLeft;
    if (timeLeft <= 0) {
      endBubbleGame();
    }
  }, 1000);
  
  createBubble();
}

// ==================== GAME COMPLETE ====================
function showGameComplete() {
  stopTimer();
  const elapsed = Math.floor((Date.now() - gameStartTime) / 1000);
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;
  
  const gameArea = document.getElementById('gameArea');
  gameArea.innerHTML = `
    <div class="game-complete">
      <h3>🎉 Game Complete!</h3>
      <p>Final Score: ${gameScore} points</p>
      <p>Time: ${timeStr}</p>
      <div class="game-controls">
        <button class="button-link" onclick="startGame('${currentGame}')">Play Again</button>
        <button class="button-link secondary" onclick="backToMenu()">Back to Menu</button>
      </div>
    </div>
  `;
}

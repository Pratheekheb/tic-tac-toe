let ws;
let symbol = "";
let currentTurn = "";
let gameOver = false;

const boardDiv = document.getElementById("board");
const statusDiv = document.getElementById("status");
const connectBtn = document.getElementById("connectBtn");
const playAgainBtn = document.getElementById("playAgainBtn");

// ================== CONNECT BUTTON ==================
connectBtn.addEventListener("click", async () => {
  // Close any existing WebSocket connection
  if (ws && ws.readyState === WebSocket.OPEN) ws.close();

  const nickname = document.getElementById("nickname").value;
  const matchId = document.getElementById("matchId").value;
  const playerId = document.getElementById("playerId").value;

  if (!nickname || !matchId || !playerId) {
    alert("Enter all details!");
    return;
  }

  // ✅ Only Player 1 resets the backend before starting
  if (playerId === "1") {
    try {
      await fetch("http://127.0.0.1:8000/reset");
      console.log("✅ Backend reset by Player 1");
      await new Promise((res) => setTimeout(res, 500)); // wait for cleanup
    } catch (e) {
      console.error("❌ Reset failed:", e);
    }
  }

  // ✅ Connect to WebSocket
  ws = new WebSocket(`ws://127.0.0.1:8000/ws/${matchId}/${playerId}`);

  ws.onopen = () => {
    statusDiv.textContent = "✅ Connected to server...";
    renderBoard();
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("📩 Received:", data);

    // Assign symbol (X or O)
    if (data.symbol) symbol = data.symbol;

    // Update whose turn
    if (data.turn) currentTurn = data.turn;

    // Update board on screen
    if (data.board) renderBoard(data.board);

    // Handle Winner
    if (data.winner) {
      statusDiv.textContent = `🎉 Player ${data.winner} Wins!`;
      disableBoard();
      playAgainBtn.style.display = "inline-block";
      gameOver = true;
      return;
    }

    // ✅ Show proper turn messages
    if (!gameOver) {
      if (currentTurn === symbol) {
        statusDiv.textContent = "🟢 Your turn!";
      } else {
        statusDiv.textContent = "⚪ Opponent’s turn...";
      }
    }

    // Show any error
    if (data.error) statusDiv.textContent = `⚠️ ${data.error}`;
  };

  ws.onclose = () => {
    statusDiv.textContent = "❌ Disconnected from server.";
  };
});

// ================== RENDER BOARD ==================
function renderBoard(board = [["", "", ""], ["", "", ""], ["", "", ""]]) {
  boardDiv.innerHTML = "";
  board.forEach((row, r) => {
    row.forEach((cell, c) => {
      const div = document.createElement("div");
      div.classList.add("cell");
      div.textContent = cell;

      // Colors for X and O
      if (cell === "X") div.style.color = "#00ffcc";
      if (cell === "O") div.style.color = "#ff007f";

      div.addEventListener("click", () => makeMove(r, c));
      boardDiv.appendChild(div);
    });
  });
}

// ================== GAME LOGIC ==================
function makeMove(row, col) {
  if (gameOver) return;

  if (currentTurn !== symbol) {
    statusDiv.textContent = "⏳ Not your turn!";
    return;
  }

  ws.send(JSON.stringify({ row, col }));
}

// ================== DISABLE BOARD AFTER WIN ==================
function disableBoard() {
  document.querySelectorAll(".cell").forEach((cell) => {
    cell.style.pointerEvents = "none";
  });
}

// ================== PLAY AGAIN BUTTON ==================
playAgainBtn.addEventListener("click", () => {
  playAgainBtn.style.display = "none";
  boardDiv.innerHTML = "";
  statusDiv.textContent = "♻️ Restarting...";
  renderBoard();
  gameOver = false;
});

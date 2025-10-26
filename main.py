import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from models import Player, Match, get_session, MatchStatus
import schemas

app = FastAPI(title="Multiplayer Tic Tac Toe Backend")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=BASE_DIR)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


def get_db():
    db = get_session()
    try:
        yield db
    finally:
        db.close()

# ✅ Global in-memory game state
active_matches = {}

# ======================================================
# ======== Basic API Endpoints for Players =============
# ======================================================

@app.post("/register", response_model=schemas.PlayerOut)
def register_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    existing_player = db.query(Player).filter(Player.nickname == player.nickname).first()
    if existing_player:
        raise HTTPException(status_code=400, detail="Nickname already exists")
    new_player = Player(nickname=player.nickname)
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@app.get("/leaderboard", response_model=list[schemas.PlayerOut])
def get_leaderboard(db: Session = Depends(get_db)):
    players = db.query(Player).order_by(Player.wins.desc()).all()
    return players


@app.post("/create_match/{player_id}", response_model=schemas.MatchOut)
def create_match(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    new_match = Match(player1_id=player.id, status=MatchStatus.waiting)
    db.add(new_match)
    db.commit()
    db.refresh(new_match)
    return new_match


@app.post("/join_match/{match_id}/{player_id}", response_model=schemas.MatchOut)
def join_match(match_id: int, player_id: int, db: Session = Depends(get_db)):
    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    if match.status != MatchStatus.waiting:
        raise HTTPException(status_code=400, detail="Match already full or started")

    player2 = db.query(Player).filter(Player.id == player_id).first()
    if not player2:
        raise HTTPException(status_code=404, detail="Player not found")

    match.player2_id = player2.id
    match.status = MatchStatus.playing
    db.commit()
    db.refresh(match)
    return match


# ======================================================
# ======== RESET ENDPOINT (Important Step) =============
# ======================================================
@app.get("/reset")
def reset_matches():
    """Clear all active matches from memory (used on page refresh)."""
    global active_matches
    active_matches = {}
    print("✅ All active matches cleared from memory.")
    return {"message": "All active matches cleared"}


# ======================================================
# ======== WebSocket Real-Time Game Logic ==============
# ======================================================

@app.websocket("/ws/{match_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, match_id: int, player_id: int):
    await websocket.accept()

    # If this is a new match
    if match_id not in active_matches:
        active_matches[match_id] = {
            "players": [],
            "symbols": {},
            "board": [["" for _ in range(3)] for _ in range(3)],
            "turn": "X"
        }

    match = active_matches[match_id]

    # Clean old connections
    match["players"] = [p for p in match["players"] if not p.client_state.name == "CLOSED"]

    # Assign X to first player, O to second
    if player_id not in match["symbols"]:
        if len(match["symbols"]) == 0:
            match["symbols"][player_id] = "X"
        elif len(match["symbols"]) == 1:
            match["symbols"][player_id] = "O"
        else:
            await websocket.send_json({"error": "Match full"})
            await websocket.close()
            return

    symbol = match["symbols"][player_id]
    match["players"].append(websocket)

    await websocket.send_json({
        "message": f"Connected successfully as Player {symbol}",
        "symbol": symbol,
        "turn": match["turn"]
    })

    if len(match["symbols"]) == 2:
        for ws in match["players"]:
            await ws.send_json({"message": "Both players connected! Player X starts."})

    try:
        while True:
            data = await websocket.receive_json()
            row, col = data["row"], data["col"]

            if match["turn"] != symbol:
                await websocket.send_json({"error": "Not your turn"})
                continue

            if match["board"][row][col] != "":
                await websocket.send_json({"error": "Cell already taken"})
                continue

            # Make move
            match["board"][row][col] = symbol

            winner = check_winner(match["board"])
            if winner:
                for ws in match["players"]:
                    await ws.send_json({
                        "board": match["board"],
                        "winner": winner,
                        "message": f"Player {winner} wins!"
                    })
                del active_matches[match_id]
                break

            # Switch turn
            match["turn"] = "O" if match["turn"] == "X" else "X"

            for ws in match["players"]:
                await ws.send_json({
                    "board": match["board"],
                    "turn": match["turn"]
                })

    except WebSocketDisconnect:
        print(f"⚠️ Player {symbol} disconnected from match {match_id}")

        if match_id in active_matches:
            match["players"] = [p for p in match["players"] if p != websocket]

            # Notify remaining player
            for ws in match["players"]:
                try:
                    await ws.send_json({"message": f"Opponent ({symbol}) left the game."})
                except:
                    pass

            if len(match["players"]) == 0:
                del active_matches[match_id]
                print(f"🗑️ Match {match_id} cleared.")


# ======================================================
# ======== Helper Function =============================
# ======================================================

def check_winner(board):
    for i in range(3):
        if board[i][0] == board[i][1] == board[i][2] != "":
            return board[i][0]
        if board[0][i] == board[1][i] == board[2][i] != "":
            return board[0][i]

    if board[0][0] == board[1][1] == board[2][2] != "":
        return board[0][0]

    if board[0][2] == board[1][1] == board[2][0] != "":
        return board[0][2]

    return None

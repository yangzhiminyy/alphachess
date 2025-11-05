from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid

from xiangqi.board import Board
from xiangqi.constants import pack_move, unpack_move
from xiangqi.alphabeta import alphabeta_search, simple_material_eval

app = FastAPI(title="Xiangqi API", version="0.1.0")

games: Dict[str, Board] = {}


class CreateGameRequest(BaseModel):
    squares: Optional[List[int]] = None
    side_to_move: Optional[int] = None


class MoveBody(BaseModel):
    from_sq: Optional[int] = None
    to_sq: Optional[int] = None
    move_id: Optional[int] = None


def serialize_state(game_id: str, b: Board) -> dict:
    legal = b.generate_legal_moves()
    legal_moves = []
    for mv in legal:
        fr, to, mt, ct, flags = unpack_move(mv)
        legal_moves.append({"from": fr, "to": to, "move_id": mv})
    return {
        "game_id": game_id,
        "squares": list(b.squares),
        "side_to_move": b.side_to_move,
        "in_check": b.is_in_check(b.side_to_move),
        "legal_moves": legal_moves,
        "can_claim_draw": b.can_claim_draw(),
        "repetition_count": b.repetition_count(),
        "hash_key": f"0x{b.hash_key & ((1<<64)-1):016x}",
    }


@app.post("/api/games")
def create_game(req: CreateGameRequest):
    gid = str(uuid.uuid4())
    b = Board()
    if req.squares:
        if len(req.squares) != 90:
            raise HTTPException(status_code=400, detail="squares must be length 90")
        b.squares = list(req.squares)
        b.side_to_move = req.side_to_move or 1
        b._rebuild_caches()
        b._recompute_hash()
        b.hash_history = [b.hash_key]
    else:
        b.set_startpos()
    games[gid] = b
    return serialize_state(gid, b)


@app.get("/api/games/{game_id}")
def get_game(game_id: str):
    b = games.get(game_id)
    if not b:
        raise HTTPException(status_code=404, detail="game not found")
    return serialize_state(game_id, b)


@app.get("/api/games/{game_id}/legal-moves")
def legal_moves(game_id: str, from_sq: Optional[int] = Query(default=None)):
    b = games.get(game_id)
    if not b:
        raise HTTPException(status_code=404, detail="game not found")
    res = []
    for mv in b.generate_legal_moves():
        fr, to, *_ = unpack_move(mv)
        if from_sq is None or fr == from_sq:
            res.append({"from": fr, "to": to, "move_id": mv})
    return {"moves": res}


@app.post("/api/games/{game_id}/move")
def make_move(game_id: str, body: MoveBody):
    b = games.get(game_id)
    if not b:
        raise HTTPException(status_code=404, detail="game not found")
    mv: Optional[int] = None
    legal = b.generate_legal_moves()
    if body.move_id is not None:
        if body.move_id in legal:
            mv = body.move_id
    elif body.from_sq is not None and body.to_sq is not None:
        # find matching move
        for cand in legal:
            fr, to, *_ = unpack_move(cand)
            if fr == body.from_sq and to == body.to_sq:
                mv = cand
                break
    if mv is None:
        raise HTTPException(status_code=400, detail="illegal or missing move")
    b.make_move(mv)
    return serialize_state(game_id, b)


@app.post("/api/games/{game_id}/undo")
def undo(game_id: str):
    b = games.get(game_id)
    if not b:
        raise HTTPException(status_code=404, detail="game not found")
    if not b.undo_stack:
        raise HTTPException(status_code=400, detail="no move to undo")
    b.unmake_move()
    return serialize_state(game_id, b)


@app.get("/api/games/{game_id}/best-move")
def best_move(game_id: str, depth: int = 3, engine: str = "ab"):
    b = games.get(game_id)
    if not b:
        raise HTTPException(status_code=404, detail="game not found")
    if engine != "ab":
        raise HTTPException(status_code=400, detail="only alpha-beta supported now")
    score, mv = alphabeta_search(b, depth, simple_material_eval)
    if mv is None:
        return {"best": None, "score": score, "pv": []}
    fr, to, *_ = unpack_move(mv)
    return {"best": {"from": fr, "to": to, "move_id": mv}, "score": score, "pv": []}


# 启动： uvicorn api.server:app --reload



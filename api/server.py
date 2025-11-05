from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
import math

from xq import GameState, constants as C, Move, legal_move_mask, alphabeta_search, MCTS
import threading

app = FastAPI(title="Xiangqi API", version="0.2.0")

# CORS for browser frontend
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
except Exception:
    pass

# Serve static frontend under /web
try:
    from fastapi.staticfiles import StaticFiles
    import os
    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
    if os.path.isdir(static_dir):
        app.mount("/web", StaticFiles(directory=static_dir, html=True), name="web")
except Exception:
    pass

games: Dict[str, GameState] = {}
_loaded_model = None
_model_path_cache = "models/latest.pt"
_model_type_cache = "legacy"  # "legacy" or "generic"


def _load_model(model_path: str):
    """
    Load either legacy XQNet or generic PolicyValueNet based on state_dict keys.
    Returns (model, model_type) where model_type is "legacy" or "generic".
    """
    import torch
    import os
    
    if not os.path.exists(model_path):
        return None, None
    
    try:
        # Load state dict to inspect keys
        state_dict = torch.load(model_path, map_location='cpu')
        
        # Check if it's generic (has batch norm keys) or legacy
        has_bn = any('bn' in key for key in state_dict.keys())
        
        if has_bn:
            # Generic model
            from alphazero.network import create_xiangqi_net
            model = create_xiangqi_net()
            model.load_state_dict(state_dict)
            model.eval()
            return model, "generic"
        else:
            # Legacy model
            from xq.nn import XQNet
            model = XQNet()
            model.load_state_dict(state_dict)
            model.eval()
            return model, "legacy"
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None


def _sq_to_coord(sq: int, one_based: bool = False) -> str:
    f = C.file_of(sq)
    r = C.rank_of(sq)
    file_char = chr(ord('a') + f)
    if one_based:
        return f"{file_char}{r+1}"
    return f"{file_char}{r}"


def _coord_to_sq(coord: str) -> int:
    if not coord or len(coord) < 2:
        raise ValueError("bad coord")
    file_char = coord[0].lower()
    if file_char < 'a' or file_char > 'i':
        raise ValueError("bad file")
    f = ord(file_char) - ord('a')
    rank_str = coord[1:]
    if not rank_str.isdigit():
        raise ValueError("bad rank")
    rank_val = int(rank_str)
    # accept 0-9 (zero-based) or 1-10 (one-based)
    if 0 <= rank_val <= 9:
        r = rank_val
    elif 1 <= rank_val <= 10:
        r = rank_val - 1
    else:
        raise ValueError("rank out of range")
    if not (0 <= f < C.FILES and 0 <= r < C.RANKS):
        raise ValueError("coord out of bounds")
    return C.index_of(f, r)



class CreateGameRequest(BaseModel):
    squares: Optional[List[int]] = None
    side_to_move: Optional[int] = None  # 1=RED, -1=BLACK


class MoveBody(BaseModel):
    from_sq: Optional[int] = None
    to_sq: Optional[int] = None
    move_id: Optional[int] = None  # 32-bit move code


def _serialize_state(game_id: str, s: GameState) -> dict:
    legal = s.generate_legal_moves()
    legal_moves = []
    for mv in legal:
        legal_moves.append({
            "from": mv.from_sq,
            "to": mv.to_sq,
            "from_coord": _sq_to_coord(mv.from_sq),
            "to_coord": _sq_to_coord(mv.to_sq),
            "move_id": int(mv),
        })
    return {
        "game_id": game_id,
        "squares": list(s.board),
        "side_to_move": s.side_to_move,
        "in_check": s.is_in_check(s.side_to_move),
        "legal_moves": legal_moves,
        "threefold": s.threefold_repetition(),
        "result": s.adjudicate_result(),
        "zkey": f"0x{s.zkey & ((1<<64)-1):016x}",
    }


@app.post("/api/games")
def create_game(req: CreateGameRequest):
    gid = str(uuid.uuid4())
    if req.squares:
        if len(req.squares) != 90:
            raise HTTPException(status_code=400, detail="squares must be length 90")
        side = req.side_to_move if req.side_to_move in (C.RED, C.BLACK) else C.RED
        s = GameState(board=list(req.squares), side_to_move=side)
    else:
        s = GameState()
        s.setup_starting_position()
    games[gid] = s
    return _serialize_state(gid, s)


@app.get("/api/games/{game_id}")
def get_game(game_id: str):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    return _serialize_state(game_id, s)


@app.get("/api/games/{game_id}/legal-moves")
def legal_moves(game_id: str, from_sq: Optional[int] = Query(default=None)):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    res = []
    for mv in s.generate_legal_moves():
        if from_sq is None or mv.from_sq == from_sq:
            res.append({
                "from": mv.from_sq,
                "to": mv.to_sq,
                "from_coord": _sq_to_coord(mv.from_sq),
                "to_coord": _sq_to_coord(mv.to_sq),
                "move_id": int(mv),
            })
    return {"moves": res}


@app.get("/api/games/{game_id}/policy-mask")
def policy_mask(game_id: str):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    mask = legal_move_mask(s)
    return {"mask": mask}


@app.post("/api/games/{game_id}/move")
def make_move(game_id: str, body: MoveBody):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    mv_obj: Optional[Move] = None
    legal = s.generate_legal_moves()
    if body.move_id is not None:
        for cand in legal:
            if int(cand) == body.move_id:
                mv_obj = cand
                break
    elif body.from_sq is not None and body.to_sq is not None:
        for cand in legal:
            if cand.from_sq == body.from_sq and cand.to_sq == body.to_sq:
                mv_obj = cand
                break
    if mv_obj is None:
        raise HTTPException(status_code=400, detail="illegal or missing move")
    s.apply_move(mv_obj)
    return _serialize_state(game_id, s)


@app.get("/api/convert/moveid-to-coord")
def convert_moveid_to_coord(move_id: int):
    # Decode using bit layout knowledge from xq.move.Move
    from_sq = (move_id >> 0) & ((1 << 7) - 1)
    to_sq = (move_id >> 7) & ((1 << 7) - 1)
    return {
        "from": from_sq,
        "to": to_sq,
        "from_coord": _sq_to_coord(from_sq),
        "to_coord": _sq_to_coord(to_sq),
    }


@app.get("/api/convert/coord-to-moveid")
def convert_coord_to_moveid(game_id: str, from_coord: str, to_coord: str):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    try:
        from_sq = _coord_to_sq(from_coord)
        to_sq = _coord_to_sq(to_coord)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    for cand in s.generate_legal_moves():
        if cand.from_sq == from_sq and cand.to_sq == to_sq:
            return {"move_id": int(cand), "from": from_sq, "to": to_sq}
    raise HTTPException(status_code=400, detail="no legal move matches the given coordinates")


class HumanAiBody(BaseModel):
    # human move (one of the forms)
    move_id: Optional[int] = None
    from_sq: Optional[int] = None
    to_sq: Optional[int] = None
    from_coord: Optional[str] = None
    to_coord: Optional[str] = None
    # engine options
    engine: str = "ab"  # ab | mcts | mcts_nn
    depth: int = 3
    sims: int = 100
    tau: float = 1.0
    model_path: Optional[str] = None
    time_ms: Optional[int] = None


@app.post("/api/games/{game_id}/human-ai")
def human_ai(game_id: str, body: HumanAiBody):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    # Find and apply human move
    mv_obj: Optional[Move] = None
    legal = s.generate_legal_moves()
    if body.move_id is not None:
        for cand in legal:
            if int(cand) == body.move_id:
                mv_obj = cand
                break
    elif body.from_sq is not None and body.to_sq is not None:
        for cand in legal:
            if cand.from_sq == body.from_sq and cand.to_sq == body.to_sq:
                mv_obj = cand
                break
    elif body.from_coord and body.to_coord:
        try:
            from_sq = _coord_to_sq(body.from_coord)
            to_sq = _coord_to_sq(body.to_coord)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        for cand in legal:
            if cand.from_sq == from_sq and cand.to_sq == to_sq:
                mv_obj = cand
                break
    if mv_obj is None:
        raise HTTPException(status_code=400, detail="illegal or missing human move")
    s.apply_move(mv_obj)
    human_move = {"from": mv_obj.from_sq, "to": mv_obj.to_sq, "from_coord": _sq_to_coord(mv_obj.from_sq), "to_coord": _sq_to_coord(mv_obj.to_sq), "move_id": int(mv_obj)}

    # Compute AI move
    ai_move_obj: Optional[Move] = None
    ai_score = None
    if body.engine == "ab":
        ai_move_obj, ai_score = alphabeta_search(s, body.depth)
    elif body.engine == "mcts" or body.engine == "mcts_nn":
        def policy_fn(state: GameState):
            mask = legal_move_mask(state)
            legal_count = sum(1 for x in mask if x > 0)
            p = [0.0] * (C.NUM_SQUARES * C.NUM_SQUARES)
            if legal_count > 0:
                w = 1.0 / legal_count
                for i, v in enumerate(mask):
                    if v > 0:
                        p[i] = w
            score = _simple_material_eval(state)
            pov = score if state.side_to_move == C.RED else -score
            val = math.tanh(pov / 2000.0)
            return p, float(val)
        # Optionally use NN when engine=mcts_nn
        if body.engine == "mcts_nn":
            global _loaded_model, _model_path_cache, _model_type_cache
            model_path = body.model_path or _model_path_cache
            if _loaded_model is None or model_path != _model_path_cache:
                _loaded_model, _model_type_cache = _load_model(model_path)
                _model_path_cache = model_path
            
            if _loaded_model is not None:
                from xq.nn import state_to_tensor  # type: ignore
                import torch  # type: ignore
                def policy_fn(state: GameState):  # type: ignore
                    with torch.no_grad():
                        x = state_to_tensor(state).unsqueeze(0)
                        logits, v = _loaded_model(x)
                        policy = torch.softmax(logits[0], dim=-1).tolist()
                        return policy, float(v.item())
        mcts = MCTS()
        root = mcts.run(s, policy_fn, num_simulations=body.sims, time_limit_s=(body.time_ms/1000.0 if body.time_ms else None))
        probs = mcts.action_probs(root, tau=body.tau)
        if probs:
            best_idx = max(probs.items(), key=lambda kv: kv[1])[0]
            from_sq = best_idx // C.NUM_SQUARES
            to_sq = best_idx % C.NUM_SQUARES
            for cand in s.generate_legal_moves():
                if cand.from_sq == from_sq and cand.to_sq == to_sq:
                    ai_move_obj = cand
                    break
    else:
        raise HTTPException(status_code=400, detail="unknown engine; use 'ab' or 'mcts' or 'mcts_nn'")

    if ai_move_obj is not None:
        s.apply_move(ai_move_obj)
    ai_move = None if ai_move_obj is None else {"from": ai_move_obj.from_sq, "to": ai_move_obj.to_sq, "from_coord": _sq_to_coord(ai_move_obj.from_sq), "to_coord": _sq_to_coord(ai_move_obj.to_sq), "move_id": int(ai_move_obj), "score": ai_score}
    state = _serialize_state(game_id, s)
    return {"human": human_move, "ai": ai_move, "state": state}


@app.get("/api/model/framework")
def get_model_framework():
    """Return information about the currently loaded model framework."""
    global _loaded_model, _model_path_cache, _model_type_cache
    return {
        "loaded": _loaded_model is not None,
        "path": _model_path_cache,
        "framework": _model_type_cache if _loaded_model is not None else None
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/model/info")
def model_info(model_path: str = "models/latest.pt", offset: int = 0, limit: int = 20):
    import os
    if not os.path.exists(model_path):
        raise HTTPException(status_code=404, detail="Model file not found")
    
    try:
        import torch
        from xq.nn import XQNet
        
        # Load model
        model = XQNet()
        state_dict = torch.load(model_path, map_location="cpu")
        model.load_state_dict(state_dict)
        
        # Get model structure
        structure = []
        for name, module in model.named_modules():
            if name:  # skip root
                structure.append({
                    "name": name,
                    "type": type(module).__name__
                })
        
        # Count parameters
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # Get layer details
        layers = []
        for name, param in model.named_parameters():
            layers.append({
                "name": name,
                "shape": list(param.shape),
                "dtype": str(param.dtype),
                "requires_grad": param.requires_grad,
                "num_params": param.numel()
            })
        
        # File info
        file_size = os.path.getsize(model_path)
        file_size_mb = file_size / (1024 * 1024)
        
        # Build topology graph
        topology = {
            "nodes": [],
            "edges": []
        }
        
        # Add input node
        topology["nodes"].append({"id": "input", "label": "Input\n[15,10,9]", "type": "input"})
        
        # Add stem
        topology["nodes"].append({"id": "stem", "label": "Stem Conv\n64 channels", "type": "conv"})
        topology["edges"].append({"from": "input", "to": "stem"})
        
        # Add residual blocks
        prev = "stem"
        for i in range(3):
            block_id = f"block{i}"
            topology["nodes"].append({"id": block_id, "label": f"ResBlock {i+1}\n64 channels", "type": "residual"})
            topology["edges"].append({"from": prev, "to": block_id})
            prev = block_id
        
        # Policy head
        topology["nodes"].append({"id": "p_conv", "label": "Policy Conv\n32 channels", "type": "conv"})
        topology["edges"].append({"from": prev, "to": "p_conv"})
        topology["nodes"].append({"id": "p_fc", "label": "Policy FC\n8100", "type": "dense"})
        topology["edges"].append({"from": "p_conv", "to": "p_fc"})
        topology["nodes"].append({"id": "policy_out", "label": "Policy Output\n[8100]", "type": "output"})
        topology["edges"].append({"from": "p_fc", "to": "policy_out"})
        
        # Value head
        topology["nodes"].append({"id": "v_conv", "label": "Value Conv\n32 channels", "type": "conv"})
        topology["edges"].append({"from": prev, "to": "v_conv"})
        topology["nodes"].append({"id": "v_fc1", "label": "Value FC1\n128", "type": "dense"})
        topology["edges"].append({"from": "v_conv", "to": "v_fc1"})
        topology["nodes"].append({"id": "v_fc2", "label": "Value FC2\n1", "type": "dense"})
        topology["edges"].append({"from": "v_fc1", "to": "v_fc2"})
        topology["nodes"].append({"id": "value_out", "label": "Value Output\n[1]", "type": "output"})
        topology["edges"].append({"from": "v_fc2", "to": "value_out"})
        
        return {
            "model_path": model_path,
            "file_size_mb": round(file_size_mb, 2),
            "architecture": {
                "in_channels": 15,
                "channels": 64,
                "num_blocks": 3,
                "policy_output": 8100,
                "value_output": 1
            },
            "parameters": {
                "total": total_params,
                "trainable": trainable_params
            },
            "structure": {
                "items": structure[offset:offset+limit],
                "total": len(structure),
                "offset": offset,
                "limit": limit
            },
            "layers": layers,
            "topology": topology
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/model/list")
def list_models():
    import os
    import glob
    
    models_dir = "models"
    if not os.path.exists(models_dir):
        return {"models": []}
    
    models = []
    for path in glob.glob(os.path.join(models_dir, "*.pt")):
        file_size = os.path.getsize(path)
        file_size_mb = file_size / (1024 * 1024)
        models.append({
            "path": path,
            "name": os.path.basename(path),
            "size_mb": round(file_size_mb, 2),
            "modified": os.path.getmtime(path)
        })
    
    models.sort(key=lambda x: x["modified"], reverse=True)
    return {"models": models}


# Training Loop Management
class TrainLoopBody(BaseModel):
    games_per_batch: int = 10
    sims_per_move: int = 100
    max_moves: int = 150
    train_epochs: int = 3
    train_batch_size: int = 32
    train_lr: float = 1e-3
    max_iterations: int = 100
    model_path: str = "models/latest.pt"
    data_dir: str = "data"
    use_nn: bool = False


@app.post("/api/train/start")
def start_training(body: TrainLoopBody):
    from xq.train_loop import TrainLoopConfig, run_train_loop, get_status, _global_status
    
    status = get_status()
    if status.running:
        raise HTTPException(status_code=400, detail="Training already running")
    
    config = TrainLoopConfig(
        games_per_batch=body.games_per_batch,
        sims_per_move=body.sims_per_move,
        max_moves=body.max_moves,
        train_epochs=body.train_epochs,
        train_batch_size=body.train_batch_size,
        train_lr=body.train_lr,
        max_iterations=body.max_iterations,
        model_path=body.model_path,
        data_dir=body.data_dir,
        use_nn=body.use_nn,
    )
    
    def callback(msg: str):
        print(f"[TrainLoop] {msg}")
    
    # Run in background thread
    thread = threading.Thread(target=run_train_loop, args=(config, callback), daemon=True)
    thread.start()
    
    return {"status": "started", "config": body.dict()}


@app.post("/api/train/stop")
def stop_training():
    from xq.train_loop import request_stop, get_status
    
    status = get_status()
    if not status.running:
        return {"status": "not_running"}
    
    request_stop()
    return {"status": "stop_requested"}


@app.get("/api/train/status")
def training_status():
    from xq.train_loop import get_status
    
    status = get_status()
    return status.to_dict()


@app.post("/api/games/{game_id}/undo")
def undo(game_id: str):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    if not s.undo_stack:
        raise HTTPException(status_code=400, detail="no move to undo")
    s.undo_move()
    return _serialize_state(game_id, s)


@app.get("/api/games/{game_id}/best-move")
def best_move(game_id: str, engine: str = "ab", depth: int = 3, sims: int = 100, tau: float = 1.0, model_path: Optional[str] = None, time_ms: Optional[int] = None):
    s = games.get(game_id)
    if not s:
        raise HTTPException(status_code=404, detail="game not found")
    if engine == "ab":
        mv, score = alphabeta_search(s, depth)
        if mv is None:
            return {"best": None, "score": score}
        return {"best": {"from": mv.from_sq, "to": mv.to_sq, "move_id": int(mv)}, "score": score}
    elif engine == "mcts":
        # minimal policy fn: uniform over legal + simple value
        def policy_fn(state: GameState):
            mask = legal_move_mask(state)
            legal_count = sum(1 for x in mask if x > 0)
            p = [0.0] * (C.NUM_SQUARES * C.NUM_SQUARES)
            if legal_count > 0:
                w = 1.0 / legal_count
                for i, v in enumerate(mask):
                    if v > 0:
                        p[i] = w
            # simple value from material
            score = _simple_material_eval(state)
            pov = score if state.side_to_move == C.RED else -score
            val = math.tanh(pov / 2000.0)
            return p, float(val)

        mcts = MCTS()
        root = mcts.run(s, policy_fn, num_simulations=sims, time_limit_s=(time_ms/1000.0 if time_ms else None))
        probs = mcts.action_probs(root, tau=tau)
        # choose action by max prob
        if not probs:
            return {"best": None, "score": None, "pi": {}}
        best_idx = max(probs.items(), key=lambda kv: kv[1])[0]
        from_sq = best_idx // C.NUM_SQUARES
        to_sq = best_idx % C.NUM_SQUARES
        mv = None
        for cand in s.generate_legal_moves():
            if cand.from_sq == from_sq and cand.to_sq == to_sq:
                mv = cand
                break
        return {
            "best": (None if mv is None else {"from": mv.from_sq, "to": mv.to_sq, "move_id": int(mv)}),
            "pi": {str(k): v for k, v in probs.items()},
        }
    elif engine == "mcts_nn":
        # Load model lazily
        global _loaded_model, _model_path_cache, _model_type_cache
        if model_path is None:
            model_path = _model_path_cache
        if _loaded_model is None or model_path != _model_path_cache:
            _loaded_model, _model_type_cache = _load_model(model_path)
            _model_path_cache = model_path

        def policy_fn(state: GameState):
            if _loaded_model is None:
                # fallback to uniform + simple value
                mask = legal_move_mask(state)
                legal_count = sum(1 for x in mask if x > 0)
                p = [0.0] * (C.NUM_SQUARES * C.NUM_SQUARES)
                if legal_count > 0:
                    w = 1.0 / legal_count
                    for i, v in enumerate(mask):
                        if v > 0:
                            p[i] = w
                score = _simple_material_eval(state)
                pov = score if state.side_to_move == C.RED else -score
                val = math.tanh(pov / 2000.0)
                return p, float(val)
            from xq.nn import state_to_tensor
            import torch
            with torch.no_grad():
                x = state_to_tensor(state).unsqueeze(0)
                logits, v = _loaded_model(x)
                policy = torch.softmax(logits[0], dim=-1).tolist()
                return policy, float(v.item())

        mcts = MCTS()
        root = mcts.run(s, policy_fn, num_simulations=sims, time_limit_s=(time_ms/1000.0 if time_ms else None))
        probs = mcts.action_probs(root, tau=tau)
        if not probs:
            return {"best": None, "score": None, "pi": {}}
        best_idx = max(probs.items(), key=lambda kv: kv[1])[0]
        from_sq = best_idx // C.NUM_SQUARES
        to_sq = best_idx % C.NUM_SQUARES
        mv = None
        for cand in s.generate_legal_moves():
            if cand.from_sq == from_sq and cand.to_sq == to_sq:
                mv = cand
                break
        return {
            "best": (None if mv is None else {"from": mv.from_sq, "to": mv.to_sq, "move_id": int(mv)}),
            "pi": {str(k): v for k, v in probs.items()},
        }
    else:
        raise HTTPException(status_code=400, detail="unknown engine; use 'ab' or 'mcts'")


def _simple_material_eval(state: GameState) -> int:
    weights = {
        C.PT_PAWN: 100,
        C.PT_CANNON: 450,
        C.PT_KNIGHT: 450,
        C.PT_BISHOP: 250,
        C.PT_ADVISOR: 250,
        C.PT_ROOK: 900,
        C.PT_KING: 10000,
    }
    red = 0
    black = 0
    for p in state.board:
        if p == 0:
            continue
        v = weights[C.piece_type(p)]
        if p > 0:
            red += v
        else:
            black += v
    return red - black


# 启动： uvicorn api.server:app --reload


# Self-play endpoint (single game; may take time)
from pydantic import BaseModel


class SelfPlayBody(BaseModel):
    engine: str = "mcts"  # "mcts" or "mcts_nn"
    sims: int = 100
    max_moves: int = 150
    tau_moves: int = 10
    tau_start: float = 1.0
    tau_final: float = 0.05
    model_path: Optional[str] = None
    compact: bool = True  # if true, omit planes and pi in records


@app.post("/api/selfplay")
def selfplay(body: SelfPlayBody):
    from xq.selfplay import SelfPlayConfig, self_play_game

    cfg = SelfPlayConfig(
        engine=body.engine,
        sims=body.sims,
        max_moves=body.max_moves,
        tau_moves=body.tau_moves,
        tau_start=body.tau_start,
        tau_final=body.tau_final,
        model_path=body.model_path,
        store_planes=(not body.compact),
        store_pi=(not body.compact),
    )
    game = self_play_game(cfg)
    return game


# ============================================================
# Arena / ELO Evaluation Endpoints
# ============================================================

class ArenaBody(BaseModel):
    engine_a: str = "random"
    engine_b: str = "random"
    model_a: Optional[str] = None
    model_b: Optional[str] = None
    params_a: Optional[Dict] = None
    params_b: Optional[Dict] = None
    n_games: int = 10

@app.post("/api/arena/run")
def run_arena(body: ArenaBody):
    """Run arena evaluation between two engines."""
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        from scripts.arena import arena
        
        results = arena(
            engine_a=body.engine_a,
            engine_b=body.engine_b,
            model_a=body.model_a,
            model_b=body.model_b,
            params_a=body.params_a or {},
            params_b=body.params_b or {},
            n_games=body.n_games,
            verbose=False
        )
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


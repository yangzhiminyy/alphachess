from typing import Callable, Optional, Dict
from constants import RED, BLACK, unpack_move


def alphabeta_search(board, depth: int,
                     eval_func: Callable,  # board -> value, higher for RED
                     policy_func: Optional[Callable] = None,
                     is_root: bool = True) -> tuple:
    """
    Alpha-Beta 主流程，允许插入自定义评估/策略排序（如NN Head）。
    返回: (得分, 最佳走法)
    """
    side = board.side_to_move
    if depth == 0:
        v = eval_func(board)
        return v, None
    legal_moves = board.generate_legal_moves()
    if not legal_moves:
        # 局面无招，输/和局（后续判和可扩展）
        return -99999 if board.is_in_check(side) else 0, None
    # 若用policy_func，先排序
    move_probs: Optional[Dict[int, float]] = None
    if policy_func:
        move_probs = policy_func(board)
        legal_moves.sort(key=lambda mv: move_probs.get(mv, 0.0), reverse=True)
    best_val = -float('inf') if side == RED else float('inf')
    best_move = None
    for mv in legal_moves:
        board.make_move(mv)
        score, _ = alphabeta_search(board, depth-1, eval_func, policy_func, False)
        board.unmake_move()
        score = -score  # 轮换视角，RED得分最大化，BLACK最小化
        if side == RED:
            if score > best_val or best_move is None:
                best_val = score
                best_move = mv
        else:
            if score < best_val or best_move is None:
                best_val = score
                best_move = mv
    if is_root:
        return best_val, best_move
    return best_val, None


def simple_material_eval(board) -> float:
    """最简单的静态评估：子力和，只看红减黑。"""
    from .constants import MATERIAL_VALUES
    val = 0.0
    for code in board.squares:
        if code != 0:
            side = RED if code > 0 else BLACK
            val += MATERIAL_VALUES[abs(code)] * (1 if side == RED else -1)
    return val

# 用法说明：
# v, mv = alphabeta_search(board, 3, simple_material_eval)
# 若要用NN，eval_func可封装一次张量推理，policy_func返回策略分布dict即可
# 例如：policy_func(board)返回{move: prob, ...}

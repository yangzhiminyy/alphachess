import torch
from typing import List
from constants import (
    RED, BLACK, PIECE_PAWN, PIECE_CANNON, PIECE_KNIGHT, PIECE_BISHOP, PIECE_ADVISOR, PIECE_ROOK, PIECE_KING
)

PIECE_TYPES = [PIECE_PAWN, PIECE_CANNON, PIECE_KNIGHT, PIECE_BISHOP, PIECE_ADVISOR, PIECE_ROOK, PIECE_KING]
NUM_TYPES = len(PIECE_TYPES)
BOARD_ROWS = 10
BOARD_COLS = 9
POLICY_PLANES = BOARD_ROWS * BOARD_COLS * BOARD_ROWS * BOARD_COLS  # 90x90 = 8100


def board_encode_planes(board, history_num=8):
    """Encode board as (channels, 10, 9) tensor, history_num为历史步数。"""
    # 通道分配：2×7×history_num，1通道side，后可加全局，如将军态等
    planes = []
    stack = [board]  # 当前只保存现态，可以用undo返回历史
    # 生成历史快照
    snapshot_list = []
    tmp = board
    for _ in range(history_num):
        snapshot = [x for x in tmp.squares]
        snapshot_list.append((snapshot, tmp.side_to_move))
        if not tmp.undo_stack:
            break
        tmp = tmp.__class__()  # 新建一个board并倒退
        # restore by replay undo
        for rec in tmp.undo_stack:
            pass  # 不实现自动回溯，防止污染当前对象。现只存当前态。
    # 填充到history_num
    while len(snapshot_list) < history_num:
        snapshot_list.append(([0]*90, RED))
    # 对每步历史填充通道
    for s, stm in snapshot_list:
        # 14通道: 红子7+黑子7
        for type_id in PIECE_TYPES:
            # 红
            chn = torch.zeros(BOARD_ROWS, BOARD_COLS, dtype=torch.float32)
            for sq, code in enumerate(s):
                if code == type_id:
                    chn[sq//9, sq%9] = 1.0
            planes.append(chn)
            # 黑
            chn = torch.zeros(BOARD_ROWS, BOARD_COLS, dtype=torch.float32)
            for sq, code in enumerate(s):
                if code == -type_id:
                    chn[sq//9, sq%9] = 1.0
            planes.append(chn)
    # 1通道side to move
    stm_plane = torch.full((BOARD_ROWS, BOARD_COLS), 1.0 if board.side_to_move == RED else 0.0, dtype=torch.float32)
    planes.append(stm_plane)
    return torch.stack(planes, dim=0)  # (channels, 10, 9)


def move_to_policy_index(from_sq, to_sq):
    """将from_sq, to_sq (0..89/0..89)映射到[0,8100)整数索引."""
    return from_sq * (BOARD_ROWS*BOARD_COLS) + to_sq

def policy_index_to_move(idx):
    """将8100空间索引还原为from,to （走法编码部分用）"""
    from_sq = idx // (BOARD_ROWS*BOARD_COLS)
    to_sq = idx % (BOARD_ROWS*BOARD_COLS)
    return from_sq, to_sq


def legal_moves_mask(board) -> torch.BoolTensor:
    """生成合法走法掩码（8100维）。用于策略分布softmax后屏蔽非法。"""
    mask = torch.zeros(POLICY_PLANES, dtype=torch.bool)
    for mv in board.generate_legal_moves():
        fr, to, *_ = board.unpack_move(mv) if hasattr(board, 'unpack_move') else (mv>>0&0x7f, mv>>7&0x7f)
        idx = move_to_policy_index(fr, to)
        mask[idx] = True
    return mask

# 一步推理/训练例用法示例
# model = ... # 任意pytorch网络
# x = board_encode_planes(board).unsqueeze(0)  # 增加batch维
# logits, value = model(x) # logits shape: [1,8100]; value: [1]
# mask = legal_moves_mask(board)
# logits[~mask] = -1e9  # 做softmax之前抑制非法走法，可用torch.where实现
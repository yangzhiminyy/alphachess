import pickle
import random
import torch
import numpy as np
from board import Board
from nnio import board_encode_planes, move_to_policy_index, legal_moves_mask


def sample_episode(policy_func_red, policy_func_black, max_steps=250):
    """执行一局自对弈, 返回(s, pi, v)三元组 list."""
    board = Board()
    board.set_startpos()
    history = []   # (state_planes, pi_vec)
    move_history = [] # only for fast reward and record
    done = False
    steps = 0
    while not done and steps < max_steps:
        planes = board_encode_planes(board)
        legal_mask = legal_moves_mask(board).numpy()
        if board.side_to_move == 1:
            policy = policy_func_red(board, legal_mask)
        else:
            policy = policy_func_black(board, legal_mask)
        # temperature采样, 保证探索度
        pi = np.zeros(8100, dtype=np.float32)
        if sum(policy.values()) > 0:
            tmp = 1.0
            sampled = random.choices(list(policy.keys()), weights=list(policy.values()), k=1)[0]
            for mv, prob in policy.items():
                fr = (mv >> 0) & 0x7F
                to = (mv >> 7) & 0x7F
                idx = move_to_policy_index(fr, to)
                pi[idx] = prob
            move = sampled
        else:
            move = random.choice([mv for mv in policy.keys()]) if policy else None
        # 保存 state, pi
        if move is not None:
            history.append((planes.numpy(), pi))
            move_history.append(move)
            board.make_move(move)
        else:
            done = True
        # 判终局
        legal = board.generate_legal_moves()
        if not legal or board.can_claim_draw():
            done = True
        steps += 1
    # 胜负归一化: 红胜+1, 黑胜-1, 和0
    if board.is_in_check(-board.side_to_move):
        reward = 1 if board.side_to_move == -1 else -1
    else:
        reward = 0
    ep_data = [(s, p, reward) if ((i % 2 == 0) == True) else (s, p, -reward)
               for i, (s, p) in enumerate(history)]
    return ep_data


def dummy_policy_func(board, legal_mask):
    """均匀随机合法走法。兼容空模型占位。"""
    legal = board.generate_legal_moves()
    out = {}
    if not legal:
        return out
    for mv in legal:
        out[mv] = 1.0
    return out

if __name__ == '__main__':
    episodes = 5
    dataset = []
    for i in range(episodes):
        print(f'=== Episode {i+1} ===')
        ep = sample_episode(dummy_policy_func, dummy_policy_func)
        dataset.extend(ep)
    # 保存为pickle供训练用
    with open('selfplay_samples.pkl', 'wb') as f:
        pickle.dump(dataset, f)
    print(f'样本保存到: selfplay_samples.pkl, 总条数: {len(dataset)}')

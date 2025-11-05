import random
import math
from board import Board
from constants import RED, BLACK
from play import ai_move, dummy_policy_func

def play_game(policy_func_red, policy_func_black, max_steps=200):
    board = Board()
    board.set_startpos()
    moves = []
    finished = False
    steps = 0
    while not finished and steps < max_steps:
        pf = policy_func_red if board.side_to_move==RED else policy_func_black
        mv = ai_move(board, pf)
        if mv is None:
            break
        board.make_move(mv)
        moves.append(mv)
        if not board.generate_legal_moves():
            finished = True
        elif board.can_claim_draw():
            finished = True
        steps += 1
    # 结果解释: 1=红胜, 0=和, -1=黑胜
    if not board.generate_legal_moves():
        winner = 1 if board.side_to_move==BLACK else -1
    elif board.can_claim_draw():
        winner = 0
    else:
        winner = 0
    return winner, moves

def elo_from_scores(scores, n_games):
    # scores: 胜=1，和=0.5，负=0，常用Elo估计
    mean = sum(scores)/n_games
    # 计算Elo基础分差
    # P = 1/(1+10^(-dr/400)) => dr = -400*log10(1/P-1)
    P = max(min(mean,0.99),0.01)
    dr = -400 * math.log10(1/P - 1)
    return dr, mean

def arena(policy_func_a, policy_func_b, n_games=20):
    # a红先，b黑后，比分换色各n_games/2
    scores = []
    for i in range(n_games//2):
        w,_ = play_game(policy_func_a, policy_func_b)
        if w == 1:
            scores.append(1.0)
        elif w == 0:
            scores.append(0.5)
        else:
            scores.append(0.0)
    # 换色
    for i in range(n_games//2):
        w,_ = play_game(policy_func_b, policy_func_a)
        if w == -1:
            scores.append(1.0)
        elif w == 0:
            scores.append(0.5)
        else:
            scores.append(0.0)
    elo, mean = elo_from_scores(scores, n_games)
    print(f'胜率: {mean*100:.2f}%, Elo估计分差: {elo:.1f} (A-B，正分说明A优于B)')
    return elo, mean, scores

if __name__ == '__main__':
    print('中国象棋策略Elo评测范例~')
    # demo: 用两个dummy_policy_func对怼，可替换为NN/AlphaBeta等
    elo, mean, scores = arena(dummy_policy_func, dummy_policy_func, n_games=10)
    print(f'得分序列: {scores}')

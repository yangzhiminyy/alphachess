import sys
import random
from board import Board
from constants import RED, BLACK, rc_to_sq
from nnio import move_to_policy_index, policy_index_to_move

def print_board(board):
    symbol = {
        0: ' . ', 1: '兵', -1: '卒',
        2: '炮', -2: '砲', 3: '马', -3: '馬',
        4: '相', -4: '象', 5: '仕', -5: '士',
        6: '车', -6: '車', 7: '帅', -7: '将',
    }
    for r in range(10):
        line = []
        for c in range(9):
            code = board.squares[r*9 + c]
            line.append(symbol.get(code, f'{code:2d}'))
        print(' '.join(line))
    print('side_to_move:', '红' if board.side_to_move == RED else '黑')

def dummy_policy_func(board, _=None):
    legal = board.generate_legal_moves()
    out = {}
    if not legal:
        return out
    for mv in legal:
        out[mv] = 1.0
    return out

def index_to_san(idx):
    # from-to索引转可读格式
    fr, to = policy_index_to_move(idx)
    return f'{fr}->{to}'

def move_to_san(mv):
    fr = (mv >> 0) & 0x7F
    to = (mv >> 7) & 0x7F
    return f'{fr}->{to}'

def ai_move(board, policy_func):
    legal = board.generate_legal_moves()
    if not legal:
        return None
    policy = policy_func(board, None)
    if sum(policy.values()) == 0:
        # fallback uniform
        return random.choice(legal)
    # 随机采样
    moves, probs = zip(*policy.items())
    mv = random.choices(moves, weights=probs, k=1)[0]
    return mv

def human_move(board):
    legal = board.generate_legal_moves()
    if not legal:
        return None
    print('可选走法:')
    for i, mv in enumerate(legal):
        print(f'{i+1}: {move_to_san(mv)}')
    while True:
        inp = input('请选择走法（数字）：')
        try:
            k = int(inp)-1
            if 0 <= k < len(legal):
                return legal[k]
        except Exception:
            pass
        print('输入无效，请重新选择。')

def play_match(policy_func_red, policy_func_black, human_side=None, max_steps=200):
    board = Board()
    board.set_startpos()
    print('开局：')
    print_board(board)
    finished = False
    moves = []
    steps = 0
    while not finished and steps < max_steps:
        current_side = '红' if board.side_to_move==RED else '黑'
        print(f'第{steps+1}步，当前 {current_side}方行棋')
        if (human_side == board.side_to_move):
            mv = human_move(board)
        else:
            pf = policy_func_red if board.side_to_move==RED else policy_func_black
            mv = ai_move(board, pf)
        if mv is None:
            print('已无合法行棋。')
            break
        print(f'选中走法：{move_to_san(mv)}')
        board.make_move(mv)
        print_board(board)
        moves.append(mv)
        if board.is_in_check(-board.side_to_move):
            print('将军！')
        if not board.generate_legal_moves():
            winner = '红' if board.side_to_move==BLACK else '黑'
            print(f'胜负已分，{winner}方胜！')
            finished = True
        elif board.can_claim_draw():
            print('可判和棋。')
            finished = True
        steps += 1
    if not finished:
        print(f'步数上限{max_steps}，判和棋。')
    return moves

if __name__ == '__main__':
    print('中国象棋 AI对弈示例：')
    print('1. AI vs AI   2. 人机（红先）   3. 人机（黑先）')
    inp = input('选择模式: ')
    if inp.strip() == '2':
        play_match(dummy_policy_func, dummy_policy_func, human_side=RED)
    elif inp.strip() == '3':
        play_match(dummy_policy_func, dummy_policy_func, human_side=BLACK)
    else:
        play_match(dummy_policy_func, dummy_policy_func)

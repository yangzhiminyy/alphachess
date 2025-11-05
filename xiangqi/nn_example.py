import torch
import torch.nn as nn
import torch.nn.functional as F
from nnio import board_encode_planes, legal_moves_mask, policy_index_to_move, move_to_policy_index
from board import Board
from alphabeta import alphabeta_search

def make_simple_resnet(in_channels=113, hidden=128, blocks=7):
    """极简中国象棋残差神经网络样板。"""
    class Block(nn.Module):
        def __init__(self, ch):
            super().__init__()
            self.conv1 = nn.Conv2d(ch, ch, 3, padding=1)
            self.bn1 = nn.BatchNorm2d(ch)
            self.conv2 = nn.Conv2d(ch, ch, 3, padding=1)
            self.bn2 = nn.BatchNorm2d(ch)
        def forward(self, x):
            h = F.relu(self.bn1(self.conv1(x)))
            h = self.bn2(self.conv2(h))
            return F.relu(x + h)
    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.init_conv = nn.Conv2d(in_channels, hidden, 3, padding=1)
            self.blocks = nn.Sequential(*[Block(hidden) for _ in range(blocks)])
            # policy: 8100 logits
            # self.head_policy = nn.Sequential(
            #     nn.Conv2d(hidden, 32, 1), nn.ReLU(), nn.Flatten(), nn.Linear(32*10*9, 8100)
            # )
            self.head_policy = nn.Sequential(
                nn.Conv2d(hidden, 2, 1),  # 2个通道，实验用，可酌情加大
                nn.Flatten(),
                nn.Linear(2*10*9, 8100)
            )
            # value: [-1,1]
            self.head_value = nn.Sequential(
                nn.Conv2d(hidden, 32, 1), nn.ReLU(), nn.Flatten(), nn.Linear(32*10*9, 64), nn.ReLU(), nn.Linear(64, 1), nn.Tanh()
            )
        def forward(self, x):
            h = F.relu(self.init_conv(x))
            h = self.blocks(h)
            p = self.head_policy(h)
            v = self.head_value(h)
            return p, v.squeeze(-1)
    return Net()


def nn_eval_func(model, device):
    """
    返回适配于alphabeta的评估器, board->float.
    给出红方 perspective 的NN值（[-1,+1]）*10000(temp分)，用于极大极小。
    """
    def evaluator(board):
        x = board_encode_planes(board).unsqueeze(0).to(device)
        with torch.no_grad():
            logits, value = model(x)
        return float(value[0].item() * 10000)
    return evaluator


def nn_policy_func(model, device):
    """
    返回策略dict: {move: prob}
    """
    def policy(board):
        x = board_encode_planes(board).unsqueeze(0).to(device)
        with torch.no_grad():
            logits, _ = model(x)
        logits = logits[0].cpu()
        mask = legal_moves_mask(board)
        logits[~mask] = -1e9
        pi = F.softmax(logits, dim=0).numpy()
        move_dict = {}
        for idx, p in enumerate(pi):
            if mask[idx]:
                from_sq, to_sq = policy_index_to_move(idx)
                moves = [mv for mv in board.generate_legal_moves()
                        if (mv>>0&0x7f)==from_sq and (mv>>7&0x7f)==to_sq]
                for mv in moves:  # 支持同一起点终点的分步(如二次炮等)
                    move_dict[mv] = p
        return move_dict
    return policy


def pick_best_by_policy(board, model, device):
    """用网络策略头概率采样一个走法。"""
    x = board_encode_planes(board).unsqueeze(0).to(device)
    with torch.no_grad():
        logits, value = model(x)
    logits = logits[0].cpu()
    mask = legal_moves_mask(board)
    logits[~mask] = -1e9
    probs = F.softmax(logits, dim=0).numpy()
    idx = probs.argmax()
    from_sq, to_sq = policy_index_to_move(idx)
    moves = [mv for mv in board.generate_legal_moves()
            if (mv>>0&0x7f)==from_sq and (mv>>7&0x7f)==to_sq]
    chosen = moves[0] if moves else None
    return chosen, value.item()


if __name__ == '__main__':
    # 实例化测试
    dev = torch.device('cpu')
    model = make_simple_resnet(hidden=64)
    board = Board()
    board.set_startpos()
    evaler = nn_eval_func(model, dev)
    policyer = nn_policy_func(model, dev)
    print('AlphaBeta+NN(伪模型)结果：')
    v, mv = alphabeta_search(board, 2, evaler, policyer)
    print('分数:', v, '推荐走法:', mv)
    print('NN最大概率走法:')
    bestmv, val = pick_best_by_policy(board, model, dev)
    print('最佳走法:', bestmv, 'value分:', val)
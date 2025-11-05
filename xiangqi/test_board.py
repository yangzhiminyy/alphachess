from board import Board
from constants import RED, BLACK, PIECE_KNIGHT, PIECE_ROOK, PIECE_PAWN, unpack_move
def print_board(board: Board):
    """Print the board position for quick inspect."""
    symbol = {
        0: ' . ',
        1: '兵', -1: '卒',
        2: '炮', -2: '砲',
        3: '马', -3: '馬',
        4: '相', -4: '象',
        5: '仕', -5: '士',
        6: '车', -6: '車',
        7: '帅', -7: '将',
    }
    for r in range(10):
        line = []
        for c in range(9):
            code = board.squares[r*9 + c]
            line.append(symbol.get(code, f'{code:2d}'))
        print(' '.join(line))
    print('side_to_move:', '红' if board.side_to_move == RED else '黑')


def test_start_moves():
    b = Board()
    b.set_startpos()
    print('开局棋盘：')
    print_board(b)
    moves = b.generate_legal_moves()
    print(f'开局红方可走步数: {len(moves)}')
    assert len(moves) > 0, '开局应有可走步'
    # 展示前10步
    for mv in moves[:10]:
        fr, to, mt, ct, flags = unpack_move(mv)
        print(f'MOVE: {fr}->{to}, type {mt}, cap {ct}')

    # 随便走一步（找第一个马步）
    for mv in moves:
        _, _, mt, _, _ = unpack_move(mv)
        if mt == PIECE_KNIGHT:
            print('Execute one knight move')
            b.make_move(mv)
            print_board(b)
            # 检查黑方未被将军
            assert not b.is_in_check(BLACK)
            b.unmake_move()
            print('After unmake:')
            print_board(b)
            assert not b.is_in_check(RED)
            break

if __name__ == '__main__':
    test_start_moves()

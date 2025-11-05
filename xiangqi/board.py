from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
import random

from constants import (
    RED,
    BLACK,
    PIECE_NONE,
    PIECE_PAWN,
    PIECE_CANNON,
    PIECE_KNIGHT,
    PIECE_BISHOP,
    PIECE_ADVISOR,
    PIECE_ROOK,
    PIECE_KING,
    pack_move,
    unpack_move,
    piece_index_for_zobrist,
    rc_to_sq,
)


@dataclass
class Zobrist:
    table: List[List[int]]  # [90][15], indices 0..14 (0 unused)
    side_key: int

    @staticmethod
    def init(seed: int = 0xC0FFEE) -> "Zobrist":
        rng = random.Random(seed)
        table = [[rng.getrandbits(64) for _ in range(15)] for _ in range(90)]
        side_key = rng.getrandbits(64)
        return Zobrist(table=table, side_key=side_key)


@dataclass
class UndoRecord:
    move: int
    captured_piece: int
    prev_hash: int
    prev_king_pos_red: int
    prev_king_pos_black: int


class Board:
    def __init__(self) -> None:
        self.squares: List[int] = [0] * 90  # signed piece codes: side * type_id
        self.side_to_move: int = RED
        self.king_pos_red: int = -1
        self.king_pos_black: int = -1

        self.piece_list_red: Dict[int, List[int]] = {t: [] for t in range(1, 8)}
        self.piece_list_black: Dict[int, List[int]] = {t: [] for t in range(1, 8)}

        self.hash_history: List[int] = []
        self.zobrist: Zobrist = Zobrist.init()
        self.hash_key: int = 0

        self.undo_stack: List[UndoRecord] = []

    # ---- Setup ----

    def set_startpos(self) -> None:
        self.squares = [0] * 90
        # Black back rank (row 0)
        self._place(0, 0, BLACK * PIECE_ROOK)
        self._place(0, 1, BLACK * PIECE_KNIGHT)
        self._place(0, 2, BLACK * PIECE_BISHOP)
        self._place(0, 3, BLACK * PIECE_ADVISOR)
        self._place(0, 4, BLACK * PIECE_KING)
        self._place(0, 5, BLACK * PIECE_ADVISOR)
        self._place(0, 6, BLACK * PIECE_BISHOP)
        self._place(0, 7, BLACK * PIECE_KNIGHT)
        self._place(0, 8, BLACK * PIECE_ROOK)

        # Black cannons (row 2)
        self._place(2, 1, BLACK * PIECE_CANNON)
        self._place(2, 7, BLACK * PIECE_CANNON)

        # Black pawns (row 3)
        for c in (0, 2, 4, 6, 8):
            self._place(3, c, BLACK * PIECE_PAWN)

        # Red pawns (row 6)
        for c in (0, 2, 4, 6, 8):
            self._place(6, c, RED * PIECE_PAWN)

        # Red cannons (row 7)
        self._place(7, 1, RED * PIECE_CANNON)
        self._place(7, 7, RED * PIECE_CANNON)

        # Red back rank (row 9)
        self._place(9, 0, RED * PIECE_ROOK)
        self._place(9, 1, RED * PIECE_KNIGHT)
        self._place(9, 2, RED * PIECE_BISHOP)
        self._place(9, 3, RED * PIECE_ADVISOR)
        self._place(9, 4, RED * PIECE_KING)
        self._place(9, 5, RED * PIECE_ADVISOR)
        self._place(9, 6, RED * PIECE_BISHOP)
        self._place(9, 7, RED * PIECE_KNIGHT)
        self._place(9, 8, RED * PIECE_ROOK)

        self.side_to_move = RED
        self._rebuild_caches()
        self._recompute_hash()
        self.hash_history = [self.hash_key]

    def _place(self, row: int, col: int, code: int) -> None:
        self.squares[rc_to_sq(row, col)] = code

    def _rebuild_caches(self) -> None:
        for d in (self.piece_list_red, self.piece_list_black):
            for t in d:
                d[t].clear()
        self.king_pos_red = -1
        self.king_pos_black = -1

        for sq, code in enumerate(self.squares):
            if code == 0:
                continue
            side = RED if code > 0 else BLACK
            t = abs(code)
            if side == RED:
                self.piece_list_red[t].append(sq)
                if t == PIECE_KING:
                    self.king_pos_red = sq
            else:
                self.piece_list_black[t].append(sq)
                if t == PIECE_KING:
                    self.king_pos_black = sq

    def _recompute_hash(self) -> None:
        h = 0
        for sq, code in enumerate(self.squares):
            if code == 0:
                continue
            idx = piece_index_for_zobrist(code)
            h ^= self.zobrist.table[sq][idx]
        # Convention: XOR side_key if BLACK to move
        if self.side_to_move == BLACK:
            h ^= self.zobrist.side_key
        self.hash_key = h

    # ---- Move generation ----

    def generate_pseudo_legal_moves(self) -> List[int]:
        moves: List[int] = []
        if self.side_to_move == RED:
            lists = self.piece_list_red
            sign = RED
        else:
            lists = self.piece_list_black
            sign = BLACK

        for sq in lists[PIECE_ROOK]:
            moves.extend(self._gen_rook(sq, sign))
        for sq in lists[PIECE_CANNON]:
            moves.extend(self._gen_cannon(sq, sign))
        for sq in lists[PIECE_KNIGHT]:
            moves.extend(self._gen_knight(sq, sign))
        for sq in lists[PIECE_BISHOP]:
            moves.extend(self._gen_bishop(sq, sign))
        for sq in lists[PIECE_ADVISOR]:
            moves.extend(self._gen_advisor(sq, sign))
        king_list = lists[PIECE_KING]
        if king_list:
            moves.extend(self._gen_king(king_list[0], sign))
        for sq in lists[PIECE_PAWN]:
            moves.extend(self._gen_pawn(sq, sign))
        return moves

    def _push_move(self, from_sq: int, to_sq: int) -> int | None:
        moving_code = self.squares[from_sq]
        captured_code = self.squares[to_sq]
        if captured_code != 0 and (captured_code > 0) == (moving_code > 0):
            return None
        mv = pack_move(
            from_sq,
            to_sq,
            abs(moving_code),
            abs(captured_code) if captured_code != 0 else 0,
            0,
        )
        return mv

    def _gen_rook(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        # Up
        for rr in range(r - 1, -1, -1):
            to = rr * 9 + c
            if self.squares[to] == 0:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
            else:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
                break
        # Down
        for rr in range(r + 1, 10):
            to = rr * 9 + c
            if self.squares[to] == 0:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
            else:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
                break
        # Left
        for cc in range(c - 1, -1, -1):
            to = r * 9 + cc
            if self.squares[to] == 0:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
            else:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
                break
        # Right
        for cc in range(c + 1, 9):
            to = r * 9 + cc
            if self.squares[to] == 0:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
            else:
                mv = self._push_move(sq, to)
                if mv is not None:
                    res.append(mv)
                break
        return res

    def _gen_cannon(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        # Up
        screen = False
        for rr in range(r - 1, -1, -1):
            to = rr * 9 + c
            if not screen:
                if self.squares[to] == 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                else:
                    screen = True
            else:
                if self.squares[to] != 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                    break
        # Down
        screen = False
        for rr in range(r + 1, 10):
            to = rr * 9 + c
            if not screen:
                if self.squares[to] == 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                else:
                    screen = True
            else:
                if self.squares[to] != 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                    break
        # Left
        screen = False
        for cc in range(c - 1, -1, -1):
            to = r * 9 + cc
            if not screen:
                if self.squares[to] == 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                else:
                    screen = True
            else:
                if self.squares[to] != 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                    break
        # Right
        screen = False
        for cc in range(c + 1, 9):
            to = r * 9 + cc
            if not screen:
                if self.squares[to] == 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                else:
                    screen = True
            else:
                if self.squares[to] != 0:
                    mv = self._push_move(sq, to)
                    if mv is not None:
                        res.append(mv)
                    break
        return res

    def _gen_knight(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        deltas = [
            (-2, -1, -1, 0), (-2, 1, -1, 0),
            (2, -1, 1, 0), (2, 1, 1, 0),
            (-1, -2, 0, -1), (1, -2, 0, -1),
            (-1, 2, 0, 1), (1, 2, 0, 1),
        ]
        for dr, dc, lr, lc in deltas:
            leg_r = r + lr
            leg_c = c + lc
            to_r = r + dr
            to_c = c + dc
            if 0 <= leg_r < 10 and 0 <= leg_c < 9 and 0 <= to_r < 10 and 0 <= to_c < 9:
                if self.squares[leg_r * 9 + leg_c] != 0:
                    continue
                to_sq = to_r * 9 + to_c
                mv = self._push_move(sq, to_sq)
                if mv is not None:
                    res.append(mv)
        return res

    def _gen_bishop(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        deltas = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
        for dr, dc in deltas:
            to_r = r + dr
            to_c = c + dc
            if not (0 <= to_r < 10 and 0 <= to_c < 9):
                continue
            # river restriction
            if sign == RED and to_r < 5:
                continue
            if sign == BLACK and to_r > 4:
                continue
            eye_r = r + dr // 2
            eye_c = c + dc // 2
            if self.squares[eye_r * 9 + eye_c] != 0:
                continue
            to_sq = to_r * 9 + to_c
            mv = self._push_move(sq, to_sq)
            if mv is not None:
                res.append(mv)
        return res

    def _gen_advisor(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        deltas = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dr, dc in deltas:
            to_r = r + dr
            to_c = c + dc
            if not (0 <= to_r < 10 and 0 <= to_c < 9):
                continue
            if sign == RED:
                if not (7 <= to_r <= 9 and 3 <= to_c <= 5):
                    continue
            else:
                if not (0 <= to_r <= 2 and 3 <= to_c <= 5):
                    continue
            to_sq = to_r * 9 + to_c
            mv = self._push_move(sq, to_sq)
            if mv is not None:
                res.append(mv)
        return res

    def _gen_king(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in deltas:
            to_r = r + dr
            to_c = c + dc
            if not (0 <= to_r < 10 and 0 <= to_c < 9):
                continue
            if sign == RED:
                if not (7 <= to_r <= 9 and 3 <= to_c <= 5):
                    continue
            else:
                if not (0 <= to_r <= 2 and 3 <= to_c <= 5):
                    continue
            to_sq = to_r * 9 + to_c
            mv = self._push_move(sq, to_sq)
            if mv is not None:
                res.append(mv)
        return res

    def _gen_pawn(self, sq: int, sign: int) -> List[int]:
        res: List[int] = []
        r, c = divmod(sq, 9)
        # forward
        to_r = r - 1 if sign == BLACK else r + 1
        if 0 <= to_r < 10:
            to_sq = to_r * 9 + c
            mv = self._push_move(sq, to_sq)
            if mv is not None:
                res.append(mv)
        # sideways after crossing river
        crossed = (sign == RED and r <= 4) or (sign == BLACK and r >= 5)
        if crossed:
            for dc in (-1, 1):
                to_c = c + dc
                if 0 <= to_c < 9:
                    to_sq = r * 9 + to_c
                    mv = self._push_move(sq, to_sq)
                    if mv is not None:
                        res.append(mv)
        return res

    def is_in_check(self, side: int) -> bool:
        """Return whether side is in check considering enemy attacks and face-to-face."""
        # Find corresponding king
        king_sq = self.king_pos_red if side == RED else self.king_pos_black
        if king_sq == -1:
            return False
        # 1. Normal attack?
        opp_side = -side
        # 2. 检查所有对方攻击是否覆盖王
        if self._is_attacked(king_sq, opp_side):
            return True
        # 3. 检查将帅是否照面
        r_king, c_king = divmod(king_sq, 9)
        # 向上或向下有无对方 king 并且之间是否无阻
        # Find opposing king (只可能在同一列)
        if side == RED:
            opp_ksq = self.king_pos_black
        else:
            opp_ksq = self.king_pos_red
        if opp_ksq != -1:
            r_other, c_other = divmod(opp_ksq, 9)
            if c_other == c_king:
                # 检查之间有无阻碍
                step = 1 if r_other > r_king else -1
                for rr in range(r_king + step, r_other, step):
                    if self.squares[rr * 9 + c_king] != 0:
                        break
                else:
                    # 照面
                    return True
        return False

    def _is_attacked(self, target_sq: int, attacker_side: int) -> bool:
        """Does attacker_side control/attack the target_sq? Used for king check detection."""
        r, c = divmod(target_sq, 9)
        enemy_lists = self.piece_list_red if attacker_side == RED else self.piece_list_black
        # 1. Pawn attack (取决于方向，红兵+1行，黑兵-1行; 过河后左右也可)
        delta = 1 if attacker_side == RED else -1
        pawn_attacks = [ (r + delta, c) ]
        # 过河兵/卒横打
        if (attacker_side == RED and r >=5) or (attacker_side == BLACK and r <=4):
            for dc in [-1, 1]:
                pawn_attacks.append((r, c + dc))
        for sq in enemy_lists[PIECE_PAWN]:
            pr, pc = divmod(sq, 9)
            if (pr, pc) in pawn_attacks:
                return True
        # 2. Knight attack
        #  "八个方向" + 跳腿不堵
        knight_dir = [
            (-2, -1, -1, 0), (-2, 1, -1, 0),
            (2, -1, 1, 0), (2, 1, 1, 0),
            (-1, -2, 0, -1), (1, -2, 0, -1),
            (-1, 2, 0, 1), (1, 2, 0, 1),
        ]
        for sq in enemy_lists[PIECE_KNIGHT]:
            nr, nc = divmod(sq, 9)
            for dr, dc, lr, lc in knight_dir:
                if (nr + dr, nc + dc) == (r, c):
                    leg_r = nr + lr
                    leg_c = nc + lc
                    if 0 <= leg_r < 10 and 0 <= leg_c < 9:
                        if self.squares[leg_r * 9 + leg_c] == 0:
                            return True
        # 3. Rook & King attack: 直线，王只在宫内参与
        for sq in enemy_lists[PIECE_ROOK] + enemy_lists[PIECE_KING]:
            sr, sc = divmod(sq, 9)
            if sr == r:
                step = 1 if sc < c else -1
                for cc in range(sc + step, c, step):
                    if self.squares[r * 9 + cc] != 0:
                        break
                else:
                    return True
            if sc == c:
                step = 1 if sr < r else -1
                for rr in range(sr + step, r, step):
                    if self.squares[rr * 9 + c] != 0:
                        break
                else:
                    return True
        # 4. Cannon attack
        for sq in enemy_lists[PIECE_CANNON]:
            sr, sc = divmod(sq, 9)
            if sr == r:
                screen = 0
                step = 1 if sc < c else -1
                for cc in range(sc + step, c, step):
                    if self.squares[r * 9 + cc] != 0:
                        screen += 1
                if screen == 1:
                    return True
            if sc == c:
                screen = 0
                step = 1 if sr < r else -1
                for rr in range(sr + step, r, step):
                    if self.squares[rr * 9 + c] != 0:
                        screen += 1
                if screen == 1:
                    return True
        # 5. Bishop attack: 象(相)的攻击也要眼位不堵
        elephant_moves = [(-2, -2), (-2, 2), (2, -2), (2, 2)]
        for sq in enemy_lists[PIECE_BISHOP]:
            sr, sc = divmod(sq, 9)
            for dr, dc in elephant_moves:
                if (sr + dr, sc + dc) == (r, c):
                    eye_r = sr + dr // 2
                    eye_c = sc + dc // 2
                    # 象眼不堵
                    if 0 <= eye_r < 10 and 0 <= eye_c < 9:
                        if self.squares[eye_r * 9 + eye_c] == 0:
                            # 象不越界（不越河）
                            if (attacker_side == RED and r >= 5) or (attacker_side == BLACK and r <= 4):
                                return True
        # 6. Advisor attack: 只在宫
        advisor_moves = [(-1,-1),(-1,1),(1,-1),(1,1)]
        for sq in enemy_lists[PIECE_ADVISOR]:
            sr, sc = divmod(sq, 9)
            for dr, dc in advisor_moves:
                if (sr + dr, sc + dc) == (r, c):
                    # 是否都在宫由走法后遗验证
                    return True
        return False

    def generate_legal_moves(self) -> List[int]:
        legal: List[int] = []
        for mv in self.generate_pseudo_legal_moves():
            self.make_move(mv)
            # After making, side_to_move already flipped; the side we just moved is -side_to_move
            if not self.is_in_check(-self.side_to_move):
                legal.append(mv)
            self.unmake_move()
        return legal

    # ---- Make/Unmake with incremental caches and Zobrist updates ----

    def make_move(self, move: int) -> None:
        from_sq, to_sq, moving_type, captured_type, flags = unpack_move(move)
        moving_code = self.squares[from_sq]
        captured_code = self.squares[to_sq]

        undo = UndoRecord(
            move=move,
            captured_piece=captured_code,
            prev_hash=self.hash_key,
            prev_king_pos_red=self.king_pos_red,
            prev_king_pos_black=self.king_pos_black,
        )
        self.undo_stack.append(undo)

        # Remove captured from piece lists
        if captured_code != 0:
            cap_side = RED if captured_code > 0 else BLACK
            cap_type = abs(captured_code)
            lst = self.piece_list_red if cap_side == RED else self.piece_list_black
            try:
                lst[cap_type].remove(to_sq)
            except ValueError:
                pass

        # Move piece on board
        self.squares[to_sq] = moving_code
        self.squares[from_sq] = 0

        # Update piece lists for moving piece
        side = RED if moving_code > 0 else BLACK
        t = abs(moving_code)
        lst = self.piece_list_red if side == RED else self.piece_list_black
        try:
            lst[t].remove(from_sq)
        except ValueError:
            pass
        lst[t].append(to_sq)

        # Update king positions
        if t == PIECE_KING:
            if side == RED:
                self.king_pos_red = to_sq
            else:
                self.king_pos_black = to_sq

        # Update hash: XOR out moving piece at from, XOR in at to, XOR out captured at to, flip side
        self._update_hash_on_move(from_sq, to_sq, moving_code, captured_code)

        # Flip side
        self.side_to_move = -self.side_to_move
        self.hash_history.append(self.hash_key)

    def unmake_move(self) -> None:
        undo = self.undo_stack.pop()
        from_sq, to_sq, moving_type, captured_type, flags = unpack_move(undo.move)
        moving_code = self.squares[to_sq]

        # Flip side back first to maintain consistency with hashing convention
        self.side_to_move = -self.side_to_move

        # Restore board
        self.squares[from_sq] = moving_code
        self.squares[to_sq] = undo.captured_piece

        # Restore piece lists
        side = RED if moving_code > 0 else BLACK
        t = abs(moving_code)
        lst = self.piece_list_red if side == RED else self.piece_list_black
        try:
            lst[t].remove(to_sq)
        except ValueError:
            pass
        lst[t].append(from_sq)

        if undo.captured_piece != 0:
            cap_side = RED if undo.captured_piece > 0 else BLACK
            cap_type = abs(undo.captured_piece)
            lst_cap = self.piece_list_red if cap_side == RED else self.piece_list_black
            lst_cap[cap_type].append(to_sq)

        # Restore kings
        self.king_pos_red = undo.prev_king_pos_red
        self.king_pos_black = undo.prev_king_pos_black

        # Restore hash
        self.hash_key = undo.prev_hash
        if self.hash_history:
            self.hash_history.pop()

    def _update_hash_on_move(self, from_sq: int, to_sq: int, moving_code: int, captured_code: int) -> None:
        # Remove moving piece from from_sq
        idx_move = piece_index_for_zobrist(moving_code)
        self.hash_key ^= self.zobrist.table[from_sq][idx_move]
        # If capture, remove captured at to_sq
        if captured_code != 0:
            idx_cap = piece_index_for_zobrist(captured_code)
            self.hash_key ^= self.zobrist.table[to_sq][idx_cap]
        # Add moving piece at to_sq
        self.hash_key ^= self.zobrist.table[to_sq][idx_move]
        # Flip side
        self.hash_key ^= self.zobrist.side_key

    def repetition_count(self, zkey=None) -> int:
        """统计指定哈希值在历史中的出现次数，如果不传则统计当前局面。"""
        if zkey is None:
            zkey = self.hash_key
        return sum(1 for h in self.hash_history if h == zkey)

    def can_claim_draw(self) -> bool:
        """简单三次重复判和判定。如果当前局面出现了3次（含现步），可判和。"""
        return self.repetition_count() >= 3

    @property
    def move_history(self):
        """返回已执行的着法序列（栈顶为最近一步）。"""
        return [rec.move for rec in self.undo_stack]



#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
竞技场/ELO 评测脚本
用于比较不同模型或策略的强度
"""

import argparse
import json
import math
import os
import sys
from datetime import datetime
from typing import List, Tuple, Dict, Callable, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xq import GameState, constants as C
from xq.policy import legal_move_mask


def play_game(
    policy_func_red: Callable,
    policy_func_black: Callable,
    max_moves: int = 200,
    verbose: bool = False
) -> Tuple[int, List[Dict]]:
    """
    两个策略对战一局
    
    Args:
        policy_func_red: 红方策略函数 (state) -> move_index
        policy_func_black: 黑方策略函数 (state) -> move_index
        max_moves: 最大回合数
        verbose: 是否打印详细信息
        
    Returns:
        (result, move_history)
        result: 1=红胜, 0=和, -1=黑胜
        move_history: 走法历史列表
    """
    state = GameState()
    state.setup_starting_position()
    
    move_history = []
    move_count = 0
    
    while move_count < max_moves:
        # 检查游戏是否结束
        result = state.adjudicate_result()
        if result is not None:
            if result == "red_win":
                return 1, move_history
            elif result == "black_win":
                return -1, move_history
            else:
                return 0, move_history
        
        # 选择策略函数
        policy_func = policy_func_red if state.side_to_move == C.RED else policy_func_black
        
        # 获取合法走法
        legal_moves = state.generate_legal_moves()
        if not legal_moves:
            # 无合法走法，判负
            return -1 if state.side_to_move == C.RED else 1, move_history
        
        # 执行策略
        try:
            move = policy_func(state)
            if move is None or move not in legal_moves:
                if verbose:
                    print(f"Invalid move from {state.side_to_move}, using first legal move")
                move = legal_moves[0]
        except Exception as e:
            if verbose:
                print(f"Error from policy: {e}, using first legal move")
            move = legal_moves[0]
        
        # 记录走法
        move_history.append({
            'move_count': move_count,
            'side': state.side_to_move,
            'from_sq': move.from_sq,
            'to_sq': move.to_sq,
            'move_id': int(move)
        })
        
        # 应用走法
        state.apply_move(move)
        move_count += 1
    
    # 达到最大回合数，判和
    return 0, move_history


def calculate_elo(scores: List[float], n_games: int) -> Tuple[float, float]:
    """
    从得分序列计算 ELO 分差和胜率
    
    Args:
        scores: 得分列表 (1.0=胜, 0.5=和, 0.0=负)
        n_games: 总局数
        
    Returns:
        (elo_diff, win_rate)
    """
    if n_games == 0:
        return 0.0, 0.5
    
    mean_score = sum(scores) / n_games
    # 限制在 (0.01, 0.99) 避免 log10(0)
    mean_score = max(min(mean_score, 0.99), 0.01)
    
    # ELO 公式: P = 1/(1+10^(-dr/400))
    # 反推: dr = -400 * log10(1/P - 1)
    elo_diff = -400 * math.log10(1/mean_score - 1)
    
    return elo_diff, mean_score


def arena(
    engine_a: str,
    engine_b: str,
    model_a: Optional[str] = None,
    model_b: Optional[str] = None,
    params_a: Optional[Dict] = None,
    params_b: Optional[Dict] = None,
    n_games: int = 20,
    verbose: bool = False
) -> Dict:
    """
    进行竞技场对战
    
    Args:
        engine_a: 引擎 A 类型 ('random', 'mcts', 'mcts_nn', 'alphabeta')
        engine_b: 引擎 B 类型
        model_a: 模型 A 路径 (如果使用 mcts_nn)
        model_b: 模型 B 路径 (如果使用 mcts_nn)
        params_a: 引擎 A 参数
        params_b: 引擎 B 参数
        n_games: 总对战局数
        verbose: 是否打印详细信息
        
    Returns:
        结果字典
    """
    # 创建策略函数
    policy_a = create_policy_func(engine_a, model_a, params_a or {})
    policy_b = create_policy_func(engine_b, model_b, params_b or {})
    
    scores_a = []
    game_results = []
    
    # 前 n_games/2 局: A 执红, B 执黑
    for i in range(n_games // 2):
        if verbose:
            print(f"Game {i+1}/{n_games}: A(RED) vs B(BLACK)...", end=" ", flush=True)
        
        result, moves = play_game(policy_a, policy_b, max_moves=200, verbose=False)
        
        if result == 1:  # 红胜 (A 胜)
            scores_a.append(1.0)
            outcome = "A wins"
        elif result == -1:  # 黑胜 (B 胜)
            scores_a.append(0.0)
            outcome = "B wins"
        else:  # 和
            scores_a.append(0.5)
            outcome = "Draw"
        
        game_results.append({
            'game_number': i + 1,
            'red': 'A',
            'black': 'B',
            'result': result,
            'outcome': outcome,
            'moves': len(moves)
        })
        
        if verbose:
            print(f"{outcome} ({len(moves)} moves)")
    
    # 后 n_games/2 局: B 执红, A 执黑 (换色)
    for i in range(n_games // 2, n_games):
        if verbose:
            print(f"Game {i+1}/{n_games}: B(RED) vs A(BLACK)...", end=" ", flush=True)
        
        result, moves = play_game(policy_b, policy_a, max_moves=200, verbose=False)
        
        if result == 1:  # 红胜 (B 胜)
            scores_a.append(0.0)
            outcome = "B wins"
        elif result == -1:  # 黑胜 (A 胜)
            scores_a.append(1.0)
            outcome = "A wins"
        else:  # 和
            scores_a.append(0.5)
            outcome = "Draw"
        
        game_results.append({
            'game_number': i + 1,
            'red': 'B',
            'black': 'A',
            'result': result,
            'outcome': outcome,
            'moves': len(moves)
        })
        
        if verbose:
            print(f"{outcome} ({len(moves)} moves)")
    
    # 计算统计数据
    elo_diff, win_rate = calculate_elo(scores_a, n_games)
    
    wins = sum(1 for s in scores_a if s == 1.0)
    draws = sum(1 for s in scores_a if s == 0.5)
    losses = sum(1 for s in scores_a if s == 0.0)
    
    return {
        'engine_a': engine_a,
        'engine_b': engine_b,
        'model_a': model_a,
        'model_b': model_b,
        'n_games': n_games,
        'elo_diff': elo_diff,  # A 相对于 B 的 ELO 分差
        'win_rate': win_rate,  # A 的胜率
        'wins': wins,
        'draws': draws,
        'losses': losses,
        'scores': scores_a,
        'games': game_results,
        'timestamp': datetime.now().isoformat()
    }


def create_policy_func(engine: str, model_path: Optional[str], params: Dict) -> Callable:
    """
    创建策略函数
    
    Args:
        engine: 引擎类型
        model_path: 模型路径
        params: 引擎参数
        
    Returns:
        策略函数 (state) -> move
    """
    if engine == 'random':
        import random
        def policy(state):
            moves = state.generate_legal_moves()
            return random.choice(moves) if moves else None
        return policy
    
    elif engine == 'alphabeta':
        from xq.search.alpha_beta import alphabeta_search, TranspositionTable
        depth = params.get('depth', 3)
        tt = TranspositionTable(size_mb=256)
        
        def policy(state):
            _, best_move = alphabeta_search(state, depth=depth, tt=tt)
            return best_move
        return policy
    
    elif engine == 'mcts':
        from xq.mcts import MCTS
        from xq.policy import legal_move_mask
        sims = params.get('sims', 200)
        
        def simple_policy_fn(s):
            mask = legal_move_mask(s)
            legal_count = sum(1 for x in mask if x > 0)
            p = [0.0] * (C.NUM_SQUARES * C.NUM_SQUARES)
            if legal_count > 0:
                w = 1.0 / legal_count
                for i, v in enumerate(mask):
                    if v > 0:
                        p[i] = w
            # Simple material eval
            score = sum(C.MATERIAL_VALUES.get(abs(pc), 0) * (1 if pc > 0 else -1) 
                       for pc in s.board if pc != 0)
            pov = score if s.side_to_move == C.RED else -score
            val = math.tanh(pov / 2000.0)
            return p, float(val)
        
        mcts = MCTS()
        
        def policy(state):
            root = mcts.run(state, simple_policy_fn, num_simulations=sims)
            probs = mcts.action_probs(root, tau=0.1)  # Low temperature for best move
            if probs:
                best_idx = max(probs.items(), key=lambda kv: kv[1])[0]
                from_sq = best_idx // C.NUM_SQUARES
                to_sq = best_idx % C.NUM_SQUARES
                for mv in state.generate_legal_moves():
                    if mv.from_sq == from_sq and mv.to_sq == to_sq:
                        return mv
            return None
        return policy
    
    elif engine == 'mcts_nn':
        import torch
        from xq.mcts import MCTS
        from xq.policy import legal_move_mask
        
        # Load model
        if model_path and os.path.exists(model_path):
            try:
                # Try to load with auto-detection
                state_dict = torch.load(model_path, map_location='cpu')
                has_bn = any('bn' in k for k in state_dict.keys())
                
                if has_bn:
                    from alphazero.network import create_xiangqi_net
                    model = create_xiangqi_net()
                else:
                    from xq.nn import XQNet
                    model = XQNet()
                
                model.load_state_dict(state_dict)
                model.eval()
                
                from xq.nn import state_to_tensor
                
                def nn_policy_fn(s):
                    with torch.no_grad():
                        x = state_to_tensor(s).unsqueeze(0)
                        logits, v = model(x)
                        policy = torch.softmax(logits[0], dim=-1).tolist()
                        return policy, float(v.item())
                
                sims = params.get('sims', 200)
                mcts = MCTS()
                
                def policy(state):
                    root = mcts.run(state, nn_policy_fn, num_simulations=sims)
                    probs = mcts.action_probs(root, tau=0.1)
                    if probs:
                        best_idx = max(probs.items(), key=lambda kv: kv[1])[0]
                        from_sq = best_idx // C.NUM_SQUARES
                        to_sq = best_idx % C.NUM_SQUARES
                        for mv in state.generate_legal_moves():
                            if mv.from_sq == from_sq and mv.to_sq == to_sq:
                                return mv
                    return None
                return policy
            except Exception as e:
                print(f"Failed to load model {model_path}: {e}")
                print("Falling back to random policy")
                import random
                def policy(state):
                    moves = state.generate_legal_moves()
                    return random.choice(moves) if moves else None
                return policy
        else:
            print(f"Model not found: {model_path}, using random policy")
            import random
            def policy(state):
                moves = state.generate_legal_moves()
                return random.choice(moves) if moves else None
            return policy
    
    else:
        raise ValueError(f"Unknown engine type: {engine}")


def main():
    parser = argparse.ArgumentParser(description="Arena/ELO evaluation for Xiangqi")
    parser.add_argument("--engine-a", default="random", 
                       choices=["random", "alphabeta", "mcts", "mcts_nn"],
                       help="Engine type for player A")
    parser.add_argument("--engine-b", default="random",
                       choices=["random", "alphabeta", "mcts", "mcts_nn"],
                       help="Engine type for player B")
    parser.add_argument("--model-a", type=str, default=None,
                       help="Model path for player A (if using mcts_nn)")
    parser.add_argument("--model-b", type=str, default=None,
                       help="Model path for player B (if using mcts_nn)")
    parser.add_argument("--depth-a", type=int, default=3,
                       help="Search depth for player A (if using alphabeta)")
    parser.add_argument("--depth-b", type=int, default=3,
                       help="Search depth for player B (if using alphabeta)")
    parser.add_argument("--sims-a", type=int, default=200,
                       help="MCTS simulations for player A (if using mcts)")
    parser.add_argument("--sims-b", type=int, default=200,
                       help="MCTS simulations for player B (if using mcts)")
    parser.add_argument("--games", type=int, default=20,
                       help="Number of games to play (half with each color)")
    parser.add_argument("--output", type=str, default=None,
                       help="Output JSON file for results")
    parser.add_argument("--verbose", action="store_true",
                       help="Print detailed progress")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Arena/ELO Evaluation")
    print("=" * 60)
    print(f"Player A: {args.engine_a}")
    if args.model_a:
        print(f"  Model: {args.model_a}")
    print(f"Player B: {args.engine_b}")
    if args.model_b:
        print(f"  Model: {args.model_b}")
    print(f"Games: {args.games} (each color: {args.games//2})")
    print("=" * 60)
    
    # Prepare parameters
    params_a = {
        'depth': args.depth_a,
        'sims': args.sims_a
    }
    params_b = {
        'depth': args.depth_b,
        'sims': args.sims_b
    }
    
    # Run arena
    results = arena(
        engine_a=args.engine_a,
        engine_b=args.engine_b,
        model_a=args.model_a,
        model_b=args.model_b,
        params_a=params_a,
        params_b=params_b,
        n_games=args.games,
        verbose=args.verbose
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("Results")
    print("=" * 60)
    print(f"Player A: {args.engine_a}")
    print(f"  Wins: {results['wins']}")
    print(f"  Draws: {results['draws']}")
    print(f"  Losses: {results['losses']}")
    print(f"  Win Rate: {results['win_rate']*100:.2f}%")
    print(f"  ELO Difference: {results['elo_diff']:+.1f} (A - B)")
    print("=" * 60)
    
    if results['elo_diff'] > 0:
        print(f"[OK] Player A is stronger by ~{results['elo_diff']:.0f} ELO points")
    elif results['elo_diff'] < 0:
        print(f"[OK] Player B is stronger by ~{-results['elo_diff']:.0f} ELO points")
    else:
        print("[OK] Players are roughly equal in strength")
    
    # Save results
    if args.output:
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()


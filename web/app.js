const { useState, useEffect, useMemo } = React;

const FILES = 9;
const RANKS = 10;
const CELL = 56; // px
const GAP = 2;   // px (grid gap)

function centerX(col){ return col * (CELL + GAP) + CELL / 2; }
function centerY(row){ return row * (CELL + GAP) + CELL / 2; }

function BoardGridSVG(){
	const width = FILES * CELL + (FILES - 1) * GAP;
	const height = RANKS * CELL + (RANKS - 1) * GAP;
	const lines = [];
	// Horizontal lines across all rows
	for (let r = 0; r < RANKS; r++){
		const y = centerY(r);
		lines.push(React.createElement('line', { key:`h-${r}`, x1: centerX(0), y1: y, x2: centerX(FILES-1), y2: y, stroke: '#6b4f1d', strokeWidth: 2 }));
	}
	// Vertical lines; inner files have river gap between rows 4 and 5
	for (let c = 0; c < FILES; c++){
		const x = centerX(c);
		if (c === 0 || c === FILES-1){
			lines.push(React.createElement('line', { key:`v-${c}-full`, x1: x, y1: centerY(0), x2: x, y2: centerY(RANKS-1), stroke: '#6b4f1d', strokeWidth: 2 }));
		}else{
			lines.push(React.createElement('line', { key:`v-${c}-top`, x1: x, y1: centerY(0), x2: x, y2: centerY(4), stroke: '#6b4f1d', strokeWidth: 2 }));
			lines.push(React.createElement('line', { key:`v-${c}-bot`, x1: x, y1: centerY(5), x2: x, y2: centerY(RANKS-1), stroke: '#6b4f1d', strokeWidth: 2 }));
		}
	}
	// Palace diagonals
	const diag = (x1,y1,x2,y2,key)=> React.createElement('line', { key, x1, y1, x2, y2, stroke:'#6b4f1d', strokeWidth:2 });
	// Top palace (files 3..5, ranks 0..2)
	lines.push(diag(centerX(3),centerY(0), centerX(5),centerY(2),'pd1'));
	lines.push(diag(centerX(5),centerY(0), centerX(3),centerY(2),'pd2'));
	// Bottom palace (files 3..5, ranks 7..9)
	lines.push(diag(centerX(3),centerY(7), centerX(5),centerY(9),'pd3'));
	lines.push(diag(centerX(5),centerY(7), centerX(3),centerY(9),'pd4'));

	const riverY = (centerY(4) + centerY(5)) / 2;
	return (
		<svg className="gridsvg" width={width} height={height}>
			{lines}
			<text x={centerX(2)} y={riverY+6} textAnchor="middle" fill="#7c4a12" fontWeight="700" opacity="0.6">楚河</text>
			<text x={centerX(6)} y={riverY+6} textAnchor="middle" fill="#7c4a12" fontWeight="700" opacity="0.6">汉界</text>
		</svg>
	);
}

const PIECE_MAP = {
	1: { red: '兵', black: '卒' },
	2: { red: '炮', black: '炮' },
	3: { red: '马', black: '马' },
	4: { red: '相', black: '象' },
	5: { red: '仕', black: '士' },
	6: { red: '车', black: '车' },
	7: { red: '帅', black: '将' },
};

function pieceNameCN(piece){
	if(!piece)return '';
	const pt = Math.abs(piece);
	return PIECE_MAP[pt][piece>0?'red':'black']||'?';
}

function fileOf(i){ return i % FILES; }
function rankOf(i){ return Math.floor(i / FILES); }

function _sq_to_coord(sq){
	const f = fileOf(sq);
	const r = rankOf(sq);
	return String.fromCharCode(97 + f) + r;
}

function Square({ idx, piece, selected, legal, onClick }){
	const cls = ['sq'];
	// Xiangqi board uses intersections; keep uniform background
	if (selected) cls.push('selected');
	if (legal) cls.push('legal');
	const content = useMemo(() => {
		if (!piece) return '';
		const color = piece > 0 ? 'red' : 'black';
		const pt = Math.abs(piece);
		const sym = (PIECE_MAP[pt] || {})[color] || '?';
		return React.createElement('span', { className: `piece ${color}` }, sym);
	}, [piece]);
	return React.createElement('div', { className: cls.join(' '), onClick }, content);
}

function App(){
	const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000');
	const [game, setGame] = useState(null);
	const [gameId, setGameId] = useState(null);
	const [selected, setSelected] = useState(null);
	const [legalFrom, setLegalFrom] = useState([]);
	const [engine, setEngine] = useState('ab');
	const [depth, setDepth] = useState(3);
	const [sims, setSims] = useState(100);
	const [tau, setTau] = useState(1.0);
	const [log, setLog] = useState([]);
	const [flipped, setFlipped] = useState(false);
	const [aiThinking, setAiThinking] = useState(false);

	async function api(path, opts){
		const res = await fetch(`${baseUrl}${path}`, opts);
		if (!res.ok) throw new Error(await res.text());
		return res.json();
	}

	async function newGame(){
		const data = await api('/api/games', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
		setGameId(data.game_id);
		setGame(data);
		setSelected(null);
		setLegalFrom([]);
		setLog(l => [{ t: 'sys', msg: '新建对局' }, ...l]);
	}

	async function refresh(){
		if (!gameId) return;
		const data = await api(`/api/games/${gameId}`);
		setGame(data);
	}

	function movesFrom(idx){
		if (!game) return [];
		return (game.legal_moves || []).filter(m => m.from === idx);
	}

	async function onSquareClick(idx){
		if (!game) return;
		if (selected == null){
			setSelected(idx);
			setLegalFrom(movesFrom(idx).map(m => m.to));
			return;
		}
		if (selected === idx){
			setSelected(null);
			setLegalFrom([]);
			return;
		}
		const cand = movesFrom(selected).find(m => m.to === idx);
		if (!cand){
			setSelected(idx);
			setLegalFrom(movesFrom(idx).map(m => m.to));
			return;
		}
		// Step 1: Play human move and update board immediately
		const movedPiece = board[selected];
		const capturedPiece = board[idx];
		const fromCoord = _sq_to_coord(selected);
		const toCoord = _sq_to_coord(idx);
		const humanMove = { from_sq: selected, to_sq: idx };
		
		// Apply human move via API
		const humanData = await api(`/api/games/${gameId}/move`, { 
			method: 'POST', 
			headers: { 'Content-Type': 'application/json' }, 
			body: JSON.stringify(humanMove) 
		});
		const humanDesc = `${pieceNameCN(movedPiece)} ${fromCoord}→${toCoord}${capturedPiece?' (吃'+pieceNameCN(capturedPiece)+')':''}`;
		
		// Update board with human move
		setGame(humanData);
		setSelected(null);
		setLegalFrom([]);
		setLog(l => [{t:'you',msg:`你: ${humanDesc}`}, ...l]);
		
		// Small delay so user sees their move
		await new Promise(r=>setTimeout(r,200));
		
		// Check if game ended after human move
		if(humanData.result){
			setLog(l => [{t:'sys',msg:`对局结束: ${humanData.result === 'red_win' ? '红胜' : humanData.result === 'black_win' ? '黑胜' : '和棋'}`}, ...l]);
			return;
		}
		
		// Step 2: Request AI move
		setAiThinking(true);
		const aiResult = await api(`/api/games/${gameId}/best-move?engine=${engine}&depth=${depth}&sims=${sims}&tau=${tau}`);
		
		if(aiResult.best){
			// Apply AI move
			const aiFromSq = aiResult.best.from;
			const aiToSq = aiResult.best.to;
			const aiMovedPiece = humanData.squares[aiFromSq];
			const aiCaptured = humanData.squares[aiToSq];
			const aiFromCoord = _sq_to_coord(aiFromSq);
			const aiToCoord = _sq_to_coord(aiToSq);
			
			const aiMove = { move_id: aiResult.best.move_id };
			const aiData = await api(`/api/games/${gameId}/move`, { 
				method: 'POST', 
				headers: { 'Content-Type': 'application/json' }, 
				body: JSON.stringify(aiMove) 
			});
			
			const aiDesc = `${pieceNameCN(aiMovedPiece)} ${aiFromCoord}→${aiToCoord}${aiCaptured?' (吃'+pieceNameCN(aiCaptured)+')':''}`;
			
			// Brief delay before showing AI move
			await new Promise(r=>setTimeout(r,400));
			setGame(aiData);
			setLog(l => [{t:'ai',msg:`AI: ${aiDesc}`}, ...l]);
			
			// Check if game ended after AI move
			if(aiData.result){
				setLog(l => [{t:'sys',msg:`对局结束: ${aiData.result === 'red_win' ? '红胜' : aiData.result === 'black_win' ? '黑胜' : '和棋'}`}, ...l]);
			}
		}
		setAiThinking(false);
	}

	async function undo(){
		if (!gameId) return;
		try {
			const data = await api(`/api/games/${gameId}/undo`, { method: 'POST' });
			setGame(data);
			setSelected(null);
			setLegalFrom([]);
		} catch(err) {
			// Already at initial position
			setLog(l => [{t:'sys',msg:'已到初始局面，无法继续悔棋'}, ...l]);
		}
	}

	const board = game ? game.squares : Array(90).fill(0);
	// Display order: flip vertically so RED is at bottom (or black if flipped)
	const displayOrder = useMemo(() => {
		const order = [];
		for(let dr=0; dr<RANKS; dr++){
			for(let df=0; df<FILES; df++){
				const br = flipped ? dr : (RANKS - 1) - dr;
				const bf = df;
				order.push(br * FILES + bf);
			}
		}
		return order;
	}, [flipped]);

	return (
		<div className="app">
			<div className="toolbar">
				<input style={{width: 240}} value={baseUrl} onChange={e=>setBaseUrl(e.target.value)} />
				<button className="primary" onClick={newGame}>新建对局</button>
				<button onClick={refresh} disabled={!gameId}>刷新</button>
				<button onClick={undo} disabled={!gameId}>悔棋</button>
				<button onClick={()=>setFlipped(!flipped)}>翻转棋盘</button>
				<select value={engine} onChange={e=>setEngine(e.target.value)}>
					<option value="ab">Alpha-Beta</option>
					<option value="mcts">MCTS</option>
					<option value="mcts_nn">MCTS+NN</option>
				</select>
				{engine === 'ab' ? (
					<input type="number" min={1} max={6} value={depth} onChange={e=>setDepth(parseInt(e.target.value||'3',10))} />
				) : (
					React.createElement(React.Fragment, null,
						<input type="number" min={10} max={2000} value={sims} onChange={e=>setSims(parseInt(e.target.value||'100',10))} />,
						<input type="number" step="0.05" min={0} max={2} value={tau} onChange={e=>setTau(parseFloat(e.target.value||'1.0'))} />
					)
				)}
				{aiThinking && <span className="hint" style={{color:'#ef4444'}}>⏳ AI 思考中...</span>}
				{!aiThinking && <span className="hint">点击棋盘：选中起点，再点终点；AI 自动应手</span>}
			</div>

			<div style={{display:'flex', gap:16}}>
				<div className="board">
					<BoardGridSVG />
					{displayOrder.map((idx) => (
						<Square key={idx} idx={idx} piece={board[idx]} selected={selected===idx} legal={legalFrom.includes(idx)} onClick={()=>onSquareClick(idx)} />
					))}
				</div>
				<div className="panel" style={{flex:1}}>
					<div className="card">
						<div>对局ID: {gameId || '-'}</div>
						<div>行棋方: {game ? (game.side_to_move>0 ? '红' : '黑') : '-'}</div>
						<div>将军: {game ? (game.in_check ? '是' : '否') : '-'}</div>
						<div>三次重复: {game ? (game.threefold ? '是' : '否') : '-'}</div>
						{game && game.result && (
							<div style={{color: '#ef4444', fontWeight: 'bold'}}>
								对局结束: {game.result === 'red_win' ? '红胜' : game.result === 'black_win' ? '黑胜' : '和棋'}
							</div>
						)}
					</div>
					<div className="card">
						<div>记录</div>
						<div className="moves-list">
							{log.map((l, i) => (<div key={i}>• {l.msg}</div>))}
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);



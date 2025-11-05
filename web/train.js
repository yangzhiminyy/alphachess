const { useState, useEffect } = React;

function TrainControl(){
	const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000');
	const [status, setStatus] = useState(null);
	const [config, setConfig] = useState({
		games_per_batch: 10,
		sims_per_move: 100,
		max_moves: 150,
		train_epochs: 3,
		train_batch_size: 32,
		train_lr: 0.001,
		max_iterations: 100,
		model_path: 'models/latest.pt',
		data_dir: 'data',
		use_nn: false
	});

	async function api(path, opts){
		const res = await fetch(`${baseUrl}${path}`, opts);
		if (!res.ok) throw new Error(await res.text());
		return res.json();
	}

	async function fetchStatus(){
		try {
			const data = await api('/api/train/status');
			setStatus(data);
		} catch(e){
			console.error('获取状态失败:', e);
		}
	}

	async function startTraining(){
		try {
			await api('/api/train/start', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(config)
			});
			fetchStatus();
		} catch(e){
			alert('启动失败: ' + e.message);
		}
	}

	async function stopTraining(){
		try {
			await api('/api/train/stop', { method: 'POST' });
			fetchStatus();
		} catch(e){
			alert('停止失败: ' + e.message);
		}
	}

	useEffect(() => {
		fetchStatus();
		const timer = setInterval(fetchStatus, 2000);
		return () => clearInterval(timer);
	}, [baseUrl]);

	const running = status && status.running;

	return (
		<div className="app">
			<div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16}}>
				<h1 style={{margin:0}}>训练控制台</h1>
				<div style={{display:'flex', gap:8}}>
					<a href="./index.html" style={{textDecoration:'none'}}>
						<button>返回对局</button>
					</a>
					<a href="./model.html" style={{textDecoration:'none'}}>
						<button>模型查看器</button>
					</a>
				</div>
			</div>

			<div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:16}}>
				<div className="card">
					<h3>训练配置</h3>
					<div style={{display:'grid', gap:8}}>
						<label>
							每批对局数: 
							<input type="number" min={1} max={100} value={config.games_per_batch} onChange={e=>setConfig({...config, games_per_batch: parseInt(e.target.value)})} disabled={running} />
						</label>
						<label>
							每步模拟数: 
							<input type="number" min={10} max={1000} value={config.sims_per_move} onChange={e=>setConfig({...config, sims_per_move: parseInt(e.target.value)})} disabled={running} />
						</label>
						<label>
							最大步数/局: 
							<input type="number" min={50} max={512} value={config.max_moves} onChange={e=>setConfig({...config, max_moves: parseInt(e.target.value)})} disabled={running} />
						</label>
						<label>
							训练轮数/批: 
							<input type="number" min={1} max={50} value={config.train_epochs} onChange={e=>setConfig({...config, train_epochs: parseInt(e.target.value)})} disabled={running} />
						</label>
						<label>
							训练批大小: 
							<input type="number" min={8} max={256} value={config.train_batch_size} onChange={e=>setConfig({...config, train_batch_size: parseInt(e.target.value)})} disabled={running} />
						</label>
						<label>
							学习率: 
							<input type="number" step="0.0001" min={0.0001} max={0.1} value={config.train_lr} onChange={e=>setConfig({...config, train_lr: parseFloat(e.target.value)})} disabled={running} />
						</label>
						<label>
							最大迭代数: 
							<input type="number" min={1} max={1000} value={config.max_iterations} onChange={e=>setConfig({...config, max_iterations: parseInt(e.target.value)})} disabled={running} />
						</label>
						<label>
							模型路径: 
							<input type="text" value={config.model_path} onChange={e=>setConfig({...config, model_path: e.target.value})} disabled={running} style={{width:'100%'}} />
						</label>
						<label>
							数据目录: 
							<input type="text" value={config.data_dir} onChange={e=>setConfig({...config, data_dir: e.target.value})} disabled={running} style={{width:'100%'}} />
						</label>
						<label style={{display:'flex', alignItems:'center', gap:8}}>
							<input type="checkbox" checked={config.use_nn} onChange={e=>setConfig({...config, use_nn: e.target.checked})} disabled={running} />
							使用神经网络自对弈 (MCTS+NN)
						</label>
					</div>

					<div style={{marginTop:16, display:'flex', gap:8}}>
						{!running && (
							<button className="primary" onClick={startTraining}>启动训练循环</button>
						)}
						{running && (
							<button style={{background:'#ef4444', color:'#fff'}} onClick={stopTraining}>停止训练</button>
						)}
					</div>
				</div>

				<div className="card">
					<h3>训练状态</h3>
					{status && (
						<div style={{display:'grid', gap:8}}>
							<div>
								<strong>状态: </strong>
								<span style={{color: status.running ? '#22c55e' : '#6b7280', fontWeight:600}}>
									{status.running ? '🟢 运行中' : '⚪ 已停止'}
								</span>
							</div>
							<div><strong>迭代次数:</strong> {status.iteration}</div>
							<div><strong>总对局数:</strong> {status.games_played}</div>
							<div><strong>总样本数:</strong> {status.samples_collected}</div>
							<div><strong>最近损失:</strong> {status.last_train_loss.toFixed(4)}</div>
							<div><strong>当前模型:</strong> <code>{status.current_model}</code></div>
							<div style={{marginTop:8, padding:8, background:'#f3f4f6', borderRadius:4, fontFamily:'monospace', fontSize:12}}>
								{status.message || '等待中...'}
							</div>
						</div>
					)}
				</div>
			</div>

			<div className="card" style={{marginTop:16}}>
				<h3>说明</h3>
				<ul style={{lineHeight:1.8, color:'#6b7280'}}>
					<li><strong>训练流程：</strong>每次迭代包含：自对弈 → 保存 JSONL（文件名按时间戳）→ 训练模型 → 保存检查点</li>
					<li><strong>JSONL 文件：</strong>保存在 data/ 目录，格式为 sp_YYYYMMDD_HHMMSS.jsonl，便于追溯和重用</li>
					<li><strong>使用神经网络：</strong>勾选后用当前模型自对弈（需先有初始模型），否则用均匀先验</li>
					<li><strong>小批量训练：</strong>每批 10 局 × 3 轮训练，快速迭代，随时可停止</li>
					<li><strong>自动更新：</strong>页面每 2 秒刷新一次状态</li>
				</ul>
			</div>
		</div>
	);
}

ReactDOM.createRoot(document.getElementById('root')).render(<TrainControl />);


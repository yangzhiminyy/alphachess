const { useState, useEffect } = React;

function TopologyGraph({ topology }){
	const nodeColors = {
		input: '#22c55e',
		conv: '#3b82f6',
		residual: '#8b5cf6',
		dense: '#f59e0b',
		output: '#ef4444'
	};
	
	const width = 800;
	const height = 600;
	const nodeRadius = 50;
	
	// Layout nodes in layers
	const layers = [
		['input'],
		['stem'],
		['block0', 'block1', 'block2'],
		['p_conv', 'v_conv'],
		['p_fc', 'v_fc1'],
		['policy_out', 'v_fc2'],
		['value_out']
	];
	
	const positions = {};
	const layerSpacing = width / (layers.length + 1);
	
	layers.forEach((layer, li) => {
		const y_spacing = height / (layer.length + 1);
		layer.forEach((nodeId, ni) => {
			positions[nodeId] = {
				x: (li + 1) * layerSpacing,
				y: (ni + 1) * y_spacing
			};
		});
	});
	
	return (
		<svg width={width} height={height} style={{border:'1px solid #e5e7eb', borderRadius:8, background:'#fafafa'}}>
			{/* Edges */}
			{topology.edges.map((e, i) => {
				const from = positions[e.from];
				const to = positions[e.to];
				if(!from || !to) return null;
				return React.createElement('line', {
					key: `edge-${i}`,
					x1: from.x,
					y1: from.y,
					x2: to.x,
					y2: to.y,
					stroke: '#9ca3af',
					strokeWidth: 2,
					markerEnd: 'url(#arrow)'
				});
			})}
			
			{/* Arrow marker */}
			<defs>
				<marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
					<path d="M0,0 L0,6 L9,3 z" fill="#9ca3af" />
				</marker>
			</defs>
			
			{/* Nodes */}
			{topology.nodes.map((n, i) => {
				const pos = positions[n.id];
				if(!pos) return null;
				const color = nodeColors[n.type] || '#6b7280';
				return React.createElement('g', { key: `node-${i}` },
					React.createElement('circle', {
						cx: pos.x,
						cy: pos.y,
						r: nodeRadius,
						fill: color,
						opacity: 0.9,
						stroke: '#fff',
						strokeWidth: 3
					}),
					React.createElement('text', {
						x: pos.x,
						y: pos.y,
						textAnchor: 'middle',
						dominantBaseline: 'middle',
						fill: '#fff',
						fontSize: 11,
						fontWeight: 600
					}, n.label.split('\n').map((line, li) => 
						React.createElement('tspan', {
							key: li,
							x: pos.x,
							dy: li === 0 ? -6 : 14
						}, line)
					))
				);
			})}
		</svg>
	);
}

function ModelViewer(){
	const [baseUrl, setBaseUrl] = useState('http://127.0.0.1:8000');
	const [models, setModels] = useState([]);
	const [selectedModel, setSelectedModel] = useState('models/latest.pt');
	const [modelInfo, setModelInfo] = useState(null);
	const [loading, setLoading] = useState(false);
	const [structureOffset, setStructureOffset] = useState(0);
	const [showTopology, setShowTopology] = useState(false);

	async function api(path){
		const res = await fetch(`${baseUrl}${path}`);
		if (!res.ok) throw new Error(await res.text());
		return res.json();
	}

	async function loadModels(){
		const data = await api('/api/model/list');
		setModels(data.models || []);
	}

	async function loadModelInfo(offset = 0){
		if(!selectedModel) return;
		setLoading(true);
		try {
			const data = await api(`/api/model/info?model_path=${encodeURIComponent(selectedModel)}&offset=${offset}&limit=20`);
			setModelInfo(data);
			setStructureOffset(offset);
		} catch(e){
			alert('加载模型失败: ' + e.message);
		}
		setLoading(false);
	}

	function loadMore(){
		if(modelInfo && structureOffset + 20 < modelInfo.structure.total){
			loadModelInfo(structureOffset + 20);
		}
	}

	function loadPrevious(){
		if(structureOffset >= 20){
			loadModelInfo(Math.max(0, structureOffset - 20));
		}
	}

	useEffect(() => {
		loadModels();
	}, [baseUrl]);

	useEffect(() => {
		if(selectedModel){
			loadModelInfo(0);
			setShowTopology(false);
		}
	}, [selectedModel]);

	return (
		<div className="app">
			<div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16}}>
				<h1 style={{margin:0}}>模型查看器</h1>
				<div style={{display:'flex', gap:8}}>
					<a href="./index.html" style={{textDecoration:'none'}}>
						<button>返回对局</button>
					</a>
					<button onClick={loadModels}>刷新列表</button>
				</div>
			</div>

			<div style={{display:'grid', gridTemplateColumns:'1fr 2fr', gap:16}}>
				<div className="card">
					<h3>可用模型</h3>
					{models.length === 0 && <div className="hint">暂无模型文件</div>}
					{models.map(m => (
						<div 
							key={m.path} 
							onClick={() => setSelectedModel(m.path)}
							style={{
								padding:8, 
								cursor:'pointer', 
								background: selectedModel===m.path ? '#dbeafe' : '#fafafa',
								borderRadius:4,
								marginBottom:4,
								border: selectedModel===m.path ? '2px solid #2563eb' : '1px solid #e5e7eb'
							}}
						>
							<div style={{fontWeight:600}}>{m.name}</div>
							<div className="hint">{m.size_mb} MB · {new Date(m.modified*1000).toLocaleString()}</div>
						</div>
					))}
				</div>

				<div>
					{loading && <div>加载中...</div>}
					{!loading && modelInfo && (
						<div style={{display:'flex', flexDirection:'column', gap:12}}>
							<div className="card">
								<h3>基本信息</h3>
								<table style={{width:'100%', borderCollapse:'collapse'}}>
									<tbody>
										<tr><td style={{padding:4}}>路径</td><td style={{padding:4, fontFamily:'monospace'}}>{modelInfo.model_path}</td></tr>
										<tr><td style={{padding:4}}>文件大小</td><td style={{padding:4}}>{modelInfo.file_size_mb} MB</td></tr>
										<tr><td style={{padding:4}}>总参数</td><td style={{padding:4}}>{modelInfo.parameters.total.toLocaleString()}</td></tr>
										<tr><td style={{padding:4}}>可训练参数</td><td style={{padding:4}}>{modelInfo.parameters.trainable.toLocaleString()}</td></tr>
									</tbody>
								</table>
							</div>

							<div className="card">
								<h3>架构</h3>
								<table style={{width:'100%', borderCollapse:'collapse'}}>
									<tbody>
										<tr><td style={{padding:4}}>输入通道</td><td style={{padding:4}}>{modelInfo.architecture.in_channels}</td></tr>
										<tr><td style={{padding:4}}>隐藏层通道</td><td style={{padding:4}}>{modelInfo.architecture.channels}</td></tr>
										<tr><td style={{padding:4}}>残差块数</td><td style={{padding:4}}>{modelInfo.architecture.num_blocks}</td></tr>
										<tr><td style={{padding:4}}>策略输出</td><td style={{padding:4}}>{modelInfo.architecture.policy_output}</td></tr>
										<tr><td style={{padding:4}}>价值输出</td><td style={{padding:4}}>{modelInfo.architecture.value_output}</td></tr>
									</tbody>
								</table>
							</div>

							<div className="card">
								<div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
									<h3 style={{margin:0}}>拓扑结构</h3>
									<button onClick={() => setShowTopology(!showTopology)}>
										{showTopology ? '隐藏' : '显示'}
									</button>
								</div>
								{showTopology && (
									<TopologyGraph topology={modelInfo.topology} />
								)}
							</div>

							<div className="card">
								<div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8}}>
									<h3 style={{margin:0}}>模块结构 ({structureOffset+1}-{Math.min(structureOffset+20, modelInfo.structure.total)} / {modelInfo.structure.total})</h3>
									<div style={{display:'flex', gap:4}}>
										<button onClick={loadPrevious} disabled={structureOffset === 0}>上一页</button>
										<button onClick={loadMore} disabled={structureOffset + 20 >= modelInfo.structure.total}>下一页</button>
									</div>
								</div>
								<div style={{maxHeight:300, overflow:'auto', fontFamily:'monospace', fontSize:12}}>
									{modelInfo.structure.items.map((s, i) => (
										<div key={i} style={{padding:'2px 4px'}}>
											<span style={{color:'#9ca3af'}}>#{structureOffset+i+1}</span> <span style={{color:'#6b7280'}}>{s.name}</span> → <span style={{color:'#2563eb'}}>{s.type}</span>
										</div>
									))}
								</div>
							</div>

							<div className="card">
								<h3>参数详情</h3>
								<div style={{maxHeight:400, overflow:'auto'}}>
									<table style={{width:'100%', borderCollapse:'collapse', fontSize:12, fontFamily:'monospace'}}>
										<thead>
											<tr style={{background:'#f3f4f6'}}>
												<th style={{padding:4, textAlign:'left'}}>参数名</th>
												<th style={{padding:4, textAlign:'left'}}>形状</th>
												<th style={{padding:4, textAlign:'right'}}>数量</th>
											</tr>
										</thead>
										<tbody>
											{modelInfo.layers.map((l, i) => (
												<tr key={i} style={{borderBottom:'1px solid #e5e7eb'}}>
													<td style={{padding:4}}>{l.name}</td>
													<td style={{padding:4, color:'#6b7280'}}>{JSON.stringify(l.shape)}</td>
													<td style={{padding:4, textAlign:'right'}}>{l.num_params.toLocaleString()}</td>
												</tr>
											))}
										</tbody>
									</table>
								</div>
							</div>
						</div>
					)}
				</div>
			</div>
		</div>
	);
}

ReactDOM.createRoot(document.getElementById('root')).render(<ModelViewer />);


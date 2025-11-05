// Arena.js - 竞技场评测前端逻辑

const API_BASE = '';

async function api(path, options = {}) {
    const res = await fetch(API_BASE + path, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    if (!res.ok) {
        const err = await res.text();
        throw new Error(err);
    }
    return await res.json();
}

// Update UI based on engine selection
function updateEngineOptions(player) {
    const engine = document.getElementById(`engine${player}`).value;
    const modelGroup = document.getElementById(`modelGroup${player}`);
    const depthGroup = document.getElementById(`depthGroup${player}`);
    const simsGroup = document.getElementById(`simsGroup${player}`);
    
    // Show/hide relevant options
    modelGroup.style.display = engine === 'mcts_nn' ? 'block' : 'none';
    depthGroup.style.display = engine === 'alphabeta' ? 'block' : 'none';
    simsGroup.style.display = (engine === 'mcts' || engine === 'mcts_nn') ? 'block' : 'none';
}

// Initialize event listeners
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('engineA').addEventListener('change', () => updateEngineOptions('A'));
    document.getElementById('engineB').addEventListener('change', () => updateEngineOptions('B'));
    
    // Initialize display
    updateEngineOptions('A');
    updateEngineOptions('B');
});

async function startArena() {
    const startBtn = document.getElementById('startBtn');
    const progress = document.getElementById('progress');
    const results = document.getElementById('results');
    
    // Get configuration
    const engineA = document.getElementById('engineA').value;
    const engineB = document.getElementById('engineB').value;
    const modelA = document.getElementById('modelA').value || null;
    const modelB = document.getElementById('modelB').value || null;
    const depthA = parseInt(document.getElementById('depthA').value);
    const depthB = parseInt(document.getElementById('depthB').value);
    const simsA = parseInt(document.getElementById('simsA').value);
    const simsB = parseInt(document.getElementById('simsB').value);
    const nGames = parseInt(document.getElementById('nGames').value);
    
    // Validate
    if (nGames % 2 !== 0) {
        alert('对战局数必须是偶数！');
        return;
    }
    
    if (nGames < 2 || nGames > 100) {
        alert('对战局数必须在 2-100 之间！');
        return;
    }
    
    // Build params
    const paramsA = {};
    if (engineA === 'alphabeta') paramsA.depth = depthA;
    if (engineA === 'mcts' || engineA === 'mcts_nn') paramsA.sims = simsA;
    
    const paramsB = {};
    if (engineB === 'alphabeta') paramsB.depth = depthB;
    if (engineB === 'mcts' || engineB === 'mcts_nn') paramsB.sims = simsB;
    
    // Show progress, hide results
    startBtn.disabled = true;
    startBtn.textContent = '对战进行中...';
    progress.style.display = 'block';
    results.style.display = 'none';
    
    const progressFill = document.getElementById('progressFill');
    progressFill.style.width = '10%';
    progressFill.textContent = '启动中...';
    
    try {
        // Call API (this will take a while)
        const arenaResults = await api('/api/arena/run', {
            method: 'POST',
            body: JSON.stringify({
                engine_a: engineA,
                engine_b: engineB,
                model_a: modelA && engineA === 'mcts_nn' ? modelA : null,
                model_b: modelB && engineB === 'mcts_nn' ? modelB : null,
                params_a: paramsA,
                params_b: paramsB,
                n_games: nGames
            })
        });
        
        progressFill.style.width = '100%';
        progressFill.textContent = '完成！';
        
        // Display results
        displayResults(arenaResults);
        
    } catch (error) {
        alert(`错误: ${error.message}`);
        console.error(error);
    } finally {
        startBtn.disabled = false;
        startBtn.textContent = '开始对战';
        setTimeout(() => {
            progress.style.display = 'none';
        }, 1000);
    }
}

function displayResults(data) {
    const results = document.getElementById('results');
    const eloDiffCard = document.getElementById('eloDiffCard');
    const eloDiff = document.getElementById('eloDiff');
    const winRate = document.getElementById('winRate');
    const record = document.getElementById('record');
    const gameList = document.getElementById('gameList');
    
    // Update ELO diff
    const eloDiffValue = data.elo_diff;
    eloDiff.textContent = `${eloDiffValue >= 0 ? '+' : ''}${eloDiffValue.toFixed(1)}`;
    
    // Color code based on value
    if (eloDiffValue >= 0) {
        eloDiffCard.classList.remove('negative');
    } else {
        eloDiffCard.classList.add('negative');
    }
    
    // Update win rate
    winRate.textContent = `${(data.win_rate * 100).toFixed(1)}%`;
    
    // Update record
    record.textContent = `${data.wins} / ${data.draws} / ${data.losses}`;
    
    // Update game list
    gameList.innerHTML = '';
    data.games.forEach(game => {
        const div = document.createElement('div');
        div.className = 'game-item';
        
        const gameNumber = document.createElement('span');
        gameNumber.className = 'game-number';
        gameNumber.textContent = `#${game.game_number}`;
        
        const matchup = document.createElement('span');
        matchup.className = 'game-matchup';
        matchup.textContent = `${game.red}(红) vs ${game.black}(黑) - ${game.moves} 步`;
        
        const result = document.createElement('span');
        result.className = 'game-result';
        
        if (game.outcome.includes('A wins')) {
            result.classList.add('win-a');
            result.textContent = 'A 胜';
        } else if (game.outcome.includes('B wins')) {
            result.classList.add('win-b');
            result.textContent = 'B 胜';
        } else {
            result.classList.add('draw');
            result.textContent = '和';
        }
        
        div.appendChild(gameNumber);
        div.appendChild(matchup);
        div.appendChild(result);
        
        gameList.appendChild(div);
    });
    
    // Show results
    results.style.display = 'block';
    results.scrollIntoView({ behavior: 'smooth' });
}

// Export for inline onclick
window.startArena = startArena;
window.updateEngineOptions = updateEngineOptions;


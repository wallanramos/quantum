let updateInterval = null;
let lwChart = null;
let chartResizeHandler = null;
let rawPriceHistory = [];
let currentChartTimeframe = '1h';
let chartRefreshTimer = null;
let chartExpanded = true;

const CHART_RANGE_MS = {
    '1m': 60 * 1000,
    '15m': 15 * 60 * 1000,
    '1h': 60 * 60 * 1000
};

const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000`;
const STORAGE_KEY_WALLET  = 'quantum_selected_wallet';
const STORAGE_KEY_CHART   = 'quantum_chart_expanded';

// ==================== CHART ====================

function toggleChart(event) {
    if (event && event.target.closest('.timeframe-btn')) return;

    const content    = document.getElementById('chartContent');
    const timeframes = document.getElementById('chartTimeframes');
    const caret      = document.getElementById('chartToggleIcon');
    const header     = document.querySelector('.chart-header');

    chartExpanded = !chartExpanded;
    localStorage.setItem(STORAGE_KEY_CHART, chartExpanded);

    if (chartExpanded) {
        content.classList.remove('collapsed');
        timeframes.style.display = 'flex';
        if (caret)  caret.classList.remove('collapsed');
        if (header) header.classList.remove('collapsed');
        setTimeout(() => {
            if (lwChart) lwChart.applyOptions({ width: document.getElementById('priceChartContainer').clientWidth || 800 });
        }, 300);
    } else {
        content.classList.add('collapsed');
        timeframes.style.display = 'none';
        if (caret)  caret.classList.add('collapsed');
        if (header) header.classList.add('collapsed');
    }
}

async function fetchPriceHistory(timeframe) {
    const tf = timeframe || currentChartTimeframe || '1h';
    try {
        const res = await fetch(`${API_BASE}/api/history?timeframe=${tf}`);
        if (res.ok) {
            const data = await res.json();
            if (data.success && Array.isArray(data.history)) return data.history;
        }
    } catch (_) {}
    return [];
}

function destroyPriceChart() {
    if (chartResizeHandler) { window.removeEventListener('resize', chartResizeHandler); chartResizeHandler = null; }
    if (lwChart) { lwChart.remove(); lwChart = null; }
}

function setPriceChartTimeframe(tf) {
    if (!CHART_RANGE_MS[tf]) return;
    currentChartTimeframe = tf;
    document.querySelectorAll('.timeframe-btn').forEach(btn => btn.classList.toggle('active', btn.dataset.tf === tf));
    refreshPriceChart();
}

function buildCandles(items) {
    return items.map(item => {
        const t = item.timestamp ? Math.floor(new Date(item.timestamp).getTime() / 1000) : null;
        if (!t || isNaN(t) || t <= 0) return null;
        const o = parseFloat(item.open), h = parseFloat(item.high),
              l = parseFloat(item.low),  c = parseFloat(item.close);
        if (!isFinite(o) || !isFinite(h) || !isFinite(l) || !isFinite(c)) return null;
        return { time: t, open: o, high: h, low: l, close: c };
    }).filter(Boolean).sort((a, b) => a.time - b.time);
}

function calculateEMA(candles, period) {
    const ema = [], mult = 2 / (period + 1);
    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) {
            ema.push({ time: candles[i].time, value: null });
        } else if (i === period - 1) {
            let sum = 0;
            for (let j = 0; j < period; j++) sum += candles[j].close;
            ema.push({ time: candles[i].time, value: sum / period });
        } else {
            ema.push({ time: candles[i].time, value: (candles[i].close * mult) + (ema[i-1].value * (1 - mult)) });
        }
    }
    return ema;
}

function renderPriceChart() {
    const container = document.getElementById('priceChartContainer');
    const emptyEl   = document.getElementById('chartEmpty');
    const statusEl  = document.getElementById('chartStatus');
    const LW = typeof LightweightCharts !== 'undefined' ? LightweightCharts : null;

    if (!container) return;
    if (!LW || typeof LW.createChart !== 'function') {
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Biblioteca não carregou.'; }
        return;
    }
    if (!rawPriceHistory || rawPriceHistory.length === 0) {
        destroyPriceChart();
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Sem dados. Backend rodando?'; }
        if (statusEl) statusEl.textContent = '';
        return;
    }

    const candles = buildCandles(rawPriceHistory);
    if (candles.length === 0) {
        destroyPriceChart();
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Candles inválidos.'; }
        return;
    }

    if (emptyEl) emptyEl.classList.add('hidden');
    destroyPriceChart();

    try {
        lwChart = LW.createChart(container, {
            width: container.clientWidth || 800,
            height: 300,
            layout: { background: { type: 'solid', color: '#080808' }, textColor: '#666', fontFamily: "'DM Mono', monospace" },
            grid: { vertLines: { color: '#141414' }, horzLines: { color: '#141414' } },
            crosshair: { mode: LW.CrosshairMode ? LW.CrosshairMode.Normal : 0 },
            rightPriceScale: { borderColor: '#1e1e1e', scaleMargins: { top: 0.08, bottom: 0.08 } },
            timeScale: { borderColor: '#1e1e1e', timeVisible: true, secondsVisible: false },
            localization: { priceFormatter: p => '$' + p.toFixed(4) }
        });

        lwChart.addCandlestickSeries({
            upColor: '#3dffa0', downColor: '#ff4d6a',
            borderUpColor: '#3dffa0', borderDownColor: '#ff4d6a',
            wickUpColor: '#3dffa0', wickDownColor: '#ff4d6a'
        }).setData(candles);

        lwChart.addLineSeries({ color: '#c8f562', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
            .setData(calculateEMA(candles, 9).filter(d => d.value !== null));

        lwChart.addLineSeries({ color: '#f472b6', lineWidth: 1, priceLineVisible: false, lastValueVisible: false })
            .setData(calculateEMA(candles, 21).filter(d => d.value !== null));

        lwChart.timeScale().fitContent();

        chartResizeHandler = () => {
            if (lwChart) lwChart.applyOptions({ width: container.clientWidth || 800 });
        };
        window.addEventListener('resize', chartResizeHandler);
    } catch (err) {
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Erro: ' + err.message; }
        return;
    }

    const tf = currentChartTimeframe;
    const delta = candles[candles.length-1].close - candles[0].open;
    const pct   = candles[0].open !== 0 ? (delta / candles[0].open) * 100 : 0;
    if (statusEl) statusEl.textContent =
        `CoinEx · ${candles.length} velas (${tf}) · ${delta >= 0 ? '+' : ''}${delta.toFixed(6)} (${delta >= 0 ? '+' : ''}${pct.toFixed(2)}%) · EMA9/21`;
}

async function refreshPriceChart() {
    rawPriceHistory = await fetchPriceHistory(currentChartTimeframe);
    renderPriceChart();
}

// ==================== UTILS ====================

async function safeFetch(url, options = {}) {
    let response;
    try { response = await fetch(url, options); }
    catch { throw new Error('Backend não está rodando. Execute: python3 backend/wallet.py'); }

    const text = await response.text();
    let data;
    try { data = JSON.parse(text); }
    catch {
        throw new Error(`Resposta inválida. Status ${response.status}. Início: ${text.substring(0, 120).replace(/\n/g,' ')}`);
    }
    return { ok: response.ok, status: response.status, data };
}

// ==================== PREÇO ====================

async function fetchOsmoPrice() {
    const { ok, data } = await safeFetch(`${API_BASE}/api/price`);
    if (!ok) throw new Error('Backend não responde.');
    if (!data.success) throw new Error(data.error || 'Erro ao buscar preço');
    return data.price;
}

async function updatePrice() {
    const priceEl  = document.getElementById('price');
    const statusEl = document.getElementById('status');
    try {
        priceEl.textContent  = '...';
        statusEl.textContent = 'carregando...';
        const price = await fetchOsmoPrice();
        priceEl.textContent  = price.toFixed(4);
        statusEl.textContent = `atualizado em: ${new Date().toLocaleString('pt-BR')}`;
        await refreshPriceChart();
    } catch (err) {
        priceEl.textContent  = 'erro';
        statusEl.textContent = err.message;
    }
}

function startAutoUpdate() {
    if (updateInterval) clearInterval(updateInterval);
    updatePrice();
    updateInterval = setInterval(updatePrice, 60000);
}

// ==================== IA ====================

async function fetchPositionSignal() {
    try {
        const res  = await fetch(`${API_BASE}/api/ai/position?timeframe=${currentChartTimeframe}`);
        const data = await res.json();
        // positionText removido do novo layout — sem-op
    } catch (_) {}
}

async function analyzeHistory() {
    const analysisDiv     = document.getElementById('analysis');
    const analysisContent = document.getElementById('analysisContent');
    const btnAi           = document.getElementById('btnAnalyzeAi');

    function mountLoadingUi(subtitle) {
        analysisContent.innerHTML = `
            <div class="ai-loading-wrap" id="aiLoadingState">
                <div class="loader"></div>
                <div class="ai-loading-text" id="aiLoadingSub">${subtitle}</div>
            </div>
            <div id="aiStreamWrap" style="display:none;">
                <div class="ai-stream-badge" id="aiStreamBadge"><span class="ai-dot-pulse"></span><span id="aiStreamBadgeText">recebendo em tempo real</span></div>
                <div class="ai-response" id="aiStreamBody"></div>
            </div>`;
    }

    function setLoadingSub(t) { const el = document.getElementById('aiLoadingSub'); if (el) el.textContent = t; }
    function revealStreamUi() {
        const l = document.getElementById('aiLoadingState'), w = document.getElementById('aiStreamWrap');
        if (l) l.style.display = 'none';
        if (w) w.style.display = 'block';
    }
    function markDone() {
        const b = document.getElementById('aiStreamBadge'), t = document.getElementById('aiStreamBadgeText');
        if (b) b.classList.add('done');
        if (t) t.textContent = 'resposta concluída';
    }

    try {
        if (btnAi) btnAi.disabled = true;
        analysisDiv.style.display = 'block';
        mountLoadingUi('conectando à IA…');
        analysisDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        const res = await fetch(`${API_BASE}/api/ai/analyze?timeframe=${currentChartTimeframe}`, {
            headers: { Accept: 'text/event-stream', 'Cache-Control': 'no-cache' }, cache: 'no-store'
        });

        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        if (!res.body) throw new Error('Streaming indisponível neste navegador.');

        setLoadingSub('aguardando primeiro token…');

        const reader = res.body.getReader(), decoder = new TextDecoder();
        let aiText = '', sseBuffer = '', firstToken = false;
        const bodyEl = document.getElementById('aiStreamBody');

        function parseSSE(s) {
            if (s === '[DONE]') return;
            let j; try { j = JSON.parse(s); } catch { return; }
            if (j.error) throw new Error(typeof j.error === 'string' ? j.error : JSON.stringify(j.error));
            const c = j.choices?.[0]?.delta?.content || '';
            if (c) {
                if (!firstToken) { firstToken = true; revealStreamUi(); }
                aiText += c;
                if (bodyEl) try { bodyEl.innerHTML = marked.parse(aiText); } catch { bodyEl.textContent = aiText; }
            }
        }

        while (true) {
            const { done, value } = await reader.read();
            sseBuffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            const lines = sseBuffer.split('\n');
            sseBuffer = lines.pop() || '';
            for (let line of lines) {
                line = line.replace(/\r$/, '');
                if (line.startsWith('data: ')) parseSSE(line.slice(6).trim());
            }
            if (done) {
                if (sseBuffer.trim() && sseBuffer.startsWith('data: ')) parseSSE(sseBuffer.slice(6).trim());
                break;
            }
        }

        if (firstToken) markDone();
        if (!aiText.trim()) analysisContent.innerHTML = '<p style="color:var(--text-dim)">IA não retornou texto. Verifique o HF_API_TOKEN no .env</p>';

        await fetchPositionSignal();
    } catch (err) {
        analysisContent.innerHTML = `<p style="color:var(--red)">Erro: ${err?.message || err}</p>`;
    } finally {
        if (btnAi) btnAi.disabled = false;
    }
}

// ==================== WALLET ====================

async function loadWallets() {
    const sel = document.getElementById('walletSelect');
    try {
        const { ok, data } = await safeFetch(`${API_BASE}/api/wallets`);
        if (!ok) { sel.innerHTML = '<option value="">backend offline</option>'; return; }
        if (!data.success) return;

        sel.innerHTML = '<option value="">selecione carteira</option>';
        data.wallets.forEach(w => {
            const opt = document.createElement('option');
            opt.value = w.address;
            opt.textContent = `${w.name} (${w.address.substring(0, 12)}...)`;
            sel.appendChild(opt);
        });

        const saved = localStorage.getItem(STORAGE_KEY_WALLET);
        if (saved) {
            sel.value = saved;
            if (sel.value === saved) loadBalances();
            else localStorage.removeItem(STORAGE_KEY_WALLET);
        }
    } catch {
        sel.innerHTML = '<option value="">backend offline</option>';
    }
}

async function loadBalances() {
    const sel     = document.getElementById('walletSelect');
    const address = sel.value;
    const actions = document.getElementById('walletActions');

    if (!address) {
        actions.classList.remove('visible');
        return;
    }

    localStorage.setItem(STORAGE_KEY_WALLET, address);
    actions.classList.add('visible');

    const balancesDiv = document.getElementById('balances');
    try {
        balancesDiv.innerHTML = '<div style="padding:14px 0;font-family:var(--mono);font-size:0.7rem;color:var(--text-dim)"><div class="loader" style="display:inline-block"></div></div>';
        const { ok, data } = await safeFetch(`${API_BASE}/api/balance/${address}`);

        if (!ok || !data.success) {
            balancesDiv.innerHTML = `<p style="color:var(--red);font-family:var(--mono);font-size:0.7rem;padding:14px 0">Erro: ${data?.error || 'falha ao carregar'}</p>`;
            return;
        }

        if (data.balances?.length > 0) {
            balancesDiv.innerHTML = data.balances.map(b => {
                let denom = b.denom, display;
                if (denom === 'uosmo') display = 'OSMO';
                else if (denom.startsWith('ibc/')) display = 'IBC/' + denom.substring(4, 12) + '...';
                else if (denom.startsWith('gamm/pool/')) display = 'Pool #' + denom.split('/')[2];
                else display = denom.substring(0, 20);
                const amount = (parseInt(b.amount) / 1_000_000).toFixed(6);
                return `<div class="balance-item"><span class="balance-denom" title="${denom}">${display}</span><span class="balance-amount">${amount}</span></div>`;
            }).join('');
        } else {
            balancesDiv.innerHTML = '<p style="color:var(--text-dim);font-family:var(--mono);font-size:0.7rem;padding:14px 0">nenhum saldo encontrado</p>';
        }
    } catch (err) {
        balancesDiv.innerHTML = `<p style="color:var(--red);font-family:var(--mono);font-size:0.7rem;padding:14px 0">Erro: ${err.message}</p>`;
    }
}

// ==================== SWAP MODAL ====================

let swapGasTimer = null;

async function fetchSwapGasInfo() {
    const label = document.getElementById('swapGasLabel');
    if (!label) return;
    try {
        const res = await fetch(`${API_BASE}/api/swap/gasinfo`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.success) {
            label.innerHTML =
                `Gas price: <span class="gas-val">${data.gas_prices}</span> &nbsp;|&nbsp; ` +
                `Ajuste: <span class="gas-val">${data.gas_adjustment}x</span> &nbsp;|&nbsp; ` +
                `Slippage: <span class="gas-val">${data.slippage_pct}%</span>`;
        }
    } catch (_) {}
}

function openSwapModal() {
    document.getElementById('swapModal').classList.add('show');
    document.getElementById('swapStatus').textContent = '';
    document.getElementById('swapAmount').value = '';
    fetchSwapGasInfo();
    swapGasTimer = setInterval(fetchSwapGasInfo, 5000);
}

function closeSwapModal(event) {
    if (event && event.target !== document.getElementById('swapModal')) return;
    document.getElementById('swapModal').classList.remove('show');
    if (swapGasTimer) { clearInterval(swapGasTimer); swapGasTimer = null; }
}

async function executeSwap() {
    const from    = document.getElementById('swapFrom').value;
    const to      = document.getElementById('swapTo').value;
    const amount  = document.getElementById('swapAmount').value;
    const address = document.getElementById('walletSelect').value;
    const status  = document.getElementById('swapStatus');

    if (!amount || parseFloat(amount) <= 0) { status.textContent = 'Digite uma quantidade válida'; status.style.color = 'var(--red)'; return; }
    if (!address) { status.textContent = 'Selecione uma carteira primeiro'; status.style.color = 'var(--red)'; return; }
    if (!confirm(`Confirma o swap de ${amount} ${from === 'uosmo' ? 'OSMO' : 'USDC'}?`)) return;

    try {
        status.textContent = 'executando swap...'; status.style.color = 'var(--text-muted)';
        const res  = await fetch(`${API_BASE}/api/swap/execute`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from, to, amount: Math.floor(parseFloat(amount) * 1_000_000), address })
        });
        const data = await res.json();
        if (data.success) {
            status.textContent = 'swap executado com sucesso!'; status.style.color = 'var(--green)';
            setTimeout(() => { loadBalances(); closeSwapModal(); }, 1500);
        } else {
            status.textContent = 'Erro: ' + data.error; status.style.color = 'var(--red)';
        }
    } catch (err) {
        status.textContent = 'Erro: ' + err.message; status.style.color = 'var(--red)';
    }
}

// ==================== WALLET MODAL ====================

function openWalletModal(tab) {
    const address = document.getElementById('walletSelect').value;
    const modal   = document.getElementById('walletModal');

    // Preenche info da aba excluir
    const nameEl = document.getElementById('deleteWalletName');
    if (nameEl) nameEl.textContent = address || '(nenhuma carteira selecionada)';

    // Limpa status
    document.getElementById('restoreStatus').textContent = '';
    document.getElementById('deleteStatus').textContent  = '';
    document.getElementById('restoreName').value     = '';
    document.getElementById('restoreMnemonic').value = '';

    switchWalletTab(tab || 'restore');
    modal.classList.add('show');
}

function closeWalletModal(event) {
    if (event && event.target !== document.getElementById('walletModal')) return;
    document.getElementById('walletModal').classList.remove('show');
}

function switchWalletTab(tab) {
    document.querySelectorAll('.wallet-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
    document.querySelectorAll('.wallet-tab-panel').forEach(p => p.classList.toggle('active', p.id === 'tab' + tab.charAt(0).toUpperCase() + tab.slice(1)));
}

async function restoreWallet() {
    const name     = document.getElementById('restoreName').value.trim();
    const mnemonic = document.getElementById('restoreMnemonic').value.trim();
    const status   = document.getElementById('restoreStatus');
    const btn      = document.getElementById('btnRestore');

    if (!name)     { status.textContent = 'Informe o nome da chave'; status.style.color = 'var(--red)'; return; }
    if (!mnemonic) { status.textContent = 'Informe o mnemônico'; status.style.color = 'var(--red)'; return; }

    try {
        btn.disabled = true;
        status.textContent = 'restaurando...'; status.style.color = 'var(--text-muted)';

        const res  = await fetch(`${API_BASE}/api/wallet/restore`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, mnemonic })
        });
        const data = await res.json();

        if (data.success) {
            status.textContent = `Carteira "${name}" restaurada com sucesso!`; status.style.color = 'var(--green)';
            setTimeout(async () => { await loadWallets(); closeWalletModal(); }, 1500);
        } else {
            status.textContent = 'Erro: ' + data.error; status.style.color = 'var(--red)';
        }
    } catch (err) {
        status.textContent = 'Erro: ' + err.message; status.style.color = 'var(--red)';
    } finally {
        btn.disabled = false;
    }
}

async function deleteWallet() {
    const address = document.getElementById('walletSelect').value;
    const status  = document.getElementById('deleteStatus');
    const btn     = document.getElementById('btnDelete');

    if (!address) { status.textContent = 'Nenhuma carteira selecionada'; status.style.color = 'var(--red)'; return; }
    if (!confirm('Tem certeza? Esta ação remove a chave do keyring permanentemente.')) return;

    try {
        btn.disabled = true;
        status.textContent = 'excluindo...'; status.style.color = 'var(--text-muted)';

        const res  = await fetch(`${API_BASE}/api/wallet/delete`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address })
        });
        const data = await res.json();

        if (data.success) {
            status.textContent = 'Chave excluída com sucesso.'; status.style.color = 'var(--green)';
            localStorage.removeItem(STORAGE_KEY_WALLET);
            setTimeout(async () => { await loadWallets(); closeWalletModal(); }, 1500);
        } else {
            status.textContent = 'Erro: ' + data.error; status.style.color = 'var(--red)';
        }
    } catch (err) {
        status.textContent = 'Erro: ' + err.message; status.style.color = 'var(--red)';
    } finally {
        btn.disabled = false;
    }
}

// ==================== INIT ====================

window.addEventListener('load', () => {
    startAutoUpdate();
    loadWallets();
    refreshPriceChart();
    chartRefreshTimer = setInterval(refreshPriceChart, 30000);

    const saved = localStorage.getItem(STORAGE_KEY_CHART);
    if (saved !== null) {
        chartExpanded = saved === 'true';
        if (!chartExpanded) {
            const content = document.getElementById('chartContent');
            const tf      = document.getElementById('chartTimeframes');
            const caret   = document.getElementById('chartToggleIcon');
            const header  = document.querySelector('.chart-header');
            content.classList.add('collapsed');
            tf.style.display = 'none';
            if (caret)  caret.classList.add('collapsed');
            if (header) header.classList.add('collapsed');
        }
    }
});

window.addEventListener('beforeunload', () => {
    if (chartRefreshTimer) clearInterval(chartRefreshTimer);
});
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
const STORAGE_KEY_WALLET = 'quantum_selected_wallet';
const STORAGE_KEY_CHART_EXPANDED = 'quantum_chart_expanded';

function toggleChart(event) {
    // Se clicou em um botão de timeframe, não faz nada
    if (event && event.target.closest('.timeframe-btn')) {
        return;
    }
    
    const content = document.getElementById('chartContent');
    const timeframes = document.getElementById('chartTimeframes');
    const caret = document.getElementById('chartToggleIcon');
    const header = document.querySelector('.chart-header');
    
    chartExpanded = !chartExpanded;
    localStorage.setItem(STORAGE_KEY_CHART_EXPANDED, chartExpanded);
    
    if (chartExpanded) {
        content.classList.remove('collapsed');
        timeframes.style.display = 'flex';
        if (caret) caret.classList.remove('collapsed');
        if (header) header.classList.remove('collapsed');
        // Aguarda a animação antes de redesenhar
        setTimeout(() => {
            if (lwChart) {
                lwChart.applyOptions({ 
                    width: document.getElementById('priceChartContainer').clientWidth || 800 
                });
            }
        }, 300);
    } else {
        content.classList.add('collapsed');
        timeframes.style.display = 'none';
        if (caret) caret.classList.add('collapsed');
        if (header) header.classList.add('collapsed');
    }
}

async function fetchPriceHistory(timeframe) {
    const tf = timeframe || currentChartTimeframe || '1h';
    try {
        const res = await fetch(`${API_BASE}/api/history?timeframe=${tf}`);
        if (res.ok) {
            const data = await res.json();
            if (data.success && Array.isArray(data.history)) {
                return data.history;
            }
        }
    } catch (_) {
        /* backend offline */
    }
    return [];
}

function destroyPriceChart() {
    if (chartResizeHandler) {
        window.removeEventListener('resize', chartResizeHandler);
        chartResizeHandler = null;
    }
    if (lwChart) {
        lwChart.remove();
        lwChart = null;
    }
}

function setPriceChartTimeframe(tf) {
    if (!CHART_RANGE_MS[tf]) return;
    currentChartTimeframe = tf;
    document.querySelectorAll('.timeframe-btn').forEach((btn) => {
        btn.classList.toggle('active', btn.dataset.tf === tf);
    });
    refreshPriceChart();
}

function buildCandles(items) {
    return items
        .map((item) => {
            const t = item.timestamp ? Math.floor(new Date(item.timestamp).getTime() / 1000) : null;
            if (!t || isNaN(t) || t <= 0) return null;
            const o = parseFloat(item.open);
            const h = parseFloat(item.high);
            const l = parseFloat(item.low);
            const c = parseFloat(item.close);
            if (!isFinite(o) || !isFinite(h) || !isFinite(l) || !isFinite(c)) return null;
            return { time: t, open: o, high: h, low: l, close: c };
        })
        .filter(Boolean)
        .sort((a, b) => a.time - b.time);
}

function calculateEMA(candles, period) {
    const ema = [];
    const multiplier = 2 / (period + 1);
    for (let i = 0; i < candles.length; i++) {
        if (i < period - 1) {
            ema.push({ time: candles[i].time, value: null });
        } else if (i === period - 1) {
            let sum = 0;
            for (let j = 0; j < period; j++) sum += candles[j].close;
            ema.push({ time: candles[i].time, value: sum / period });
        } else {
            const prevEma = ema[i - 1].value;
            ema.push({ time: candles[i].time, value: (candles[i].close * multiplier) + (prevEma * (1 - multiplier)) });
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
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Biblioteca lightweight-charts não carregou.'; }
        return;
    }

    if (!rawPriceHistory || rawPriceHistory.length === 0) {
        destroyPriceChart();
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Sem dados. Verifique se o backend está rodando.'; }
        if (statusEl) statusEl.textContent = '';
        return;
    }

    const candles = buildCandles(rawPriceHistory);

    if (candles.length === 0) {
        destroyPriceChart();
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Dados recebidos mas sem candles válidos.'; }
        if (statusEl) statusEl.textContent = '';
        return;
    }

    if (emptyEl) emptyEl.classList.add('hidden');

    const w = container.clientWidth || 800;
    destroyPriceChart();

    try {
        lwChart = LW.createChart(container, {
            width: w,
            height: 320,
            layout: {
                background: { type: 'solid', color: 'rgba(15, 15, 35, 0.92)' },
                textColor: '#9ca3af',
                fontFamily: "'Inter', sans-serif"
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.06)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.06)' }
            },
            crosshair: { mode: LW.CrosshairMode ? LW.CrosshairMode.Normal : 0 },
            rightPriceScale: { borderColor: 'rgba(255, 255, 255, 0.1)', scaleMargins: { top: 0.08, bottom: 0.08 } },
            timeScale: { borderColor: 'rgba(255, 255, 255, 0.1)', timeVisible: true, secondsVisible: false },
            localization: { priceFormatter: (p) => '$' + p.toFixed(4) }
        });

        const series = lwChart.addCandlestickSeries({
            upColor: '#34d399', downColor: '#f87171',
            borderUpColor: '#34d399', borderDownColor: '#f87171',
            wickUpColor: '#34d399', wickDownColor: '#f87171'
        });
        series.setData(candles);

        const ema9Data = calculateEMA(candles, 9).filter(d => d.value !== null);
        const ema9Series = lwChart.addLineSeries({ color: '#fbbf24', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        ema9Series.setData(ema9Data);

        const ema21Data = calculateEMA(candles, 21).filter(d => d.value !== null);
        const ema21Series = lwChart.addLineSeries({ color: '#f472b6', lineWidth: 1, priceLineVisible: false, lastValueVisible: false });
        ema21Series.setData(ema21Data);

        lwChart.timeScale().fitContent();

        chartResizeHandler = () => {
            if (!lwChart) return;
            lwChart.applyOptions({ width: container.clientWidth || 800, height: 320 });
        };
        window.addEventListener('resize', chartResizeHandler);

    } catch (err) {
        console.error('Erro ao desenhar gráfico:', err);
        if (emptyEl) { emptyEl.classList.remove('hidden'); emptyEl.textContent = 'Erro ao renderizar: ' + err.message; }
        return;
    }

    const tf = currentChartTimeframe;
    const firstOpen = candles[0].open;
    const lastClose = candles[candles.length - 1].close;
    const delta = lastClose - firstOpen;
    const deltaPct = firstOpen !== 0 ? (delta / firstOpen) * 100 : 0;
    if (statusEl) {
        statusEl.textContent =
            `CoinEx · ${candles.length} velas (${tf}) · O→F: ${delta >= 0 ? '+' : ''}${delta.toFixed(6)} (${delta >= 0 ? '+' : ''}${deltaPct.toFixed(2)}%) · EMA9/21`;
    }
}

async function refreshPriceChart() {
    rawPriceHistory = await fetchPriceHistory(currentChartTimeframe);
    renderPriceChart();
}

async function safeFetch(url, options = {}) {
    let response;
    try {
        response = await fetch(url, options);
    } catch (error) {
        throw new Error('Backend não está rodando. Execute: python3 backend/wallet.py');
    }

    const text = await response.text();
    let data;
    try {
        data = JSON.parse(text);
    } catch (_) {
        const preview = text.substring(0, 120).replace(/\n/g, ' ');
        throw new Error(`Resposta inválida do servidor (não é JSON). Status ${response.status}. Início: ${preview}`);
    }

    return { ok: response.ok, status: response.status, data };
}

async function fetchOsmoPrice() {
    const { ok, data } = await safeFetch(`${API_BASE}/api/price`);
    if (!ok) throw new Error('Backend não está respondendo. Inicie o servidor: python3 backend/wallet.py');
    if (!data.success) throw new Error(data.error || 'Erro ao buscar preço');
    return data.price;
}

async function updatePrice() {
    const priceElement = document.getElementById('price');
    const statusElement = document.getElementById('status');

    try {
        priceElement.textContent = '...';
        statusElement.textContent = 'Carregando...';
        const price = await fetchOsmoPrice();
        priceElement.textContent = price.toFixed(4);
        statusElement.textContent = `Atualizado em: ${new Date().toLocaleString('pt-BR')}`;
        await refreshPriceChart();
    } catch (error) {
        priceElement.textContent = 'Erro';
        statusElement.textContent = 'Erro: ' + error.message;
    }
}

function startAutoUpdate() {
    if (updateInterval) clearInterval(updateInterval);
    updatePrice();
    updateInterval = setInterval(updatePrice, 60000);
}

async function fetchPositionSignal() {
    // const signalDiv  = document.getElementById('positionSignal');
    const signalText = document.getElementById('positionText');

    try {
        const response = await fetch(`${API_BASE}/api/ai/position?timeframe=${currentChartTimeframe}`);
        const data = await response.json();

        if (data.success) {
            // signalDiv.style.display = 'flex';
            signalText.textContent = data.signal;
            signalText.className = 'position-text ' + data.signal.toLowerCase();
        } else {
            // signalDiv.style.display = 'none';
        }
    } catch (error) {
        console.error('Erro ao buscar sinal de posição:', error);
        // signalDiv.style.display = 'none';
    }
}

async function analyzeHistory() {
    const analysisDiv    = document.getElementById('analysis');
    const analysisContent = document.getElementById('analysisContent');
    const btnAi          = document.getElementById('btnAnalyzeAi');

    function mountLoadingUi(subtitle) {
        analysisContent.innerHTML = `
            <div class="ai-loading-wrap" id="aiLoadingState">
                <div class="loader"></div>
                <div class="ai-loading-text">
                    <strong class="ai-loading-title">Análise com IA</strong>
                    <p class="ai-loading-sub" id="aiLoadingSub">${subtitle}</p>
                </div>
            </div>
            <div id="aiStreamWrap" class="ai-stream-container" style="display:none;">
                <div class="ai-stream-badge" id="aiStreamBadge"><span class="ai-dot-pulse"></span> <span id="aiStreamBadgeText">Recebendo em tempo real</span></div>
                <div class="ai-response" id="aiStreamBody"></div>
            </div>`;
    }

    function setLoadingSub(text) {
        const el = document.getElementById('aiLoadingSub');
        if (el) el.textContent = text;
    }

    function revealStreamUi() {
        const loadEl = document.getElementById('aiLoadingState');
        const wrapEl = document.getElementById('aiStreamWrap');
        if (loadEl) loadEl.style.display = 'none';
        if (wrapEl) wrapEl.style.display = 'block';
    }

    function markStreamDone() {
        const badge     = document.getElementById('aiStreamBadge');
        const badgeText = document.getElementById('aiStreamBadgeText');
        if (badge) badge.classList.add('done');
        if (badgeText) badgeText.textContent = 'Resposta concluída';
    }

    try {
        if (btnAi) btnAi.disabled = true;
        analysisDiv.style.display = 'block';
        mountLoadingUi('Conectando à IA…');
        analysisDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        const aiResponse = await fetch(`${API_BASE}/api/ai/analyze?timeframe=${currentChartTimeframe}`, {
            method: 'GET',
            headers: { Accept: 'text/event-stream', 'Cache-Control': 'no-cache' },
            cache: 'no-store'
        });

        if (!aiResponse.ok) {
            const errText = await aiResponse.text();
            throw new Error(`API IA retornou HTTP ${aiResponse.status}. ${errText.slice(0, 280)}`);
        }

        if (!aiResponse.body) {
            throw new Error('Resposta da IA sem corpo (streaming indisponível neste navegador?)');
        }

        setLoadingSub('Aguardando o primeiro token da resposta…');

        const reader = aiResponse.body.getReader();
        const decoder = new TextDecoder();
        let aiAnalysis = '';
        let sseBuffer = '';
        let firstTokenReceived = false;
        const aiResponseDiv = document.getElementById('aiStreamBody');

        function parseSseDataPayload(dataStr) {
            if (dataStr === '[DONE]') return;
            let json;
            try { json = JSON.parse(dataStr); } catch { return; }
            if (json.error) {
                const msg = typeof json.error === 'string' ? json.error : json.error.message || JSON.stringify(json.error);
                throw new Error(msg + (json.code ? ' (código ' + json.code + ')' : ''));
            }
            const content = json.choices?.[0]?.delta?.content || '';
            if (content) {
                if (!firstTokenReceived) { firstTokenReceived = true; revealStreamUi(); }
                aiAnalysis += content;
                if (aiResponseDiv) {
                    try { aiResponseDiv.innerHTML = marked.parse(aiAnalysis); }
                    catch (mdErr) { aiResponseDiv.textContent = aiAnalysis; }
                }
            }
        }

        while (true) {
            const { done, value } = await reader.read();
            sseBuffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            const lines = sseBuffer.split('\n');
            sseBuffer = lines.pop() || '';
            for (let line of lines) {
                line = line.replace(/\r$/, '');
                if (!line.startsWith('data: ')) continue;
                const data = line.slice(6).trim();
                if (data) parseSseDataPayload(data);
            }
            if (done) {
                if (sseBuffer.trim()) {
                    const last = sseBuffer.replace(/\r$/, '');
                    if (last.startsWith('data: ')) parseSseDataPayload(last.slice(6).trim());
                }
                break;
            }
        }

        if (firstTokenReceived) markStreamDone();
        if (!aiAnalysis.trim()) {
            analysisContent.innerHTML = '<p style="color: #9ca3af;">A IA não devolveu texto. Verifique se o token HuggingFace está configurado no .env</p>';
        }

        await fetchPositionSignal();
    } catch (error) {
        analysisContent.innerHTML =
            '<p style="color: #ef4444;">Erro ao gerar análise: ' + (error?.message || String(error)) + '</p>';
    } finally {
        if (btnAi) btnAi.disabled = false;
    }
}

// ==================== WALLET ====================

async function loadWallets() {
    const walletSelect = document.getElementById('walletSelect');
    try {
        const { ok, data } = await safeFetch(`${API_BASE}/api/wallets`);
        if (!ok) {
            walletSelect.innerHTML = '<option value="">Backend offline</option>';
            return;
        }
        if (!data.success) return;

        walletSelect.innerHTML = '<option value="">-- Selecione --</option>';
        data.wallets.forEach(wallet => {
            const option = document.createElement('option');
            option.value = wallet.address;
            option.textContent = `${wallet.name} (${wallet.address.substring(0, 12)}...)`;
            walletSelect.appendChild(option);
        });

        // Restaura a carteira salva anteriormente
        const saved = localStorage.getItem(STORAGE_KEY_WALLET);
        if (saved) {
            walletSelect.value = saved;
            if (walletSelect.value === saved) {
                loadBalances();
            } else {
                // Endereço salvo não existe mais na lista
                localStorage.removeItem(STORAGE_KEY_WALLET);
            }
        }
    } catch (error) {
        console.error('Erro ao carregar carteiras:', error);
        walletSelect.innerHTML = '<option value="">Backend offline - Execute: python3 backend/wallet.py</option>';
    }
}

async function loadBalances() {
    const walletSelect   = document.getElementById('walletSelect');
    const selectedAddress = walletSelect.value;
    if (!selectedAddress) return;

    // Persiste a seleção
    localStorage.setItem(STORAGE_KEY_WALLET, selectedAddress);

    const balancesDiv = document.getElementById('balances');

    try {
        balancesDiv.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loader"></div></div>';
        const { ok, data } = await safeFetch(`${API_BASE}/api/balance/${selectedAddress}`);

        if (!ok || !data.success) {
            balancesDiv.innerHTML = `<p style="color: #ef4444; text-align: center;">Erro: ${data?.error || 'Erro ao carregar saldos'}</p>`;
            return;
        }

        if (data.balances && data.balances.length > 0) {
            let html = '';
            data.balances.forEach(balance => {
                let denom = balance.denom;
                let displayDenom;
                if (denom === 'uosmo') {
                    displayDenom = 'OSMO';
                } else if (denom.startsWith('ibc/')) {
                    displayDenom = 'IBC/' + denom.substring(4, 12) + '...';
                } else if (denom.startsWith('gamm/pool/')) {
                    displayDenom = 'Pool #' + denom.split('/')[2];
                } else {
                    displayDenom = denom.substring(0, 20);
                }
                const amount = (parseInt(balance.amount) / 1000000).toFixed(6);
                html += `
                    <div class="balance-item">
                        <span class="balance-denom" title="${denom}">${displayDenom}</span>
                        <span class="balance-amount">${amount}</span>
                    </div>`;
            });
            balancesDiv.innerHTML = html;
        } else {
            balancesDiv.innerHTML = '<p style="color: #9ca3af; text-align: center;">Nenhum saldo encontrado</p>';
        }
    } catch (error) {
        console.error('Erro ao carregar saldos:', error);
        balancesDiv.innerHTML = `<p style="color: #ef4444; text-align: center;">Erro: ${error.message}</p>`;
    }
}


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
                `Tolerância slippage: <span class="gas-val">${data.slippage_pct}%</span>`;
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
    const fromToken      = document.getElementById('swapFrom').value;
    const toToken        = document.getElementById('swapTo').value;
    const amount         = document.getElementById('swapAmount').value;
    const selectedAddress = document.getElementById('walletSelect').value;
    const statusDiv      = document.getElementById('swapStatus');

    if (!amount || parseFloat(amount) <= 0) {
        statusDiv.textContent = 'Digite uma quantidade válida';
        statusDiv.style.color = '#ef4444';
        return;
    }

    if (!selectedAddress) {
        statusDiv.textContent = 'Selecione uma carteira primeiro';
        statusDiv.style.color = '#ef4444';
        return;
    }

    if (!confirm(`Confirma o swap de ${amount} ${fromToken === 'uosmo' ? 'OSMO' : 'USDC'}?`)) return;

    try {
        statusDiv.textContent = 'Executando swap...';
        statusDiv.style.color = '#9ca3af';

        const amountMicro = Math.floor(parseFloat(amount) * 1000000);
        const response = await fetch(`${API_BASE}/api/swap/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from: fromToken, to: toToken, amount: amountMicro, address: selectedAddress })
        });
        const data = await response.json();

        if (data.success) {
            statusDiv.textContent = 'Swap executado com sucesso!';
            statusDiv.style.color = '#10b981';
            setTimeout(() => {
                loadBalances();
                closeSwapModal();
            }, 1500);
        } else {
            statusDiv.textContent = 'Erro: ' + data.error;
            statusDiv.style.color = '#ef4444';
        }
    } catch (error) {
        statusDiv.textContent = 'Erro ao executar: ' + error.message;
        statusDiv.style.color = '#ef4444';
    }
}

window.addEventListener('load', () => {
    startAutoUpdate();
    loadWallets();
    refreshPriceChart();
    chartRefreshTimer = setInterval(refreshPriceChart, 30000);
    
    // Restaura o estado do gráfico
    const savedExpanded = localStorage.getItem(STORAGE_KEY_CHART_EXPANDED);
    if (savedExpanded !== null) {
        chartExpanded = savedExpanded === 'true';
        if (!chartExpanded) {
            const content = document.getElementById('chartContent');
            const timeframes = document.getElementById('chartTimeframes');
            const caret = document.getElementById('chartToggleIcon');
            const header = document.querySelector('.chart-header');
            content.classList.add('collapsed');
            timeframes.style.display = 'none';
            if (caret) caret.classList.add('collapsed');
            if (header) header.classList.add('collapsed');
        }
    }
});

window.addEventListener('beforeunload', () => {
    if (chartRefreshTimer) clearInterval(chartRefreshTimer);
});
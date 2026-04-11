let updateInterval = null;
let lwChart = null;
let chartResizeHandler = null;
let rawPriceHistory = [];
let currentChartTimeframe = '15m';
let chartRefreshTimer = null;

const CHART_RANGE_MS = {
    '1m': 60 * 1000,
    '15m': 15 * 60 * 1000,
    '1h': 60 * 60 * 1000
};

/** Tamanho de cada vela (ms) conforme o período do gráfico */
const CANDLE_BUCKET_MS = {
    '1m': 10 * 1000,
    '15m': 60 * 1000,
    '1h': 5 * 60 * 1000
};

const CANDLE_BUCKET_LABEL = {
    '1m': '10s',
    '15m': '1 min',
    '1h': '5 min'
};

const API_BASE = `${window.location.protocol}//${window.location.hostname}:5000`;

async function fetchPriceHistory(timeframe) {
    const tf = timeframe || currentChartTimeframe || '15m';
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

/** Converte rawPriceHistory (items com open/high/low/close/timestamp) em candles para LightweightCharts */
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
            `CoinEx · ${candles.length} velas (${tf}) · O→F: ${delta >= 0 ? '+' : ''}${delta.toFixed(6)} (${delta >= 0 ? '+' : ''}${deltaPct.toFixed(2)}%)`;
    }
}

async function refreshPriceChart() {
    rawPriceHistory = await fetchPriceHistory(currentChartTimeframe);
    renderPriceChart();
}

// Função auxiliar para fazer fetch com tratamento de erros
async function safeFetch(url, options = {}) {
    let response;

    try {
        response = await fetch(url, options);
    } catch (error) {
        // Falha de rede: backend offline ou CORS bloqueando
        throw new Error('Backend não está rodando. Execute: python3 backend/wallet.py');
    }

    // Lê o corpo como texto primeiro para poder inspecionar em caso de erro
    const text = await response.text();

    let data;
    try {
        data = JSON.parse(text);
    } catch (_) {
        // O servidor respondeu mas não é JSON válido (ex: página de erro HTML do Flask)
        const preview = text.substring(0, 120).replace(/\n/g, ' ');
        throw new Error(`Resposta inválida do servidor (não é JSON). Status ${response.status}. Início da resposta: ${preview}`);
    }

    return { ok: response.ok, status: response.status, data };
}

// Função para buscar o preço do OSMO via backend Python (atualização em tempo real)
async function fetchOsmoPrice() {
    try {
        const { ok, data } = await safeFetch(`${API_BASE}/api/price`);
        
        if (!ok) {
            throw new Error('Backend não está respondendo. Inicie o servidor: python3 backend/wallet.py');
        }
        
        if (!data.success) {
            throw new Error(data.error || 'Erro ao buscar preço');
        }
        
        return data.price;
    } catch (error) {
        console.error('Erro ao buscar preço:', error);
        throw error;
    }
}

// Função para atualizar o preço na interface
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

// Iniciar atualização automática
function startAutoUpdate() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    
    updatePrice(); // Atualiza imediatamente
    updateInterval = setInterval(updatePrice, 60000); // Atualiza a cada 1 minuto
}

// Função para analisar o histórico com IA (loading até o 1º token; resposta em stream SSE)
async function analyzeHistory() {
    const analysisDiv = document.getElementById('analysis');
    const analysisContent = document.getElementById('analysisContent');
    const btnAi = document.getElementById('btnAnalyzeAi');

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
        if (el) {
            el.textContent = text;
        }
    }

    function revealStreamUi() {
        const loadEl = document.getElementById('aiLoadingState');
        const wrapEl = document.getElementById('aiStreamWrap');
        if (loadEl) {
            loadEl.style.display = 'none';
        }
        if (wrapEl) {
            wrapEl.style.display = 'block';
        }
    }

    function markStreamDone() {
        const badge = document.getElementById('aiStreamBadge');
        const badgeText = document.getElementById('aiStreamBadgeText');
        if (badge) {
            badge.classList.add('done');
        }
        if (badgeText) {
            badgeText.textContent = 'Resposta concluída';
        }
    }

    try {
        if (btnAi) {
            btnAi.disabled = true;
        }
        analysisDiv.style.display = 'block';
        mountLoadingUi('Carregando histórico de preços…');
        analysisDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

        const history = await fetchPriceHistory(currentChartTimeframe);

        if (!history || history.length === 0) {
            analysisContent.innerHTML = '<p>Nenhum dado disponível para análise.</p>';
            return;
        }

        setLoadingSub('Montando o prompt e conectando à IA…');

        const prices = history.map((item) => item.price);
        const currentPrice = prices[0];
        const oldestPrice = prices[prices.length - 1];
        const maxPrice = Math.max(...prices);
        const minPrice = Math.min(...prices);
        const avgPrice = prices.reduce((a, b) => a + b, 0) / prices.length;

        const prompt = `Analise os seguintes dados de preço da criptomoeda OSMO (Osmosis):

Dados do histórico:
- Total de registros: ${history.length}
- Preço atual: ${currentPrice.toFixed(6)}
- Preço mais antigo: ${oldestPrice.toFixed(6)}
- Preço máximo: ${maxPrice.toFixed(6)}
- Preço mínimo: ${minPrice.toFixed(6)}
- Preço médio: ${avgPrice.toFixed(6)}

Últimos 10 preços: ${prices.slice(0, 10).map((p) => p.toFixed(6)).join(', ')}

Por favor, forneça uma análise detalhada incluindo:
1. Tendência geral do preço
2. Volatilidade observada
3. Pontos de atenção
4. Recomendações para investidores
5. Análise técnica básica

Responda em português de forma clara e objetiva.`;

        setLoadingSub('Aguardando o servidor… (stream SSE ativo)');

        const aiResponse = await fetch(`${API_BASE}/api/ai/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                Accept: 'text/event-stream',
                'Cache-Control': 'no-cache'
            },
            cache: 'no-store',
            body: JSON.stringify({
                model: 'Qwen/Qwen3-Coder-Next:novita',
                stream: true,
                messages: [
                    {
                        role: 'system',
                        content:
                            'Você é um analista financeiro especializado em criptomoedas. Forneça análises técnicas detalhadas, objetivas e profissionais. Use formatação markdown para organizar suas respostas com títulos, listas e destaques. Seja claro e direto nas suas recomendações.'
                    },
                    {
                        role: 'user',
                        content: prompt
                    }
                ],
                temperature: 0.7
            })
        });

        if (!aiResponse.ok) {
            const errText = await aiResponse.text();
            throw new Error(`API IA retornou HTTP ${aiResponse.status}. ${errText.slice(0, 280)}`);
        }

        if (!aiResponse.body) {
            throw new Error('Resposta da IA sem corpo (streaming indisponível neste navegador?)');
        }

        setLoadingSub('Conectado. Aguardando o primeiro token da resposta…');

        const reader = aiResponse.body.getReader();
        const decoder = new TextDecoder();
        let aiAnalysis = '';
        let sseBuffer = '';
        let firstTokenReceived = false;

        const aiResponseDiv = document.getElementById('aiStreamBody');

        function parseSseDataPayload(dataStr) {
            if (dataStr === '[DONE]') {
                return;
            }
            let json;
            try {
                json = JSON.parse(dataStr);
            } catch {
                return;
            }
            if (json.error) {
                const msg =
                    typeof json.error === 'string'
                        ? json.error
                        : json.error.message || JSON.stringify(json.error);
                throw new Error(msg + (json.code ? ' (código ' + json.code + ')' : ''));
            }
            const content =
                json.choices && json.choices[0] && json.choices[0].delta
                    ? json.choices[0].delta.content || ''
                    : '';
            if (content) {
                if (!firstTokenReceived) {
                    firstTokenReceived = true;
                    revealStreamUi();
                }
                aiAnalysis += content;
                if (aiResponseDiv) {
                    try {
                        aiResponseDiv.innerHTML = marked.parse(aiAnalysis);
                    } catch (mdErr) {
                        aiResponseDiv.textContent = aiAnalysis;
                        console.warn('marked:', mdErr);
                    }
                }
            }
        }

        while (true) {
            const { done, value } = await reader.read();
            sseBuffer += decoder.decode(value || new Uint8Array(), { stream: !done });
            const lines2 = sseBuffer.split('\n');
            sseBuffer = lines2.pop() || '';

            for (let line of lines2) {
                line = line.replace(/\r$/, '');
                if (!line.startsWith('data: ')) {
                    continue;
                }
                const data = line.slice(6).trim();
                if (!data) {
                    continue;
                }
                parseSseDataPayload(data);
            }

            if (done) {
                if (sseBuffer.trim()) {
                    const lastLine = sseBuffer.replace(/\r$/, '');
                    if (lastLine.startsWith('data: ')) {
                        const data = lastLine.slice(6).trim();
                        if (data) {
                            parseSseDataPayload(data);
                        }
                    }
                }
                break;
            }
        }

        if (firstTokenReceived) {
            markStreamDone();
        }

        if (!aiAnalysis.trim()) {
            analysisContent.innerHTML =
                '<p style="color: #9ca3af;">A IA não devolveu texto. Abra o console (F12), confira se o backend em <code>' +
                API_BASE +
                '</code> está no ar e se <code>HF_API_TOKEN</code> ou <code>backend/hf_token.txt</code> está configurado.</p>';
        }
    } catch (error) {
        analysisContent.innerHTML =
            '<p style="color: #ef4444;">Erro ao gerar análise: ' +
            (error && error.message ? error.message : String(error)) +
            '</p><p style="color:#6b7280;font-size:0.85rem;margin-top:8px;">Dica: o backend Python precisa estar em <code>' +
            API_BASE +
            '</code> com <code>HF_API_TOKEN</code> ou <code>backend/hf_token.txt</code>.</p>';
    } finally {
        if (btnAi) {
            btnAi.disabled = false;
        }
    }
}

// Função para carregar lista de carteiras
async function loadWallets() {
    const walletSelect = document.getElementById('walletSelect');
    
    try {
        const { ok, data } = await safeFetch(`${API_BASE}/api/wallets`);
        
        if (!ok) {
            console.error('Backend não está respondendo');
            walletSelect.innerHTML = '<option value="">Backend offline</option>';
            return;
        }
        
        if (!data.success) {
            console.error('Erro ao carregar carteiras:', data.error);
            return;
        }
        
        // Limpa e adiciona as opções
        walletSelect.innerHTML = '<option value="">-- Selecione --</option>';
        
        data.wallets.forEach(wallet => {
            const option = document.createElement('option');
            option.value = wallet.address;
            option.textContent = `${wallet.name} (${wallet.address.substring(0, 12)}...)`;
            walletSelect.appendChild(option);
        });
        
    } catch (error) {
        console.error('Erro ao carregar carteiras:', error);
        walletSelect.innerHTML = '<option value="">Backend offline - Execute: python3 backend/wallet.py</option>';
    }
}

// Função para carregar saldos da wallet
async function loadBalances() {
    const walletSelect = document.getElementById('walletSelect');
    const selectedAddress = walletSelect.value;
    
    if (!selectedAddress) {
        return;
    }
    
    const balancesDiv = document.getElementById('balances');
    const addressDiv = document.getElementById('walletAddress');
    
    try {
        balancesDiv.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loader"></div></div>';
        
        const { ok, data } = await safeFetch(`${API_BASE}/api/balance/${selectedAddress}`);
        
        if (!ok || !data.success) {
            balancesDiv.innerHTML = `<p style="color: #ef4444; text-align: center;">Erro: ${data?.error || 'Erro ao carregar saldos'}</p>`;
            return;
        }
        
        // Mostra o endereço
        addressDiv.textContent = data.address;
        
        // Mostra os saldos
        if (data.balances && data.balances.length > 0) {
            let html = '';
            data.balances.forEach(balance => {
                let denom = balance.denom;
                let displayDenom = denom;
                
                // Formata o nome do token
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
                    </div>
                `;
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

// Função para simular swap
async function simulateSwap() {
    const fromToken = document.getElementById('swapFrom').value;
    const toToken = document.getElementById('swapTo').value;
    const amount = document.getElementById('swapAmount').value;
    const statusDiv = document.getElementById('swapStatus');
    const estimateDiv = document.getElementById('swapEstimate');
    const outputDiv = document.getElementById('swapOutput');
    
    if (!amount || parseFloat(amount) <= 0) {
        statusDiv.textContent = 'Digite uma quantidade válida';
        statusDiv.style.color = '#ef4444';
        return;
    }
    
    try {
        statusDiv.textContent = 'Simulando...';
        statusDiv.style.color = '#9ca3af';
        estimateDiv.style.display = 'none';
        
        // Converte para microunits (1 token = 1,000,000 micro)
        const amountMicro = Math.floor(parseFloat(amount) * 1000000);
        
        const response = await fetch(`${API_BASE}/api/swap/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from: fromToken, to: toToken, amount: amountMicro })
        });
        const data = await response.json();
        
        if (data.success) {
            const outputAmount = (parseInt(data.token_out_amount) / 1000000).toFixed(6);
            outputDiv.textContent = outputAmount + ' ' + (toToken === 'uosmo' ? 'OSMO' : 'USDC');
            estimateDiv.style.display = 'block';
            statusDiv.textContent = 'Simulação concluída';
            statusDiv.style.color = '#10b981';
        } else {
            statusDiv.textContent = 'Erro: ' + data.error;
            statusDiv.style.color = '#ef4444';
        }
        
    } catch (error) {
        console.error('Erro ao simular swap:', error);
        statusDiv.textContent = 'Erro ao simular: ' + error.message;
        statusDiv.style.color = '#ef4444';
    }
}

// Função para executar swap
async function executeSwap() {
    const fromToken = document.getElementById('swapFrom').value;
    const toToken = document.getElementById('swapTo').value;
    const amount = document.getElementById('swapAmount').value;
    const walletSelect = document.getElementById('walletSelect');
    const selectedAddress = walletSelect.value;
    const statusDiv = document.getElementById('swapStatus');
    
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
    
    if (!confirm(`Confirma o swap de ${amount} ${fromToken === 'uosmo' ? 'OSMO' : 'USDC'}?`)) {
        return;
    }
    
    try {
        statusDiv.textContent = 'Executando swap...';
        statusDiv.style.color = '#9ca3af';
        
        const amountMicro = Math.floor(parseFloat(amount) * 1000000);
        
        const response = await fetch(`${API_BASE}/api/swap/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                from: fromToken, 
                to: toToken, 
                amount: amountMicro,
                address: selectedAddress
            })
        });
        const data = await response.json();
        
        if (data.success) {
            statusDiv.textContent = 'Swap executado com sucesso!';
            statusDiv.style.color = '#10b981';
            // Atualiza os saldos
            setTimeout(loadBalances, 2000);
        } else {
            statusDiv.textContent = 'Erro: ' + data.error;
            statusDiv.style.color = '#ef4444';
        }
        
    } catch (error) {
        console.error('Erro ao executar swap:', error);
        statusDiv.textContent = 'Erro ao executar: ' + error.message;
        statusDiv.style.color = '#ef4444';
    }
}

// Registrar Service Worker para PWA
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then((registration) => {
                console.log('Service Worker registrado:', registration.scope);
            })
            .catch((error) => {
                console.log('Falha ao registrar Service Worker:', error);
            });
    });
}

// Função para mostrar o popup manualmente
function showInstallPopup() {
    const installPopup = document.getElementById('installPopup');
    if (installPopup) {
        installPopup.classList.add('show');
    }
}

// PWA Install Prompt
let deferredPrompt;
const installPrompt = document.getElementById('installPrompt');
const installBtn = document.getElementById('installBtn');
const installClose = document.getElementById('installClose');
const installPopup = document.getElementById('installPopup');
const popupInstallBtn = document.getElementById('popupInstallBtn');
const popupCloseBtn = document.getElementById('popupCloseBtn');

window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt = e;
    console.log('beforeinstallprompt disparado');
    
    // Verifica se já foi instalado ou se o usuário já recusou
    const hasDeclined = localStorage.getItem('pwa-declined');
    const isInstalled = localStorage.getItem('pwa-installed');
    
    console.log('hasDeclined:', hasDeclined, 'isInstalled:', isInstalled);
    
    if (!hasDeclined && !isInstalled) {
        // Mostra o popup após 5 segundos
        setTimeout(() => {
            console.log('Mostrando popup de instalação');
            if (installPopup) {
                installPopup.classList.add('show');
            }
        }, 5000);
    }
});

// Verifica se já está instalado
if (window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true) {
    console.log('App já está instalado e rodando em modo standalone');
    localStorage.setItem('pwa-installed', 'true');
    // Esconde o botão de instalação se estiver em modo app
    const installHeader = document.querySelector('.header .btn');
    if (installHeader) {
        installHeader.style.display = 'none';
    }
} else {
    console.log('App não está instalado ou rodando no navegador');
    // Detecta Firefox
    const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
    console.log('Firefox detectado:', isFirefox);
    
    // Mostra o popup após 3 segundos se não estiver instalado
    setTimeout(() => {
        const hasDeclined = localStorage.getItem('pwa-declined');
        const isInstalled = localStorage.getItem('pwa-installed');
        if (!hasDeclined && !isInstalled) {
            console.log('Mostrando popup (fallback)');
            showInstallPopup();
        }
    }, 3000);
}

// Botão do popup
if (popupInstallBtn) {
    popupInstallBtn.addEventListener('click', async () => {
        console.log('Botão de instalação clicado');
        
        const isFirefox = navigator.userAgent.toLowerCase().indexOf('firefox') > -1;
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent);
        
        if (!deferredPrompt) {
            console.log('Sem deferredPrompt, mostrando instruções');
            
            if (isFirefox) {
                // Instruções específicas para Firefox
                const msg = `Para instalar no Firefox:\n\n` +
                    `Desktop:\n` +
                    `1. Clique no ícone de três linhas (☰) no canto superior direito\n` +
                    `2. Clique em "Instalar"\n` +
                    `   ou\n` +
                    `3. Clique no ícone de instalação (⊕) na barra de endereço\n\n` +
                    `Android:\n` +
                    `1. Toque no menu (⋮)\n` +
                    `2. Toque em "Instalar"\n` +
                    `3. Confirme a instalação`;
                alert(msg);
            } else if (isIOS) {
                alert('Para instalar no iOS:\n\n1. Toque no botão Compartilhar (□↑)\n2. Role para baixo\n3. Toque em "Adicionar à Tela Inicial"');
            } else {
                alert('Para instalar:\n\n• Chrome/Edge: Menu (⋮) → Instalar quantum\n• Ou clique no ícone de instalação na barra de endereço');
            }
            
            // Fecha o popup após mostrar instruções
            if (installPopup) {
                installPopup.classList.remove('show');
            }
            return;
        }
        
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        
        console.log(`Usuário ${outcome === 'accepted' ? 'aceitou' : 'recusou'} a instalação`);
        
        if (outcome === 'accepted') {
            localStorage.setItem('pwa-installed', 'true');
        } else {
            localStorage.setItem('pwa-declined', 'true');
        }
        
        deferredPrompt = null;
        if (installPopup) {
            installPopup.classList.remove('show');
        }
    });
}

// Fechar popup
if (popupCloseBtn) {
    popupCloseBtn.addEventListener('click', () => {
        console.log('Popup fechado');
        if (installPopup) {
            installPopup.classList.remove('show');
        }
        localStorage.setItem('pwa-declined', 'true');
    });
}

// Fechar popup clicando fora
if (installPopup) {
    installPopup.addEventListener('click', (e) => {
        if (e.target === installPopup) {
            console.log('Popup fechado (clique fora)');
            installPopup.classList.remove('show');
            localStorage.setItem('pwa-declined', 'true');
        }
    });
}

// Botão do banner pequeno
if (installBtn) {
    installBtn.addEventListener('click', async () => {
        if (!deferredPrompt) {
            // Mostra o popup se não houver prompt
            if (installPopup) {
                installPopup.classList.add('show');
            }
            return;
        }
        
        deferredPrompt.prompt();
        const { outcome } = await deferredPrompt.userChoice;
        
        console.log(`Usuário ${outcome === 'accepted' ? 'aceitou' : 'recusou'} a instalação`);
        
        deferredPrompt = null;
        if (installPrompt) {
            installPrompt.classList.remove('show');
        }
    });
}

if (installClose) {
    installClose.addEventListener('click', () => {
        if (installPrompt) {
            installPrompt.classList.remove('show');
        }
    });
}

window.addEventListener('appinstalled', () => {
    console.log('PWA instalado com sucesso!');
    localStorage.setItem('pwa-installed', 'true');
    deferredPrompt = null;
    if (installPrompt) {
        installPrompt.classList.remove('show');
    }
    if (installPopup) {
        installPopup.classList.remove('show');
    }
});

// Inicialização ao carregar a página
window.addEventListener('load', () => {
    startAutoUpdate();
    loadWallets();
    refreshPriceChart();
    chartRefreshTimer = setInterval(refreshPriceChart, 30000);
});

window.addEventListener('beforeunload', () => {
    if (chartRefreshTimer) {
        clearInterval(chartRefreshTimer);
    }
});
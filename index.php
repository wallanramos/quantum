<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="description" content="Monitor de preços e trading OSMO/USDC">
    <meta name="theme-color" content="#0a0a0a">
    <title>quantum</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Mono:ital,wght@0,300;0,400;0,500;1,300&family=Syne:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #080808;
            --surface: #111111;
            --border: #1e1e1e;
            --border-subtle: #141414;
            --text: #e4e4e4;
            --text-muted: #999;
            --text-dim: #666;
            --accent: #c8f562;
            --accent-dim: rgba(200, 245, 98, 0.07);
            --accent-border: rgba(200, 245, 98, 0.18);
            --green: #3dffa0;
            --green-dim: rgba(61, 255, 160, 0.07);
            --red: #ff4d6a;
            --mono: 'DM Mono', monospace;
            --sans: 'Syne', sans-serif;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: var(--sans);
            background: var(--bg);
            min-height: 100vh;
            color: var(--text);
            overflow-x: hidden;
        }

        .app {
            max-width: 860px;
            margin: 0 auto;
            padding: 0 36px;
        }

        /* ── TOP BAR ── */
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 30px 0 22px;
            border-bottom: 1px solid var(--border);
        }

        .wordmark {
            font-family: var(--sans);
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--text);
        }

        .wordmark em {
            font-style: normal;
            color: var(--accent);
        }

        /* ── SECTIONS ── */
        .section {
            padding: 24px 0;
            border-bottom: 1px solid var(--border);
        }

        .section:last-child { border-bottom: none; }

        .section-label {
            font-family: var(--mono);
            font-size: 0.63rem;
            font-weight: 400;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 22px;
        }

        /* ── PRICE ── */
        .price-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 18px;
        }

        .price-left {
            display: flex;
            align-items: baseline;
            gap: 18px;
            flex-wrap: wrap;
            flex: 1;
            min-width: 0;
        }

        .price-main {
            font-family: var(--mono);
            font-size: 3.8rem;
            font-weight: 300;
            color: var(--text);
            letter-spacing: -0.03em;
            line-height: 1;
        }

        .price-main::before {
            content: '$';
            font-size: 1.3rem;
            color: var(--text-muted);
            vertical-align: 0.55em;
            margin-right: 2px;
        }

        .price-tag {
            font-family: var(--mono);
            font-size: 0.68rem;
            font-weight: 500;
            padding: 4px 9px;
            border-radius: 2px;
            background: var(--green-dim);
            color: var(--green);
            border: 1px solid rgba(61, 255, 160, 0.15);
        }

        .price-tag.negative {
            background: rgba(255, 77, 106, 0.07);
            color: var(--red);
            border-color: rgba(255, 77, 106, 0.14);
        }

        .status-line {
            font-family: var(--mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 10px;
        }

        /* ── BALANCES ── */
        .balance-list {
            margin-top: 28px;
        }

        .balance-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 13px 0;
            border-top: 1px solid var(--border-subtle);
            transition: opacity 0.15s;
        }

        .balance-item:hover { opacity: 0.6; }

        .balance-denom {
            font-family: var(--mono);
            font-size: 0.72rem;
            color: var(--text-muted);
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }

        .balance-amount {
            font-family: var(--mono);
            font-size: 0.9rem;
            color: var(--text);
        }

        .wallet-address {
            font-family: var(--mono);
            font-size: 0.62rem;
            color: var(--text-dim);
            margin-top: 16px;
            word-break: break-all;
            line-height: 1.6;
        }

        /* ── ACTIONS ── */
        .action-row {
            display: flex;
            gap: 10px;
            margin-top: 30px;
            flex-wrap: wrap;
        }

        /* ── BUTTONS ── */
        .btn {
            font-family: var(--sans);
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            border: none;
            cursor: pointer;
            padding: 12px 22px;
            border-radius: 2px;
            transition: all 0.15s ease;
        }

        .btn-ghost {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
        }

        .btn-ghost:hover { border-color: #3a3a3a; color: var(--text); }

        .btn-accent { background: var(--accent); color: #060606; }
        .btn-accent:hover { background: #d5ff70; transform: translateY(-1px); }
        .btn-accent:active { transform: none; }

        .btn:disabled { opacity: 0.25; cursor: not-allowed; transform: none !important; }

        /* ── SELECT ── */
        .select {
            appearance: none;
            background: transparent;
            background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%23444' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            border: 1px solid var(--border);
            border-radius: 2px;
            padding: 9px 34px 9px 13px;
            font-family: var(--mono);
            font-size: 0.72rem;
            color: var(--text-muted);
            cursor: pointer;
            transition: border-color 0.15s, color 0.15s;
        }

        .select:focus { outline: none; border-color: var(--accent-border); color: var(--text); }
        .select option { background: #111; color: var(--text); }

        /* ── CHART ── */
        .chart-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
            margin-bottom: 20px;
        }

        .chart-header.collapsed {
            margin-bottom: 0;
        }

        .chart-header-left {
            display: flex;
            align-items: center;
            gap: 20px;
            flex: 1;
            min-width: 0;
        }

        .chart-caret {
            font-family: var(--mono);
            font-size: 0.6rem;
            color: var(--text-dim);
            transition: transform 0.25s ease;
        }

        .chart-caret.collapsed { transform: rotate(-90deg); }

        .timeframes { display: flex; gap: 2px; }

        .timeframe-btn {
            font-family: var(--mono);
            font-size: 0.66rem;
            padding: 5px 11px;
            border: 1px solid transparent;
            border-radius: 2px;
            background: transparent;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.12s;
        }

        .timeframe-btn:hover { color: var(--text); border-color: var(--border); }

        .timeframe-btn.active {
            color: var(--accent);
            border-color: var(--accent-border);
            background: var(--accent-dim);
        }

        .chart-wrap { position: relative; height: 300px; }

        .chart-lw { width: 100%; height: 300px; }

        .chart-empty {
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: var(--mono);
            font-size: 0.72rem;
            color: var(--text-dim);
            pointer-events: none;
        }

        .chart-empty.hidden { display: none !important; }

        .chart-content {
            transition: max-height 0.3s ease, opacity 0.25s ease;
            overflow: hidden;
        }

        .chart-content.collapsed { 
            max-height: 0 !important; 
            opacity: 0;
            margin: 0;
            padding: 0;
        }

        /* ── ANALYSIS ── */
        .analysis-container { display: none; }

        .ai-stream-badge {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            font-family: var(--mono);
            font-size: 0.6rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--green);
            margin-bottom: 18px;
            padding: 5px 10px;
            border: 1px solid rgba(61, 255, 160, 0.18);
            border-radius: 2px;
            background: var(--green-dim);
        }

        .ai-stream-badge.done {
            color: var(--text-muted);
            border-color: var(--border);
            background: transparent;
        }

        .ai-dot-pulse {
            width: 5px; height: 5px;
            background: var(--green);
            border-radius: 50%;
            animation: aiPulse 1.2s ease-in-out infinite;
        }

        .ai-stream-badge.done .ai-dot-pulse { animation: none; background: var(--text-dim); }

        @keyframes aiPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.35; transform: scale(0.75); }
        }

        .ai-response {
            font-family: var(--mono);
            font-size: 0.8rem;
            color: #999;
            line-height: 1.85;
        }

        .ai-response h1, .ai-response h2, .ai-response h3 {
            font-family: var(--sans);
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text);
            margin: 22px 0 10px;
        }

        .ai-response p { margin-bottom: 10px; }
        .ai-response strong { color: var(--accent); font-weight: 500; }
        .ai-response ul, .ai-response ol { margin-left: 18px; margin-bottom: 10px; }
        .ai-response li { margin-bottom: 4px; }

        .ai-response code {
            background: rgba(200, 245, 98, 0.07);
            padding: 2px 5px;
            color: var(--accent);
            font-size: 0.9em;
        }

        .ai-loading-wrap {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 16px 0;
        }

        .loader {
            width: 14px; height: 14px;
            border: 1.5px solid var(--border);
            border-top-color: var(--accent);
            border-radius: 50%;
            animation: spin 0.7s linear infinite;
            flex-shrink: 0;
        }

        @keyframes spin { to { transform: rotate(360deg); } }

        .ai-loading-text {
            font-family: var(--mono);
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        /* ── MODAL ── */
        .modal-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.88);
            backdrop-filter: blur(16px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            padding: 24px;
        }

        .modal-overlay.show { display: flex; }

        .modal-content {
            background: #0e0e0e;
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 32px;
            width: 100%;
            max-width: 420px;
            animation: slideUp 0.18s ease;
        }

        @keyframes slideUp {
            from { transform: translateY(10px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        .modal-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 28px;
        }

        .modal-title {
            font-family: var(--sans);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
        }

        .modal-close {
            background: none;
            border: none;
            font-family: var(--mono);
            font-size: 1.1rem;
            color: var(--text-dim);
            cursor: pointer;
            padding: 2px 5px;
            transition: color 0.15s;
            line-height: 1;
        }

        .modal-close:hover { color: var(--text); }

        .input-group { margin-bottom: 18px; }

        .input-label {
            display: block;
            font-family: var(--mono);
            font-size: 0.6rem;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: var(--text-muted);
            margin-bottom: 7px;
        }

        .input, .modal-select {
            width: 100%;
            padding: 11px 14px;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: 2px;
            font-family: var(--mono);
            font-size: 0.82rem;
            color: var(--text);
            transition: border-color 0.15s;
        }

        .input:focus, .modal-select:focus {
            outline: none;
            border-color: var(--accent-border);
        }

        .input::placeholder { color: var(--text-dim); }

        .modal-select {
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%23444' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 12px center;
            cursor: pointer;
        }

        .modal-select option { background: #111; }

        .modal-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

        .swap-gas-info {
            font-family: var(--mono);
            font-size: 0.67rem;
            color: var(--text-muted);
            line-height: 1.7;
            padding: 14px 0;
            border-top: 1px solid var(--border-subtle);
            margin-bottom: 18px;
        }

        .gas-val { color: #f0b429; }

        .status-text {
            font-family: var(--mono);
            font-size: 0.67rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            line-height: 1.5;
        }

        .modal-actions { display: flex; gap: 10px; }
        .modal-actions .btn { flex: 1; }

        /* ── RESPONSIVE ── */
        @media (max-width: 600px) {
            .app { padding: 0 20px; }
            .price-main { font-size: 2.8rem; }
            .price-row { gap: 12px; }
            .btn { padding: 10px 18px; font-size: 0.7rem; }
            .modal-content { padding: 24px; }
            .modal-row { grid-template-columns: 1fr; }
            .chart-header { gap: 12px; }
            .chart-header-left { gap: 12px; flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <div class="app">

        <!-- TOP BAR -->
        <div class="topbar">
            <div class="wordmark">quan<em>t</em>um</div>
            <select id="walletSelect" class="select" onchange="loadBalances()">
                <option value="">selecione carteira</option>
            </select>
        </div>

        <!-- PRICE SECTION -->
        <div class="section">
            <div class="section-label">OSMO / USDC</div>
            <div class="price-row">
                <div class="price-left">
                    <div class="price-main" id="price">...</div>
                </div>
                <button class="btn btn-accent" onclick="openSwapModal()">Swap</button>
            </div>
            <div class="status-line" id="status">carregando dados...</div>

            <div id="balances" class="balance-list">
                <div style="padding: 14px 0; font-family: var(--mono); font-size: 0.7rem; color: var(--text-dim);">
                    nenhuma carteira selecionada
                </div>
            </div>

            <div class="action-row">
                <button type="button" class="btn btn-ghost" id="btnAnalyzeAi" onclick="analyzeHistory()">Análise IA</button>
            </div>
        </div>

        <!-- CHART SECTION -->
        <div class="section" id="chartCard">
            <div class="chart-header" onclick="toggleChart(event)">
                <div class="chart-header-left">
                    <div class="section-label" style="margin-bottom: 0;">Gráfico</div>
                    <div class="timeframes" id="chartTimeframes" role="group">
                        <button type="button" class="timeframe-btn" data-tf="1m" onclick="setPriceChartTimeframe('1m'); event.stopPropagation();">1m</button>
                        <button type="button" class="timeframe-btn active" data-tf="15m" onclick="setPriceChartTimeframe('15m'); event.stopPropagation();">15m</button>
                        <button type="button" class="timeframe-btn" data-tf="1h" onclick="setPriceChartTimeframe('1h'); event.stopPropagation();">1h</button>
                    </div>
                </div>
                <div class="chart-caret" id="chartToggleIcon">▼</div>
            </div>
            <div class="chart-content" id="chartContent">
                <div class="chart-wrap">
                    <div id="priceChartContainer" class="chart-lw" aria-label="Gráfico de candles OSMO"></div>
                    <div id="chartEmpty" class="chart-empty">carregando histórico...</div>
                </div>
                <div class="status-text" id="chartStatus"></div>
            </div>
        </div>

        <!-- ANALYSIS SECTION -->
        <div id="analysis" class="analysis-container">
            <div class="section">
                <div class="section-label">Análise de Mercado</div>
                <div id="analysisContent"></div>
            </div>
        </div>

    </div>

    <!-- SWAP MODAL -->
    <div id="swapModal" class="modal-overlay" onclick="closeSwapModal(event)">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Swap OSMO / USDC</div>
                <button class="modal-close" onclick="closeSwapModal()">&times;</button>
            </div>

            <div class="modal-row">
                <div class="input-group">
                    <label class="input-label">De</label>
                    <select id="swapFrom" class="modal-select">
                        <option value="uosmo">OSMO</option>
                        <option value="ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4">USDC</option>
                    </select>
                </div>
                <div class="input-group">
                    <label class="input-label">Para</label>
                    <select id="swapTo" class="modal-select">
                        <option value="ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4">USDC</option>
                        <option value="uosmo">OSMO</option>
                    </select>
                </div>
            </div>

            <div class="input-group">
                <label class="input-label">Quantidade</label>
                <input type="number" id="swapAmount" class="input" placeholder="0.000000" step="0.000001">
            </div>

            <div class="status-text" id="swapStatus"></div>

            <div id="swapGasInfo" class="swap-gas-info">
                <span id="swapGasLabel">carregando taxas...</span>
            </div>

            <div class="modal-actions">
                <button class="btn btn-ghost" onclick="closeSwapModal()">Cancelar</button>
                <button class="btn btn-accent" onclick="executeSwap()">Executar</button>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="osmo-price.js?v=<?php echo time(); ?>"></script>
</body>
</html>
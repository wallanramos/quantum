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
            --red-dim: rgba(255, 77, 106, 0.08);
            --red-border: rgba(255, 77, 106, 0.18);
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

        .app { max-width: 860px; margin: 0 auto; padding: 0 36px; }

        /* ── TOP BAR ── */
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 30px 0 22px;
            border-bottom: 1px solid var(--border);
            gap: 16px;
        }

        .wordmark {
            font-family: var(--sans);
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.22em;
            text-transform: uppercase;
            color: var(--text);
            flex-shrink: 0;
        }

        .wordmark em { font-style: normal; color: var(--accent); }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .wallet-actions {
            display: none;
            align-items: center;
            gap: 6px;
        }

        .wallet-actions.visible { display: flex; }

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

        .status-line {
            font-family: var(--mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            margin-top: 10px;
        }

        /* ── BALANCES ── */
        .balance-list { margin-top: 28px; }

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

        .btn-danger {
            background: transparent;
            border: 1px solid var(--red-border);
            color: var(--red);
        }

        .btn-danger:hover { background: var(--red-dim); border-color: var(--red); }

        .btn-icon { padding: 8px 12px; font-size: 0.85rem; line-height: 1; }

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

        .chart-header.collapsed { margin-bottom: 0; }

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

        /* ── MODAL BASE ── */
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
            min-height: 1.2em;
        }

        .modal-actions { display: flex; gap: 10px; }
        .modal-actions .btn { flex: 1; }

        /* ── WALLET MODAL ── */
        .wallet-modal-content { max-width: 460px; }

        .wallet-modal-tabs {
            display: flex;
            gap: 0;
            margin-bottom: 26px;
            border-bottom: 1px solid var(--border);
        }

        .wallet-tab {
            font-family: var(--mono);
            font-size: 0.66rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            padding: 8px 18px;
            background: transparent;
            border: none;
            color: var(--text-dim);
            cursor: pointer;
            border-bottom: 2px solid transparent;
            margin-bottom: -1px;
            transition: all 0.15s;
        }

        .wallet-tab:hover { color: var(--text-muted); }

        .wallet-tab.active {
            color: var(--accent);
            border-bottom-color: var(--accent);
        }

        .wallet-tab-panel { display: none; }
        .wallet-tab-panel.active { display: block; }

        .wallet-info-block {
            font-family: var(--mono);
            font-size: 0.7rem;
            color: var(--text-muted);
            line-height: 1.7;
            padding: 14px;
            background: rgba(255,255,255,0.02);
            border: 1px solid var(--border-subtle);
            border-radius: 2px;
            margin-bottom: 18px;
            word-break: break-all;
        }

        .wallet-info-block strong {
            color: var(--text-dim);
            display: block;
            font-size: 0.58rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            margin-bottom: 5px;
        }

        .wallet-warning {
            font-family: var(--mono);
            font-size: 0.65rem;
            color: var(--red);
            line-height: 1.65;
            padding: 12px 14px;
            border: 1px solid var(--red-border);
            border-radius: 2px;
            background: var(--red-dim);
            margin-bottom: 20px;
        }

        /* ── SCHEDULER ── */
        .scheduler-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: var(--mono);
            font-size: 0.62rem;
            letter-spacing: 0.1em;
            padding: 4px 10px;
            border: 1px solid var(--border);
            border-radius: 2px;
            color: var(--text-dim);
        }

        /* ── AI PHASES ── */
        .ai-phase {
            padding: 16px 0;
            border-bottom: 1px solid var(--border-subtle);
        }

        .ai-phase:last-child { border-bottom: none; }

        .ai-phase-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .ai-phase-icon {
            font-family: var(--mono);
            font-size: 0.75rem;
            color: var(--text-dim);
            width: 14px;
            flex-shrink: 0;
            transition: color 0.2s;
        }

        .ai-phase-label {
            font-family: var(--mono);
            font-size: 0.65rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            color: var(--text-muted);
            flex-shrink: 0;
        }

        .ai-phase-status {
            font-family: var(--mono);
            font-size: 0.65rem;
            color: var(--text-dim);
            margin-left: auto;
            text-align: right;
            transition: color 0.2s;
        }

        /* ── TOOL ITEMS ── */
        .ai-tools-list {
            margin-top: 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .ai-tool-item {
            display: flex;
            align-items: baseline;
            gap: 10px;
            padding: 8px 12px;
            border-radius: 2px;
            border: 1px solid var(--border-subtle);
            background: rgba(255,255,255,0.01);
        }

        .ai-tool-item.ai-tool-ok {
            border-color: rgba(61, 255, 160, 0.1);
            background: rgba(61, 255, 160, 0.03);
        }

        .ai-tool-item.ai-tool-error {
            border-color: var(--red-border);
            background: var(--red-dim);
        }

        .ai-tool-item.ai-tool-running {
            border-color: rgba(200, 245, 98, 0.1);
            background: rgba(200, 245, 98, 0.02);
            animation: toolPulse 1.4s ease-in-out infinite;
        }

        @keyframes toolPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.55; }
        }

        .ai-tool-name {
            font-family: var(--mono);
            font-size: 0.65rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--text);
            flex-shrink: 0;
            min-width: 110px;
        }

        .ai-tool-preview {
            font-family: var(--mono);
            font-size: 0.63rem;
            color: var(--text-muted);
            line-height: 1.5;
            word-break: break-word;
        }

        .ai-tool-error .ai-tool-preview { color: var(--red); }

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
            .topbar { flex-wrap: wrap; }
            .topbar-right { width: 100%; justify-content: space-between; }
        }
    </style>
</head>
<body>
    <div class="app">

        <!-- TOP BAR -->
        <div class="topbar">
            <div class="wordmark">quan<em>t</em>um</div>
            <div class="topbar-right">
                <div class="wallet-actions" id="walletActions">
                    <button class="btn btn-ghost btn-icon" title="Restaurar carteira" onclick="openWalletModal('restore')">↺</button>
                    <button class="btn btn-danger btn-icon" title="Excluir carteira" onclick="openWalletModal('delete')">✕</button>
                </div>
                <select id="walletSelect" class="select" onchange="loadBalances()">
                    <option value="">selecione carteira</option>
                </select>
            </div>
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

        <!-- ANALYSIS SECTION (manual) -->
        <div id="analysis" class="analysis-container">
            <div class="section">
                <div class="section-label">Análise de Mercado</div>
                <div id="analysisContent"></div>
            </div>
        </div>

        <!-- SCHEDULER SECTION -->
        <div class="section" id="schedulerSection">
            <div class="section-label">Análise Automática</div>

            <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:16px;">
                <span class="scheduler-badge" id="schedulerBadge">○ inativo</span>
                <button class="btn btn-accent" id="btnSchedulerStart" onclick="startScheduler()" style="padding:8px 18px;font-size:0.72rem;">
                    Ativar (1h)
                </button>
                <button class="btn btn-danger" id="btnSchedulerStop" onclick="stopScheduler()" style="display:none;padding:8px 18px;font-size:0.72rem;">
                    Parar
                </button>
            </div>

            <div class="status-text" id="schedulerInfo" style="margin-bottom:20px;min-height:1.2em;"></div>

            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:10px;">
                <span style="font-family:var(--mono);font-size:0.63rem;letter-spacing:.12em;text-transform:uppercase;color:var(--text-muted)">Histórico de sinais</span>
                <span style="font-family:var(--mono);font-size:0.62rem;color:var(--text-dim)" id="schedulerTotal"></span>
            </div>
            <div id="schedulerHistory"></div>
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

    <!-- WALLET MODAL -->
    <div id="walletModal" class="modal-overlay" onclick="closeWalletModal(event)">
        <div class="modal-content wallet-modal-content">
            <div class="modal-header">
                <div class="modal-title">Gerenciar Carteira</div>
                <button class="modal-close" onclick="closeWalletModal()">&times;</button>
            </div>

            <div class="wallet-modal-tabs">
                <button class="wallet-tab active" data-tab="restore" onclick="switchWalletTab('restore')">Restaurar</button>
                <button class="wallet-tab" data-tab="delete" onclick="switchWalletTab('delete')">Excluir</button>
            </div>

            <!-- Painel: Restaurar -->
            <div class="wallet-tab-panel active" id="tabRestore">
                <div class="input-group">
                    <label class="input-label">Nome da chave</label>
                    <input type="text" id="restoreName" class="input" placeholder="ex: minha_wallet">
                </div>
                <div class="input-group">
                    <label class="input-label">Mnemônico (24 palavras)</label>
                    <textarea id="restoreMnemonic" class="input" rows="3"
                        style="resize: vertical; line-height: 1.6;"
                        placeholder="palavra1 palavra2 palavra3 ..."></textarea>
                </div>
                <div class="status-text" id="restoreStatus"></div>
                <div class="modal-actions">
                    <button class="btn btn-ghost" onclick="closeWalletModal()">Cancelar</button>
                    <button class="btn btn-accent" id="btnRestore" onclick="restoreWallet()">Restaurar</button>
                </div>
            </div>

            <!-- Painel: Excluir -->
            <div class="wallet-tab-panel" id="tabDelete">
                <div class="wallet-info-block">
                    <strong>Carteira selecionada</strong>
                    <span id="deleteWalletName">—</span>
                </div>
                <div class="wallet-warning">
                    Esta ação remove a chave do keyring local. Certifique-se de ter o mnemônico salvo antes de continuar. Esta operação não pode ser desfeita.
                </div>
                <div class="status-text" id="deleteStatus"></div>
                <div class="modal-actions">
                    <button class="btn btn-ghost" onclick="closeWalletModal()">Cancelar</button>
                    <button class="btn btn-danger" id="btnDelete" onclick="deleteWallet()">Excluir chave</button>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="osmo-price.js?v=<?php echo time(); ?>"></script>
</body>
</html>
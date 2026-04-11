<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <meta name="description" content="Monitor de preços e trading OSMO/USDC">
    <meta name="theme-color" content="#8b5cf6">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="quantum">
    <meta name="application-name" content="quantum">
    <meta name="msapplication-TileColor" content="#8b5cf6">
    <meta name="msapplication-tap-highlight" content="no">
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" href="/icon-192.png">
    <link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png">
    <link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png">
    <title>quantum</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            min-height: 100vh;
            color: #e8eaed;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }
        
        body::before {
            content: '';
            position: fixed;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(139, 92, 246, 0.1) 0%, transparent 50%);
            animation: rotate 30s linear infinite;
            pointer-events: none;
        }
        
        @keyframes rotate {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }
        
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding: 12px 0;
            width: 100%;
        }
        
        .header h1 {
            font-size: 1.8rem;
            font-weight: 700;
            background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 0;
            flex-shrink: 0;
        }
        
        .header .btn {
            margin: 0;
            white-space: nowrap;
            flex-shrink: 0;
            padding: 10px 20px;
            font-size: 0.85rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 28px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
        }
        
        .card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(139, 92, 246, 0.5), transparent);
        }
        
        .card:hover {
            transform: translateY(-4px);
            border-color: rgba(139, 92, 246, 0.3);
            box-shadow: 0 20px 40px rgba(139, 92, 246, 0.1);
        }
        
        .card-title {
            font-size: 0.875rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #9ca3af;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .card-title::before {
            content: '';
            width: 4px;
            height: 16px;
            background: linear-gradient(180deg, #8b5cf6, #ec4899);
            border-radius: 2px;
        }
        
        .price-display {
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #10b981 0%, #34d399 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin: 20px 0;
            line-height: 1;
        }
        
        .price-display::before {
            content: '$';
            font-size: 1.5rem;
            opacity: 0.6;
            margin-right: 4px;
        }
        
        .status-text {
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 12px;
        }
        
        .btn {
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
            font-family: 'Inter', sans-serif;
        }
        
        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
            transition: left 0.5s;
        }
        
        .btn:hover::before {
            left: 100%;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(139, 92, 246, 0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-secondary {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 10px 25px rgba(255, 255, 255, 0.05);
        }
        
        .btn-success {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
        }
        
        .btn-success:hover {
            box-shadow: 0 10px 25px rgba(16, 185, 129, 0.3);
        }
        
        .btn-group {
            display: flex;
            gap: 12px;
            margin-top: 20px;
            flex-wrap: wrap;
        }
        
        .input-group {
            margin-bottom: 20px;
        }
        
        .input-label {
            display: block;
            font-size: 0.85rem;
            font-weight: 500;
            color: #9ca3af;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .input, .select {
            width: 100%;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            color: #e8eaed;
            font-size: 0.95rem;
            font-family: 'Inter', sans-serif;
            transition: all 0.3s ease;
        }
        
        .input:focus, .select:focus {
            outline: none;
            border-color: #8b5cf6;
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 0 0 3px rgba(139, 92, 246, 0.1);
        }
        
        .select option {
            background: #1a1a2e;
            color: #e8eaed;
        }
        
        .balance-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-top: 16px;
        }
        
        .balance-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 16px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            transition: all 0.3s ease;
        }
        
        .balance-item:hover {
            background: rgba(255, 255, 255, 0.05);
            border-color: rgba(139, 92, 246, 0.3);
        }
        
        .balance-denom {
            font-weight: 600;
            color: #8b5cf6;
            font-size: 0.95rem;
        }
        
        .balance-amount {
            font-weight: 600;
            color: #10b981;
            font-size: 1.1rem;
        }
        
        .wallet-address {
            font-size: 0.8rem;
            color: #6b7280;
            margin-top: 12px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            word-break: break-all;
        }
        
        .swap-estimate {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            display: none;
        }
        
        .swap-estimate-label {
            font-size: 0.85rem;
            color: #9ca3af;
            margin-bottom: 8px;
        }
        
        .swap-estimate-value {
            font-size: 1.8rem;
            font-weight: 700;
            color: #10b981;
        }
        
        .loader {
            width: 24px;
            height: 24px;
            border: 3px solid rgba(139, 92, 246, 0.2);
            border-top-color: #8b5cf6;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            display: inline-block;
            vertical-align: middle;
            margin-right: 10px;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .ai-response {
            color: #d1d5db;
            line-height: 1.7;
            padding: 24px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 12px;
            border-left: 3px solid #10b981;
        }
        
        .ai-response h1, .ai-response h2, .ai-response h3 {
            color: #10b981;
            margin-top: 20px;
            margin-bottom: 12px;
            font-weight: 600;
        }
        
        .ai-response h1 { font-size: 1.5rem; }
        .ai-response h2 { font-size: 1.25rem; }
        .ai-response h3 { font-size: 1.1rem; }
        
        .ai-response p {
            margin-bottom: 12px;
        }
        
        .ai-response ul, .ai-response ol {
            margin-left: 24px;
            margin-bottom: 12px;
        }
        
        .ai-response li {
            margin-bottom: 6px;
        }
        
        .ai-response strong {
            color: #8b5cf6;
        }
        
        .ai-response code {
            background: rgba(139, 92, 246, 0.2);
            padding: 3px 8px;
            border-radius: 6px;
            color: #c4b5fd;
            font-size: 0.9em;
        }
        
        .ai-response pre {
            background: rgba(0, 0, 0, 0.4);
            padding: 16px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 12px 0;
        }
        
        .ai-response pre code {
            background: none;
            padding: 0;
        }
        
        .analysis-container {
            display: none;
            margin-top: 24px;
        }
        
        .ai-loading-wrap {
            display: flex;
            align-items: flex-start;
            gap: 20px;
            padding: 28px;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 12px;
            border: 1px solid rgba(139, 92, 246, 0.25);
            min-height: 120px;
        }
        
        .ai-loading-text {
            flex: 1;
        }
        
        .ai-loading-title {
            display: block;
            color: #e8eaed;
            font-size: 1rem;
            margin-bottom: 8px;
        }
        
        .ai-loading-sub {
            color: #9ca3af;
            font-size: 0.9rem;
            line-height: 1.5;
            margin: 0;
        }
        
        .ai-stream-container {
            margin-top: 0;
        }
        
        .ai-stream-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #34d399;
            margin-bottom: 12px;
            padding: 6px 12px;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.35);
            border-radius: 999px;
        }
        
        .ai-stream-badge.done {
            color: #9ca3af;
            border-color: rgba(255, 255, 255, 0.12);
            background: rgba(255, 255, 255, 0.04);
        }
        
        .ai-dot-pulse {
            width: 8px;
            height: 8px;
            background: #34d399;
            border-radius: 50%;
            animation: aiPulse 1.2s ease-in-out infinite;
        }
        
        .ai-stream-badge.done .ai-dot-pulse {
            animation: none;
            background: #6b7280;
        }
        
        @keyframes aiPulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }
        
        .btn:disabled {
            opacity: 0.55;
            cursor: not-allowed;
            transform: none;
        }
        
        .chart-header-row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 16px;
        }
        
        .chart-header-row .card-title {
            margin-bottom: 0;
        }
        
        .chart-timeframes {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        
        .timeframe-btn {
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 0.8rem;
            font-weight: 600;
            font-family: 'Inter', sans-serif;
            cursor: pointer;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background: rgba(255, 255, 255, 0.04);
            color: #9ca3af;
            transition: all 0.2s ease;
        }
        
        .timeframe-btn:hover {
            border-color: rgba(139, 92, 246, 0.4);
            color: #e8eaed;
        }
        
        .timeframe-btn.active {
            background: linear-gradient(135deg, rgba(139, 92, 246, 0.35) 0%, rgba(124, 58, 237, 0.25) 100%);
            border-color: rgba(139, 92, 246, 0.5);
            color: #fff;
        }
        
        .chart-wrap {
            position: relative;
            height: 320px;
            width: 100%;
        }
        
        .chart-lw {
            position: relative;
            z-index: 1;
            width: 100%;
            height: 320px;
        }
        
        .chart-empty {
            position: absolute;
            inset: 0;
            z-index: 2;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 16px;
            color: #6b7280;
            font-size: 0.9rem;
            pointer-events: none;
            background: rgba(15, 15, 35, 0.35);
        }
        
        .chart-empty.hidden {
            display: none !important;
        }
        
        .install-prompt {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 1000;
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: white;
            padding: 16px 24px;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(139, 92, 246, 0.4);
            display: none;
            align-items: center;
            gap: 12px;
            animation: slideUp 0.3s ease;
        }
        
        .install-prompt.show {
            display: flex;
        }
        
        @keyframes slideUp {
            from {
                transform: translateY(100px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .install-prompt-text {
            flex: 1;
        }
        
        .install-prompt-title {
            font-weight: 600;
            margin-bottom: 4px;
        }
        
        .install-prompt-desc {
            font-size: 0.85rem;
            opacity: 0.9;
        }
        
        .install-prompt-btn {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s;
        }
        
        .install-prompt-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        .install-prompt-close {
            background: none;
            border: none;
            color: white;
            font-size: 1.5rem;
            cursor: pointer;
            opacity: 0.7;
            transition: opacity 0.2s;
            padding: 0 8px;
        }
        
        .install-prompt-close:hover {
            opacity: 1;
        }
        
        .popup-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            z-index: 2000;
            display: none;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease;
        }
        
        .popup-overlay.show {
            display: flex;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        
        .popup-content {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 1px solid rgba(139, 92, 246, 0.3);
            border-radius: 24px;
            padding: 40px;
            max-width: 400px;
            width: 90%;
            text-align: center;
            animation: slideIn 0.3s ease;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }
        
        @keyframes slideIn {
            from {
                transform: scale(0.9) translateY(20px);
                opacity: 0;
            }
            to {
                transform: scale(1) translateY(0);
                opacity: 1;
            }
        }
        
        .popup-icon {
            width: 80px;
            height: 80px;
            margin: 0 auto 24px;
            background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 3rem;
            font-weight: 700;
            color: white;
            box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4);
        }
        
        .popup-title {
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 12px;
            background: linear-gradient(135deg, #8b5cf6 0%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        
        .popup-description {
            color: #9ca3af;
            font-size: 1rem;
            line-height: 1.6;
            margin-bottom: 32px;
        }
        
        .popup-features {
            text-align: left;
            margin-bottom: 32px;
        }
        
        .popup-feature {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 16px;
            color: #d1d5db;
        }
        
        .popup-feature-icon {
            width: 24px;
            height: 24px;
            background: rgba(139, 92, 246, 0.2);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1rem;
            flex-shrink: 0;
        }
        
        .popup-buttons {
            display: flex;
            gap: 12px;
            flex-direction: column;
        }
        
        .popup-btn-primary {
            background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
            color: white;
            border: none;
            padding: 16px 32px;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            font-family: 'Inter', sans-serif;
        }
        
        .popup-btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 30px rgba(139, 92, 246, 0.4);
        }
        
        .popup-btn-secondary {
            background: transparent;
            color: #9ca3af;
            border: none;
            padding: 12px;
            font-size: 0.9rem;
            cursor: pointer;
            transition: color 0.2s;
            font-family: 'Inter', sans-serif;
        }
        
        .popup-btn-secondary:hover {
            color: #e8eaed;
        }
        
        @media (max-width: 768px) {
            .header {
                flex-direction: row;
                gap: 12px;
                padding: 8px 0;
                margin-bottom: 20px;
            }
            
            .header .btn {
                width: auto;
                padding: 8px 14px;
                font-size: 0.8rem;
            }
            
            .header h1 {
                font-size: 1.5rem;
            }
            
            .price-display {
                font-size: 2.5rem;
            }
            
            .grid {
                grid-template-columns: 1fr;
            }
            
            .btn-group {
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
            
            .chart-wrap {
                height: 260px;
            }
            
            .chart-header-row {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .install-prompt {
                left: 20px;
                right: 20px;
                bottom: 20px;
            }
            
            .popup-content {
                padding: 32px 24px;
            }
            
            .popup-title {
                font-size: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>quantum</h1>
            <button class="btn" onclick="showInstallPopup()">
                📱 Instalar App
            </button>
        </div>
        
        <div class="grid">
            <!-- Card de Preço -->
            <div class="card">
                <div class="card-title">Preço OSMO</div>
                <div class="price-display" id="price">...</div>
                <div class="status-text" id="status">Carregando dados...</div>
                <div class="btn-group">
                    <button class="btn" onclick="updatePrice()">Atualizar</button>
                    <button type="button" class="btn btn-secondary" id="btnAnalyzeAi" onclick="analyzeHistory()">Análise IA</button>
                </div>
            </div>
            
            <!-- Card de Wallet -->
            <div class="card">
                <div class="card-title">Carteira</div>
                <div class="input-group">
                    <label class="input-label">Selecione a Carteira</label>
                    <select id="walletSelect" class="select" onchange="loadBalances()">
                        <option value="">-- Selecione --</option>
                    </select>
                </div>
                <div class="wallet-address" id="walletAddress">Nenhuma carteira selecionada</div>
                <div id="balances" class="balance-list">
                    <div style="text-align: center; color: #6b7280; padding: 20px;">
                        Selecione uma carteira
                    </div>
                </div>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="loadBalances()">Atualizar Saldos</button>
                </div>
            </div>
        </div>
        
        <!-- Gráfico de preço OSMO -->
        <div class="card" style="margin-bottom: 24px; overflow: visible;">
            <div class="chart-header-row">
                <div class="card-title" style="margin-bottom: 0;">OSMO / USD — velas</div>
                <div class="chart-timeframes" role="group" aria-label="Intervalo do gráfico">
                    <button type="button" class="timeframe-btn" data-tf="1m" onclick="setPriceChartTimeframe('1m')">1m</button>
                    <button type="button" class="timeframe-btn active" data-tf="15m" onclick="setPriceChartTimeframe('15m')">15m</button>
                    <button type="button" class="timeframe-btn" data-tf="1h" onclick="setPriceChartTimeframe('1h')">1h</button>
                </div>
            </div>
            <div class="chart-wrap">
                <div id="priceChartContainer" class="chart-lw" style="height: 320px;" aria-label="Gráfico de candles OSMO"></div>
                <div id="chartEmpty" class="chart-empty">Carregando histórico...</div>
            </div>
            <div class="status-text" id="chartStatus"></div>
        </div>
        
        <!-- Card de Swap (largura completa) -->
        <div class="card">
            <div class="card-title">Swap OSMO/USDC</div>
            
            <div class="grid">
                <div class="input-group">
                    <label class="input-label">De</label>
                    <select id="swapFrom" class="select">
                        <option value="uosmo">OSMO</option>
                        <option value="ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4">USDC</option>
                    </select>
                </div>
                
                <div class="input-group">
                    <label class="input-label">Para</label>
                    <select id="swapTo" class="select">
                        <option value="ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4">USDC</option>
                        <option value="uosmo">OSMO</option>
                    </select>
                </div>
            </div>
            
            <div class="input-group">
                <label class="input-label">Quantidade</label>
                <input type="number" id="swapAmount" class="input" placeholder="0.000000" step="0.000001">
            </div>
            
            <div id="swapEstimate" class="swap-estimate">
                <div class="swap-estimate-label">Você receberá aproximadamente</div>
                <div class="swap-estimate-value" id="swapOutput">-</div>
            </div>
            
            <div class="status-text" id="swapStatus"></div>
            
            <div class="btn-group">
                <button class="btn btn-secondary" onclick="simulateSwap()">Simular Swap</button>
                <button class="btn btn-success" onclick="executeSwap()">Executar Swap</button>
            </div>
        </div>
        
        <!-- Análise IA -->
        <div id="analysis" class="analysis-container">
            <div class="card">
                <div class="card-title">Análise de Mercado</div>
                <div id="analysisContent"></div>
            </div>
        </div>
    </div>
    
    <!-- Prompt de instalação PWA -->
    <div id="installPrompt" class="install-prompt">
        <div class="install-prompt-text">
            <div class="install-prompt-title">Instalar quantum</div>
            <div class="install-prompt-desc">Acesse offline e mais rápido</div>
        </div>
        <button class="install-prompt-btn" id="installBtn">Instalar</button>
        <button class="install-prompt-close" id="installClose">&times;</button>
    </div>
    
    <!-- Popup de instalação -->
    <div id="installPopup" class="popup-overlay">
        <div class="popup-content">
            <div class="popup-icon">Q</div>
            <h2 class="popup-title">Instalar quantum</h2>
            <p class="popup-description">
                Adicione o quantum à sua tela inicial para acesso rápido e experiência completa.<br>
                <small style="color: #6b7280; margin-top: 8px; display: block; line-height: 1.5;">
                    <strong>⚠️ Importante no Firefox:</strong><br>
                    Após instalar, abra sempre pelo ícone do app na tela inicial.<br>
                    Não abra pelo navegador para ter a experiência completa.
                </small>
            </p>
            
            <div class="popup-features">
                <div class="popup-feature">
                    <div class="popup-feature-icon">⚡</div>
                    <div>Acesso instantâneo</div>
                </div>
                <div class="popup-feature">
                    <div class="popup-feature-icon">📱</div>
                    <div>Funciona offline</div>
                </div>
                <div class="popup-feature">
                    <div class="popup-feature-icon">🚀</div>
                    <div>Carregamento mais rápido</div>
                </div>
                <div class="popup-feature">
                    <div class="popup-feature-icon">🔔</div>
                    <div>Notificações em tempo real</div>
                </div>
            </div>
            
            <div class="popup-buttons">
                <button class="popup-btn-primary" id="popupInstallBtn">
                    Adicionar à Tela Inicial
                </button>
                <button class="popup-btn-secondary" id="popupCloseBtn">
                    Agora não
                </button>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="osmo-price.js"></script>
</body>
</html>
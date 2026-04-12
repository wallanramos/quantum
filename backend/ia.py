#!/usr/bin/env python3
"""
Módulo de IA para análise de preços OSMO
Integração com Hugging Face para análise de mercado
"""
import json
import os

import requests

from preco import fetch_kline_history


# Configurações do modelo
HF_MODEL = 'Qwen/Qwen3-Coder-Next:novita'
HF_TEMPERATURE = 0.7
HF_MAX_TOKENS = 2000
HF_TIMEOUT = (15, 120)

SYSTEM_MESSAGE = (
    'Você é um analista financeiro especializado em criptomoedas. '
    'Forneça análises técnicas detalhadas, objetivas e profissionais. '
    'Use formatação markdown para organizar suas respostas com títulos, listas e destaques. '
    'Seja claro e direto nas suas recomendações.'
)


def _read_hf_token_from_dotenv(path):
    """Lê HF_API_TOKEN= ou HUGGINGFACE_HUB_TOKEN= de um arquivo estilo .env."""
    if not os.path.isfile(path):
        return ''
    try:
        with open(path, encoding='utf-8') as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith('#'):
                    continue
                for prefix in ('HF_API_TOKEN=', 'HUGGINGFACE_HUB_TOKEN='):
                    if line.startswith(prefix):
                        val = line[len(prefix):].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if val.startswith('hf_'):
                            return val
    except OSError:
        pass
    return ''


def hf_resolve_api_token():
    """Token HF: variável de ambiente ou arquivo .env."""
    for key in ('HF_API_TOKEN', 'HUGGINGFACE_HUB_TOKEN'):
        t = os.environ.get(key, '').strip()
        if t:
            return t
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)
    for root in (script_dir, parent):
        t = _read_hf_token_from_dotenv(os.path.join(root, '.env'))
        if t:
            return t
    return ''


def calculate_ema(prices, period):
    """Calcula Média Móvel Exponencial (EMA) para um período."""
    ema = []
    multiplier = 2 / (period + 1)
    
    # Primeiro valor é a média simples dos primeiros 'period' valores
    for i in range(len(prices)):
        if i < period - 1:
            ema.append(None)
        elif i == period - 1:
            # SMA inicial
            ema.append(sum(prices[:period]) / period)
        else:
            # EMA = (Preço atual × multiplicador) + (EMA anterior × (1 - multiplicador))
            ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))
    
    return ema


def build_analysis_prompt(timeframe='15m'):
    """Monta o prompt de análise com dados do histórico de preços."""
    result = fetch_kline_history(timeframe)
    
    if not result['success']:
        return None, result.get('error', 'Erro ao buscar histórico')
    
    history = result['history']
    if not history:
        return None, 'Nenhum dado disponível para análise'
    
    prices = [item['price'] for item in history]
    current_price = prices[0]
    oldest_price = prices[-1]
    max_price = max(prices)
    min_price = min(prices)
    avg_price = sum(prices) / len(prices)
    
    # Calcular médias móveis exponenciais
    ema9 = calculate_ema(prices, 9)
    ema21 = calculate_ema(prices, 21)
    
    # Últimos valores das médias móveis
    current_ema9 = ema9[-1] if ema9[-1] else 0
    current_ema21 = ema21[-1] if ema21[-1] else 0
    
    # Histórico das médias móveis (últimos 10 valores válidos)
    ema9_history = [v for v in ema9 if v is not None][-10:]
    ema21_history = [v for v in ema21 if v is not None][-10:]
    
    last_10 = ', '.join(f'{p:.6f}' for p in prices[:10])
    ema9_str = ', '.join(f'{v:.6f}' for v in ema9_history)
    ema21_str = ', '.join(f'{v:.6f}' for v in ema21_history)
    
    # Timestamp atual
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    # Mapear timeframe para descrição
    tf_desc = {
        '1m': '1 minuto',
        '15m': '15 minutos',
        '1h': '1 hora',
        '4h': '4 horas',
        '1d': '1 dia'
    }.get(timeframe, timeframe)
    
    # Tendência baseada no cruzamento das médias
    trend = "ALTA" if current_ema9 > current_ema21 else "BAIXA" if current_ema9 < current_ema21 else "LATERAL"
    
    prompt = f"""Analise os seguintes dados de preço da criptomoeda OSMO (Osmosis):

Data/Hora da análise: {now}
Timeframe: {tf_desc} (cada vela representa {tf_desc})

Dados do histórico:
- Total de registros: {len(history)}
- Preço atual: {current_price:.6f}
- Preço mais antigo: {oldest_price:.6f}
- Preço máximo: {max_price:.6f}
- Preço mínimo: {min_price:.6f}
- Preço médio: {avg_price:.6f}

Médias Móveis Exponenciais (EMA):
- EMA 9 atual: {current_ema9:.6f}
- EMA 21 atual: {current_ema21:.6f}
- Tendência (cruzamento EMA9/EMA21): {trend}

Últimos 10 preços (velas mais recentes): {last_10}

Histórico EMA 9 (últimos 10): {ema9_str}
Histórico EMA 21 (últimos 10): {ema21_str}

Por favor, forneça uma análise detalhada incluindo:
1. Tendência geral do preço
2. Análise do cruzamento das médias móveis (EMA 9 e EMA 21)
3. Volatilidade observada
4. Pontos de atenção
5. Recomendações para investidores
6. Análise técnica básica

Responda em português de forma clara e objetiva."""
    
    return prompt, None


def get_position_signal(timeframe='15m'):
    """Consulta a IA para obter sinal de posição: COMPRA, VENDE ou ESPERA."""
    import requests
    
    token = hf_resolve_api_token()
    if not token:
        return None, 'Token Hugging Face não configurado'
    
    result = fetch_kline_history(timeframe)
    
    if not result['success']:
        return None, result.get('error', 'Erro ao buscar histórico')
    
    history = result['history']
    if not history:
        return None, 'Nenhum dado disponível'
    
    prices = [item['price'] for item in history]
    current_price = prices[0]
    oldest_price = prices[-1]
    max_price = max(prices)
    min_price = min(prices)
    avg_price = sum(prices) / len(prices)
    
    # Calcular EMA
    ema9 = calculate_ema(prices, 9)
    ema21 = calculate_ema(prices, 21)
    
    current_ema9 = ema9[-1] if ema9[-1] else 0
    current_ema21 = ema21[-1] if ema21[-1] else 0
    
    # Histórico das EMAs (últimos 5 valores)
    ema9_history = [v for v in ema9 if v is not None][-5:]
    ema21_history = [v for v in ema21 if v is not None][-5:]
    
    last_5 = ', '.join(f'{p:.6f}' for p in prices[:5])
    ema9_str = ', '.join(f'{v:.6f}' for v in ema9_history)
    ema21_str = ', '.join(f'{v:.6f}' for v in ema21_history)
    
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    tf_desc = {
        '1m': '1 minuto',
        '15m': '15 minutos',
        '1h': '1 hora',
        '4h': '4 horas',
        '1d': '1 dia'
    }.get(timeframe, timeframe)
    
    prompt = f"""Você é um trader profissional. Analise os dados abaixo e responda APENAS com uma palavra: COMPRA, VENDE ou ESPERA.

Data/Hora: {now}
Timeframe: {tf_desc}

Preço atual: {current_price:.6f}
Preço mais antigo: {oldest_price:.6f}
Preço máximo: {max_price:.6f}
Preço mínimo: {min_price:.6f}
Preço médio: {avg_price:.6f}

EMA 9 atual: {current_ema9:.6f}
EMA 21 atual: {current_ema21:.6f}

Últimos 5 preços: {last_5}
EMA 9 (últimos 5): {ema9_str}
EMA 21 (últimos 5): {ema21_str}

Responda APENAS com: COMPRA, VENDE ou ESPERA"""

    try:
        response = requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
            json={
                'model': HF_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'Você é um trader profissional. Responda APENAS com uma palavra: COMPRA, VENDE ou ESPERA.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.3,
                'max_tokens': 10,
            },
            timeout=30
        )
        
        if response.status_code >= 400:
            return None, f'Erro na API: {response.status_code}'
        
        data = response.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip().upper()
        
        # Validar resposta
        if 'COMPRA' in content:
            signal = 'COMPRA'
        elif 'VENDE' in content:
            signal = 'VENDE'
        else:
            signal = 'ESPERA'
        
        return {
            'signal': signal,
            'price': current_price,
            'ema9': current_ema9,
            'ema21': current_ema21
        }, None
        
    except Exception as e:
        return None, str(e)


def stream_ai_analysis(timeframe='15m'):
    """Generator que faz streaming da análise de IA.
    
    Yields bytes no formato SSE (data: ...\n\n).
    """
    token = hf_resolve_api_token()
    if not token:
        yield f'data: {json.dumps({"error": "Token Hugging Face não configurado. Configure HF_API_TOKEN no .env"})}\n\n'.encode('utf-8')
        return
    
    prompt, error = build_analysis_prompt(timeframe)
    if error:
        yield f'data: {json.dumps({"error": error})}\n\n'.encode('utf-8')
        return
    
    payload = {
        'model': HF_MODEL,
        'messages': [
            {'role': 'system', 'content': SYSTEM_MESSAGE},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': HF_TEMPERATURE,
        'stream': True,
        'max_tokens': HF_MAX_TOKENS,
    }
    
    try:
        with requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {token}',
            },
            json=payload,
            stream=True,
            timeout=HF_TIMEOUT,
        ) as r:
            if r.status_code >= 400:
                body = (r.text or '')[:1200]
                yield f'data: {json.dumps({"error": body or r.reason, "code": r.status_code})}\n\n'.encode('utf-8')
                return
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
    except requests.RequestException as e:
        yield f'data: {json.dumps({"error": str(e)})}\n\n'.encode('utf-8')
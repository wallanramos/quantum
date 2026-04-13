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
    ema = []
    multiplier = 2 / (period + 1)
    for i in range(len(prices)):
        if i < period - 1:
            ema.append(None)
        elif i == period - 1:
            ema.append(sum(prices[:period]) / period)
        else:
            ema.append((prices[i] * multiplier) + (ema[-1] * (1 - multiplier)))
    return ema


def _build_market_data(timeframe):
    """Busca histórico e calcula indicadores. Retorna (dados, erro)."""
    result = fetch_kline_history(timeframe)
    if not result['success']:
        return None, result.get('error', 'Erro ao buscar histórico')

    history = result['history']
    if not history:
        return None, 'Nenhum dado disponível'

    prices = [item['price'] for item in history]
    ema9  = calculate_ema(prices, 9)
    ema21 = calculate_ema(prices, 21)

    return {
        'prices': prices,
        'current':  prices[0],
        'oldest':   prices[-1],
        'max':      max(prices),
        'min':      min(prices),
        'avg':      sum(prices) / len(prices),
        'ema9':     ema9[-1] or 0,
        'ema21':    ema21[-1] or 0,
        'ema9_hist':  [v for v in ema9  if v is not None][-10:],
        'ema21_hist': [v for v in ema21 if v is not None][-10:],
        'count':    len(history),
    }, None


def build_analysis_prompt(timeframe='15m'):
    """Monta o prompt de análise completa."""
    from datetime import datetime, timezone
    d, err = _build_market_data(timeframe)
    if err:
        return None, err

    tf_desc = {'1m': '1 minuto', '15m': '15 minutos', '1h': '1 hora', '4h': '4 horas', '1d': '1 dia'}.get(timeframe, timeframe)
    trend   = 'ALTA' if d['ema9'] > d['ema21'] else 'BAIXA' if d['ema9'] < d['ema21'] else 'LATERAL'
    now     = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

    prompt = f"""Analise os seguintes dados de preço da criptomoeda OSMO (Osmosis):

Data/Hora da análise: {now}
Timeframe: {tf_desc}

Dados do histórico:
- Total de registros: {d['count']}
- Preço atual: {d['current']:.6f}
- Preço mais antigo: {d['oldest']:.6f}
- Preço máximo: {d['max']:.6f}
- Preço mínimo: {d['min']:.6f}
- Preço médio: {d['avg']:.6f}

Médias Móveis Exponenciais:
- EMA 9 atual: {d['ema9']:.6f}
- EMA 21 atual: {d['ema21']:.6f}
- Tendência (EMA9/EMA21): {trend}

Últimos 10 preços: {', '.join(f'{p:.6f}' for p in d['prices'][:10])}
EMA 9 (últimos 10): {', '.join(f'{v:.6f}' for v in d['ema9_hist'])}
EMA 21 (últimos 10): {', '.join(f'{v:.6f}' for v in d['ema21_hist'])}

Forneça uma análise detalhada incluindo:
1. Tendência geral do preço
2. Análise do cruzamento das médias móveis (EMA 9 e EMA 21)
3. Volatilidade observada
4. Pontos de atenção
5. Recomendações para investidores
6. Análise técnica básica

Responda em português de forma clara e objetiva."""

    return prompt, None


def get_position_signal(timeframe='15m'):
    """Consulta a IA e retorna COMPRA, VENDE ou ESPERA."""
    token = hf_resolve_api_token()
    if not token:
        return None, 'Token Hugging Face não configurado'

    d, err = _build_market_data(timeframe)
    if err:
        return None, err

    tf_desc = {'1m': '1 minuto', '15m': '15 minutos', '1h': '1 hora', '4h': '4 horas', '1d': '1 dia'}.get(timeframe, timeframe)
    trend   = 'ALTA' if d['ema9'] > d['ema21'] else 'BAIXA' if d['ema9'] < d['ema21'] else 'LATERAL'

    prompt = f"""Timeframe: {tf_desc}
Preço atual: {d['current']:.6f}
EMA 9: {d['ema9']:.6f} | EMA 21: {d['ema21']:.6f} | Tendência: {trend}
Últimos 5 preços: {', '.join(f'{p:.6f}' for p in d['prices'][:5])}

Responda APENAS com uma única palavra: COMPRA, VENDE ou ESPERA."""

    try:
        response = requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
            json={
                'model': HF_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'Você é um trader profissional. Responda APENAS com uma única palavra: COMPRA, VENDE ou ESPERA. Nenhuma outra palavra.'},
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.1,
                'max_tokens': 5,
            },
            timeout=30,
        )

        if response.status_code >= 400:
            return None, f'Erro na API: {response.status_code}'

        content = response.json()['choices'][0]['message']['content'].strip().upper()

        # Extrai a palavra mesmo se a IA colocar texto extra
        if 'COMPRA' in content:
            signal = 'COMPRA'
        elif 'VENDE' in content:
            signal = 'VENDE'
        else:
            signal = 'ESPERA'

        return {'signal': signal, 'price': d['current'], 'ema9': d['ema9'], 'ema21': d['ema21']}, None

    except Exception as e:
        return None, str(e)


def stream_ai_analysis(timeframe='15m'):
    """Generator que faz streaming da análise de IA em formato SSE."""
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
            {'role': 'user',   'content': prompt},
        ],
        'temperature': HF_TEMPERATURE,
        'stream': True,
        'max_tokens': HF_MAX_TOKENS,
    }

    try:
        with requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
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
#!/usr/bin/env python3
"""
ia.py — Módulo de IA para análise de mercado OSMO

Fluxo agentic loop (single-context):
  1. IA recebe intenção + tools disponíveis
  2. IA chama tools → backend executa → resultado vai pro contexto
  3. IA decide: faz swap? compra ou venda? ou só analisa?
  4. IA pode chamar mais tools (ex: tool_swap) com base nos dados
  5. Quando satisfeita, gera resposta final em streaming

Tudo acontece no mesmo contexto de mensagens.
"""
import json
import os
from datetime import datetime, timezone

import requests

from preco import fetch_kline_history, get_current_price


# ── Configurações ──────────────────────────────────────────────
HF_MODEL        = 'meta-llama/Llama-3.3-70B-Instruct:novita'
HF_TEMPERATURE  = 0.7
HF_MAX_TOKENS   = 3000
HF_TIMEOUT      = (15, 120)
HF_URL          = 'https://router.huggingface.co/v1/chat/completions'
MAX_TOOL_ROUNDS = 5  # segurança: máximo de rounds do agentic loop

SYSTEM_MESSAGE = (
    'Você é um trader e analista financeiro especializado na blockchain Osmosis. '
    'Seu objetivo é analisar o mercado de OSMO e decidir a melhor ação. '
    'Siga este fluxo obrigatório:\n'
    '1. Chame tool_controle para ver saldo, posição e P&L\n'
    '2. Chame tool_analise para obter dados técnicos (EMA, tendência, histórico)\n'
    '3. Com base nos dados, decida: COMPRAR, VENDER ou AGUARDAR\n'
    '4. Se decidir operar, chame tool_swap para executar\n'
    '5. Apresente sua análise completa em markdown, incluindo:\n'
    '   - Situação atual do portfólio\n'
    '   - Análise técnica\n'
    '   - Decisão tomada e justificativa\n'
    '   - Resultado do swap (se executado)\n'
    'Use português. Seja direto e objetivo.'
)

# ── Definição das Tools ────────────────────────────────────────

TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'tool_controle',
            'description': (
                'Retorna o estado atual da carteira: saldo OSMO e USDC, '
                'posição atual (comprado ou vendido/sem_posicao), '
                'P&L em USDC desde o último trade, '
                'preço atual do OSMO e resumo do histórico de klines.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'address': {
                        'type': 'string',
                        'description': 'Endereço osmo1... da carteira'
                    },
                    'timeframe': {
                        'type': 'string',
                        'enum': ['1m', '15m', '1h', '4h', '1d'],
                        'description': 'Timeframe para o histórico'
                    }
                },
                'required': ['address', 'timeframe']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'tool_analise',
            'description': (
                'Busca klines do OSMO, calcula EMA9 e EMA21, '
                'retorna dados técnicos: tendência, preços, médias móveis, '
                'saldo e posição atual da carteira.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'address': {
                        'type': 'string',
                        'description': 'Endereço osmo1... da carteira'
                    },
                    'timeframe': {
                        'type': 'string',
                        'enum': ['1m', '15m', '1h', '4h', '1d'],
                        'description': 'Timeframe da análise técnica'
                    }
                },
                'required': ['address', 'timeframe']
            }
        }
    },
    {
        'type': 'function',
        'function': {
            'name': 'tool_swap',
            'description': (
                'Executa um swap: compra (USDC→OSMO) ou venda (OSMO→USDC). '
                'Persiste o trade no histórico com posição, timestamp, preço, '
                'quantidade, saldo antes e depois. '
                'Só chame esta tool se tiver certeza de que a operação é adequada.'
            ),
            'parameters': {
                'type': 'object',
                'properties': {
                    'address': {
                        'type': 'string',
                        'description': 'Endereço osmo1... da carteira'
                    },
                    'direcao': {
                        'type': 'string',
                        'enum': ['compra', 'venda'],
                        'description': 'compra = USDC→OSMO, venda = OSMO→USDC'
                    },
                    'quantidade': {
                        'type': 'number',
                        'description': (
                            'Quantidade em unidades (não micro). '
                            'Para compra: quantidade em USDC. '
                            'Para venda: quantidade em OSMO.'
                        )
                    }
                },
                'required': ['address', 'direcao', 'quantidade']
            }
        }
    }
]

# ── Token HF ──────────────────────────────────────────────────

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
                        val = line[len(prefix):].strip().strip('"\'')
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
    for root in (script_dir, os.path.dirname(script_dir)):
        t = _read_hf_token_from_dotenv(os.path.join(root, '.env'))
        if t:
            return t
    return ''


# ── EMA ───────────────────────────────────────────────────────

def calculate_ema(prices: list, period: int) -> list:
    ema, mult = [], 2 / (period + 1)
    for i in range(len(prices)):
        if i < period - 1:
            ema.append(None)
        elif i == period - 1:
            ema.append(sum(prices[:period]) / period)
        else:
            ema.append((prices[i] * mult) + (ema[-1] * (1 - mult)))
    return ema


# ── Implementações das Tools ───────────────────────────────────

def _exec_tool_controle(address: str, timeframe: str) -> dict:
    from swap import get_balance, get_last_trade, _parse_balances

    bal_result = get_balance(address)
    if not bal_result.get('success'):
        return {'error': bal_result.get('error', 'Erro ao consultar saldo')}

    saldo      = _parse_balances(bal_result.get('balances', []))
    history_r  = fetch_kline_history(timeframe)
    history    = history_r.get('history', []) if history_r.get('success') else []
    last_trade = get_last_trade()
    posicao    = 'comprado' if (last_trade and last_trade.get('posicao') == 'compra') else 'vendido/sem_posicao'

    lucro_usdc = None
    if last_trade and 'saldo_depois' in last_trade:
        usdc_ref   = last_trade['saldo_depois'].get('usdc', 0)
        lucro_usdc = round(saldo['usdc'] - usdc_ref, 6)

    return {
        'saldo':            saldo,
        'posicao':          posicao,
        'lucro_usdc':       lucro_usdc,
        'preco_atual':      get_current_price(),
        'ultimo_trade':     last_trade,
        'historico_resumo': {'timeframe': timeframe, 'candles': len(history)},
    }


def _exec_tool_analise(address: str, timeframe: str) -> dict:
    from swap import get_balance, get_last_trade, _parse_balances

    result = fetch_kline_history(timeframe)
    if not result.get('success'):
        return {'error': result.get('error', 'Erro ao buscar histórico')}

    history = result['history']
    if not history:
        return {'error': 'Histórico vazio'}

    prices    = [item['price'] for item in history]
    ema9      = calculate_ema(prices, 9)
    ema21     = calculate_ema(prices, 21)
    ema9_val  = next((v for v in reversed(ema9)  if v is not None), 0)
    ema21_val = next((v for v in reversed(ema21) if v is not None), 0)
    trend     = 'ALTA' if ema9_val > ema21_val else 'BAIXA' if ema9_val < ema21_val else 'LATERAL'

    bal_result = get_balance(address)
    saldo      = _parse_balances(bal_result.get('balances', [])) if bal_result.get('success') else {}
    last_trade = get_last_trade()
    posicao    = 'comprado' if (last_trade and last_trade.get('posicao') == 'compra') else 'vendido/sem_posicao'

    return {
        'timeframe':         timeframe,
        'candles':           len(history),
        'preco_atual':       prices[0],
        'preco_min':         min(prices),
        'preco_max':         max(prices),
        'preco_medio':       round(sum(prices) / len(prices), 6),
        'ema9':              round(ema9_val, 6),
        'ema21':             round(ema21_val, 6),
        'tendencia':         trend,
        'ultimos_10_precos': [round(p, 6) for p in prices[:10]],
        'ema9_hist':         [round(v, 6) for v in [x for x in ema9  if x][-10:]],
        'ema21_hist':        [round(v, 6) for v in [x for x in ema21 if x][-10:]],
        'saldo':             saldo,
        'posicao':           posicao,
        'ultimo_trade':      last_trade,
        'gerado_em':         datetime.now(timezone.utc).isoformat(),
    }


def _exec_tool_swap(address: str, direcao: str, quantidade: float) -> dict:
    from swap import execute_swap, USDC

    amount_micro = int(quantidade * 1_000_000)
    from_token   = USDC    if direcao == 'compra' else 'uosmo'
    to_token     = 'uosmo' if direcao == 'compra' else USDC

    return execute_swap(address, from_token, to_token, amount_micro)


def _dispatch_tool(name: str, args: dict) -> str:
    try:
        if name == 'tool_controle':
            result = _exec_tool_controle(args.get('address', ''), args.get('timeframe', '15m'))
        elif name == 'tool_analise':
            result = _exec_tool_analise(args.get('address', ''), args.get('timeframe', '15m'))
        elif name == 'tool_swap':
            result = _exec_tool_swap(args.get('address', ''), args.get('direcao', ''), float(args.get('quantidade', 0)))
        else:
            result = {'error': f'Tool desconhecida: {name}'}
    except Exception as e:
        result = {'error': str(e)}

    return json.dumps(result, ensure_ascii=False, default=str)


# ── Agentic Loop ───────────────────────────────────────────────

def stream_ai_analysis(address: str, timeframe: str = '15m'):
    """
    Generator SSE com agentic loop single-context:

    - A IA chama tools → backend executa → resultado entra no contexto
    - Isso se repete até a IA não chamar mais tools
    - Só então a resposta final é gerada em streaming

    Eventos SSE especiais (JSON com campo 'phase'):
      {"phase": "intent", "message": "..."}
      {"phase": "tool_running", "tool": "tool_controle"}
      {"phase": "tool_result",  "tool": "...", "result": {...}}
      {"phase": "analysis",     "message": "..."}
    Depois: chunks SSE padrão OpenAI (delta.content)
    """
    token = hf_resolve_api_token()
    if not token:
        yield _sse({'error': 'Token Hugging Face não configurado. Configure HF_API_TOKEN no .env'})
        return

    headers = {
        'Content-Type':  'application/json',
        'Authorization': f'Bearer {token}',
    }

    messages = [
        {'role': 'system', 'content': SYSTEM_MESSAGE},
        {
            'role': 'user',
            'content': (
                f'Analise o mercado OSMO agora para a carteira {address}. '
                f'Timeframe: {timeframe}. '
                f'Colete os dados necessários, avalie a situação e decida a melhor ação.'
            )
        },
    ]

    yield _sse({'phase': 'intent', 'message': 'Analisando mercado…'})

    # ── Agentic loop: resolve tools até a IA parar de chamar ──
    for _ in range(MAX_TOOL_ROUNDS):

        try:
            resp = requests.post(
                HF_URL,
                headers=headers,
                json={
                    'model':       HF_MODEL,
                    'messages':    messages,
                    'tools':       TOOLS,
                    'tool_choice': 'auto',
                    'temperature': 0.3,
                    'max_tokens':  1000,
                    'stream':      False,
                },
                timeout=HF_TIMEOUT,
            )
        except requests.RequestException as e:
            yield _sse({'error': str(e)})
            return

        if resp.status_code >= 400:
            yield _sse({'error': f'API erro {resp.status_code}: {resp.text[:500]}'})
            return

        choice     = resp.json()['choices'][0]
        msg        = choice['message']
        tool_calls = msg.get('tool_calls') or []

        # Adiciona resposta do assistente ao contexto
        messages.append(msg)

        # IA não quer mais chamar tools → sai do loop para streaming
        if not tool_calls:
            break

        # Executa cada tool e adiciona resultado ao contexto
        for tc in tool_calls:
            tool_name = tc['function']['name']
            tool_id   = tc['id']

            try:
                tool_args = json.loads(tc['function']['arguments'])
            except json.JSONDecodeError:
                tool_args = {}

            yield _sse({'phase': 'tool_running', 'tool': tool_name})

            tool_result_str = _dispatch_tool(tool_name, tool_args)

            try:
                result_preview = json.loads(tool_result_str)
            except Exception:
                result_preview = {}

            yield _sse({'phase': 'tool_result', 'tool': tool_name, 'result': result_preview})

            # Resultado entra no contexto — IA lê no próximo round
            messages.append({
                'role':         'tool',
                'tool_call_id': tool_id,
                'content':      tool_result_str,
            })

    # ── Streaming da resposta final ────────────────────────────
    yield _sse({'phase': 'analysis', 'message': 'Gerando análise…'})

    try:
        with requests.post(
            HF_URL,
            headers=headers,
            json={
                'model':       HF_MODEL,
                'messages':    messages,
                'temperature': HF_TEMPERATURE,
                'max_tokens':  HF_MAX_TOKENS,
                'stream':      True,
            },
            stream=True,
            timeout=HF_TIMEOUT,
        ) as resp_stream:
            if resp_stream.status_code >= 400:
                body = (resp_stream.text or '')[:1200]
                yield _sse({'error': body or resp_stream.reason, 'code': resp_stream.status_code})
                return
            for chunk in resp_stream.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
    except requests.RequestException as e:
        yield _sse({'error': str(e)})


# ── Sinal rápido (sem streaming) ───────────────────────────────

def get_position_signal(address: str, timeframe: str = '15m'):
    token = hf_resolve_api_token()
    if not token:
        return None, 'Token Hugging Face não configurado'

    data = _exec_tool_analise(address, timeframe)
    if 'error' in data:
        return None, data['error']

    prompt = (
        f"Timeframe: {timeframe}\n"
        f"Preço atual: {data['preco_atual']:.6f}\n"
        f"EMA9: {data['ema9']:.6f} | EMA21: {data['ema21']:.6f} | Tendência: {data['tendencia']}\n"
        f"Posição atual: {data['posicao']}\n"
        f"Últimos 5 preços: {', '.join(str(p) for p in data['ultimos_10_precos'][:5])}\n\n"
        f"Responda APENAS com uma única palavra: COMPRA, VENDE ou ESPERA."
    )

    try:
        response = requests.post(
            HF_URL,
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {hf_resolve_api_token()}'},
            json={
                'model':    HF_MODEL,
                'messages': [
                    {'role': 'system', 'content': 'Você é um trader profissional. Responda APENAS com uma única palavra: COMPRA, VENDE ou ESPERA.'},
                    {'role': 'user',   'content': prompt},
                ],
                'temperature': 0.1,
                'max_tokens':  5,
            },
            timeout=30,
        )
        if response.status_code >= 400:
            return None, f'Erro na API: {response.status_code}'

        content = response.json()['choices'][0]['message']['content'].strip().upper()
        signal  = 'COMPRA' if 'COMPRA' in content else 'VENDE' if 'VENDE' in content else 'ESPERA'

        return {
            'signal':  signal,
            'price':   data['preco_atual'],
            'ema9':    data['ema9'],
            'ema21':   data['ema21'],
            'posicao': data['posicao'],
        }, None

    except Exception as e:
        return None, str(e)


# ── Helper SSE ─────────────────────────────────────────────────

def _sse(payload: dict) -> bytes:
    return f'data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n'.encode('utf-8')
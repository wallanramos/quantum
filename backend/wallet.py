#!/usr/bin/env python3
"""
Backend de Wallet Osmosis em Python
API REST para gerenciamento de wallets, swaps e preço OSMO em tempo real
"""
import json
import subprocess
import threading
import time

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS

from ia import stream_ai_analysis
from preco import (
    COINEX_INTERVAL_MAP,
    fetch_kline_history,
    get_price_state,
    update_price,
    UPDATE_INTERVAL,
)

app = Flask(__name__)
CORS(
    app,
    origins='*',
    allow_headers='*',
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    expose_headers='*',
)


# Configurações Wallet
OSMOSISD_PATH = '/usr/local/bin/osmosisd'
NODE_URL = 'https://rpc.osmosis.zone:443'
CHAIN_ID = 'osmosis-1'

# Mapeamento de chaves
KEY_MAPPING = {
    'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88': 'wallet_osmo1sp8'
}


def run_command(command):
    """Executa comando shell e retorna output"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, "Timeout", 1
    except Exception as e:
        return None, str(e), 1


# ==================== FUNÇÕES DE WALLET ====================

def get_balance(address):
    """Consulta saldo de um endereço"""
    if not address.startswith('osmo1'):
        return {'success': False, 'error': 'Endereço inválido'}

    command = f"{OSMOSISD_PATH} query bank balances {address} --node {NODE_URL} --output json"
    stdout, stderr, code = run_command(command)

    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao consultar saldo'}

    try:
        data = json.loads(stdout)
        return {
            'success': True,
            'address': address,
            'balances': data.get('balances', [])
        }
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta'}


def list_keys():
    """Lista todas as chaves do keyring"""
    command = f"{OSMOSISD_PATH} keys list --output json"
    stdout, stderr, code = run_command(command)

    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao listar chaves'}

    try:
        keys = json.loads(stdout)
        return {'success': True, 'keys': keys}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta'}


def simulate_swap(from_token, to_token, amount):
    """Simula um swap"""
    USDC = 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'
    try:
        amount = int(amount)
        if amount <= 0:
            return {'success': False, 'error': 'Quantidade inválida'}

        if from_token == 'uosmo':
            estimated_out = int(amount * 0.03)
            token_out_denom = USDC
        else:
            estimated_out = int(amount / 0.03)
            token_out_denom = 'uosmo'

        return {
            'success': True,
            'token_out_amount': str(estimated_out),
            'token_out_denom': token_out_denom,
            'estimated': True,
            'method': 'calculation'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def execute_swap(key_name, from_token, to_token, amount):
    """Executa um swap real"""
    USDC = 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'
    POOL_ID = 1464
    try:
        amount = int(amount)
        if amount <= 0:
            return {'success': False, 'error': 'Quantidade inválida'}

        token_in_denom = 'uosmo' if from_token == 'uosmo' else USDC
        token_out_denom = 'uosmo' if to_token == 'uosmo' else USDC
        token_in_str = f"{amount}{token_in_denom}"

        command = (
            f"{OSMOSISD_PATH} tx gamm swap-exact-amount-in "
            f"{token_in_str} 1 "
            f"--swap-route-pool-ids {POOL_ID} "
            f"--swap-route-denoms {token_out_denom} "
            f"--from {key_name} "
            f"--chain-id {CHAIN_ID} "
            f"--node {NODE_URL} "
            f"--gas auto "
            f"--gas-adjustment 1.3 "
            f"--gas-prices 0.0025uosmo "
            f"--yes "
            f"--output json"
        )

        stdout, stderr, code = run_command(command)

        if code != 0:
            return {'success': False, 'error': stderr or 'Erro ao executar swap'}

        try:
            result = json.loads(stdout)
            if result.get('code', 0) != 0:
                return {
                    'success': False,
                    'error': result.get('raw_log', 'Erro desconhecido'),
                    'code': result.get('code')
                }
            return {
                'success': True,
                'tx_hash': result.get('txhash'),
                'height': result.get('height'),
                'gas_used': result.get('gas_used'),
                'gas_wanted': result.get('gas_wanted')
            }
        except json.JSONDecodeError:
            return {'success': False, 'error': 'Erro ao decodificar resposta'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ==================== ROTAS DA API ====================

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    state = get_price_state()
    uptime = time.time() - state['last_update'] if state.get('last_update') else None
    return jsonify({
        'status': 'ok',
        'service': 'wallet-backend',
        'price_available': state['price'] is not None,
        'price_update_count': state['update_count'],
        'price_last_update': state['timestamp'],
        'uptime_seconds': uptime
    })


@app.route('/api/price', methods=['GET'])
def api_get_price():
    """Retorna o preço atual do OSMO"""
    state = get_price_state()
    if state['price'] is None:
        return jsonify({
            'success': False,
            'error': state['error'] or 'Preço ainda não disponível'
        }), 503

    return jsonify({
        'success': True,
        'price': state['price'],
        'timestamp': state['timestamp'],
        'method': state['method'],
        'update_count': state['update_count'],
    })


@app.route('/api/keys', methods=['GET'])
def api_list_keys():
    """Lista chaves disponíveis"""
    return jsonify(list_keys())


@app.route('/api/balance/<address>', methods=['GET'])
def api_get_balance(address):
    """Consulta saldo de um endereço"""
    return jsonify(get_balance(address))


@app.route('/api/wallets', methods=['GET'])
def api_list_wallets():
    """Lista wallets configuradas"""
    wallets = [
        {
            'name': 'Wallet Principal',
            'address': 'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88',
            'key_name': 'wallet_osmo1sp8'
        }
    ]
    return jsonify({'success': True, 'wallets': wallets})


@app.route('/api/history', methods=['GET'])
def api_get_history():
    """Retorna histórico de klines OHLCV do OSMO buscado diretamente da CoinEx.
    Parâmetro opcional: ?timeframe=1m|15m|1h|4h|1d (padrão: 15m)
    """
    timeframe = request.args.get('timeframe', '15m')
    result = fetch_kline_history(timeframe)
    
    if not result['success']:
        return jsonify(result), 400 if 'inválido' in result.get('error', '') else 502
    
    return jsonify(result)


@app.route('/api/swap/simulate', methods=['POST'])
def api_simulate_swap():
    """Simula um swap"""
    data = request.get_json()
    from_token = data.get('from')
    to_token = data.get('to')
    amount = data.get('amount')

    if not all([from_token, to_token, amount]):
        return jsonify({'success': False, 'error': 'Parâmetros faltando'}), 400

    return jsonify(simulate_swap(from_token, to_token, amount))


@app.route('/api/swap/execute', methods=['POST'])
def api_execute_swap():
    """Executa um swap real"""
    data = request.get_json()
    from_token = data.get('from')
    to_token = data.get('to')
    amount = data.get('amount')
    address = data.get('address', 'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88')

    if not all([from_token, to_token, amount]):
        return jsonify({'success': False, 'error': 'Parâmetros faltando'}), 400

    key_name = KEY_MAPPING.get(address, 'wallet_osmo1sp8')
    return jsonify(execute_swap(key_name, from_token, to_token, amount))


@app.route('/api/ai/position', methods=['GET', 'OPTIONS'])
def api_ai_position():
    """Retorna sinal de posição baseado em EMA."""
    if request.method == 'OPTIONS':
        return ('', 204)

    from ia import get_position_signal
    timeframe = request.args.get('timeframe', '1h')
    
    result, error = get_position_signal(timeframe)
    
    if error:
        return jsonify({'success': False, 'error': error}), 400
    
    return jsonify({'success': True, **result})


@app.route('/api/ai/analyze', methods=['GET', 'OPTIONS'])
def api_ai_analyze():
    """Análise de mercado com IA via streaming SSE."""
    if request.method == 'OPTIONS':
        return ('', 204)

    timeframe = request.args.get('timeframe', '15m')
    
    resp = Response(
        stream_with_context(stream_ai_analysis(timeframe)),
        mimetype='text/event-stream; charset=utf-8',
    )
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


@app.route('/api/ai/chat', methods=['POST', 'OPTIONS'])
def api_ai_chat():
    """Proxy streaming para Hugging Face."""
    if request.method == 'OPTIONS':
        return ('', 204)

    token = hf_resolve_api_token()
    if not token:
        return jsonify({
            'error': (
                'Chave Hugging Face não encontrada. Crie um arquivo .env em backend/ ou na raiz com: '
                'HF_API_TOKEN=hf_... ou export HF_API_TOKEN=hf_... antes de iniciar o servidor.'
            ),
        }), 503

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': 'JSON inválido'}), 400

    messages = data.get('messages') or []
    if not messages:
        return jsonify({'error': 'messages obrigatório'}), 400

    payload = {
        'model': data.get('model', 'Qwen/Qwen3-Coder-Next:novita'),
        'messages': messages,
        'temperature': float(data.get('temperature', 0.7)),
        'stream': True,
        'max_tokens': 2000,
    }

    def stream_hf():
        try:
            with requests.post(
                'https://router.huggingface.co/v1/chat/completions',
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {token}',
                },
                json=payload,
                stream=True,
                timeout=(15, 120),
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

    resp = Response(
        stream_with_context(stream_hf()),
        mimetype='text/event-stream; charset=utf-8',
    )
    resp.headers['Cache-Control'] = 'no-cache'
    resp.headers['X-Accel-Buffering'] = 'no'
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


# ==================== INICIALIZAÇÃO ====================

def price_updater_thread():
    """Thread que atualiza o preço continuamente"""
    while True:
        try:
            update_price()
        except Exception:
            pass
        time.sleep(UPDATE_INTERVAL)


if __name__ == '__main__':
    price_thread = threading.Thread(target=price_updater_thread, daemon=True)
    price_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
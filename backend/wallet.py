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

from ia import hf_resolve_api_token, stream_ai_analysis
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
NODE_URL      = 'https://rpc.osmosis.zone:443'
CHAIN_ID      = 'osmosis-1'
POOL_ID       = 1464
USDC          = 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'
SLIPPAGE      = 0.01   # 1%
GAS_PRICES    = '0.04uosmo'   # fee mínima atual da rede Osmosis
GAS_ADJUSTMENT = '1.4'        # margem sobre o gas estimado

# Mapeamento de chaves
KEY_MAPPING = {
    'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88': 'wallet_osmo1sp8'
}


def run_command(command):
    """Executa comando shell e retorna (stdout, stderr, returncode)."""
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
        return None, 'Timeout', 1
    except Exception as e:
        return None, str(e), 1


# ==================== FUNÇÕES DE WALLET ====================

def get_balance(address):
    if not address.startswith('osmo1'):
        return {'success': False, 'error': 'Endereço inválido'}

    stdout, stderr, code = run_command(
        f"{OSMOSISD_PATH} query bank balances {address} --node {NODE_URL} --output json"
    )
    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao consultar saldo'}

    try:
        data = json.loads(stdout)
        return {'success': True, 'address': address, 'balances': data.get('balances', [])}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta'}


def list_keys():
    stdout, stderr, code = run_command(
        f"{OSMOSISD_PATH} keys list --output json"
    )
    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao listar chaves'}

    try:
        return {'success': True, 'keys': json.loads(stdout)}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta'}


def estimate_swap_out(from_token, amount):
    """Consulta a pool via osmosisd e retorna o valor real de saída.

    Sintaxe: estimate-swap-exact-amount-in [pool-id] [sender] [token-in]
             --swap-route-pool-ids --swap-route-denoms
    Retorna (token_out_amount: int, error: str|None)
    """
    token_in_denom  = 'uosmo' if from_token == 'uosmo' else USDC
    token_out_denom = USDC if from_token == 'uosmo' else 'uosmo'
    token_in_str    = f"{amount}{token_in_denom}"
    sender          = next(iter(KEY_MAPPING))

    stdout, stderr, code = run_command(
        f"{OSMOSISD_PATH} query gamm estimate-swap-exact-amount-in "
        f"{POOL_ID} {sender} {token_in_str} "
        f"--swap-route-pool-ids={POOL_ID} "
        f"--swap-route-denoms={token_out_denom} "
        f"--node {NODE_URL} --output json"
    )

    if code != 0:
        return None, stderr.strip() or 'Erro ao estimar swap'

    try:
        data = json.loads(stdout)
        raw = data.get('token_out_amount') or data.get('tokenOutAmount', '0')
        return int(raw), None
    except (json.JSONDecodeError, ValueError) as e:
        return None, str(e)


def simulate_swap(from_token, to_token, amount):
    """Simula swap consultando a pool real via osmosisd."""
    try:
        amount = int(amount)
        if amount <= 0:
            return {'success': False, 'error': 'Quantidade inválida'}

        estimated_out, error = estimate_swap_out(from_token, amount)

        if error or estimated_out is None:
            return {'success': False, 'error': error or 'Não foi possível estimar'}

        token_out_min = int(estimated_out * (1 - SLIPPAGE))
        token_out_denom = USDC if from_token == 'uosmo' else 'uosmo'

        return {
            'success': True,
            'token_out_amount': str(estimated_out),
            'token_out_min': str(token_out_min),
            'token_out_denom': token_out_denom,
            'slippage_pct': SLIPPAGE * 100,
            'method': 'osmosisd_estimate',
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def execute_swap(key_name, from_token, to_token, amount):
    """Executa swap real com token_out_min calculado via estimativa da pool."""
    try:
        amount = int(amount)
        if amount <= 0:
            return {'success': False, 'error': 'Quantidade inválida'}

        # Estima saída real pela pool
        estimated_out, error = estimate_swap_out(from_token, amount)
        if error or estimated_out is None:
            return {'success': False, 'error': f'Erro ao estimar slippage: {error}'}

        token_in_denom  = 'uosmo' if from_token == 'uosmo' else USDC
        token_out_denom = 'uosmo' if to_token   == 'uosmo' else USDC
        token_in_str    = f"{amount}{token_in_denom}"
        token_out_min   = int(estimated_out * (1 - SLIPPAGE))

        command = (
            f"{OSMOSISD_PATH} tx gamm swap-exact-amount-in "
            f"{token_in_str} {token_out_min} "
            f"--swap-route-pool-ids {POOL_ID} "
            f"--swap-route-denoms {token_out_denom} "
            f"--from {key_name} "
            f"--chain-id {CHAIN_ID} "
            f"--node {NODE_URL} "
            f"--gas auto "
            f"--gas-adjustment {GAS_ADJUSTMENT} "
            f"--gas-prices {GAS_PRICES} "
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
                    'code': result.get('code'),
                }
            return {
                'success': True,
                'tx_hash': result.get('txhash'),
                'height': result.get('height'),
                'gas_used': result.get('gas_used'),
                'gas_wanted': result.get('gas_wanted'),
                'token_out_min': str(token_out_min),
                'estimated_out': str(estimated_out),
                'slippage_pct': SLIPPAGE * 100,
            }
        except json.JSONDecodeError:
            return {'success': False, 'error': 'Erro ao decodificar resposta'}

    except Exception as e:
        return {'success': False, 'error': str(e)}


# ==================== ROTAS DA API ====================

@app.route('/api/health', methods=['GET'])
def health():
    state  = get_price_state()
    uptime = time.time() - state['last_update'] if state.get('last_update') else None
    return jsonify({
        'status': 'ok',
        'service': 'wallet-backend',
        'price_available': state['price'] is not None,
        'price_update_count': state['update_count'],
        'price_last_update': state['timestamp'],
        'uptime_seconds': uptime,
    })


@app.route('/api/price', methods=['GET'])
def api_get_price():
    state = get_price_state()
    if state['price'] is None:
        return jsonify({'success': False, 'error': state['error'] or 'Preço ainda não disponível'}), 503
    return jsonify({
        'success': True,
        'price': state['price'],
        'timestamp': state['timestamp'],
        'method': state['method'],
        'update_count': state['update_count'],
    })


@app.route('/api/keys', methods=['GET'])
def api_list_keys():
    return jsonify(list_keys())


@app.route('/api/balance/<address>', methods=['GET'])
def api_get_balance(address):
    return jsonify(get_balance(address))


@app.route('/api/wallets', methods=['GET'])
def api_list_wallets():
    result = list_keys()
    if not result.get('success'):
        return jsonify(result)
    
    wallets = []
    for key in result.get('keys', []):
        wallets.append({
            'name': key.get('name', 'Sem nome'),
            'address': key.get('address', ''),
            'key_name': key.get('name', ''),
        })
    
    return jsonify({'success': True, 'wallets': wallets})


@app.route('/api/history', methods=['GET'])
def api_get_history():
    timeframe = request.args.get('timeframe', '15m')
    result    = fetch_kline_history(timeframe)
    if not result['success']:
        status = 400 if 'inválido' in result.get('error', '') else 502
        return jsonify(result), status
    return jsonify(result)


@app.route('/api/wallet/restore', methods=['POST'])
def api_wallet_restore():
    """Restaura uma carteira a partir do mnemônico via osmosisd keys add --recover."""
    data     = request.get_json()
    name     = (data.get('name') or '').strip()
    mnemonic = (data.get('mnemonic') or '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Nome da chave é obrigatório'}), 400
    if not mnemonic:
        return jsonify({'success': False, 'error': 'Mnemônico é obrigatório'}), 400

    # Passa o mnemônico via stdin para evitar que apareça no histórico do shell
    command = f"{OSMOSISD_PATH} keys add {name} --recover --output json"
    try:
        result = subprocess.run(
            command,
            shell=True,
            input=mnemonic + '\n',
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip() or 'Erro ao restaurar chave'
            return jsonify({'success': False, 'error': err})

        # Tenta parsear a saída JSON para retornar o endereço
        try:
            out = json.loads(result.stdout or result.stderr)
            address = out.get('address', '')
        except (json.JSONDecodeError, AttributeError):
            address = ''

        return jsonify({'success': True, 'name': name, 'address': address})

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Timeout ao restaurar carteira'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/wallet/delete', methods=['POST'])
def api_wallet_delete():
    """Remove uma chave do keyring via osmosisd keys delete."""
    data    = request.get_json()
    address = (data.get('address') or '').strip()

    if not address:
        return jsonify({'success': False, 'error': 'Endereço é obrigatório'}), 400

    # Resolve o nome da chave pelo endereço
    key_name = KEY_MAPPING.get(address)
    if not key_name:
        # Tenta buscar pelo endereço direto na listagem
        keys_result = list_keys()
        if keys_result.get('success'):
            for k in keys_result.get('keys', []):
                if k.get('address') == address:
                    key_name = k.get('name')
                    break

    if not key_name:
        return jsonify({'success': False, 'error': 'Chave não encontrada para este endereço'})

    stdout, stderr, code = run_command(
        f"{OSMOSISD_PATH} keys delete {key_name} --yes --output json"
    )

    if code != 0:
        return jsonify({'success': False, 'error': stderr.strip() or 'Erro ao excluir chave'})

    # Remove do mapeamento em memória se existir
    KEY_MAPPING.pop(address, None)

    return jsonify({'success': True, 'name': key_name})


@app.route('/api/swap/gasinfo', methods=['GET'])
def api_swap_gasinfo():
    """Retorna as configurações atuais de gas e slippage."""
    return jsonify({
        'success': True,
        'gas_prices': GAS_PRICES,
        'gas_adjustment': GAS_ADJUSTMENT,
        'slippage_pct': SLIPPAGE * 100,
    })


@app.route('/api/swap/simulate', methods=['POST'])
def api_simulate_swap():
    data      = request.get_json()
    from_token = data.get('from')
    to_token   = data.get('to')
    amount     = data.get('amount')

    if not all([from_token, to_token, amount]):
        return jsonify({'success': False, 'error': 'Parâmetros faltando'}), 400

    return jsonify(simulate_swap(from_token, to_token, amount))


@app.route('/api/swap/execute', methods=['POST'])
def api_execute_swap():
    data       = request.get_json()
    from_token  = data.get('from')
    to_token    = data.get('to')
    amount      = data.get('amount')
    address     = data.get('address', 'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88')

    if not all([from_token, to_token, amount]):
        return jsonify({'success': False, 'error': 'Parâmetros faltando'}), 400

    key_name = KEY_MAPPING.get(address, 'wallet_osmo1sp8')
    return jsonify(execute_swap(key_name, from_token, to_token, amount))


@app.route('/api/ai/position', methods=['GET', 'OPTIONS'])
def api_ai_position():
    if request.method == 'OPTIONS':
        return ('', 204)

    from ia import get_position_signal
    timeframe      = request.args.get('timeframe', '1h')
    result, error  = get_position_signal(timeframe)

    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **result})


@app.route('/api/ai/analyze', methods=['GET', 'OPTIONS'])
def api_ai_analyze():
    if request.method == 'OPTIONS':
        return ('', 204)

    timeframe = request.args.get('timeframe', '15m')
    resp = Response(
        stream_with_context(stream_ai_analysis(timeframe)),
        mimetype='text/event-stream; charset=utf-8',
    )
    resp.headers['Cache-Control']               = 'no-cache'
    resp.headers['X-Accel-Buffering']           = 'no'
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


@app.route('/api/ai/chat', methods=['POST', 'OPTIONS'])
def api_ai_chat():
    if request.method == 'OPTIONS':
        return ('', 204)

    token = hf_resolve_api_token()
    if not token:
        return jsonify({'error': 'Chave Hugging Face não encontrada. Configure HF_API_TOKEN no .env'}), 503

    data     = request.get_json(silent=True)
    messages = (data or {}).get('messages') or []
    if not messages:
        return jsonify({'error': 'messages obrigatório'}), 400

    import requests as req
    payload = {
        'model': data.get('model', 'Qwen/Qwen3-Coder-Next:novita'),
        'messages': messages,
        'temperature': float(data.get('temperature', 0.7)),
        'stream': True,
        'max_tokens': 2000,
    }

    def stream_hf():
        try:
            with req.post(
                'https://router.huggingface.co/v1/chat/completions',
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
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
        except req.RequestException as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'.encode('utf-8')

    resp = Response(stream_with_context(stream_hf()), mimetype='text/event-stream; charset=utf-8')
    resp.headers['Cache-Control']               = 'no-cache'
    resp.headers['X-Accel-Buffering']           = 'no'
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


# ==================== INICIALIZAÇÃO ====================

def price_updater_thread():
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
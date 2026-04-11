#!/usr/bin/env python3
"""
Backend de Wallet Osmosis em Python
API REST para gerenciamento de wallets, swaps e preço OSMO em tempo real
"""
import os
import json
import subprocess
import threading
import time
from datetime import datetime, timezone
import requests

from flask import Flask, Response, jsonify, request, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(
    app,
    origins='*',
    allow_headers='*',
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    expose_headers='*',
)


def _read_hf_token_line_from_file(path):
    """Primeira linha útil: comentários # ignorados; token deve começar com hf_."""
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith('#'):
                    continue
                if s.startswith('hf_'):
                    return s
    except OSError:
        pass
    return ''


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
                        val = line[len(prefix) :].strip()
                        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                            val = val[1:-1]
                        if val.startswith('hf_'):
                            return val
    except OSError:
        pass
    return ''


def hf_token_search_paths():
    """Caminhos absolutos verificados (para mensagem de erro)."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)
    out = []
    for root in (script_dir, parent):
        for name in ('.env', 'hf_token.txt', '.hf_token'):
            out.append(os.path.abspath(os.path.join(root, name)))
    return out


def hf_resolve_api_token():
    """Token HF: variável de ambiente, .env ou hf_token.txt / .hf_token em backend/ e bot/."""
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
    for root in (script_dir, parent):
        for name in ('hf_token.txt', '.hf_token'):
            path = os.path.join(root, name)
            t = _read_hf_token_line_from_file(path)
            if t:
                return t
    return ''

# Configurações Wallet
OSMOSISD_PATH = '/usr/local/bin/osmosisd'
NODE_URL = 'https://rpc.osmosis.zone:443'
CHAIN_ID = 'osmosis-1'
POOL_ID = 1464
USDC_DENOM = 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'
OSMO_DENOM = 'uosmo'

# Configurações Preço
UPDATE_INTERVAL = 1  # segundos

# Mapeamento de chaves
KEY_MAPPING = {
    'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88': 'wallet_osmo1sp8'
}

# Estado global do preço
_price_state = {
    'price': None,
    'timestamp': None,
    'error': None,
    'updating': False,
    'last_update': None,
    'update_count': 0,
    'method': None,
    'pool_liquidity': None
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


# ==================== FUNÇÕES DE PREÇO ====================



def update_price():
    """Atualiza o preço OSMO via ticker da CoinEx."""
    global _price_state

    _price_state['updating'] = True

    try:
        url = f'https://api.coinex.com/v2/spot/ticker?market={COINEX_MARKET}'
        resp = requests.get(url, timeout=10, headers={'Accept': 'application/json'})
        resp.raise_for_status()
        data = resp.json()

        if data.get('code') != 0 or not isinstance(data.get('data'), list) or not data['data']:
            _price_state['error'] = f'CoinEx ticker erro: {data.get("message", "resposta inválida")}'
            return

        price = float(data['data'][0]['last'])
        if not price or price <= 0:
            _price_state['error'] = 'CoinEx: preço inválido recebido'
            return

        _price_state['price'] = price
        _price_state['method'] = 'coinex_ticker'
        _price_state['pool_liquidity'] = None
        _price_state['timestamp'] = datetime.now(timezone.utc).isoformat()
        _price_state['error'] = None
        _price_state['last_update'] = time.time()
        _price_state['update_count'] += 1

    except requests.RequestException as e:
        _price_state['error'] = f'Erro ao acessar CoinEx: {str(e)}'
    except Exception as e:
        _price_state['error'] = f'Erro inesperado: {str(e)}'
    finally:
        _price_state['updating'] = False


def price_updater_thread():
    """Thread que atualiza o preço continuamente"""
    while True:
        try:
            update_price()
        except Exception as e:
            pass
        time.sleep(UPDATE_INTERVAL)


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
    try:
        amount = int(amount)
        if amount <= 0:
            return {'success': False, 'error': 'Quantidade inválida'}
        
        # Estimativa simples baseada em preço
        if from_token == 'uosmo':
            estimated_out = int(amount * 0.03)
            token_out_denom = USDC_DENOM
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
    try:
        amount = int(amount)
        if amount <= 0:
            return {'success': False, 'error': 'Quantidade inválida'}
        
        # Determina tokens
        token_in_denom = 'uosmo' if from_token == 'uosmo' else USDC_DENOM
        token_out_denom = 'uosmo' if to_token == 'uosmo' else USDC_DENOM
        
        # Formata token_in
        token_in_str = f"{amount}{token_in_denom}"
        token_out_min = "1"
        
        # Monta comando
        command = (
            f"{OSMOSISD_PATH} tx gamm swap-exact-amount-in "
            f"{token_in_str} {token_out_min} "
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
    uptime = time.time() - _price_state.get('last_update', time.time()) if _price_state.get('last_update') else None
    
    return jsonify({
        'status': 'ok',
        'service': 'wallet-backend',
        'price_available': _price_state['price'] is not None,
        'price_update_count': _price_state['update_count'],
        'price_last_update': _price_state['timestamp'],
        'uptime_seconds': uptime
    })


@app.route('/api/price', methods=['GET'])
def api_get_price():
    """Retorna o preço atual do OSMO"""
    if _price_state['price'] is None:
        return jsonify({
            'success': False,
            'error': _price_state['error'] or 'Preço ainda não disponível'
        }), 503
    
    response = {
        'success': True,
        'price': _price_state['price'],
        'timestamp': _price_state['timestamp'],
        'source': f'osmosis_pool_{POOL_ID}',
        'update_count': _price_state['update_count']
    }
    
    if _price_state['pool_liquidity']:
        response['pool_liquidity'] = _price_state['pool_liquidity']
    
    if _price_state.get('method'):
        response['method'] = _price_state['method']
    
    return jsonify(response)

@app.route('/api/keys', methods=['GET'])
def api_list_keys():
    """Lista chaves disponíveis"""
    result = list_keys()
    return jsonify(result)

@app.route('/api/balance/<address>', methods=['GET'])
def api_get_balance(address):
    """Consulta saldo de um endereço"""
    result = get_balance(address)
    return jsonify(result)

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

# Mapeamento de timeframe (parâmetro do JS) -> intervalo aceito pela CoinEx v2
COINEX_INTERVAL_MAP = {
    '1m':  '1min',
    '15m': '15min',
    '1h':  '1hour',
    '4h':  '4hour',
    '1d':  '1day',
}
COINEX_MARKET = 'OSMOUSDT'
COINEX_KLINE_LIMIT = 200


def fetch_coinex_klines(timeframe='15m'):
    """Busca klines OHLCV da CoinEx v2 e retorna no formato { price, timestamp } esperado pelo JS."""
    interval = COINEX_INTERVAL_MAP.get(timeframe, '15min')
    url = (
        f'https://api.coinex.com/v2/spot/kline'
        f'?market={COINEX_MARKET}&period={interval}&limit={COINEX_KLINE_LIMIT}'
    )
    try:
        resp = requests.get(url, timeout=10, headers={'Accept': 'application/json'})
        resp.raise_for_status()
        data = resp.json()

        if data.get('code') != 0 or not isinstance(data.get('data'), list):
            return {'success': False, 'error': f'CoinEx erro: {data.get("message", "resposta inválida")}'}

        # CoinEx v2 retorna dicionários: { created_at, open, high, low, close, volume, ... }
        history = []
        for k in data['data']:
            try:
                # Suporta tanto dict (v2) quanto lista (v1)
                if isinstance(k, dict):
                    ts_ms = int(k.get('created_at', k.get('timestamp', 0)))
                    o     = float(k['open'])
                    h     = float(k['high'])
                    l     = float(k['low'])
                    c     = float(k['close'])
                    vol   = float(k.get('volume', 0))
                else:
                    ts_ms = int(k[0])
                    o     = float(k[1])
                    c     = float(k[2])
                    h     = float(k[3])
                    l     = float(k[4])
                    vol   = float(k[5])

                if ts_ms <= 0 or c <= 0:
                    continue

                history.append({
                    'price':     c,
                    'open':      o,
                    'high':      h,
                    'low':       l,
                    'close':     c,
                    'volume':    vol,
                    'timestamp': datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(),
                    'currency':  'USD',
                    'source':    'coinex',
                })
            except (KeyError, IndexError, ValueError, TypeError):
                continue

        # Retorna do mais recente para o mais antigo (mesmo padrão do histórico antigo)
        history.reverse()
        return {'success': True, 'history': history}

    except requests.RequestException as e:
        return {'success': False, 'error': f'Erro ao acessar CoinEx: {str(e)}'}


@app.route('/api/history', methods=['GET'])
def api_get_history():
    """Retorna histórico de klines OHLCV do OSMO buscado diretamente da CoinEx.
    Parâmetro opcional: ?timeframe=1m|15m|1h|4h|1d (padrão: 15m)
    """
    timeframe = request.args.get('timeframe', '15m')
    if timeframe not in COINEX_INTERVAL_MAP:
        return jsonify({'success': False, 'error': f'Timeframe inválido. Use: {list(COINEX_INTERVAL_MAP.keys())}'}), 400

    result = fetch_coinex_klines(timeframe)
    if not result['success']:
        return jsonify(result), 502

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
    
    result = simulate_swap(from_token, to_token, amount)
    return jsonify(result)

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
    
    # Obtém nome da chave
    key_name = KEY_MAPPING.get(address, 'wallet_osmo1sp8')
    
    result = execute_swap(key_name, from_token, to_token, amount)
    return jsonify(result)

@app.route('/api/pool/<int:pool_id>', methods=['GET'])
def api_get_pool(pool_id):
    """Consulta informações de uma pool"""
    command = f"{OSMOSISD_PATH} query gamm pool {pool_id} --node {NODE_URL} --output json"
    stdout, stderr, code = run_command(command)
    
    if code != 0:
        return jsonify({'success': False, 'error': stderr or 'Erro ao consultar pool'})
    
    try:
        data = json.loads(stdout)
        return jsonify({'success': True, 'pool': data})
    except json.JSONDecodeError:
        return jsonify({'success': False, 'error': 'Erro ao decodificar resposta'})


@app.route('/api/ai/chat', methods=['POST', 'OPTIONS'])
def api_ai_chat():
    """Proxy streaming para Hugging Face (substitui hg.php)."""
    if request.method == 'OPTIONS':
        return ('', 204)

    token = hf_resolve_api_token()
    if not token:
        checked = '; '.join(hf_token_search_paths())
        resp = jsonify({
            'error': (
                'Chave Hugging Face não encontrada. Opções: (1) export HF_API_TOKEN=hf_... antes de iniciar o '
                'wallet.py; (2) arquivo bot/.env ou backend/.env com linha HF_API_TOKEN=hf_...; '
                '(3) arquivo bot/hf_token.txt ou backend/hf_token.txt com uma linha hf_... '
                f'Arquivos verificados: {checked}'
            ),
        })
        resp.status_code = 503
        return resp

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
                    yield f'data: {json.dumps({"error": body or r.reason, "code": r.status_code})}\n\n'.encode(
                        'utf-8'
                    )
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

if __name__ == '__main__':
    price_thread = threading.Thread(target=price_updater_thread, daemon=True)
    price_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
#!/usr/bin/env python3
"""
wallet.py — Backend Flask do projeto Quantum
API REST para gerenciamento de wallets, swaps e preço OSMO em tempo real.
A lógica de swap foi movida para swap.py.
"""
import json
import subprocess
import threading
import time
from pathlib import Path

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
from swap import (
    KEY_MAPPING,
    SLIPPAGE,
    GAS_PRICES,
    GAS_ADJUSTMENT,
    OSMOSISD_PATH,
    execute_swap,
    get_balance,
    simulate_swap,
    load_trades,
)

KEY_MAPPING_FILE = Path(__file__).parent / 'key_mapping.json'

app = Flask(__name__)
CORS(
    app,
    origins='*',
    allow_headers='*',
    methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    expose_headers='*',
)


# ── Helpers de wallet (não-swap) ───────────────────────────────

def list_keys():
    stdout, stderr, code = _run_command(f"{OSMOSISD_PATH} keys list --output json")
    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao listar chaves'}
    try:
        return {'success': True, 'keys': json.loads(stdout)}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta'}


def _run_command(command):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, 'Timeout', 1
    except Exception as e:
        return None, str(e), 1


def _save_key_mapping():
    """Persiste KEY_MAPPING em disco. Loga warning em caso de falha."""
    try:
        KEY_MAPPING_FILE.write_text(
            json.dumps(KEY_MAPPING, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
    except OSError as e:
        app.logger.warning('Não foi possível salvar key_mapping.json: %s', e)


# ── Rotas: Health & Preço ──────────────────────────────────────

@app.route('/api/health', methods=['GET'])
def health():
    state  = get_price_state()
    uptime = time.time() - state['last_update'] if state.get('last_update') else None
    return jsonify({
        'status':              'ok',
        'service':             'quantum-backend',
        'price_available':     state['price'] is not None,
        'price_update_count':  state['update_count'],
        'price_last_update':   state['timestamp'],
        'uptime_seconds':      uptime,
    })


@app.route('/api/price', methods=['GET'])
def api_get_price():
    state = get_price_state()
    if state['price'] is None:
        return jsonify({'success': False, 'error': state['error'] or 'Preço ainda não disponível'}), 503
    return jsonify({
        'success':      True,
        'price':        state['price'],
        'timestamp':    state['timestamp'],
        'method':       state['method'],
        'update_count': state['update_count'],
    })


@app.route('/api/history', methods=['GET'])
def api_get_history():
    timeframe = request.args.get('timeframe', '15m')
    result    = fetch_kline_history(timeframe)
    if not result['success']:
        status = 400 if 'inválido' in result.get('error', '') else 502
        return jsonify(result), status
    return jsonify(result)


# ── Rotas: Wallet ──────────────────────────────────────────────

@app.route('/api/keys', methods=['GET'])
def api_list_keys():
    return jsonify(list_keys())


@app.route('/api/wallets', methods=['GET'])
def api_list_wallets():
    result = list_keys()
    if not result.get('success'):
        return jsonify(result)
    wallets = [
        {
            'name':     k.get('name', 'Sem nome'),
            'address':  k.get('address', ''),
            'key_name': k.get('name', ''),
        }
        for k in result.get('keys', [])
    ]
    return jsonify({'success': True, 'wallets': wallets})


@app.route('/api/balance/<address>', methods=['GET'])
def api_get_balance(address):
    return jsonify(get_balance(address))


@app.route('/api/wallet/restore', methods=['POST'])
def api_wallet_restore():
    data     = request.get_json()
    name     = (data.get('name')     or '').strip()
    mnemonic = (data.get('mnemonic') or '').strip()

    if not name:
        return jsonify({'success': False, 'error': 'Nome da chave é obrigatório'}), 400
    if not mnemonic:
        return jsonify({'success': False, 'error': 'Mnemônico é obrigatório'}), 400

    command = f"{OSMOSISD_PATH} keys add {name} --recover --output json"
    try:
        result = subprocess.run(
            command, shell=True, input=mnemonic + '\n',
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            err = result.stderr.strip() or result.stdout.strip() or 'Erro ao restaurar chave'
            return jsonify({'success': False, 'error': err})

        try:
            out     = json.loads(result.stdout or result.stderr)
            address = out.get('address', '')
        except (json.JSONDecodeError, AttributeError):
            address = ''

        # ── Atualiza key_mapping em memória e em disco ─────────
        if address:
            KEY_MAPPING[address] = name
            _save_key_mapping()

        return jsonify({'success': True, 'name': name, 'address': address})

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Timeout ao restaurar carteira'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/wallet/delete', methods=['POST'])
def api_wallet_delete():
    data    = request.get_json()
    address = (data.get('address') or '').strip()

    if not address:
        return jsonify({'success': False, 'error': 'Endereço é obrigatório'}), 400

    key_name = KEY_MAPPING.get(address)
    if not key_name:
        keys_result = list_keys()
        if keys_result.get('success'):
            for k in keys_result.get('keys', []):
                if k.get('address') == address:
                    key_name = k.get('name')
                    break

    if not key_name:
        return jsonify({'success': False, 'error': 'Chave não encontrada para este endereço'})

    stdout, stderr, code = _run_command(
        f"{OSMOSISD_PATH} keys delete {key_name} --yes --output json"
    )
    if code != 0:
        return jsonify({'success': False, 'error': stderr.strip() or 'Erro ao excluir chave'})

    # ── Atualiza key_mapping em memória e em disco ─────────────
    KEY_MAPPING.pop(address, None)
    _save_key_mapping()

    return jsonify({'success': True, 'name': key_name})


# ── Rotas: Swap ────────────────────────────────────────────────

@app.route('/api/swap/gasinfo', methods=['GET'])
def api_swap_gasinfo():
    return jsonify({
        'success':        True,
        'gas_prices':     GAS_PRICES,
        'gas_adjustment': GAS_ADJUSTMENT,
        'slippage_pct':   SLIPPAGE * 100,
    })


@app.route('/api/swap/simulate', methods=['POST'])
def api_simulate_swap():
    data       = request.get_json()
    from_token = data.get('from')
    to_token   = data.get('to')
    amount     = data.get('amount')

    if not all([from_token, to_token, amount]):
        return jsonify({'success': False, 'error': 'Parâmetros faltando'}), 400

    return jsonify(simulate_swap(from_token, to_token, int(amount)))


@app.route('/api/swap/execute', methods=['POST'])
def api_execute_swap():
    data       = request.get_json()
    from_token = data.get('from')
    to_token   = data.get('to')
    amount     = data.get('amount')
    address    = data.get('address', '').strip()

    if not all([from_token, to_token, amount, address]):
        return jsonify({'success': False, 'error': 'Parâmetros faltando (from, to, amount, address)'}), 400

    return jsonify(execute_swap(address, from_token, to_token, int(amount)))


# ── Rotas: Histórico de Trades ─────────────────────────────────

@app.route('/api/trades', methods=['GET'])
def api_get_trades():
    trades = load_trades()
    return jsonify({'success': True, 'trades': trades, 'total': len(trades)})


# ── Rotas: IA ─────────────────────────────────────────────────

@app.route('/api/ai/analyze', methods=['GET', 'OPTIONS'])
def api_ai_analyze():
    if request.method == 'OPTIONS':
        return ('', 204)

    timeframe = request.args.get('timeframe', '15m')
    address   = request.args.get('address', '').strip()

    if not address:
        return jsonify({'success': False, 'error': 'Parâmetro address obrigatório'}), 400

    resp = Response(
        stream_with_context(stream_ai_analysis(address, timeframe)),
        mimetype='text/event-stream; charset=utf-8',
    )
    resp.headers['Cache-Control']               = 'no-cache'
    resp.headers['X-Accel-Buffering']           = 'no'
    resp.headers['Access-Control-Allow-Origin']  = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp


@app.route('/api/ai/position', methods=['GET', 'OPTIONS'])
def api_ai_position():
    if request.method == 'OPTIONS':
        return ('', 204)

    from ia import get_position_signal
    timeframe = request.args.get('timeframe', '1h')
    address   = request.args.get('address', '').strip()

    if not address:
        return jsonify({'success': False, 'error': 'Parâmetro address obrigatório'}), 400

    result, error = get_position_signal(address, timeframe)
    if error:
        return jsonify({'success': False, 'error': error}), 400
    return jsonify({'success': True, **result})


@app.route('/api/ai/chat', methods=['POST', 'OPTIONS'])
def api_ai_chat():
    if request.method == 'OPTIONS':
        return ('', 204)

    token = hf_resolve_api_token()
    if not token:
        return jsonify({'error': 'Chave Hugging Face não encontrada. Configure HF_API_TOKEN no .env'}), 503

    import requests as req
    data     = request.get_json(silent=True)
    messages = (data or {}).get('messages') or []
    if not messages:
        return jsonify({'error': 'messages obrigatório'}), 400

    payload = {
        'model':       data.get('model', 'Qwen/Qwen3-235B-A22B:novita'),
        'messages':    messages,
        'temperature': float(data.get('temperature', 0.7)),
        'stream':      True,
        'max_tokens':  2000,
    }

    def stream_hf():
        try:
            with req.post(
                'https://router.huggingface.co/v1/chat/completions',
                headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'},
                json=payload, stream=True, timeout=(15, 120),
            ) as r:
                if r.status_code >= 400:
                    yield f'data: {json.dumps({"error": (r.text or "")[:1200] or r.reason, "code": r.status_code})}\n\n'.encode('utf-8')
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


# ── Inicialização ──────────────────────────────────────────────

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
#!/usr/bin/env python3
"""
swap.py — Tool de swap OSMO/USDC
Usada pela IA e diretamente pela API.
Persiste histórico de trades em trades.json.
"""
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Configurações ──────────────────────────────────────────────
OSMOSISD_PATH  = '/usr/local/bin/osmosisd'
NODE_URL       = 'https://rpc.osmosis.zone:443'
CHAIN_ID       = 'osmosis-1'
POOL_ID        = 1464
USDC           = 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'
SLIPPAGE       = 0.01   # 1%
GAS_PRICES     = '0.04uosmo'
GAS_ADJUSTMENT = '1.4'

TRADES_FILE = Path(__file__).parent / 'trades.json'

# ── Mapeamento de chaves (carregado de env ou arquivo) ─────────
def _load_key_mapping() -> dict:
    raw = os.environ.get('KEY_MAPPING_JSON', '')
    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    mapping_file = Path(__file__).parent / 'key_mapping.json'
    if mapping_file.exists():
        try:
            return json.loads(mapping_file.read_text())
        except Exception:
            pass
    return {}

KEY_MAPPING: dict = _load_key_mapping()


# ── Histórico de trades ────────────────────────────────────────

def load_trades() -> list:
    if not TRADES_FILE.exists():
        return []
    try:
        return json.loads(TRADES_FILE.read_text(encoding='utf-8'))
    except Exception:
        return []


def save_trade(entry: dict) -> None:
    trades = load_trades()
    trades.append(entry)
    TRADES_FILE.write_text(json.dumps(trades, ensure_ascii=False, indent=2), encoding='utf-8')


def get_last_trade() -> dict | None:
    trades = load_trades()
    return trades[-1] if trades else None


# ── Shell helper ───────────────────────────────────────────────

def _run(command: str):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30
        )
        return result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired:
        return None, 'Timeout', 1
    except Exception as e:
        return None, str(e), 1


# ── Estimativa de saída ────────────────────────────────────────

def estimate_swap_out(from_token: str, amount: int):
    """Consulta a pool e retorna (token_out_amount: int, error: str|None)."""
    token_in_denom  = 'uosmo' if from_token == 'uosmo' else USDC
    token_out_denom = USDC    if from_token == 'uosmo' else 'uosmo'
    token_in_str    = f"{amount}{token_in_denom}"
    sender          = next(iter(KEY_MAPPING), '')

    stdout, stderr, code = _run(
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
        raw  = data.get('token_out_amount') or data.get('tokenOutAmount', '0')
        return int(raw), None
    except (json.JSONDecodeError, ValueError) as e:
        return None, str(e)


# ── Simulação ──────────────────────────────────────────────────

def simulate_swap(from_token: str, to_token: str, amount: int) -> dict:
    """Retorna estimativa de saída sem executar o swap."""
    if amount <= 0:
        return {'success': False, 'error': 'Quantidade inválida'}

    estimated_out, error = estimate_swap_out(from_token, amount)
    if error or estimated_out is None:
        return {'success': False, 'error': error or 'Não foi possível estimar'}

    token_out_denom = USDC if from_token == 'uosmo' else 'uosmo'
    token_out_min   = int(estimated_out * (1 - SLIPPAGE))

    return {
        'success':          True,
        'token_out_amount': str(estimated_out),
        'token_out_min':    str(token_out_min),
        'token_out_denom':  token_out_denom,
        'slippage_pct':     SLIPPAGE * 100,
        'method':           'osmosisd_estimate',
    }


# ── Saldo ──────────────────────────────────────────────────────

def get_balance(address: str) -> dict:
    if not address.startswith('osmo1'):
        return {'success': False, 'error': 'Endereço inválido'}

    stdout, stderr, code = _run(
        f"{OSMOSISD_PATH} query bank balances {address} --node {NODE_URL} --output json"
    )
    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao consultar saldo'}
    try:
        data = json.loads(stdout)
        return {'success': True, 'address': address, 'balances': data.get('balances', [])}
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta'}


def _parse_balances(balances: list) -> dict:
    """Extrai OSMO e USDC do array de balances."""
    osmo = usdc = 0.0
    for b in balances:
        if b.get('denom') == 'uosmo':
            osmo = int(b['amount']) / 1_000_000
        elif b.get('denom') == USDC:
            usdc = int(b['amount']) / 1_000_000
    return {'osmo': osmo, 'usdc': usdc}


# ── Execução ───────────────────────────────────────────────────

def execute_swap(address: str, from_token: str, to_token: str, amount: int) -> dict:
    """
    Executa o swap, persiste o trade e retorna o resultado.

    Parâmetros
    ----------
    address    : endereço osmo1… do remetente
    from_token : 'uosmo' ou denom USDC
    to_token   : 'uosmo' ou denom USDC
    amount     : quantidade em micro-unidades (uosmo ou uusdc)
    """
    if amount <= 0:
        return {'success': False, 'error': 'Quantidade inválida'}

    key_name = KEY_MAPPING.get(address)
    if not key_name:
        return {'success': False, 'error': f'Chave não encontrada para {address}. '
                                            'Verifique key_mapping.json ou KEY_MAPPING_JSON.'}

    # Saldo antes
    bal_before_raw = get_balance(address)
    saldo_antes    = _parse_balances(bal_before_raw.get('balances', []))

    # Estima saída real
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
        f"--yes --output json"
    )

    stdout, stderr, code = _run(command)
    if code != 0:
        return {'success': False, 'error': stderr or 'Erro ao executar swap'}

    try:
        result = json.loads(stdout)
        if result.get('code', 0) != 0:
            return {
                'success': False,
                'error':   result.get('raw_log', 'Erro desconhecido'),
                'code':    result.get('code'),
            }
    except json.JSONDecodeError:
        return {'success': False, 'error': 'Erro ao decodificar resposta da tx'}

    # Aguarda 1 bloco (~6s) para saldo atualizar
    time.sleep(7)
    bal_after_raw = get_balance(address)
    saldo_depois  = _parse_balances(bal_after_raw.get('balances', []))

    # Determina posição
    posicao    = 'compra' if to_token == 'uosmo' else 'venda'
    quantidade = amount / 1_000_000

    from preco import get_current_price
    preco_atual = get_current_price() or 0

    trade_entry = {
        'posicao':      posicao,
        'timestamp':    datetime.now(timezone.utc).isoformat(),
        'preco':        preco_atual,
        'quantidade':   quantidade,
        'from_token':   'OSMO' if from_token == 'uosmo' else 'USDC',
        'to_token':     'USDC' if to_token   != 'uosmo' else 'OSMO',
        'tx_hash':      result.get('txhash'),
        'gas_used':     result.get('gas_used'),
        'saldo_antes':  saldo_antes,
        'saldo_depois': saldo_depois,
        'slippage_pct': SLIPPAGE * 100,
        'token_out_min':   str(token_out_min),
        'estimated_out':   str(estimated_out),
    }
    save_trade(trade_entry)

    return {
        'success':       True,
        'tx_hash':       result.get('txhash'),
        'height':        result.get('height'),
        'gas_used':      result.get('gas_used'),
        'gas_wanted':    result.get('gas_wanted'),
        'posicao':       posicao,
        'preco':         preco_atual,
        'quantidade':    quantidade,
        'saldo_antes':   saldo_antes,
        'saldo_depois':  saldo_depois,
        'token_out_min': str(token_out_min),
        'estimated_out': str(estimated_out),
        'slippage_pct':  SLIPPAGE * 100,
        'trade':         trade_entry,
    }
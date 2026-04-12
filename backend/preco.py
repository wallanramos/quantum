#!/usr/bin/env python3
"""
Módulo de preço OSMO
Busca preço em tempo real e histórico de klines da CoinEx
"""
import time
from datetime import datetime, timezone

import requests

# Configurações Preço
COINEX_MARKET = 'OSMOUSDT'
COINEX_KLINE_LIMIT = 200
COINEX_INTERVAL_MAP = {
    '1m':  '1min',
    '15m': '15min',
    '1h':  '1hour',
    '4h':  '4hour',
    '1d':  '1day',
}
UPDATE_INTERVAL = 1  # segundos

# Estado global do preço
_price_state = {
    'price': None,
    'timestamp': None,
    'error': None,
    'updating': False,
    'last_update': None,
    'update_count': 0,
    'method': None,
}


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


def get_price_state():
    """Retorna o estado atual do preço."""
    return _price_state


def get_current_price():
    """Retorna o preço atual ou None se não disponível."""
    return _price_state.get('price')


def fetch_kline_history(timeframe='15m'):
    """Busca histórico de klines OHLCV do OSMO na CoinEx."""
    if timeframe not in COINEX_INTERVAL_MAP:
        return {'success': False, 'error': f'Timeframe inválido. Use: {list(COINEX_INTERVAL_MAP.keys())}'}

    interval = COINEX_INTERVAL_MAP[timeframe]
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

        history = []
        for k in data['data']:
            try:
                if isinstance(k, dict):
                    ts_ms = int(k.get('created_at', k.get('timestamp', 0)))
                    o = float(k['open'])
                    h = float(k['high'])
                    l = float(k['low'])
                    c = float(k['close'])
                    vol = float(k.get('volume', 0))
                else:
                    ts_ms = int(k[0])
                    o = float(k[1])
                    c = float(k[2])
                    h = float(k[3])
                    l = float(k[4])
                    vol = float(k[5])

                if ts_ms <= 0 or c <= 0:
                    continue

                history.append({
                    'price': c,
                    'open': o,
                    'high': h,
                    'low': l,
                    'close': c,
                    'volume': vol,
                    'timestamp': datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat(),
                    'currency': 'USD',
                    'source': 'coinex',
                })
            except (KeyError, IndexError, ValueError, TypeError):
                continue

        history.reverse()
        return {'success': True, 'history': history}

    except requests.RequestException as e:
        return {'success': False, 'error': f'Erro ao acessar CoinEx: {str(e)}'}
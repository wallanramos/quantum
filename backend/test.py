#!/usr/bin/env python3
"""
Script de teste para o backend da wallet
"""
import requests
import json

BASE_URL = 'http://localhost:5000/api'

def test_health():
    """Testa health check"""
    print("🔍 Testando health check...")
    response = requests.get(f'{BASE_URL}/health')
    print(f"   Status: {response.status_code}")
    print(f"   Resposta: {response.json()}")
    print()

def test_list_keys():
    """Testa listagem de chaves"""
    print("🔑 Testando listagem de chaves...")
    response = requests.get(f'{BASE_URL}/keys')
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"   Chaves encontradas: {len(data.get('keys', []))}")
        for key in data.get('keys', []):
            print(f"     - {key.get('name')}: {key.get('address')}")
    else:
        print(f"   Erro: {data.get('error')}")
    print()

def test_list_wallets():
    """Testa listagem de wallets"""
    print("👛 Testando listagem de wallets...")
    response = requests.get(f'{BASE_URL}/wallets')
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"   Wallets encontradas: {len(data.get('wallets', []))}")
        for wallet in data.get('wallets', []):
            print(f"     - {wallet.get('name')}: {wallet.get('address')}")
    print()

def test_get_balance():
    """Testa consulta de saldo"""
    address = 'osmo1sp8se0r87nwwwk9xz0fhg6963lgu86mes6he88'
    print(f"💰 Testando consulta de saldo para {address[:20]}...")
    response = requests.get(f'{BASE_URL}/balance/{address}')
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        print(f"   Saldos encontrados: {len(data.get('balances', []))}")
        for balance in data.get('balances', []):
            denom = balance.get('denom')
            amount = int(balance.get('amount', 0)) / 1000000
            if denom == 'uosmo':
                print(f"     - OSMO: {amount:.6f}")
            else:
                print(f"     - {denom[:30]}...: {amount:.6f}")
    else:
        print(f"   Erro: {data.get('error')}")
    print()

def test_simulate_swap():
    """Testa simulação de swap"""
    print("🔄 Testando simulação de swap (1 OSMO → USDC)...")
    payload = {
        'from': 'uosmo',
        'to': 'usdc',
        'amount': 1000000  # 1 OSMO
    }
    response = requests.post(f'{BASE_URL}/swap/simulate', json=payload)
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        out_amount = int(data.get('token_out_amount', 0)) / 1000000
        print(f"   Você receberá: {out_amount:.6f} USDC")
        print(f"   Método: {data.get('method')}")
    else:
        print(f"   Erro: {data.get('error')}")
    print()

def test_get_pool():
    """Testa consulta de pool"""
    pool_id = 1464
    print(f"💧 Testando consulta da pool {pool_id}...")
    response = requests.get(f'{BASE_URL}/pool/{pool_id}')
    print(f"   Status: {response.status_code}")
    data = response.json()
    if data.get('success'):
        pool = data.get('pool', {}).get('pool', {})
        print(f"   Pool ID: {pool.get('id')}")
        print(f"   Type: {pool.get('@type', 'N/A').split('.')[-1]}")
        print(f"   Token0: {pool.get('token0', 'N/A')}")
        print(f"   Token1: {pool.get('token1', 'N/A')[:30]}...")
    else:
        print(f"   Erro: {data.get('error')}")
    print()

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTES DO BACKEND DA WALLET")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_list_keys()
        test_list_wallets()
        test_get_balance()
        test_simulate_swap()
        test_get_pool()
        
        print("=" * 60)
        print("✅ Todos os testes concluídos!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("❌ Erro: Não foi possível conectar ao backend.")
        print("   Certifique-se de que o servidor está rodando:")
        print("   python3 wallet.py")
    except Exception as e:
        print(f"❌ Erro: {e}")

from typing import Dict

# Basit in-memory cüzdan. Prod için kalıcı DB gerekir.
_balances: Dict[str, float] = {}

def get_balance(user_id: str) -> float:
    return round(_balances.get(user_id, 0.0), 2)

def top_up(user_id: str, amount: float) -> float:
    if amount <= 0:
        raise ValueError("Amount must be positive")
    _balances[user_id] = get_balance(user_id) + amount
    return get_balance(user_id)

def charge(user_id: str, amount: float) -> float:
    if amount < 0:
        raise ValueError("Amount must be non-negative")
    if get_balance(user_id) < amount:
        raise ValueError("Insufficient funds")
    _balances[user_id] = get_balance(user_id) - amount
    return get_balance(user_id)

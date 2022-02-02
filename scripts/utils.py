from brownie import accounts, network, config, interface, chain
from scipy.optimize import linprog
from datetime import datetime
import sys, getopt, os
import bot_config
from bot_config import (
    LOCAL_BLOCKCHAIN_ENVIRONMENTS,
    NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS,
)


def get_latest_block_number():
    # Retrieve the latest block mined: chain[-1]
    # https://eth-brownie.readthedocs.io/en/stable/core-chain.html#accessing-block-information
    # Get its number
    try:
        latest_block_number = chain[-1]["number"]
        return latest_block_number
    except Exception as e:
        return e


def is_testing_mode():
    return "PYTEST_CURRENT_TEST" in sys.argv[0]


def log(msg, path):
    msg = f"\n{datetime.now()}\n" + msg
    with open(path, "a") as f:
        f.write(msg)


def num_digits(number: int) -> int:
    return len(str(number))


def mult_list_by_scalar(_list, _scalar):
    return [_scalar * element for element in _list]


def fix_parameters_of_function(_fun, _args_1_tuple):
    def new_fun(*args_2):
        return _fun(*args_2, *_args_1_tuple)

    return new_fun


def reverse_scalar_fun(_fun):
    def reverse_fun(*args):
        return -_fun(*args)

    return reverse_fun


def rebooter(function):
    def wrapped_fun(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            if bot_config.rebooter_bot:
                return wrapped_fun(*args, **kwargs)
            else:
                raise e

    return wrapped_fun


def print_args_wrapped(fun):
    def w_fun(*args, **kwargs):
        print(*args)
        return fun(*args, **kwargs)

    return w_fun


def get_token_names_and_addresses():
    token_names = config["networks"][network.show_active()]["token_names"]
    # we do it like this to avoid getting the wrapped mainnet token in this list
    token_addresses = [
        config["networks"][network.show_active()]["token_addresses"][token_name]
        for token_name in token_names
    ]
    print("Token names:", token_names)
    print("Token addresses:", token_addresses)
    return token_names, token_addresses


def get_wallet_balances(account, tokens, verbose=True):
    balances = []
    for token in tokens:
        token_balance = token.balanceOf(account)
        if verbose:
            print(
                f"{token.name()} (decimals {token.decimals()}) "
                f"balance {(token_balance/10**token.decimals())}"
            )
        balances.append(token_balance)
    return balances


def get_account(index=None, id=None):

    """
    - If index is passed, this returns accounts[index]
    - If id is passed, this returns the corresponding account stored in brownie under such id
    - If nothing is passed, this returns account[0] if we are in a local blockchain,
      and if not it returns accounts.add(config["wallets"]["from_key"])
    """
    if index:
        return accounts[index]
    elif id:
        return accounts.load(id)
    elif network.show_active() in LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        return accounts[0]
    else:
        return accounts.add(config["wallets"]["from_key"])

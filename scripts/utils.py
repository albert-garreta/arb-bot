from brownie import accounts, network, config, interface, chain
from datetime import datetime
import sys
import bot_config
from bot_config import LOCAL_BLOCKCHAIN_ENVIRONMENTS


"""General utility functions. Leter there are brownie-specific utilities"""


def is_testing_mode():
    # Returns True if we are running a test (with pytest).
    # Otherwise returns False
    return "PYTEST_CURRENT_TEST" in sys.argv[0]


def log(msg, path):
    msg = f"\n{datetime.now()}\n" + msg
    with open(path, "a") as f:
        f.write(msg)


def mult_list_by_scalar(_list, _scalar):
    return [_scalar * element for element in _list]


def fix_parameters_of_function(_fun, _args_1_tuple):
    # Given a function f(x,y) where x, y are two vectors,
    # and a vector y_0, it returns the function g(x) = f(x, y_0)
    # Here y_0 = _args_1_tuple and x=args_2
    def new_fun(*args_2):
        return _fun(*args_2, *_args_1_tuple)

    return new_fun


def reverse_scalar_fun(_fun):
    # Transforms a function f(x) into -f(x)
    def reverse_fun(*args):
        return -_fun(*args)

    return reverse_fun


def auto_reboot(function, auto_reboot=bot_config.auto_reboot):
    # Any function wrapped with this will re-execute itself in case of
    # raising an exception.
    # The auto_reboot parameter allows to switch off the auto_reboot from a config file

    def wrapped_fun(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as e:
            if auto_reboot:
                print(f"\nREBOOTING due to the following exception:\n{e}\n")
                return wrapped_fun(*args, **kwargs)
            else:
                raise e

    return wrapped_fun


def print_args_wrapped(fun):
    # A function wrapped with this will print its args upon being called
    def w_fun(*args, **kwargs):
        print(*args)
        return fun(*args, **kwargs)

    return w_fun


def swap_if_true_flag(value0, value1, bool_flag):
    if bool_flag:
        return value1, value0
    else:
        return value0, value1


"""Brownie specific utility functions"""


def get_latest_block_number():
    # Retrieve the latest block mined: chain[-1]
    # https://eth-brownie.readthedocs.io/en/stable/core-chain.html#accessing-block-information
    # Get its number
    try:
        latest_block_number = chain[-1]["number"]
        return latest_block_number
    except Exception as e:
        return e


def get_token_names_and_addresses():
    token_names = config["networks"][network.show_active()]["token_names"]
    token_addresses = [
        config["networks"][network.show_active()]["token_addresses"][token_name]
        for token_name in token_names
    ]
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

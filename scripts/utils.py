from brownie import accounts, network, config, interface
from scipy.optimize import linprog
from datetime import datetime
import sys, getopt

NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS + [
    "mainnet-fork",
    "ftm-main-fork",
]
ETH_NETWORKS = ["mainnet", "mainnet-fork", "kovan"]
FTM_NETWORKS = ["ftm-main", "ftm-main-fork", "ftm-test"]
MAIN_NETWORKS = ["ftm-main", "mainnet"]


def print_and_log(msg, path):
    msg = f"\n{datetime.now()}\n" + msg
    print(msg)
    with open(path, "a") as f:
        f.write(msg)


def num_digits(number: int) -> int:
    return len(str(number))


def fix_parameters_of_function(_fun, _args_1):
    def new_fun(*args_2):
        return _fun(*args_2, *_args_1)

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


def get_address(_name):
    # This line of code is used so often that maybe it is better to have
    # a short-hand version of it
    return config["networks"][network.show_active()][_name]


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


def get_all_dexes_and_factories(dex_list):
    routers_and_factories = []
    for dex_name in dex_list:
        routers_and_factories.append(get_dex_router_and_factory(dex_name))
    return routers_and_factories


def get_dex_router_and_factory(_dex_name):
    network_addresses = config["networks"][network.show_active()]
    dex_addresses = network_addresses["dexes"][_dex_name]

    # Do I need to instantiate them, or would it be enough to just pass the address?
    router = interface.IUniswapV2Router02(dex_addresses["swap_router_V2_address"])
    factory = interface.IUniswapV2Factory(dex_addresses["uniswap_factory_address"])
    return router, factory


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


def ensure_amount_of_wrapped_maintoken(_amount: int, _actor):
    # Makes sure that the balance between actor and caller of wrapped
    # maintoken is the one passed in the argument

    weth = interface.IWeth(
        config["networks"][network.show_active()]["token_addresses"][
            "wrapped_main_token_address"
        ]
    )
    actor_balance = weth.balanceOf(_actor.address)
    caller_balance = weth.balanceOf(get_account())
    total_balance = actor_balance + caller_balance
    if total_balance < _amount:
        print(f"Depositing {_amount} mainnet token into its wrapped ERC20 version...")
        tx = weth.deposit({"from": get_account(), "value": _amount - total_balance})
        tx.wait(1)
        print("Deposit done")
    else:
        print("Caller already has enough Wrapped main token")


contract_name_to_contract_type = {
    # "weth_token_usd_price_feed": MockV3Aggregator,
    # "dai_token_usd_price_feed": MockV3Aggregator,
    # "dapp_token_usd_price_feed": MockV3Aggregator,
    # "dai_token": MockDai,
    # "weth_token": MockWeth,
    # "dapp_token": DappToken,
    "weth_address": interface.IWeth,
    "usdt_address": interface.IERC20,
}


def get_contract(contract_name):
    """
    This function will grab the eth/usd feed address from the brownie config if defined.
    Otherwise it will deplou a mock verion of that contract.
    Returns the contract.

        Args:
            contract_name (string)

        Returns:
            brownie.network.contract.ProjectContract:
            the address of the most recently deployed version of this contract
    """

    contract_type = contract_name_to_contract_type[contract_name]

    if network.show_active() in NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS:
        if len(contract_type) <= 0:
            deploy_mocks()
        contract = contract_type[-1]
    else:
        try:
            contract_address = config["networks"][network.show_active()][contract_name]
            contract = contract_type(contract_address)

        except KeyError:
            print(
                f"{network.show_active()} address for {contract_name} not found. "
                f"Perhaps you should add it to the config or deploy mocks?"
            )
    return contract


def deploy_mocks():
    """
    Use this script if you want to deploy mocks to a testnet
    """
    pass


def print_args_wrapped(fun):
    def w_fun(*args, **kwargs):
        print(*args)
        # print(**kwargs) How to print this?
        return fun(*args, **kwargs)

    return w_fun


def process_line_commands():
    long_options = ["slippage=", "lending_fee="]
    short_options = "s:lf:"
    try:
        arguments, values = getopt.getopt(sys.argv[1:], short_options, long_options)
    except getopt.error as err:
        # Output error, and return with an error code
        print(str(err))
        sys.exit(2)

from brownie import accounts, network, config, interface

NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS + [
    "mainnet-fork",
    "ftm-main-fork",
]
ETH_NETWORKS = ["mainnet", "mainnet-fork", "kovan"]
FTM_NETWORKS = ["ftm-main", "ftm-main-fork", "ftm-test"]


def get_address(_name):
    # This line of code is used so often that maybe it is better to have
    # a short-hand version of it
    return config["networks"][network.show_active()][_name]


def get_token_addresses(_token_names):
    network_addresses = config["networks"][network.show_active()]
    return [network_addresses[name] for name in _token_names]


def get_all_dexes_and_factories(dex_list):
    routers_and_factories = []
    for dex_name in dex_list:
        routers_and_factories.append(get_dex_router_and_factory(dex_name))
    return routers_and_factories


def get_dex_router_and_factory(_dex_name="default_dex"):
    network_addresses = config["networks"][network.show_active()]
    if _dex_name == "default_dex":
        _dex_name = network_addresses["dex_addresses"]["default_dex"]
    dex_addresses = network_addresses["dex_addresses"][_dex_name]

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


def deposit_main_token_into_wrapped_version(_amount):
    # the amount is in Wei
    print("Depositing mainnet token into its wrapped ERC20 version...")
    tx = interface.IWeth(
        config["networks"][network.show_active()]["wrapped_main_token_address"]
    ).deposit({"from": get_account(), "value": _amount})
    tx.wait(1)
    print("Deposit done")


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
            # contract = Contract.from_abi(
            #     contract_type._name, contract_address, contract_type.abi
            # )
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

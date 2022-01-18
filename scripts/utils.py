from brownie import accounts, network, config, Contract, interface
from web3 import Web3

NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS + [
    "mainnet-fork",
    "ftm-main-fork",
]
DECIMALS = 18
INITIAL_PRICE_FEED_VALUE = 3300 * 10 ** 18


def get_wallet_balances(account, tokens, verbose=True):
    balances = []
    for token in tokens:
        token_balance = token.balanceOf(account)
        if verbose:
            print(
                f"{token.name()} (decimals {token.decimals()}) "
                f"balance {round((token_balance/10**token.decimals()),8)}"
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


def deposit_eth_into_weth(_amount):
    # the amount is in Wei
    if (
        network.show_active()
        in LOCAL_BLOCKCHAIN_ENVIRONMENTS + NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS
    ):
        print("Depositing ETH into WETH...")
        tx = interface.IWeth(
            config["networks"][network.show_active()]["weth_address"]
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


def deploy_mocks(decimals=DECIMALS, initial_value=INITIAL_PRICE_FEED_VALUE):
    """
    Use this script if you want to deploy mocks to a testnet
    """
    print(f"The active network is {network.show_active()}")
    print("Deploying Mocks...")
    account = get_account()

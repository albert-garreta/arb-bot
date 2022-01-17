from brownie import accounts, network, config, Contract


NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS = ["development", "ganache"]
LOCAL_BLOCKCHAIN_ENVIRONMENTS = NON_FORKED_LOCAL_BLOCKCHAIN_ENVIRONMENTS + [
    "ftm-main-fork",
]
DECIMALS = 18
INITIAL_PRICE_FEED_VALUE = 3300 * 10 ** 18

contract_name_to_contract_type = {
    # "weth_token_usd_price_feed": MockV3Aggregator,
    # "dai_token_usd_price_feed": MockV3Aggregator,
    # "dapp_token_usd_price_feed": MockV3Aggregator,
    # "dai_token": MockDai,
    # "weth_token": MockWeth,
    # "dapp_token": DappToken,
}


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
            """         
            The following allows to retrieve a deployed contract from its name, address, and abi
            Since in the Lottery contract we only need the addresses
            we could here just return the address (and in the case above add .address)
            """
            contract = Contract.from_abi(
                contract_type._name, contract_address, contract_type.abi
            )
            """         
            An alternative method can be obtained by using an interface, for example:       
                link_token_contract = interface.LinkTokenInterface(link_token_address)
            this is useful if the contract is already deployed in a network and we want
            to interact with it (?). 
            """
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

    print("Deploying Mock Price Feed...")
    mock_price_feed = MockV3Aggregator.deploy(
        decimals, initial_value, {"from": account}
    )
    print(f"Deployed to {mock_price_feed.address}")

    print("Deploying Mock DAI...")
    dai_token = MockDai.deploy({"from": account})
    print(f"Deployed to {dai_token.address}")

    print("Deploying Mock WETH")
    weth_token = MockWeth.deploy({"from": account})
    print(f"Deployed to {weth_token.address}")

from logging import raiseExceptions
from utils import account
from scripts.deploy_swapper import deploy_swapper
from brownie import IUniswapV3Pool


def get_pair_price(_token_in_address, _token_out_address, _version="V2"):
    if _version == "V3":
        raiseExceptions("V3 is not supported")
    
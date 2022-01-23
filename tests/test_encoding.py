from brownie import testEncoding
from matplotlib.pyplot import get
from scripts.utils import get_account


def test_encoding():
    testEncoding.deploy({"from": get_account()})
    testE = testEncoding[-1]
    testE.decode()
    assert testE.decodedParam() == 1

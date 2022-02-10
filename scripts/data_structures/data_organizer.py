import bot_config
from scripts.data_structures.variable_pair_data import VariablePairData, dotdict
from scripts.data_structures.static_pair_data import NonExistingLPException


class DataOrganizer(dotdict):
    """This class accomplishes two goals:
    1.

    Attributes:
        - token_index_pair_to_VariablePairData (dictionary):
                given a str of the form, e.g. "1_2", it gives the VariablePairData class
                correspindin to the token pair (token_names[1], token_names[2])
        - list_index_pairs (list of ints):
                A utility attribute: stores all pairs (token[i], token[j]) with i<j. This allows
                to map the choices of the multi_armed_bandit,
                (which occur among a range between 1 and len(list_index_pairs)+1)
                and the actual pair of tokens.

                The order in which the pairs are stored should not be altered and it is
                as follows: first i=0 and j ranges from 1 to len(token_names), then i=1
                and j ranges from 2 to len(token_names), and so on.

    Methods:
        - set_up_all_VariablePairData():
                Fills in the dictionary `token_index_pair_to_VariablePairData`
        - get_VariablePairData(index0, index1):
                Given two token indices, returns the corresponding VariablePairData object
        - maintenance():
                It updates the min_net_profits we require for each pair in order to execute
                an arbitrage operation.

    """

    def __init__(self):
        self.index_pair_to_VariablePairData = {}
        self.list_index_pairs = []
        self.num_tokens = len(bot_config.token_names)
        self.set_up_all_VariablePairData()

    def set_up_all_VariablePairData(self):
        for index0 in range(self.num_tokens):
            for index1 in range(index0 + 1, self.num_tokens):
                self.set_up_VariablePairData(index0, index1)

    def set_up_VariablePairData(self, index0, index1):
        # We expect this function to fail in some cases: this is because
        # not all pairs exist as an LP in both dexes. In this case the
        # we get a custom exception NonExistingLPException, which we 
        # print but we do not raise. If some other exception occurs then
        # we raise it.
        try:
            name0, name1 = (
                bot_config.token_names[index0],
                bot_config.token_names[index1],
            )
            print(f"Setting up VariablePairData for the token pair {name0}_{name1}...")
            self._set_up_VariablePairData(index0, index1)
            print("Set up done\n")
        except Exception as e:
            if type(e) is NonExistingLPException:
                print(f"Setting up failed. Ignoring pair.\nThe exception was:\n{e}\n")
            else:
                raise e

    def _set_up_VariablePairData(self, index0, index1):
        str_pair = get_index_pair_to_str_form(index0, index1)
        self.index_pair_to_VariablePairData[str_pair] = VariablePairData(index0, index1)
        self.list_index_pairs.append([index0, index1])

    def get_pair_data(self, index0, index1):
        str_pair = get_index_pair_to_str_form(index0, index1)
        return self.index_pair_to_VariablePairData[str_pair]

    def maintenance(self):
        print("Updating min net profits...")
        for (
            str_pair,
            variable_pair_data,
        ) in self.index_pair_to_VariablePairData.items():
            variable_pair_data.fill_in_min_net_profit()
            self.index_pair_to_VariablePairData[str_pair] = variable_pair_data
        print("Net profits updated")


def get_index_pair_to_str_form(index0, index1):
    return str(index0) + "_" + str(index1)

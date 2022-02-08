from copyreg import pickle
from turtle import st
import numpy as np
import bot_config
import os
import pickle

# TODO: clean this up
class MultiArmedBandit(object):
    """
    https://en.wikipedia.org/wiki/Multi-armed_bandit
    https://ieeexplore.ieee.org/document/892116
    """

    def __init__(self, _num_bandits):
        self.token_names = (
            bot_config.token_names
        )  # this is used only for loading states when starting the bot after an interruption
        self.num_bandits = _num_bandits
        self.range_for_bandits = range(1, self.num_bandits + 1)
        self.exploration_probability = bot_config.bandit_exploration_probability
        self.choice_weights = np.ones((self.num_bandits,))
        self.choice_probabilities = None
        self.last_choice = None
        self.num_updates = 0
        self.load_state()

    def update_choice_probs(self):
        self.choice_probabilities = (
            self.exploration_probability / self.num_bandits
        ) + (
            (1 - self.exploration_probability)
            * self.choice_weights
            / sum(self.choice_weights)
        )

    def choose(self):
        self.last_choice = np.random.choice(
            self.range_for_bandits, p=self.choice_probabilities
        )

    def update_choice_weights(self, _chosen_pair_data):
        reward = compute_reward(_chosen_pair_data)
        x_ = np.zeros((self.num_bandits,))
        x_[self.last_choice - 1] = (
            reward / self.choice_probabilities[self.last_choice - 1]
        )
        self.choice_weights *= np.exp(
            self.exploration_probability * x_ / self.num_bandits
        )
        print("MultiArmedBandit choice weights:", self.choice_weights)
        print(f"MultiArmedBandit reward: {reward}")



    def maintenance(self):
        # TODO: clean this up
        print("Saving Multi Armed Bandit state...")
        dir = bot_config.log_directory
        save_path_choices = os.path.join(dir, "multi_armed_bandit_choice_weights.npy")
        save_path_names = os.path.join(dir, "multi_armed_bandit_token_names.list")
        np.save(save_path_choices, self.choice_weights)
        with open(save_path_names, "wb") as f:
            pickle.dump(self.token_names, f)
        print("Save done!")

    def load_state(self):
        # TODO: clean this up

        if "multi_armed_bandit_token_names.list" in os.listdir(
            bot_config.log_directory
        ):
            save_path_names = os.path.join(
                bot_config.log_directory, "multi_armed_bandit_token_names.list"
            )
            with open(save_path_names, "rb") as f:
                token_names = pickle.load(f)
                if token_names == self.token_names:
                    print("Loading MultiArmedBandit state...")
                    save_path_choices = os.path.join(
                        bot_config.log_directory,
                        "multi_armed_bandit_choice_weights.npy",
                    )
                    self.choice_weights = np.load(save_path_choices)
                    print("Loading done!")
                    return True
                else:
                    print(
                        "No matching token names and choice weights for "
                        "MultiArmedBandit found"
                    )
def compute_reward(_chosen_pair_data):
    # Given a fully updated VariablePairData object, returns the reward for
    # the MultiArmedBandit. This rewards represents how good of a choice the Pair
    # fron the VariablePairData was.
    cpd = _chosen_pair_data  # For readibility reasons
    cpd.price_buy_dex = cpd.get_dex_price(cpd.reserves_buying_dex)
    cpd.price_sell_dex = cpd.get_dex_price(cpd.reserves_selling_dex)
    cpd.price_ratio = cpd.price_buy_dex / cpd.price_sell_dex
    reward = cpd.net_profit / (1e18 * cpd.min_net_profit)
    return reward
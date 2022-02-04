import random
from turtle import st
import numpy as np
import sys
import bot_config


def get_num_bandits():
    num_tokens = len(bot_config.token_names)
    # n choose 2 = n(n-1)/2
    num_bandits = int(num_tokens * (num_tokens - 1) / 2)
    return num_bandits


class MultiArmedBandit(object):
    def __init__(self, _num_bandits):
        self.num_bandits =_num_bandits
        self.range_for_bandits = range(1, self.num_bandits + 1)
        self.exploration_probability = bot_config.bandit_exploration_probability
        self.choice_weights = np.ones((self.num_bandits,))
        self.choice_probabilities = None
        self.last_choice = None
        self.num_updates = 0

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

    def update_choice_weights(self, _reward):
        x_ = np.zeros((self.num_bandits,))
        x_[self.last_choice - 1] = (
            _reward / self.choice_probabilities[self.last_choice - 1]
        )
        self.choice_weights *= np.exp(
            self.exploration_probability * x_ / self.num_bandits
        )
        print('Choice weights:', self.choice_weights)
        self.maintenance()
    
    def maintenance(self):
        self.num_updates +=1
        if self.num_updates > self.num_bandits*1500:
            self.reset()
        
    def reset(self):
        self.num_updates = 0 
        self.choice_weights = np.ones((self.num_bandits,))

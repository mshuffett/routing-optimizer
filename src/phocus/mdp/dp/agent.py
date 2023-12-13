import random

import numpy as np

from phocus.mdp.dp.value_func import QFunction
from phocus.mdp.env import Environment


class Agent(object):
    def __init__(self, value_function: QFunction, gamma: float):
        self.value_function = value_function
        self.gamma = gamma

    def sample_action(self, env: Environment, action_epsilon: float) -> (int, np.ndarray):
        action_values = self.value_function.output(env.state)
        action_values *= env.valid_actions
        # Epsilon-greedy
        if np.random.rand() > action_epsilon:
            return np.argmax(action_values).item(), action_values
        else:
            return random.sample(np.flatnonzero(env.valid_actions).tolist(), 1)[0], action_values

    def run_episode(self, env: Environment, epsilon: float, alpha: float, on_policy=True):
        s_t = env.state.copy()
        a_t, _ = self.sample_action(env, epsilon)

        while True:
            reward, s_t_next = env.step(a_t)
            if env.is_terminal():
                break
            a_t_next, action_values = self.sample_action(env, epsilon)
            q_t_next = action_values[a_t_next] if on_policy else action_values.max()
            target = reward + self.gamma * q_t_next
            self.value_function.update(
                state=s_t,
                action_idx=a_t,
                target=target,
                alpha=alpha,
            )

            s_t = s_t_next.copy()
            a_t = a_t_next

        self.value_function.update(
            state=s_t,
            action_idx=a_t,
            target=0,
            alpha=alpha,
        )

    def sample_trajectory(self, env: Environment):
        env.reset()
        total_reward = 0

        while not env.is_terminal():
            action, _ = self.sample_action(env, action_epsilon=0.)
            reward, _ = env.step(action)
            total_reward += reward

        return env.visited_nodes[:env.num_visited + 1], total_reward

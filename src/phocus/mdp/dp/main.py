import numpy as np

from phocus.mdp import Segment
from phocus.mdp.dp.agent import Agent
from phocus.mdp.dp.value_func import QFunction
from phocus.mdp.env import Environment

NUM_NODES = 50
WORLD_SIZE = (7, 7)  # SF
SALES_TIME = 0.5  # hour per sale
TRAVEL_SPEED = 15  # miles per hour
EPISODE_SEGMENTS = [
    Segment(hours=3, start_node=0, end_node=None),
    Segment(hours=5, start_node=None, end_node=None),
]
NUM_EPISODES = 5000
ALPHA = 3e-4  # Generic ADAM learning rate
GAMMA = 0.99
NUM_HIDDEN_LAYERS = 1
HIDDEN_DIM_FACTOR = 2
BASE_EPSILON = 1.0  # Start exploring randomly
ON_POLICY = False  # Toggle SARSA vs Q-Learning

"""
Dynamic Programming approach to solving MDP
Temporal Difference with pure bootstrapping (TD(0))
Both on-policy (SARSA(0)) and off-policy (Q-Learning)
"""


def main():
    # Node 0 is home
    node_locations = np.random.rand(NUM_NODES, 2) * WORLD_SIZE
    node_rewards = np.ones(NUM_NODES)

    env = Environment(
        node_locations=node_locations,
        node_rewards=node_rewards,
        travel_speed=TRAVEL_SPEED,
        sales_time=SALES_TIME,
        segments=EPISODE_SEGMENTS,
    )

    value_function = QFunction(
        action_size=NUM_NODES,
        state_size=2 * NUM_NODES + 2,
        num_hidden_layers=NUM_HIDDEN_LAYERS,
        hidden_dim_factor=HIDDEN_DIM_FACTOR,
    )

    agent = Agent(value_function=value_function, gamma=GAMMA)

    for ep_idx in range(NUM_EPISODES):
        epsilon = BASE_EPSILON * (NUM_EPISODES - ep_idx) / NUM_EPISODES  # linear epsilon schedule (not GLIE)
        env.reset()
        agent.run_episode(env=env, epsilon=epsilon, alpha=ALPHA, on_policy=ON_POLICY)

        # Evaluate and print progress
        if ep_idx % 1000 == 0:
            sample_path, total_reward = agent.sample_trajectory(env)
            print("Episode {0}\nGreedy trajectory: {1}\n\tCoordinates: {2}\n\tReward: {3}".format(
                ep_idx,
                sample_path,
                list(map(lambda idx: node_locations[idx], sample_path)),
                total_reward,
            ))

    sample_path, total_reward = agent.sample_trajectory(env)
    print("Final trajectory: {0}\nCoordinates: {1}\nReward: {2}".format(
        sample_path,
        list(map(lambda idx: node_locations[idx], sample_path)),
        total_reward,
    ))


if __name__ == '__main__':
    import time

    start: float = time.time()
    main()
    print("Elapsed:", time.time() - start)

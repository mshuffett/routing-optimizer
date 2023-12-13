from typing import Sequence

import numpy as np

from phocus.mdp import Segment
from phocus.mdp.env import Environment
from phocus.mdp.po.policy import Policy

"""
Policy Optimization approach to solving MDP
Maximize the log probability of parameters theta
1. DFO: Cross Entropy Method, Evolution Strategies, Simulated Annealing
2. Policy Gradients
"""

NUM_NODES = 50
WORLD_SIZE = (7, 7)  # SF
SALES_TIME = 0.5  # hour per sale
TRAVEL_SPEED = 15  # miles per hour
EPISODE_SEGMENTS = [
    Segment(hours=3, start_node=0, end_node=None),
    Segment(hours=5, start_node=None, end_node=None),
    Segment(hours=3, start_node=0, end_node=None),
    Segment(hours=5, start_node=None, end_node=None),
]
POPULATION = 50
NUM_HIDDEN_LAYERS = 1
HIDDEN_DIM_FACTOR = 2

# Evolution Strategies Parameters
ES_SIGMA = 0.2  # Noise std dev
ALPHA = 1E-2  # Learning Rate
ES_EPSILON_STOPPING = 1E-2  # max std dev of theta as stopping criteria

# Cross Entropy Method Parameters
ELITE_RATIO = 0.5  # fraction of samples used as elite set
CE_EPSILON_STOPPING = 1E-2  # max std dev of theta as stopping criteria

# Simulated Annealing Parameters
K_MAX = 20000
SA_SIGMA = 1E-2


def sample_trajectory(policy: Policy, env: Environment) -> (Sequence[int], float):
    total_reward = 0

    env.reset()

    while True:
        a = policy.sample_action(env.state, env.valid_actions)
        reward, state = env.step(node_idx=a)
        total_reward += reward
        if env.is_terminal():
            break

    return env.visited_nodes[:env.num_visited + 1], total_reward


def train_cross_entropy(env: Environment, node_locations):
    state_size = 2 * NUM_NODES + 2
    action_size = NUM_NODES
    hidden_dim = HIDDEN_DIM_FACTOR * int(np.ceil(np.sqrt(state_size)))
    dim_theta = (state_size + 1) * hidden_dim + (hidden_dim + 1) * action_size

    theta_mean = np.random.randn(dim_theta)
    theta_std = np.ones(dim_theta)

    # Sample trajectory from this policy
    sample_path, total_reward = sample_trajectory(
        Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta_mean),
        env=env,
    )
    print("Train using Cross Entropy Method")
    print("Initial random path {0}\nInitial reward {1}".format(sample_path, total_reward))

    iteration = 0
    while True:
        # Sample parameter vectors
        thetas = np.random.normal(
            loc=np.tile(theta_mean, POPULATION),
            scale=np.tile(theta_std, POPULATION),
        ).reshape(POPULATION, dim_theta)
        rewards = [
            sample_trajectory(
                Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
                env=env,
            )[1]
            for theta in thetas
        ]
        # Get elite parameters
        n_elite = int(POPULATION * ELITE_RATIO)
        elite_indices = np.argsort(rewards)[POPULATION - n_elite:POPULATION]
        elite_thetas = thetas[elite_indices]
        # Update theta parameters
        theta_mean = np.mean(elite_thetas, axis=0)
        theta_std = np.std(elite_thetas, axis=0)

        # Check if stopping condition met
        if theta_std.max() < CE_EPSILON_STOPPING:
            break

        if iteration % 100 == 0:
            print("Iteration %i. mean: %8.3g max: %8.3g" % (iteration, np.mean(rewards).item(), np.max(rewards)))
            print("theta mean %s \n theta std %s" % (theta_mean, theta_std))
            # Sample trajectory from this policy
            sample_path, total_reward = sample_trajectory(
                Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta_mean),
                env=env,
            )
            print("Sample path {0}\nTotal reward {1}".format(sample_path, total_reward))

        iteration += 1

    sample_path, total_reward = sample_trajectory(
        Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta_mean),
        env=env,
    )
    print("Final path {0}\nCoordinates: {1}\nReward {2}".format(
        sample_path,
        list(map(lambda idx: node_locations[idx], sample_path)),
        total_reward,
    ))


def train_evolution_strategies(env: Environment, node_locations):
    state_size = 2 * NUM_NODES + 2
    action_size = NUM_NODES
    hidden_dim = HIDDEN_DIM_FACTOR * int(np.ceil(np.sqrt(state_size)))
    dim_theta = (state_size + 1) * hidden_dim + (hidden_dim + 1) * action_size

    theta = np.random.randn(dim_theta)

    # Sample trajectory from this policy
    sample_path, total_reward = sample_trajectory(
        Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
        env=env,
    )
    print("Train using Evolution Strategies")
    print("Initial random path {0}\nInitial reward {1}".format(sample_path, total_reward))

    generation_idx = 0

    while True:
        # Sample parameter vectors
        noise = np.random.randn(POPULATION, dim_theta)
        rewards = np.zeros(POPULATION)
        for member_idx in range(POPULATION):
            theta_member = theta + ES_SIGMA * noise[member_idx]
            policy = Policy(
                state_size=state_size,
                action_size=action_size,
                hidden_dim=hidden_dim,
                theta=theta_member,
            )
            _, rewards[member_idx] = sample_trajectory(env=env, policy=policy)

        rewards_norm = (rewards - np.mean(rewards)) / (np.std(rewards) + 1E-6)
        theta_update = ALPHA / (POPULATION * ES_SIGMA) * np.dot(noise.T, rewards_norm)
        if theta_update.max() < ES_EPSILON_STOPPING:
            break
        theta += theta_update

        if generation_idx % 100 == 0:
            print("Generation %i. mean: %8.3g max: %8.3g" % (generation_idx, np.mean(rewards).item(), np.max(rewards)))
            print("theta mean %s" % theta)
            # Sample trajectory from this policy
            sample_path, total_reward = sample_trajectory(
                Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
                env=env,
            )
            print("Sample path {0}\nTotal reward {1}".format(sample_path, total_reward))

        generation_idx += 1

    sample_path, total_reward = sample_trajectory(
        Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
        env=env,
    )
    print("Final path {0}\nCoordinates: {1}\nReward {2}".format(
        sample_path,
        list(map(lambda idx: node_locations[idx], sample_path)),
        total_reward,
    ))


def train_simulated_annealing(env: Environment, node_locations):
    state_size = 2 * NUM_NODES + 2
    action_size = NUM_NODES
    hidden_dim = HIDDEN_DIM_FACTOR * int(np.ceil(np.sqrt(state_size)))
    dim_theta = (state_size + 1) * hidden_dim + (hidden_dim + 1) * action_size

    theta = np.random.randn(dim_theta)

    # Sample trajectory from this policy
    sample_path, total_reward = sample_trajectory(
        Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
        env=env,
    )
    print("Train using Simulated Annealing")
    print("Initial random path {0}\nInitial reward {1}".format(sample_path, total_reward))

    current_score = total_reward

    for k in range(K_MAX):
        candidate_theta = neighbor(theta)
        _, candidate_score = sample_trajectory(
            policy=Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=candidate_theta),
            env=env,
        )
        temperature = get_temperature(k, K_MAX)
        accept_prob = acceptance_probability(current=current_score, candidate=candidate_score, temperature=temperature)

        if np.random.rand() < accept_prob:
            current_score = candidate_score
            theta = candidate_theta

        if k % 1000 == 0:
            print("Iteration %i. reward: %8.3g" % (k, current_score))
            print("theta mean %s" % theta)
            # Sample trajectory from this policy
            sample_path, total_reward = sample_trajectory(
                Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
                env=env,
            )
            print("Sample path {0}\nTotal reward {1}".format(sample_path, total_reward))

    sample_path, total_reward = sample_trajectory(
        Policy(action_size=action_size, state_size=state_size, hidden_dim=hidden_dim, theta=theta),
        env=env,
    )
    print("Final path {0}\nCoordinates: {1}\nReward {2}".format(
        sample_path,
        list(map(lambda idx: node_locations[idx], sample_path)),
        total_reward,
    ))


def get_temperature(k: float, k_max: float) -> float:
    return (k_max - k) / k_max


def acceptance_probability(current: float, candidate: float, temperature: float) -> float:
    if candidate > current:
        return 1.
    else:
        return np.exp((candidate - current) / temperature)


def neighbor(theta: np.ndarray) -> np.ndarray:
    return theta + np.random.randn(theta.shape[0]) * SA_SIGMA


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
    import time
    start_time = time.time()
    train_cross_entropy(env=env, node_locations=node_locations)
    print("Elapsed: ", time.time() - start_time)
    start_time = time.time()
    train_evolution_strategies(env=env, node_locations=node_locations)
    print("Elapsed: ", time.time() - start_time)
    start_time = time.time()
    train_simulated_annealing(env=env, node_locations=node_locations)
    print("Elapsed: ", time.time() - start_time)


if __name__ == '__main__':
    main()

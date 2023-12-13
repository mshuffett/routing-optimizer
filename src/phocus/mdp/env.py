from typing import Sequence

import numpy as np

from phocus.mdp import Segment


class Environment(object):
    def __init__(
        self,
        node_locations,
        node_rewards: np.ndarray,
        travel_speed: float,
        sales_time: float,
        segments: Sequence[Segment],
    ):
        # Static assignments
        self.num_nodes: int = len(node_locations)
        self.reserved_nodes = set()
        for segment in segments:
            self.reserved_nodes.add(segment.start_node)
            self.reserved_nodes.add(segment.end_node)
        self.reserved_nodes.discard(None)
        self.node_rewards = node_rewards
        # Normalized segment times
        total_time = sum(map(lambda _: _.hours, segments))
        self.segments = segments
        self.segment_times: Sequence[float] = list(map(lambda _: _.hours / total_time, segments))
        self.distance_matrix = self.compute_distance_matrix(
            node_locations, sales_time, travel_speed, total_time)
        self.visited_nodes = np.zeros(shape=[self.num_nodes], dtype=np.int)

        # Dynamic state
        self.segment_start_node = self.segments[0].start_node
        self.segment_end_node = self.segments[0].end_node
        self.num_visited: int = 0
        self.reset_visited_nodes(self.segment_start_node)
        self.valid_actions: np.ndarray = np.ones(shape=[self.num_nodes])
        self.reset_valid_actions()
        self.current_segment_times = self.segment_times[:]
        self.current_segment_idx = 0
        self.time_remaining = 1.
        self.state = np.zeros(shape=[self.num_nodes * 2 + 2])
        self.state[self.num_nodes:-2] = self.distance_matrix[self.segment_start_node]
        self.state[-2] = self.current_segment_times[0]
        self.state[-1] = self.time_remaining

    def reset(self):
        # Reset dynamic state
        self.segment_start_node = self.segments[0].start_node
        self.segment_end_node = self.segments[0].end_node
        self.reset_visited_nodes(self.segment_start_node)
        self.reset_valid_actions()
        self.current_segment_times = self.segment_times[:]
        self.current_segment_idx = 0
        self.time_remaining = 1.
        self.state.fill(0)
        self.state[self.num_nodes:-2] = self.distance_matrix[self.segment_start_node]
        self.state[-2] = self.current_segment_times[0]
        self.state[-1] = self.time_remaining

    def compute_distance_matrix(self, node_locations, sales_time: float, travel_speed: float, episode_time: float):
        # Compute travel times based on manhattan distance and travel speed
        travel_times = np.zeros(shape=(self.num_nodes, self.num_nodes))

        for i in range(self.num_nodes):
            for j in range(self.num_nodes):
                travel_times[i, j] = np.sum(np.abs(node_locations[i] - node_locations[j])) / travel_speed

        # Incorporate sales time into the distance matrix
        travel_times += sales_time

        return travel_times / episode_time

    def is_terminal(self):
        return self.time_remaining < 1e-6

    def reset_visited_nodes(self, start_node: int):
        self.num_visited = 0
        self.visited_nodes.fill(0)
        self.visited_nodes[0] = start_node

    def reset_valid_actions(self):
        self.valid_actions.fill(1)
        self.valid_actions[list(self.reserved_nodes)] = 0.
        self.valid_actions[self.visited_nodes] = 0.

    def visit_node(self, node_idx):
        self.num_visited += 1
        self.visited_nodes[self.num_visited] = node_idx

    def step(self, node_idx) -> (float, np.ndarray):
        previous_node = self.visited_nodes[self.num_visited]
        node_distance = self.distance_matrix[previous_node, node_idx]
        segment_end_node = self.segments[self.current_segment_idx].end_node
        # Mark node as visited
        self.visit_node(node_idx)
        # Update time remaining in segment and episode
        self.current_segment_times[self.current_segment_idx] -= node_distance
        self.time_remaining -= node_distance
        # Update valid actions
        self.valid_actions[node_idx] = 0.
        self.valid_actions *= self.distance_matrix[node_idx] < self.current_segment_times[self.current_segment_idx]
        if segment_end_node is not None:
            self.valid_actions *= self.distance_matrix[:, segment_end_node] < \
                                  self.current_segment_times[self.current_segment_idx]

        # Handle end of segment
        if np.count_nonzero(self.valid_actions) is 0:
            # Drain remaining segment time
            self.time_remaining -= self.current_segment_times[self.current_segment_idx]
            self.current_segment_times[self.current_segment_idx] = 0
            # Go to end node of segment if exists
            if segment_end_node is not None:
                self.visit_node(segment_end_node)
            # Advance to next segment
            if not self.is_terminal():
                self.current_segment_idx += 1
                self.reset_valid_actions()

        # Update state vector
        self.state[node_idx] = 1
        self.state[self.num_nodes:-2] = self.distance_matrix[node_idx]
        self.state[-1] = self.time_remaining
        self.state[-2] = self.current_segment_times[self.current_segment_idx]

        return self.node_rewards[node_idx], self.state

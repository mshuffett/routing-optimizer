import numpy as np


class Policy(object):
    def __init__(self, state_size: int, action_size: int, hidden_dim: int, theta: np.ndarray):
        """
        Deterministic Discrete Action Policy
        :param state_size: dimensionality of state vector
        :param action_size: number of discrete actions
        :param theta: flattened weight vector
        """
        assert len(theta) == (state_size + 1) * hidden_dim + (hidden_dim + 1) * action_size
        acc_idx = 0
        weights_in_slice: np.ndarray = theta[:state_size * hidden_dim]
        acc_idx += weights_in_slice.shape[0]
        bias_in_slice: np.ndarray = theta[acc_idx: acc_idx + hidden_dim]
        acc_idx += bias_in_slice.shape[0]
        weights_out_slice: np.ndarray = theta[acc_idx: acc_idx + hidden_dim * action_size]
        acc_idx += weights_out_slice.shape[0]
        bias_out_slice: np.ndarray = theta[acc_idx:]
        self.weights_in: np.ndarray = weights_in_slice.reshape(state_size, hidden_dim)
        self.bias_in: np.ndarray = bias_in_slice.reshape(1, hidden_dim)
        self.weights_out: np.ndarray = weights_out_slice.reshape(hidden_dim, action_size)
        self.bias_out = bias_out_slice.reshape(1, action_size)

    def score_actions(self, state: np.ndarray) -> np.ndarray:
        hidden = state.dot(self.weights_in) + self.bias_in
        activation: np.ndarray = np.tanh(hidden)
        output = activation.dot(self.weights_out) + self.bias_out
        return output

    @staticmethod
    def ensure_numerical_stability(scores: np.ndarray) -> np.ndarray:
        return scores - scores.max()

    def sample_action(self, state: np.ndarray, valid_actions: np.ndarray) -> int:
        """
        Return index of highest scoring action
        :param state: state vector
        :param valid_actions: binary mask of valid actions
        :return: index of highest score action
        """
        s = self.score_actions(state)
        # s = Policy.ensure_numerical_stability(scores=s)
        y: np.ndarray = np.exp(s)  # Scale to range (0, inf)
        y_masked = y * valid_actions
        a = y_masked.argmax()
        return a

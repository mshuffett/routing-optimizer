import numpy as np
import tensorflow as tf


class QFunction(object):
    def __init__(self, state_size: int, action_size: int, num_hidden_layers: int, hidden_dim_factor: int):
        self.sess = tf.InteractiveSession()
        hidden_dim = hidden_dim_factor * int(np.ceil(np.sqrt(state_size)))

        # Define inputs
        self.x = tf.placeholder(tf.float32, shape=[None, state_size], name="state")
        self.target = tf.placeholder(tf.float32, shape=[None], name="target")
        self.action_idx = tf.placeholder(tf.int32, shape=[None], name="action_idx")
        self.alpha = tf.placeholder(tf.float32, name="alpha")

        # Model initialization
        activation = self.x
        for layer_idx in range(0, num_hidden_layers + 1):
            input_dim = state_size if layer_idx is 0 else hidden_dim
            output_dim = action_size if layer_idx is num_hidden_layers else hidden_dim

            weights = QFunction.weight_variable(shape=[input_dim, output_dim], layer_idx=layer_idx)
            bias = QFunction.bias_variable(shape=[output_dim], layer_idx=layer_idx)

            if layer_idx is num_hidden_layers:
                self.q = tf.matmul(activation, weights) + bias
            else:
                activation = QFunction.layer(activation, weights, bias)

        # Define training step
        self.selected_q = tf.reduce_sum(tf.multiply(tf.one_hot(self.action_idx, depth=action_size), self.q))
        self.loss = tf.nn.l2_loss(self.target - self.selected_q)
        self.optimizer = tf.train.AdamOptimizer(self.alpha)
        self.grads_and_vars = self.optimizer.compute_gradients(self.loss)
        self.train_step = self.optimizer.apply_gradients(self.grads_and_vars)

        self.sess.run(tf.global_variables_initializer())

    def update(self, state, action_idx, target, alpha):
        self.train_step.run(feed_dict={
            self.x: [state],
            self.target: [target],
            self.action_idx: [action_idx],
            self.alpha: alpha,
        })

    def output(self, state_vector):
        return self.sess.run(self.q, feed_dict={self.x: [state_vector]})[0]

    @staticmethod
    def weight_variable(shape, layer_idx):
        # Glorot Uniform
        abs_val = np.sqrt(6 / (shape[0] + shape[1]))
        initial = tf.random_uniform(shape, minval=-abs_val, maxval=abs_val)
        return tf.Variable(initial, name="W_{0}".format(layer_idx))

    @staticmethod
    def bias_variable(shape, layer_idx):
        initial = tf.constant(0., shape=shape)
        return tf.Variable(initial, name="b_{0}".format(layer_idx))

    @staticmethod
    def layer(a, w, b):
        return tf.nn.tanh(tf.matmul(a, w) + b)

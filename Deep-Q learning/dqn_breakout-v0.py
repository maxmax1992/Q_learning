from collections import deque

import numpy as np
import keras
import random
import os
import matplotlib.pyplot as plt
from keras.models import Sequential
from keras.layers import Dense, Flatten
from keras.layers import Conv2D

from baselines import deepq
from baselines.common.atari_wrappers import make_atari
from keras.optimizers import Adam


env = make_atari('BreakoutNoFrameskip-v4')
env = deepq.wrap_atari_dqn(env)

#baselines deepq hyperparameters:
    # env -> enviroment
    # q_func = model, -> CNN
    # lr = 1e-4,    ->  learning rate
    # max_timesteps = args.num_timesteps,
    # buffer_size = 10000,
    # exploration_fraction = 0.1,
    # exploration_final_eps = 0.01,
    # train_freq = 4,
    # learning_starts = 10000,
    # target_network_update_freq = 1000,
    # gamma = 0.99,
    # prioritized_replay = bool(args.prioritized)


class QNetwork:
    def __init__(self, learning_rate=0.0025, action_space=4, model=None):
        # state inputs to the Q-network
        if model is not None:
            self.model = model
            return
        self.model = Sequential()

        self.model.add(Conv2D(32, (8, 8), strides=(4, 4), activation='relu',
                         input_shape=(84, 84, 4)))
        self.model.add(Conv2D(64, (4, 4), strides=(2, 2), activation='relu'))
        self.model.add(Conv2D(64, (3, 3), activation='relu'))
        self.model.add(Flatten())
        self.model.add(Dense(256, activation='relu'))
        self.model.add(Dense(action_space, activation='linear'))

        self.optimizer = Adam(lr=learning_rate)

        # if os.path.exists('breakout-v0-weights-v0.h5'):
        #     self.loadModel()
        #     print('loaded nn weights from file')

        self.model.compile(loss='mse',
                           optimizer=self.optimizer,
                           metrics=['accuracy'])

    def copyModel(self):
        copy_model = keras.models.clone_model(self.model)
        copy_model.set_weights(self.model.get_weights())
        return QNetwork(model=copy_model)

    def saveModel(self):
        self.model.save_weights('breakout-v0-weights-v0.h5')

    def loadModel(self):
        self.model.load_weights('breakout-v0-weights-v0.h5')

    def predict(self, state):
        return self.model.predict(np.array([state]))[0]

    def fit(self, x, y):
        self.model.fit(x=x, y=y, shuffle=False, verbose=False)

    def setWeights(self, weights):
        self.model.set_weights(weights)

    def getWeights(self):
        return self.model.get_weights()


def processBatch(data_arr, df, DQN, DQN_target):
    X, Y = [], []
    for elem in data_arr:
        s1, action, reward, done, s2 = elem.getValues()
        y = DQN.predict(s1)
        y[action] = reward
        if not done:
            y[action] = reward + df * max(DQN_target.predict(s2))
        X.append(s1)
        Y.append(y)
    return np.array(X), np.array(Y)


class Memory:
    def __init__(self, s1, action, reward, done, s2):
        self.values = s1, action, reward, done, s2

    def getValues(self):
        return self.values




e_start = float(1.00)
e_end = float(0.10)
decay_frames = 1000000
change = float(e_start - e_end) / float(1000000)
epsilon = e_start
sum = 0
test_e = epsilon


df = 0.99
rewards = []

DQN = QNetwork()
DQN_target = DQN.copyModel()

replay_memory = deque([], maxlen=1000000)

frame = 0
showedFirst = False
rewards = []

ep = 0
randPolicy = True
for i in range(0, 5000000):

    frame += 1
    done = False
    state = env.reset()
    action = env.action_space.sample()
    totalReward = 0
    ep += 1


    if randPolicy and frame > 50000:
        randPolicy = False

    while not done:

        # env.render()
        if frame % 10000 == 0:
            DQN_target.setWeights(DQN.getWeights())

        #skip frames and repeat same action
        if frame % 4 is not 0:
            frame += 1

            state1, reward, done, _ = env.step(action)
            replay_memory.append(Memory(state, action, reward, done, state1))

            totalReward += reward
            state = state1
            continue

        randaction_p = random.uniform(0, 1)

        if randaction_p < epsilon or randPolicy:
            action = env.action_space.sample()
            # print('random action', action)
        else:
            action = np.argmax(DQN.predict(state))
            # print('action', action)

        state1, reward, done, info = env.step(action)
        totalReward += reward

        replay_memory.append(Memory(state, action, reward, done, state1))

        if not randPolicy:
            batch = random.sample(replay_memory, min(32, len(replay_memory)))
            X, Y = processBatch(batch, df, DQN, DQN_target)
            DQN.fit(X, Y)
            #plotting
            # if frame % 500 == 0:
            #     plot_rewards(rewards)

        state = state1
        # env.render()
        frame += 1
        epsilon = max(epsilon - change, e_end)

    if ep % 100 is 0:

        DQN.saveModel()

        a = plt.plot(rewards)
        plt.ylabel('reward')
        plt.xlabel('episode')
        plt.savefig('rewardsPlot.png')

    rewards.append(totalReward)
    print('episode: {}, epsilon: {}, frames: {}, totReward: {}' .format(ep, epsilon, frame, totalReward))

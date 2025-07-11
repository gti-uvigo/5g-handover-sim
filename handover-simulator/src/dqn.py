from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from tensorflow.keras.losses import Huber
from environment import Environment
import numpy as np
import random
import tensorflow as tf
import os

# Based on: https://github.com/PacktPublishing/Advanced-Deep-Learning-with-Keras/blob/master/chapter9-drl/dqn-cartpole-9.6.1.py

class DQNAgent:
    # Initialize the agent
    def __init__(self, nGnbs, n_states,epsilon=0.9):
        
        self.nGnbs = nGnbs
        self.n_states = n_states
        self.memory = []
        self.gamma = 0.9
        self.memory_size = 500
        self.epsilon = epsilon 
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995 
        self.sync_rate = 10
        self.learning_rate = 0.01
        self.replay_counter = 0
        self.policy_net = self.create_model()
        self.target_net = self.create_model()
        self.traces = []
        self.isRecordingTraces = False
        self.max_size_traces = 1000
        
    # Create the model
    def create_model(self):
        model = Sequential()
        model.add(Dense(32, input_dim=self.n_states, activation='relu'))
        model.add(Dense(32, activation='relu'))
        model.add(Dense(self.nGnbs, activation='linear'))
        loss = Huber(delta=1.0)
        model.compile(loss=loss, optimizer=Adam())
        return model
    
    # Store the experience in the memory
    def remember(self, state, action, reward, next_state, done, ):
        self.memory.append([state, action, reward, next_state, done])
        if len(self.memory) > self.memory_size:
            self.memory.pop(0)
        
    # Choose an action
    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return np.random.randint(0, self.nGnbs)
        state = np.reshape(state, (1, -1))

        act_values = self.policy_net.predict(state,verbose=0)
        return np.argmax(act_values[0])
    

    # Replay the memory
    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        states = []
        q_values = []
        print("epsilon: ", self.epsilon)
        for state, action, reward, next_state, done in minibatch:
            
            # Reshape state to include batch dimension
            state = np.reshape(state, (1, -1))
            next_state = np.reshape(next_state, (1, -1))
            
            # Get q-values for current state from policy network
            policy_q_values = self.policy_net.predict(state, verbose=0)
            
            # Get q-values for next state from target network
            target_q_value = self.get_target_q_value(next_state, reward)
            
            if done:
                policy_q_values[0][action] = reward
            else:
                policy_q_values[0][action] = target_q_value
            
            states.append(state[0])
            q_values.append(policy_q_values[0])

            
        # Convert lists to numpy arrays for fitting
        self.policy_net.fit(np.array(states), np.array(q_values), batch_size=batch_size, epochs=1, verbose=0)

        # Decay epsilon
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

        # Update target network weights if required
        if self.replay_counter % self.sync_rate == 0:
            self.update_target_weights()
        
        self.replay_counter += 1
                
                
            
    def get_target_q_value(self,  next_state, reward):
    
        q_value = np.amax(self.target_net.predict(next_state,verbose=0))
        
        q_max = reward + self.gamma * q_value
        return q_max


    # Update Weights
    def update_target_weights(self):
        self.target_net.set_weights(self.policy_net.get_weights())
    

    # Load the model
    def load(self, name):
        self.policy_net.load_weights(name)
        
        
    # Save the model
    def save(self, name):
        self.model.save_weights(name)
    

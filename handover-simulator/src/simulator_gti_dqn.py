#usr/bin/env python3
# encoding: UTF-8


# File for the implementation of the DQN algorithm for the handover simulator
from environment import Environment
from dqn import DQNAgent
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os
import simulator_common
from scoring import calculate_algorithm_score

def weighted_avg(df, value_column, weight_column):
    weighted_sum = (df[value_column] * df[weight_column])
    weight_sum = df[weight_column]
    return weighted_sum / weight_sum 

os.environ["KERAS_BACKEND"] = "jax"
ALGORITHM = "DQN"


def simulate_gti_dqn_handover(nUEs=False,debug=False,traces_sim_folder=str, nGnbs=int, interval=float ,simDataframes=None ,intervals=None ,scenario=None, packetSize=int, penalty_dict=None):
    # create resulf folder if not exists
    result_folder_path = traces_sim_folder + "/results"
    print(result_folder_path)
    if not os.path.exists(traces_sim_folder):
        os.makedirs(traces_sim_folder)
        
    result_folder_path = result_folder_path + "/DDQN"
    if not os.path.exists(result_folder_path):
        os.makedirs(result_folder_path)
        
    
    
    # Create the environment
    env = Environment(simDataframes, intervals, scenario, nUEs, interval, packetSize)

    # Initialize lists for interval actions and average rewards    
    episode_rewards = [[] for _ in range(nUEs)]
    # create agents, load the models
    train = 0
    if train:
        agents = [ DQNAgent(nGnbs, env.get_observation(0).shape[0]) for _ in range(nUEs)]
        print("Trainning the DQN agents")
        rewards = []
        traces = []
        thr_episode_list = []
        
        for e in range(900):

            env.reset()
            episode_rewards = [[] for _ in range(nUEs)]
            episode_traces = []

            for i,_ in enumerate(intervals):
                # Initialize lists for observations, actions and next observations
                observations, actions, next_observations = [], [], []

                for ue_id in range(nUEs):
                    # Get the current interval and observation for the current UE
                    observation = env.get_observation(ue_id)

                    # Select an action using the DQN agent and set the action in the environment
                    action = agents[ue_id].act(observation)
                    env.set_action(ue_id, action)

                    # Append to the lists
                    observations.append(observation)
                    actions.append(action)
                # Step the environment once, outside of the UEs loop
                env.step()


                for ue_id in range(nUEs):
                    # Get the next observation for the current UE and the reward
                    next_observation = env.get_observation(ue_id)
                    reward = env.get_reward(ue_id)

                    # Append to the lists and the episode rewards
                    next_observations.append(next_observation)
                    episode_rewards[ue_id].append(reward)
                    
                    # Remember the state, action, reward, next state, and done
                    agents[ue_id].remember(observations[ue_id], actions[ue_id], reward, next_observations[ue_id], False)
                    
                    # Each 32 samples replay the memory
                    if i % 100 == 0 and len(agents[ue_id].memory) > 100: 
                        agents[ue_id].replay(100)

                    # Check if the episode is done
                    done = env.is_done()

                    # Reset the environment if done
                    if done:
                        env.reset()
                        break
            episode_mean_reward = np.mean([np.mean(rewards) for rewards in episode_rewards])
            print(f"Episode {e} - Interval {i} - Mean Reward: {episode_mean_reward}")
            rewards.append(episode_mean_reward)
            # save model
            if not os.path.exists(f"{result_folder_path}/train_results"):
                os.makedirs(f"{result_folder_path}/train_results")
                
            thr_episode = np.mean([sum(interval[ue]["Throughput"] for ue in range(nUEs)) for interval in episode_traces])
            thr_episode_list.append(thr_episode)
        for ue_id in range(nUEs):
            agents[ue_id].policy_net.save_weights(f"{result_folder_path}/train_results/agent_model_{ue_id}.weights.h5")
            agents[ue_id].target_net.save_weights(f"{result_folder_path}/train_results/agent_target_model_{ue_id}.weights.h5")
            
        # plot average reward over the episodes
        plt.clf()
        plt.plot(rewards)
        plt.xlabel("Episode")
        plt.ylabel("Average Reward")
        plt.title("Average Reward over Episodes")
        plt.savefig(os.path.join(result_folder_path, "average_reward.png"))
        # save rewards to a csv file
        pd.DataFrame(rewards).to_csv(os.path.join(result_folder_path, "rewards.csv"), index=False)
        
        plt.clf()
        plt.plot(thr_episode_list)
        plt.xlabel("Episode")
        plt.ylabel("Throughput")
        plt.title("Throughput over Episodes")
        plt.savefig(os.path.join(result_folder_path, "throughput.png"))
        # save thr to a csv file
        pd.DataFrame(thr_episode_list).to_csv(os.path.join(result_folder_path, "throughput.csv"), index=False)
            
        # Plot the average reward over the intervals
        plt.clf()
        for ue in range(nUEs):
            plt.plot(episode_rewards[ue])
        plt.xlabel("Interval")
        plt.ylabel("Average Reward")
        plt.title(f"Average Reward over Intervals")
        plt.savefig(os.path.join(result_folder_path, f"episode_rewards_test.png"))
        print("Saved to: ",os.path.join(result_folder_path, f"episode_rewards_test.png"))
        
        # plot the troughput
        plt.clf()
        # for interval for each UE take the throughput
        aggregate_throughput = [sum(interval[ue]["Throughput"] for ue in range(nUEs)) for interval in traces]
    
        # Fit polynomial
        #degree = 3
        #coefficients = np.polyfit(range(len(aggregate_throughput)), aggregate_throughput, degree)

        #polynomial = np.poly1d(coefficients)

        #trendline = polynomial(range(len(aggregate_throughput)))

        plt.plot(aggregate_throughput)
        #plt.plot(trendline)
        plt.ylabel("Throughput")
        plt.title(f"Throughput over Intervals ")
        plt.savefig(os.path.join(result_folder_path, f"throughput_test.png"))
        print("Saved to: ",os.path.join(result_folder_path, f"throughput_test.png"))
        
        
        plt.clf()
        # print aggregate throughput per episode
        for ue in range(nUEs):
            plt.plot([sum(interval[ue]["Throughput"] for interval in traces)])
        plt.xlabel("Episode")
        
        print("DQN agents trained")
    else:
        agents = [ DQNAgent(nGnbs, env.get_observation(0).shape[0],epsilon=0.01) for _ in range(nUEs)]
        
        print("Loading the DQN agents")
        for ue_id in range(nUEs):
            agents[ue_id].policy_net.load_weights(f"{result_folder_path}/train_results/agent_model_{ue_id}.weights.h5")
            agents[ue_id].target_net.load_weights(f"{result_folder_path}/train_results/agent_target_model_{ue_id}.weights.h5")
        print("DQN agents loaded")
    # Reset the environment
    
    env.reset()
    
    env.start_trace_recording()
    # execute one episode to save the traces
    while not env.is_done():
        observations, actions, next_observations = [], [], []
        i,_ = env.get_current_interval()
        for ue_id in range(nUEs):
            # Get the current interval and observation for the current UE
            observation = env.get_observation(ue_id)

            # Select an action using the DQN agent and set the action in the environment
            action = agents[ue_id].act(observation)
            env.set_action(ue_id, action)

            # Append to the lists
            observations.append(observation)
            actions.append(action)

        # Step the environment once, outside of the UEs loop
        env.step()
        
        for ue_id in range(nUEs):
            # Get the next observation for the current UE and the reward
            next_observation = env.get_observation(ue_id)
            reward = env.get_reward(ue_id)

            # Append to the lists and the episode rewards
            next_observations.append(next_observation)
            episode_rewards[ue_id].append(reward)

            
            # Check if the episode is done
            done = env.is_done()
            
            # Remember the state, action, reward, next state, and done
            agents[ue_id].remember(observations[ue_id], actions[ue_id], reward, next_observations[ue_id], done)
            
            # Each 32 samples replay the memory
            if i % 100 == 0 and len(agents[ue_id].memory) > 100: 
                agents[ue_id].replay(100)
            


        done = env.is_done()

        # Reset the environment if done
        if done:
            env.reset()
            break
    env.stop_trace_recording()
    # save the traces
    traces = env.get_traces()
    
    #save the traces
    if not os.path.exists(f"{result_folder_path}/ue-ideal"):
        os.makedirs(f"{result_folder_path}/ue-ideal")
        
    for ue_id in range(nUEs):
        traces[ue_id].to_csv(f"{result_folder_path}/ue-ideal/UE-{ue_id}.csv", index=False)
    print("Saved traces to ",f"{result_folder_path}/ue-ideal/UE-{ue_id}.csv")

    # gnb simulation
    if not os.path.exists(f"{result_folder_path}/gnb"):
        os.makedirs(f"{result_folder_path}/gnb")
    gnb_results = []
    for  gnb_id in range(nGnbs):
        gnb_result = simulator_common.simulate_gnb( gnb_id, intervals, nUEs,traces,scenario, packetSize)
        gnb_results.append(pd.DataFrame(gnb_result))
        pd.DataFrame(gnb_result).to_csv(f"{result_folder_path}/gnb/GNB-{gnb_id}.csv", index=False)
        
    # execute the restricted simulation
    restricted_ue_results = []
    # create a folder to save the results
    if not os.path.exists(f"{result_folder_path}/ue-restricted"):
        os.makedirs(f"{result_folder_path}/ue-restricted")
    for ue_id in range(nUEs):
        ue_result = simulator_common.simulate_user_restricted(traces,gnb_results, ue_id, intervals, packetSize)
        restricted_ue_results.append(ue_result)
        pd.DataFrame(ue_result).to_csv(f"{result_folder_path}/ue-restricted/UE-{ue_id}.csv", index=False)

    # convert the list of dataframes to a single dataframe
    gnbs_metrics = pd.concat(gnb_results)
    # aggregate the fields
    throughput_total = gnbs_metrics['Throughput'].sum()

    gnbs_metrics["Latency"] = gnbs_metrics['Latency'] * gnbs_metrics['Throughput']

    gnbs_metrics = gnbs_metrics.groupby(['Time']).agg({
        'Throughput': 'sum',
        'TxPacketsAcc': 'sum',
        'TxBytesAcc': 'sum',
        'TxBytesDiff': 'sum',
        'TxPacketsDiff': 'sum',
        'Latency': 'mean',
        'RxPacketsAcc': 'sum',
        'RxBytesAcc': 'sum',
        'RxBytesDiff': 'sum',
        'RxPacketsDiff': 'sum',
        'Jitter': 'mean',
        'LostPackets': 'sum',
        'ConnectedUEs': 'sum',
        'Occupation': 'mean',
        'PLostPackets': 'mean',
        'MOS': 'mean'
    })
    # Calculate total throughput
    gnbs_metrics["Latency"] = gnbs_metrics['Latency'] / gnbs_metrics['Throughput']
    
    # Calculate new latency
    meanThroughput = gnbs_metrics['Throughput'] / nGnbs
    gnbs_metrics['MeanThroughput'] = gnbs_metrics['Throughput'] / nGnbs

    print("Saving the results")
    # save the results to a file into the results folder
    gnbs_metrics_file = os.path.join(result_folder_path, "scenario.csv")
    gnbs_metrics.to_csv(gnbs_metrics_file)
    print(f"Finished {ALGORITHM} algorithm simulation")

    #save the score of the algorithm
    score = calculate_algorithm_score(gnbs_metrics)
    print(f"Scenario Score: {score}")
    # save the score in a file
    score_file = os.path.join(result_folder_path, "scenario-score.txt")
    with open(score_file, "w") as file:
        file.write(str(int(score)))
    


    




#usr/bin/env python3
#encoding: utf-8

import pandas as pd
from utils import *
import os
from scoring import *
import logging
from nrEvents import *
from simulator_common import *


ALGORITHM = "SBGH"

DELAY_INTERVALS = 1

SCORE_THRESHOLD = 1.25





HANDOVER_INTERVAL = 100 # The interval for the handover calculation, in multiples of the t_interval


def simulate_sbgh_users(nUEs=int ,simDataframes=None ,intervals=None, interval=None ,scenario=None, alpha=float, beta=float,delay = 0,penalty_dict=None,penalty_time=float):
    """Simulate the SBGH/GTI handover algorithm for the UEs.

    Args:
        nUEs (int): The number of UEs.
        interval (float): The interval of the simulation.
        simDataframes (list): A list of lists of dataframes.
        intervals (list): A list of intervals.
        scenario (dict): The scenario data.
        alpha (float): The alpha parameter for the score calculation.
        beta (float): The beta parameter for the score calculation.
        delay (int): The delay in intervals for the handover decision.
        penalty_dict (dict): A dictionary containing the penalty values for each gNB.
        penalty_time (float): The penalty time for the handover, the time the connection gets degraded after each handover.

    Returns:
        list: A list of dataframes containing the simulation results.
    """
    if  delay == 0:
        algorithm = "ideal-SBGH"
    else:
        algorithm = "SBGH"
    logging.info(f"Starting  {algorithm} Algorithm Handover Simulation")
    gnbs = scenario['gnbs']
    bands = scenario['bands']
    # create a structure to store the UEs connected to each gNB
    connected_ues = {}
    ues_connected_gnbs = [-1] * nUEs
    handover_flag = False
    
        
    timers = [0] * nUEs  
    penalty_timers = [0] * nUEs  
    # create the value Remaining bandwidth for each gNB
    for gnb in gnbs:
        # create a list of connected UEs for each gNB
        connected_ues[gnb["GNB_ID"]] = []
        for band in bands:
            if band['Band_ID'] == gnb['Band_ID']:
                gnb['RemainingThroughput'] = get_datarate(band['GNB_Bandwidth_Hz']) 
                gnb["GnBBandwidth"] = band['GNB_Bandwidth_Hz']
                gnb["UserBandwidth"] = band['User_Bandwidth_Hz']
                gnb["MaxUsers"] = math.floor(band['GNB_Bandwidth_Hz'] / band['User_Bandwidth_Hz'])
                gnb['GnBThroughput'] = get_datarate(band['GNB_Bandwidth_Hz'])
                gnb['UserThroughput'] = get_datarate(band['User_Bandwidth_Hz'])
                gnb["connected_ues"] = 0
                break
            
                
                
    # Create a list of pandas dataframes for each user
    results = []
    results_score = []
    for user in range(nUEs):
        results.append([])
        results_score.append([])
        
        
    for index,match_interval in enumerate(intervals):
        if index < delay:
            delay_index = 0 
        else:
            delay_index = index - delay # delay the decision by DELAY_INTERVALS
        
        print_progress(index+1, len(intervals), prefix = 'UE Simulation Progress:', suffix = 'Complete')
        # reset the gNB remaining throughput
        for gnb in gnbs:
            for band in bands:
                if band['Band_ID'] == gnb['Band_ID']:
                    connected_ues_count = sum([1 for y in ues_connected_gnbs if y == gnb["GNB_ID"]])
                    #print(f"Index: {index} - gnb {gnb['GNB_ID']} - Connected UEs: {connected_ues_count} - Max Users: {gnb['MaxUsers']}")
                    break
        interval_scores = []
        for user in range(nUEs):

            dataframes = simDataframes[user]
            handovers = 0
            t_handover = 0

            previous_gnb = None
            previous_gnb_id = None

            connected_gnb = None
            connected_gnb_id = None
            
            connected_gnb_delay = None
            
            
            candidates = []
            scores = []
            position = None
            sysTime = None
            
            # if the UE is already connected to a gNB, calculate if the interval is a handover interval (index % HANDOVER_INTERVAL == 0)
            # - if so calculate the score for the gNBs
            # - if not, continue with the current gNB
            # if the UE is not connected to a gNB, calculate the score for the gNBs
            
            if ues_connected_gnbs[user] != -1:
                connected_gnb_id = ues_connected_gnbs[user]
                
            for gnb in gnbs:
                for band in bands:
                    if band['Band_ID'] == gnb['Band_ID']:
                        connected_ues_count = sum([1 for y in ues_connected_gnbs if y == gnb["GNB_ID"]])
                        gnb['connected_ues'] = connected_ues_count
                        break
            
            if connected_gnb_id is  None or index % HANDOVER_INTERVAL == 0:
                for file_id, df in enumerate(dataframes):
                    gnb_data = get_gnb_data(file_id, dataframes, delay_index)
                    score = calculate_score(gnb_data, scenario, file_id, alpha, beta)
                    scores.append({"GNB_ID": file_id, "score": score})
                scores = sorted(scores, key=lambda x: x["score"], reverse=True)
                interval_scores.append(scores)
                # Candidate criteria: the gNB has a positive score and the gNB has enough bandwidth for the UE considering a ideal scenario
                
                for score in scores:
                    gnb = gnbs[score["GNB_ID"]]
                    connected_ues_count = sum([1 for y in ues_connected_gnbs if y == gnb["GNB_ID"]])
                    if score["score"] > 0 and (connected_ues_count)* gnb["UserThroughput"] < gnb["GnBThroughput"]:
                        candidates.append(score)
                if len(candidates) > 0:
                    #print(f"Best candidate is {candidates}")

                        best_candidate = candidates[0]["GNB_ID"]

                else:
                    best_candidate = None
                    
                
                
                
                # Possible options:
                    #-------------------------------|
                    # There is not a best candidate: - nothing happens
                    #-------------------------------|
                    #                                - If the UE is connected to the best candidate, nothing happens, the UE remains connected to the same gNB
                    # There is a best candidate:     - If the UE is connected to a different gNB,
                    #                                       -  if the best candidate is better than a SCORE_THRESHOLD of the current gNB, the UE initiates the handover process
                    #                                       -  if the best candidate is not better than a SCORE_THRESHOLD of the current gNB, nothing happens
                    #                                - If the UE is disconnected, the UE initiates the connection process
                    #-------------------------------|
                previous_gnb = connected_gnb
                previous_gnb_id = connected_gnb_id
                if best_candidate is None:
                    if connected_gnb_id is not None:
                        # nothing happens
                        connected_gnb_id = connected_gnb_id
                else: 
                    # directly connect to the best candidate
                    if connected_gnb_id is None:
                        connected_gnb_id = best_candidate
                        
                    else:
                        # if the UE is connected to a different gNB and has a candidate
                        if connected_gnb_id != best_candidate:
                            
                            connected_scores = next((score for score in scores if score["GNB_ID"] == connected_gnb_id), None)
                            best_scores = next((score for score in scores if score["GNB_ID"] == best_candidate), None)
                            timers[user] = HANDOVER_INTERVAL
                            # evaluate the best candidate
                            if best_scores["score"] > SCORE_THRESHOLD * connected_scores["score"]:
                                # it is a better candidate than the current gNB, initiate the handover
                                connected_gnb_id = best_candidate
                                handovers += 1
                                penalty_timers[user] = penalty_time
                                
                            
            
                        
            ues_connected_gnbs[user] = connected_gnb_id
            if connected_gnb_id is not None:
                connected_gnb = get_gnb_data(connected_gnb_id,dataframes, delay_index)
                connected_gnb_delay = get_gnb_data(connected_gnb_id,dataframes, index)
                if penalty_timers[user] > 0:
                    # apply the penalty
                    apply_penalty(connected_gnb_delay, penalty_dict, penalty_timers[user], interval)
                    penalty_timers[user] -= interval
            else:
                connected_gnb = None
                connected_gnb_delay = None
                    # take the data for the connected gNB
            for gnb in gnbs:
                for band in bands:
                    if band['Band_ID'] == gnb['Band_ID']:
                        # number of UEs connected to the gNB
                        # 1 if the UE is connected to the gNB, 0 otherwise for each y = ues_connected_gnbs[user] == gnb["GNB_ID"]
                        # the sum of the y values is the number of UEs connected to the gNB
                        connected_ues_count = sum([1 for y in ues_connected_gnbs if y == gnb["GNB_ID"]])
                        gnb['connected_ues'] = connected_ues_count
                        break            
                        
                            
            if connected_gnb_delay is not None:
                tx_packets_diff = connected_gnb_delay["TxPacketsDiff"]
                tx_bytes_diff = connected_gnb_delay["TxBytesDiff"]
                rx_packets_diff = connected_gnb_delay["RxPacketsDiff"]
                rx_bytes_diff = connected_gnb_delay["RxBytesDiff"]
                latencySum = connected_gnb_delay["LatencySum"]
                jitter = connected_gnb_delay["JitterSum"]
                lost_packets = connected_gnb_delay["LostPacketsDiff"]
                distance = connected_gnb_delay["Distance"]
                rsrp = connected_gnb_delay["Rsrp"]
                position = connected_gnb_delay["UE Position"]
                throughput = connected_gnb_delay["Throughput"]
                
                #sysTime = connected_gnb_delay["System Time"].values[0]
            else:
                connected_gnb_id = None
                throughput = 0
                tx_packets_diff = 0
                tx_bytes_diff = 0
                rx_packets_diff = 0
                rx_bytes_diff = 0
                latencySum = 0
                lost_packets = 0
                jitter = 0
                rsrp = None
                distance = None
                position = gnb_data["UE Position"]

            



            interval_metrics = {
                "Time": float(match_interval),
                "GNodeB": connected_gnb_id,
                "Throughput": throughput,
                "TxBytesDiff": tx_bytes_diff,
                "TxPacketsDiff": tx_packets_diff,
                "RxBytesDiff": rx_bytes_diff,
                "RxPacketsDiff": rx_packets_diff,
                "Latency": latencySum,
                "Jitter": jitter,
                "LostPackets": lost_packets,
                "Distance": distance,
                "Rsrp": rsrp,
                "UE Position": position,
                "Handovers": handovers,
            }
            results[user].append(interval_metrics)
    for user in range(nUEs):
        results[user] = pd.DataFrame(results[user])
        # calculate the adding the Diff values per each interval
        results[user]["TxBytesAcc"] = results[user]["TxBytesDiff"].cumsum()
        results[user]["TxPacketsAcc"] = results[user]["TxPacketsDiff"].cumsum()
        results[user]["RxBytesAcc"] = results[user]["RxBytesDiff"].cumsum()
        results[user]["RxPacketsAcc"] = results[user]["RxPacketsDiff"].cumsum()
    return results,results_score


def simulate_sbgh_handover(nUEs=False,debug=False,traces_sim_folder=str, nGnbs=int, interval=float ,simDataframes=None ,intervals=None ,scenario=None, packetSize=int, alpha=float, beta=float, penalty_dict=None, penalty_time=float):
        """Simulate the proposed SBGH handover algorithm.

        Args:
        
            nUEs (int): The number of UEs.
            debug (bool): If True, the debug mode is activated.
            traces_sim_folder (str): The folder where the traces are stored.
            nGnbs (int): The number of gNBs.
            interval (float): The interval of the simulation.
            simDataframes (list): A list of lists of dataframes.
            intervals (list): A list of intervals.
            scenario (dict): The scenario data.
            packetSize (int): The packet size.
            alpha (float): The alpha parameter for the score calculation.
            beta (float): The beta parameter for the score calculation.
            penalty_dict (dict): A dictionary containing the penalty values for each gNB.
            penalty_time (float): The penalty time for the handover, the time the connection gets degraded after each handover.
            
        
        Returns:
            None
        """
        ue_results, score_results = simulate_sbgh_users(nUEs ,simDataframes ,intervals,interval,scenario,alpha, beta, delay = 1, penalty_dict=penalty_dict, penalty_time=penalty_time)
        results_folder = os.path.join(traces_sim_folder, "results")
        if not os.path.isdir(results_folder):
            os.mkdir(results_folder)
        # create a folder for the the algorithm
        results_folder = os.path.join(results_folder, ALGORITHM)
        if not os.path.isdir(results_folder):
            os.mkdir(results_folder)
        # create a folder for the scores
        scores_folder = os.path.join(results_folder, "scores")
        if not os.path.isdir(scores_folder):
            os.mkdir(scores_folder)
        ue_results_folder = os.path.join(results_folder, "ue-ideal")
        if not os.path.isdir(ue_results_folder):
            os.mkdir(ue_results_folder)
    
        for user in range(nUEs):
            print_progress(user+1, nUEs, prefix = 'Ideal UE Simulation Progress:', suffix = 'Complete')
            results = ue_results[user]
            results_file = os.path.join(ue_results_folder, f"UE-{user}.csv")
            results.to_csv(results_file, index=False)

        # calculate the gNB metrics
        gnbResults_list = []    
        logging.info("Calculating gNB metrics")
        for gnb in range(nGnbs):
            print_progress(gnb+1, nGnbs, prefix = 'GNB Simulation Progress:', suffix = 'Complete')
            gnbResults_list.append(simulate_gnb(gnb,intervals,nUEs, ue_results, scenario, packetSize))
        # Save the results to a file
        for gnb in range(nGnbs):
            gnbResults_folder = os.path.join(results_folder, "gnb")
            if not os.path.isdir(gnbResults_folder):
                os.mkdir(gnbResults_folder)
            gnbResults_file = os.path.join(gnbResults_folder, f"GNB-{gnb}.csv")
            gnbResults_list[gnb] = pd.DataFrame(gnbResults_list[gnb])
            gnbResults_list[gnb].to_csv(gnbResults_file, index=False)
        
        logging.info("Calculating the restricted UE throughput")
        # create a folder to save the results
        ueResults_folder = os.path.join(results_folder, "ue-restricted")
        if not os.path.isdir(ueResults_folder):
            os.mkdir(ueResults_folder)
        
        for ue in range(nUEs):
            print_progress(ue+1, nUEs, prefix = 'Restricted UE Simulation Progress:', suffix = 'Complete')
            ue_results[ue] = simulate_user_restricted(ue_results, gnbResults_list, ue, intervals, packetSize)
            # Save the results to a file
            ueResults_file = os.path.join(ueResults_folder, f"UE-{ue}.csv")
            ue_results[ue].to_csv(ueResults_file, index=False)
    
        logging.info("Calculating the scenario metrics")
        # convert the list of dataframes to a single dataframe
        gnbs_metrics = pd.concat(gnbResults_list)
        # aggregate the fields
        
        gnbs_metrics = gnbs_metrics.groupby(['Time']).agg({
            'Throughput': 'sum',
            'TxPacketsAcc': 'sum',
            'TxBytesAcc': 'sum',
            'TxBytesDiff': 'sum',
            'TxPacketsDiff': 'sum',
            'RxPacketsAcc': 'sum',
            'RxBytesAcc': 'sum',
            'RxBytesDiff': 'sum',
            'RxPacketsDiff': 'sum',
            'Latency': 'mean',
            'Jitter': 'mean',
            'LostPackets': 'sum',
            'ConnectedUEs': 'sum',
            'Occupation': 'mean',
            'PLostPackets': 'mean',
            'Handovers': 'sum',
        })

        gnbs_metrics['MeanThroughput'] = gnbs_metrics['Throughput'] / nGnbs
        
        logging.info("Saving the results")
        # save the results to a file into the results folder
        gnbs_metrics_file = os.path.join(results_folder, "scenario.csv")
        gnbs_metrics.to_csv(gnbs_metrics_file)
        algorithm = "SBGH"
        logging.info(f"Finished {algorithm} algorithm simulation")
        
    
        #save the score of the algorithm
        score = calculate_algorithm_score(gnbs_metrics)
        logging.info(f"Scenario Score: {score}")
        # save the score in a file
        score_file = os.path.join(results_folder, "scenario-score.txt")
        with open(score_file, "w") as file:
            file.write(str(int(score)))


def simulate_ideal_sbgh_handover(nUEs=False,debug=False,traces_sim_folder=str, nGnbs=int, interval=float ,simDataframes=None ,intervals=None ,scenario=None, packetSize=int, alpha=float, beta=float, penalty_dict=None, penalty_time=float):
        """Simulate the propossed handover algorithm.

        Args:
        
            nUEs (int): The number of UEs.
            debug (bool): If True, the debug mode is activated.
            traces_sim_folder (str): The folder where the traces are stored.
            nGnbs (int): The number of gNBs.
            interval (float): The interval of the simulation.
            simDataframes (list): A list of lists of dataframes.
            intervals (list): A list of intervals.
            scenario (dict): The scenario data.
            packetSize (int): The packet size.
        
        Returns:
            None
        """
        ue_results,ue_results_score = simulate_sbgh_users(nUEs ,simDataframes ,intervals,interval ,scenario,alpha, beta, delay = 0, penalty_dict=penalty_dict, penalty_time=penalty_time)
        results_folder = os.path.join(traces_sim_folder, "results")
        if not os.path.isdir(results_folder):
            os.mkdir(results_folder)
        # create a folder for the the algorithm
        results_folder = os.path.join(results_folder, "ideal-SBGH")
        if not os.path.isdir(results_folder):
            os.mkdir(results_folder)
        # create a folder for the scores
        scores_folder = os.path.join(results_folder, "scores")
        if not os.path.isdir(scores_folder):
            os.mkdir(scores_folder)
        ue_results_folder = os.path.join(results_folder, "ue-ideal")
        if not os.path.isdir(ue_results_folder):
            os.mkdir(ue_results_folder)
    
        for user in range(nUEs):
            print_progress(user+1, nUEs, prefix = 'Ideal UE Simulation Progress:', suffix = 'Complete')
            results = pd.DataFrame(ue_results[user])
            results_score = pd.DataFrame(ue_results_score[user])
            # save the scores in a file
            results_score_file = os.path.join(scores_folder, f"UE-{user}.csv")
            
            results_score.to_csv(results_score_file, index=False)
            # save the results in a file
            results_file = os.path.join(ue_results_folder, f"UE-{user}.csv")
            results.to_csv(results_file, index=False)

        # calculate the gNB metrics
        gnbResults_list = []    
        logging.info("Calculating gNB metrics")
        for gnb in range(nGnbs):
            print_progress(gnb+1, nGnbs, prefix = 'GNB Simulation Progress:', suffix = 'Complete')
            gnbResults_list.append(simulate_gnb(gnb,intervals,nUEs, ue_results, scenario, packetSize))
        # Save the results to a file
        for gnb in range(nGnbs):
            gnbResults_folder = os.path.join(results_folder, "gnb")
            if not os.path.isdir(gnbResults_folder):
                os.mkdir(gnbResults_folder)
            gnbResults_file = os.path.join(gnbResults_folder, f"GNB-{gnb}.csv")
            gnbResults_list[gnb] = pd.DataFrame(gnbResults_list[gnb])
            gnbResults_list[gnb].to_csv(gnbResults_file, index=False)
        
        logging.info("Calculating the restricted UE throughput")
        # create a folder to save the results
        ueResults_folder = os.path.join(results_folder, "ue-restricted")
        if not os.path.isdir(ueResults_folder):
            os.mkdir(ueResults_folder)
        
        for ue in range(nUEs):
            print_progress(ue+1, nUEs, prefix = 'Restricted UE Simulation Progress:', suffix = 'Complete')
            ue_results[ue] = simulate_user_restricted(ue_results, gnbResults_list, ue, intervals, packetSize)
            # Save the results to a file
            ueResults_file = os.path.join(ueResults_folder, f"UE-{ue}.csv")
            ue_results[ue].to_csv(ueResults_file, index=False)
    
        logging.info("Calculating the scenario metrics")
        # convert the list of dataframes to a single dataframe
        gnbs_metrics = pd.concat(gnbResults_list)
        # aggregate the fields
        gnbs_metrics = gnbs_metrics.groupby(['Time']).agg({
            'Throughput': 'sum',
            'TxPacketsAcc': 'sum',
            'TxBytesAcc': 'sum',
            'TxBytesDiff': 'sum',
            'TxPacketsDiff': 'sum',
            'RxPacketsAcc': 'sum',
            'RxBytesAcc': 'sum',
            'RxBytesDiff': 'sum',
            'RxPacketsDiff': 'sum',
            'Latency': 'mean',
            'Jitter': 'mean',
            'LostPackets': 'sum',
            'ConnectedUEs': 'sum',
            'Occupation': 'mean',
            'PLostPackets': 'mean',

        })

        meanThroughput = gnbs_metrics['Throughput'] / nGnbs
        gnbs_metrics['MeanThroughput'] = gnbs_metrics['Throughput'] / nGnbs
        

        
        logging.info("Saving the results")
        # save the results to a file into the results folder
        gnbs_metrics_file = os.path.join(results_folder, "scenario.csv")
        gnbs_metrics.to_csv(gnbs_metrics_file)
        algorithm = "ideal-SBGH"
        logging.info(f"Finished {algorithm} algorithm simulation")
        
        #save the score of the algorithm
        score = calculate_algorithm_score(gnbs_metrics)
        logging.info(f"Scenario Score: {score}")
        # save the score in a file
        score_file = os.path.join(results_folder, "scenario-score.txt")
        with open(score_file, "w") as file:
            file.write(str(int(score)))

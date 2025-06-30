#usr/bin/env python3
# encoding: UTF-8
import pandas as pd
from utils import *
import os
import multiprocessing as mp
from occupation import *
from simulator_common import *
from scoring import calculate_algorithm_score


import pandas as pd
import logging
import logging.config
from nrEvents import *
ALGORITHM = "3GPP_A3"
def simulate_user(user=int,simDataframes=None, intervals=None, Hys=float, A3Offset=float, NrMeasureInt=float, interval=float, DECISION_PARAMETER=str, TTT=float, penalty_time=float, bands=None, packetSize=int):
    logging.info(f"Simulating UE {user}")
    ueResults = []

    dataframes = simDataframes[user]
    handovers = 0
    t_handover = 0

    nr_timer = 0
    ttt_timer = 0  # TTT timer
    ttt_event = None  # TTT event

    handover_started = False
    handover_remaining_time = 0  
    
    ttt_started = False  # Flag to indicate if TTT has started
    nr_event_triggered = False 


    connected_gnb = None
    connected_gnb_id = None
    tx_packets_acc = 0
    tx_bytes_acc = 0
    rx_bytes_acc = 0
    rx_packets_acc = 0

    for index,match_interval in enumerate(intervals):
        
        best_gnb = None
        best_gnb_id = None
        best_metric_value = float('-inf')
        postition = None
        sysTime = None
        




        # Iterate over each gNB file
        for file_id, df in enumerate(dataframes):
            # Filter the dataframe for the current time interval "Time" == match_interval
            interval_df = df.loc[df["Time"] == match_interval]
            # Find the row with the maximum value of the metric
            interval_metric_value = interval_df[DECISION_PARAMETER].values[0]
            if interval_metric_value > best_metric_value:
                if connected_gnb_id is not None and connected_gnb_id == file_id:
                    continue
                best_gnb_id = file_id  # Adding 1 to match the file_id
                best_gnb = interval_df
                best_metric_value = interval_metric_value
                # Get the thoughput in the interval
        if connected_gnb is not None:
            throughput = connected_gnb["Throughput"]
            tx_packets_diff = connected_gnb["TxPacketsDiff"]
            tx_bytes_diff = connected_gnb["TxBytesDiff"]
            rx_packets_diff = connected_gnb["RxPacketsDiff"]
            rx_bytes_diff = connected_gnb["RxBytesDiff"]
            latencySum = connected_gnb["LatencySum"]
            jitter = connected_gnb["JitterSum"]
            lost_packets_diff = connected_gnb["LostPacketsDiff"]
            distance = connected_gnb["Distance"]
            rsrp = connected_gnb["Rsrp"]
            postition = connected_gnb["UE Position"]
            sysTime = connected_gnb["System Time"]
        else:
            throughput = 0
            tx_bytes_diff = 0
            tx_packets_diff = 0
            rx_bytes_diff = 0
            rx_packets_diff = 0
            lost_packets_diff = 0         
            latencySum = 0
            jitter = 0
            rsrp = None
            distance = None
            # take the position from the UE file
            postition = interval_df["UE Position"].values[0]
            sysTime = interval_df["System Time"].values[0]
            
            

            



        t_handover += interval

        tx_packets_acc += tx_packets_diff
        tx_bytes_acc += tx_bytes_diff
        rx_packets_acc += rx_packets_diff
        rx_bytes_acc += rx_bytes_diff
        
        interval_metrics = {
            "Time": match_interval,
            "GNodeB": connected_gnb_id,
            "Throughput": throughput,
            "TxPacketsAcc": tx_packets_acc,
            "TxBytesAcc": tx_bytes_acc,
            "TxBytesDiff": tx_bytes_diff,
            "TxPacketsDiff": tx_packets_diff,
            "RxBytesAcc": rx_bytes_acc,
            "RxPacketsAcc": rx_packets_acc,
            "RxBytesDiff": rx_bytes_diff,
            "RxPacketsDiff": rx_packets_diff,
            "Latency": latencySum,
            "Jitter": jitter,
            "LostPackets": lost_packets_diff,
            "Distance": distance,
            "Rsrp": rsrp,
            "UE Position": postition,
            "Handovers": handovers,
            "System Time": sysTime
        }

        ueResults.append(interval_metrics)



        nr_timer += interval
        # If NR timmer expires then we need to check the events
        if nr_timer >= NrMeasureInt:
            nr_timer -= NrMeasureInt
            #logging.debug(f"NR timer expired. Checking events")
            if best_gnb_id is not None:
                best_rsrp = best_gnb["Rsrp"].values[0]
                if not ttt_started and not handover_started and not nr_event_triggered:
                    if connected_gnb_id == None:
                        if best_gnb_id != None:
                            logging.debug(f"Connected to GNB {best_gnb_id}")
                            connected_gnb_id = best_gnb_id
                            continue;
                    else:
                        if connected_gnb is not None:  
                                connected_rsrp = connected_gnb["Rsrp"]
                                if check_A3_event(best_rsrp, connected_rsrp, A3Offset, Hys, best_gnb_id, connected_gnb_id):
                                    logging.debug("A3 event detected. Starting TTT timer")
                                    ttt_started = True
                                    ttt_event = 3
                                    continue;
                if nr_event_triggered:
                    
                    nr_event_triggered = False
                    if ttt_event == 3 and  not check_A3_2_event(best_rsrp, connected_rsrp, A3Offset, Hys, best_gnb_id, connected_gnb_id):
                        logging.info(f"A3 event detected. Handover from GNB {connected_gnb_id} to GNB {best_gnb_id}")
                        connected_gnb_id = best_gnb_id
                        handover_started = True
                        handover_remaining_time = penalty_time
                        handovers = True
                    ttt_event = None
                        

            if ttt_started:
                ttt_timer += interval
                # Check A3-2 event
                if ttt_event == 3:
                    if check_A3_2_event(best_rsrp, connected_rsrp, A3Offset, Hys, best_gnb_id, connected_gnb_id):
                        logging.info(f"A3-2 event detected.Exiting TTT timer")
                        ttt_event = None
                        ttt_started = False
                        nr_event_triggered = False
                        ttt_timer = 0
                if ttt_timer >= TTT:
                    logging.debug(f"TTT timer expired. Asociated event: A{ttt_event}")
                    nr_event_triggered = True
                    ttt_timer = 0
                    ttt_started = False
                    
                    

            if connected_gnb_id is not None:
                connected_gnb = get_gnb_data(connected_gnb_id, dataframes, index)
                
                if handover_remaining_time > 0:
                    penalty_dict = {}
                    penalty_dict["LatencySum"] = 0.020 
                    # connected_gnb = apply_penalty(connected_gnb, penalty_dict, handover_remaining_time,interval)
                    handover_remaining_time -= interval
                    

            else:
                connected_gnb = None

    return ueResults




def simulate_3gpp_handover(nUEs=False,debug=False,traces_sim_folder=str, nGnbs=int,  Hys=float, A3Offset=float, NrMeasureInt=float, interval=float, DECISION_PARAMETER=str, TTT=float, penalty_time=float, intervals= None, simDataframes=None, scenario=None, packetSize=int):
    ueResults_df = [] * nUEs
    gnbResults_list = []
    logging.info(f"Simulating 3GPP A3 NR event based handover")
    # Create the results folder
    results_folder = os.path.join(traces_sim_folder, "results")
    if not os.path.isdir(results_folder):
        os.mkdir(results_folder)
    results_folder = os.path.join(results_folder, ALGORITHM)
    if not os.path.isdir(results_folder):
        os.mkdir(results_folder)
    # CPU threads
    cpu_threads_count =  mp.cpu_count()
    with mp.Pool(cpu_threads_count) as pool:
        # create a list of processes
        processes = [{'p':pool.apply_async(simulate_user, args=(ue,simDataframes, intervals, Hys, A3Offset, NrMeasureInt, interval, DECISION_PARAMETER, TTT, penalty_time)), 'id': ue} for ue in range(nUEs)]
        # save the results by id
        for p in processes:
            logging.info(f"UE {p['id']} started")
            ueResults_df.insert(p['id'], p['p'].get())
            logging.info(f"UE {p['id']} finished")
    # Save the results to a file
    for ue in range(nUEs):
        ueIdealResults_folder = os.path.join(results_folder, "ue-ideal")
        if not os.path.isdir(ueIdealResults_folder):
            os.mkdir(ueIdealResults_folder)
        ueResults_file = os.path.join(ueIdealResults_folder, f"UE-{ue}.csv")
        ueResults_df[ue] = pd.DataFrame(ueResults_df[ue])
        ueResults_df[ue].to_csv(ueResults_file, index=False)
        
    # calculate the gNB metrics
    logging.info("Calculating gNB metrics")
    for gnb in range(nGnbs):
        gnbResults_list.append(simulate_gnb(gnb,intervals,nUEs, ueResults_df, scenario, packetSize))
        logging.info(f"GNB {gnb} finished")
    # Save the results to a file
    for gnb in range(nGnbs):
        gnbResults_folder = os.path.join(results_folder, "gnb")
        if not os.path.isdir(gnbResults_folder):
            os.mkdir(gnbResults_folder)
        gnbResults_file = os.path.join(gnbResults_folder, f"GNB-{gnb}.csv")
        gnbResults_list[gnb] = pd.DataFrame(gnbResults_list[gnb])
        gnbResults_list[gnb].to_csv(gnbResults_file, index=False)
    
    # now from the ocupation in the gnb we can calculate the restricted ue troughput
    logging.info("Calculating the restricted UE throughput")
    # create a folder to save the results
    restricted_ueResults_folder = os.path.join(results_folder, "ue-restricted")
    restricted_ueResults_df = []
    if not os.path.isdir(restricted_ueResults_folder):
        os.mkdir(restricted_ueResults_folder)

    for ue in range(nUEs):
        restricted_ueResults_df.append(pd.DataFrame(simulate_user_restricted(ueResults_df, gnbResults_list, ue, intervals, packetSize)))
        logging.info(f"UE {ue} finished")
        restricted_ueResults_file = os.path.join(restricted_ueResults_folder, f"UE-{ue}.csv")
        
        pd.DataFrame(restricted_ueResults_df[ue]).to_csv(restricted_ueResults_file, index=False)
    # calculate the scenario metrics
    logging.info("Calculating the scenario metrics")
    scenarioResults = []
    # calculate the scenario metrics for each interval aggregate each gnb
    for index, interval in enumerate(intervals):
        interval_data = []
        for gnb in range(nGnbs):
            gnb_data = gnbResults_list[gnb]
            interval_data.append(gnb_data.iloc[index])
        interval_data = pd.DataFrame(interval_data)
        if len(interval_data) > 0:
            interval_data = interval_data.agg({
                        "Throughput": "sum",
                        "TxPacketsAcc": "sum",
                        "TxBytesAcc": "sum",
                        "TxBytesDiff": "sum",
                        "TxPacketsDiff": "sum",
                        "RxBytesAcc": "sum",
                        "RxPacketsAcc": "sum",
                        "RxBytesDiff": "sum",
                        "RxPacketsDiff": "sum",
                        "Latency": "mean",
                        "Jitter": "mean",
                        "LostPackets": "sum",
                        "ConnectedUEs": "sum",
                        "MeanThroughput": "mean",
                        'PLostPackets': 'mean',
                        "Handovers": "mean",
                        'MOS': 'mean'
                    })
        else:
            interval_data = {
                "Throughput": 0,
                "TxPacketsAcc": 0,
                "TxBytesAcc": 0,
                "TxBytesDiff": 0,
                "TxPacketsDiff": 0,
                "RxBytesAcc": 0,
                "RxPacketsAcc": 0,
                "RxBytesDiff": 0,
                "RxPacketsDiff": 0,
                "Latency": 0,
                "Jitter": 0,
                "LostPackets": 0,
                "ConnectedUEs": 0,
                "MeanThroughput": 0,
                'PLostPackets': 0,
                'MOS': 0
            }
        
        
        # inssert time in the first position
        interval_data = {"Time": interval, **interval_data}
        scenarioResults.append(interval_data)
    scenarioResults = pd.DataFrame(scenarioResults)
    # Save the results to a file in results/<algorithm>/scenario.csv
    scenarioResults.to_csv(os.path.join(results_folder, "scenario.csv"), index=False)
    #save the score of the algorithm
    score = calculate_algorithm_score(scenarioResults)
    logging.info(f"Scenario Score: {score}")
    # save the score in a file
    score_file = os.path.join(results_folder, "scenario-score.txt")
    with open(score_file, "w") as file:
        file.write(str(score))
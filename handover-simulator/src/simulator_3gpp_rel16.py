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
ALGORITHM = "3GPP_REL16_CHO"

def simulate_user(user=int, simDataframes=None, intervals=None, Hys=float, A3Offset=float, 
                  NrMeasureInt=float, interval=float, DECISION_PARAMETER=str, TTT=float, 
                  penalty_time=float, bands=None, packetSize=int, penalty_dict=None,
                  Hys_FR2=None, TTT_FR2=None):
    """
    Simulate user with 3GPP Rel-16 CHO (Conditional Handover)
    - Scans network until A3 event is detected from any gNB
    - When A3 is detected, evaluates all gNBs for CHO candidates
    - Uses different Hysteresis and TTT values for FR1 and FR2 bands
    """
    logging.info(f"Simulating UE {user} with CHO")
    ueResults = []

    dataframes = simDataframes[user]
    handovers = 0
    t_handover = 0

    nr_timer = 0
    ttt_timer = 0  # TTT timer for primary A3 event
    ttt_event = None  # Primary TTT event

    handover_started = False
    handover_remaining_time = 0  
    
    ttt_started = False  # Flag for primary TTT
    nr_event_triggered = False
    
    # CHO specific variables
    cho_mode = False  # Flag to indicate CHO evaluation mode
    cho_candidates = {}  # Dictionary {gnb_id: {'timer': float, 'ttt_required': float, 'triggered': bool}}
    cho_preparation_done = False
    cho_target_gnb_id = None  # The gNB that triggered the initial A3 event
    
    # Set default FR2 parameters if not provided
    # FR2 uses HIGHER hysteresis (6dB) and LONGER TTT (2x) to avoid ping-pong effects
    # due to higher signal variability in mmWave frequencies
    if Hys_FR2 is None:
        Hys_FR2 = 6.0  # FR2 uses 6dB hysteresis to reduce ping-pong
    if TTT_FR2 is None:
        TTT_FR2 = TTT * 2.0  # FR2 uses 2x TTT for more stable handovers
    
    logging.info(f"UE {user} - FR1 params: Hys={Hys}dB, TTT={TTT}s")
    logging.info(f"UE {user} - FR2 params: Hys={Hys_FR2}dB, TTT={TTT_FR2}s") 


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
        position = None
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
                # Get the throughput in the interval
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
            position = connected_gnb["UE Position"]
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
            position = interval_df["UE Position"].values[0]
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
            "UE Position": position,
            "Handovers": handovers,
            "System Time": sysTime
        }

        ueResults.append(interval_metrics)



        nr_timer += interval
        # If NR timer expires then we need to check the events
        if nr_timer >= NrMeasureInt:
            nr_timer -= NrMeasureInt
            
            # Initial connection (no gNB connected yet)
            if connected_gnb_id is None:
                if best_gnb_id is not None:
                    logging.debug(f"UE {user}: Initial connection to GNB {best_gnb_id}")
                    connected_gnb_id = best_gnb_id
                    continue
            
            # Normal operation: scan for A3 events when not in handover or CHO mode
            if connected_gnb is not None and not handover_started and not cho_mode:
                connected_rsrp = connected_gnb["Rsrp"]
                
                # Scan all gNBs for A3 events (excluding current gNB)
                for gnb_id, df in enumerate(dataframes):
                    if gnb_id == connected_gnb_id:
                        continue
                    
                    gnb_df = df.loc[df["Time"] == match_interval]
                    if len(gnb_df) == 0:
                        continue
                    
                    gnb_rsrp = gnb_df["Rsrp"].values[0]
                    gnb_band = bands[gnb_id] if bands is not None else "FR1"
                    
                    # Determine Hys based on the gNB's band
                    gnb_hys = Hys_FR2 if gnb_band == "FR2" else Hys
                    
                    # Check A3 event for this gNB with appropriate Hys
                    if check_A3_event(gnb_rsrp, connected_rsrp, A3Offset, gnb_hys, gnb_id, connected_gnb_id):
                        # A3 event detected! Enter CHO mode
                        logging.info(f"UE {user}: A3 event detected from GNB {gnb_id} ({gnb_band}, Hys={gnb_hys}dB). Entering CHO mode")
                        cho_mode = True
                        cho_target_gnb_id = gnb_id
                        cho_candidates = {}
                        
                        # Evaluate ALL gNBs as CHO candidates (including the one that triggered)
                        for candidate_id, candidate_df in enumerate(dataframes):
                            if candidate_id == connected_gnb_id:
                                continue
                            
                            candidate_data = candidate_df.loc[candidate_df["Time"] == match_interval]
                            if len(candidate_data) == 0:
                                continue
                            
                            candidate_rsrp = candidate_data["Rsrp"].values[0]
                            candidate_band = bands[candidate_id] if bands is not None else "FR1"
                            
                            # Determine Hys and TTT based on band
                            if candidate_band == "FR2":
                                candidate_hys = Hys_FR2
                                candidate_ttt = TTT_FR2
                            else:
                                candidate_hys = Hys
                                candidate_ttt = TTT
                            
                            # Check if candidate meets A3 condition
                            if check_A3_event(candidate_rsrp, connected_rsrp, A3Offset, candidate_hys, candidate_id, connected_gnb_id):
                                logging.debug(f"UE {user}: GNB {candidate_id} ({candidate_band}) added as CHO candidate (TTT={candidate_ttt}s, Hys={candidate_hys}dB)")
                                cho_candidates[candidate_id] = {
                                    'timer': 0,
                                    'ttt_required': candidate_ttt,
                                    'hys': candidate_hys,
                                    'band': candidate_band,
                                    'triggered': False
                                }
                        
                        break  # Exit the scan loop once CHO mode is activated
            
            # CHO mode: update candidate timers and check for execution
            if cho_mode:
                connected_rsrp = connected_gnb["Rsrp"]
                candidates_to_remove = []
                first_cho_candidate = None  # First candidate to complete TTT
                
                # Update timers for all CHO candidates
                for candidate_id, candidate_info in cho_candidates.items():
                    candidate_df = dataframes[candidate_id]
                    candidate_data = candidate_df.loc[candidate_df["Time"] == match_interval]
                    
                    if len(candidate_data) == 0:
                        continue
                    
                    candidate_rsrp = candidate_data["Rsrp"].values[0]
                    candidate_hys = candidate_info['hys']
                    candidate_band = candidate_info['band']
                    candidate_timer = candidate_info['timer']
                    
                    # Check if A3-2 event occurred (candidate no longer suitable)
                    # A3-2: RSRP_neighbor < RSRP_serving + A3Offset - Hys
                    if check_A3_2_event(candidate_rsrp, connected_rsrp, A3Offset, candidate_hys, candidate_id, connected_gnb_id):
                        # Calculate the A3-2 threshold for logging
                        a32_threshold = connected_rsrp + A3Offset - candidate_hys
                        # A3-2 event detected - candidate falls below threshold
                        logging.info(f"UE {user}: CHO candidate GNB {candidate_id} ({candidate_band}) triggered A3-2 event: "
                                   f"RSRP={candidate_rsrp:.2f}dBm < {a32_threshold:.2f}dBm (serving={connected_rsrp:.2f} + offset={A3Offset} - hys={candidate_hys}) "
                                   f"after {candidate_timer:.3f}s - removing from CHO")
                        candidates_to_remove.append(candidate_id)
                        # Reset timer for this candidate
                        candidate_info['timer'] = 0
                    else:
                        # A3 condition still holds, increment timer
                        candidate_info['timer'] += interval
                        
                        if candidate_info['timer'] >= candidate_info['ttt_required'] and not candidate_info['triggered']:
                            candidate_info['triggered'] = True
                            candidate_info['rsrp'] = candidate_rsrp  # Store RSRP for logging
                            
                            # If this is the first candidate to complete TTT, execute HO immediately
                            if first_cho_candidate is None:
                                first_cho_candidate = candidate_id
                                logging.info(f"UE {user}: CHO candidate GNB {candidate_id} ({candidate_band}, Hys={candidate_hys}dB, TTT={candidate_info['ttt_required']}s) completed first - executing HO")
                
                # Remove candidates that no longer meet A3
                for candidate_id in candidates_to_remove:
                    del cho_candidates[candidate_id]
                
                # Execute handover to the FIRST candidate that completed TTT
                if first_cho_candidate is not None:
                    source_band = bands[connected_gnb_id] if bands is not None else "FR1"
                    target_info = cho_candidates[first_cho_candidate]
                    target_band = target_info['band']
                    target_ttt = target_info['ttt_required']
                    target_hys = target_info['hys']
                    target_rsrp = target_info.get('rsrp', 0)
                    
                    logging.info(f"UE {user}: Executing CHO: GNB {connected_gnb_id} ({source_band}) -> GNB {first_cho_candidate} ({target_band}, TTT={target_ttt}s, Hys={target_hys}dB, RSRP={target_rsrp:.2f}dBm)")
                    connected_gnb_id = first_cho_candidate
                    handover_started = True
                    handover_remaining_time = penalty_time
                    handovers += 1
                    
                    # Exit CHO mode
                    cho_mode = False
                    cho_candidates = {}
                    cho_target_gnb_id = None
                
                # Exit CHO mode if no candidates remain
                elif len(cho_candidates) == 0:
                    logging.debug(f"UE {user}: No CHO candidates remaining, exiting CHO mode")
                    cho_mode = False
                    cho_target_gnb_id = None
                    
                    

            if connected_gnb_id is not None:
                connected_gnb = get_gnb_data(connected_gnb_id, dataframes, index)
                
                if handover_remaining_time > 0:
                    connected_gnb = apply_penalty(connected_gnb, penalty_dict, handover_remaining_time,interval)
                    handover_remaining_time -= interval
                    

            else:
                connected_gnb = None

    return ueResults




def simulate_3gpp_cho_handover(nUEs=False, debug=False, traces_sim_folder=str, nGnbs=int, Hys=float, 
                          A3Offset=float, NrMeasureInt=float, interval=float, DECISION_PARAMETER=str, 
                          TTT=float, penalty_time=float, intervals=None, simDataframes=None, 
                          scenario=None, packetSize=int, penalty_dict=None, bands=None, 
                          Hys_FR2=None, TTT_FR2=None):
    ueResults_df = [] * nUEs
    gnbResults_list = []
    
   
    if Hys_FR2 is None:
        Hys_FR2 = 6.0
    if TTT_FR2 is None:
        TTT_FR2 = TTT * 1.0  
    
    logging.info(f"=== Simulating 3GPP Rel-16 CHO (Conditional Handover) ===")
    logging.info(f"Bands configuration: {bands}")
    logging.info(f"FR1 parameters: Hys={Hys}dB, TTT={TTT}s, A3Offset={A3Offset}dB")
    logging.info(f"FR2 parameters: Hys={Hys_FR2}dB , TTT={TTT_FR2}s , A3Offset={A3Offset}dB")
    
    # Count gNBs by band
    if bands is not None:
        fr1_count = bands.count('FR1')
        fr2_count = bands.count('FR2')
        logging.info(f"Network composition: {fr1_count} FR1 gNBs, {fr2_count} FR2 gNBs")
        for i, band in enumerate(bands):
            logging.info(f"  gNB {i}: {band}")
    
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
        processes = [{'p':pool.apply_async(simulate_user, args=(ue, simDataframes, intervals, Hys, A3Offset, 
                                                                  NrMeasureInt, interval, DECISION_PARAMETER, TTT, 
                                                                  penalty_time, bands, packetSize, penalty_dict, 
                                                                  Hys_FR2, TTT_FR2)), 'id': ue} for ue in range(nUEs)]
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

    # Now from the occupation in the gnb we can calculate the restricted ue throughput
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
    # Calculate the scenario metrics
    logging.info("Calculating the scenario metrics")
    scenarioResults = []
    # Calculate the scenario metrics for each interval aggregate each gnb
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

            }


        # insert time in the first position
        interval_data = {"Time": interval, **interval_data}
        scenarioResults.append(interval_data)
    scenarioResults = pd.DataFrame(scenarioResults)
    # Save the results to a file in results/<algorithm>/scenario.csv
    scenarioResults.to_csv(os.path.join(results_folder, "scenario.csv"), index=False)
    # Save the score of the algorithm
    score = calculate_algorithm_score(scenarioResults)
    logging.info(f"Scenario Score: {score}")
    # Save the score in a file
    score_file = os.path.join(results_folder, "scenario-score.txt")
    with open(score_file, "w") as file:
        file.write(str(score))
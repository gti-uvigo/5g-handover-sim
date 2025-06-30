#!/usr/bin/env python3
# encoding: UTF-8

import os
from datetime import datetime
import argparse
import subprocess
from concurrent.futures import ThreadPoolExecutor
import multiprocessing
import time
import json
import logging
import logging.config
import yaml
from simulator_gti_dqn import simulate_gti_dqn_handover
import matplotlib.pyplot as plt
import tensorflow as tf


from utils import *
from simulator_3gpp import simulate_3gpp_handover
from simulator_sbgh import simulate_sbgh_handover, simulate_ideal_sbgh_handover

import warnings
warnings.filterwarnings("ignore")

results = []
processes_state = {}

parser = argparse.ArgumentParser(description="NS3 simulation parameters")
logging.config.fileConfig('logging.conf')


def build_simulation():
    command = [
        ns3_executable,
        "build",
        ns3_sim_src_main_file,
    ]
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        logging.info(f"Building simulation")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error building simulation")
        exit(-1)
    for line in process.stdout:
        logging.info(line.rstrip())
    


    # wait for the simulation to finish
    process.wait()


import matplotlib.pyplot as plt
import pandas as pd
import os

def plot_rsrp(simDataframes, nUEs, nGnb, traces_sim_folder):
    # Assuming simDataframes is a list of pandas DataFrames where each DataFrame represents the simulation data for a UE
    for j in range(nUEs):
        plt.figure(figsize=(10, 6))
        for i in range(nGnb):
            # Extract RSRP data for this gNB
            rsrp_data = simDataframes[j][i]['Rsrp']
            
            # Plot the RSRP data
            plt.step(rsrp_data.index, rsrp_data, label=f' gNB{i+1}', where='mid')
        
        # Add labels and title
        plt.xlabel('Time (seconds)')
        plt.ylabel('RSRP (index)')
        plt.legend()

        # Adding grid
        plt.grid(True)

        # Save the plot to the specified folder
        results_folder = os.path.join(traces_sim_folder, 'results')
        if not os.path.exists(results_folder):
            os.makedirs(results_folder)
        
        plt.savefig(os.path.join(results_folder, f'rsrp_plot-{j}.png'))
        plt.close()  # Close the figure to avoid memory issues





def plot_throughput(simDataframes, nUEs, nGnb, traces_sim_folder):
    # Assuming simDataframes is a list of pandas DataFrames where each DataFrame represents the simulation data for a gNB
    for j in range(nUEs):
        plt.figure()
        for i in range(nGnb):
            # Extract throughput data for this gNB
            throughput_data = simDataframes[j][i]['Throughput']
            
            # Plot the throughput data
            plt.plot(throughput_data, label=f'gNB {i+1}')
        
        # Add labels and title
        plt.xlabel('Time')
        plt.ylabel('Throughput')
        plt.title('Throughput over Time')
        plt.legend()
        # create the results folder if not exists
        if not os.path.exists(f'{traces_sim_folder}/results'):
            os.makedirs(f'{traces_sim_folder}/results')
        # Save the plot to the specified folder
        plt.savefig(f'{traces_sim_folder}/results/throughput_plot-{j}.png')
    



def run_simulation(index):

    
    selectedGnb = index % nGnb
    ue = index // nGnb
    nodeSeed = seed + ue # Each node has a different seed
    traces_folder = os.path.join(traces_sim_folder,str(ue)+"/"+str(selectedGnb)+"/")
    
    if not os.path.exists(traces_folder):
        try:
            os.makedirs(traces_folder)
            logging.debug(f'Created {traces_folder}')
        except:
            logging.debug(f'Failed to create {traces_folder}')
    else:
        logging.debug(f'{traces_folder} already exists')
    # Creating the command for each simulation
    command = [
        ns3_simulation_exec,
        f"--path={traces_folder}",
        f"--logging={debug}",
        f"--simTime={simTime}",
        f"--gnb={selectedGnb}",
        f"--sc={sc}",
        f"--MaxPackets={max_packets}",
        f"--packetSize={packetSize}",
        f"--bitRate={bitRate}",
        f"--seed={nodeSeed}",
        f"--int={int(interval*1e6)}",
        f"--errorModel={errorModel}",
        f"--tolerance={tolerance}",
        f"--speed={speed}",
        f"--trayectoryTime={trayectoryTime}",
        ]
    if wp is not None:
        print(f"Using waypoints file: {wp}")
        command.append(f"--wp={wp}")

    print(command)
    time.sleep(10)
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        logging.info(f"Started NS3 simulation for gNodeB {selectedGnb}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing the command for gNodeB {selectedGnb}: {e}")
    for line in process.stdout:
        line_str = line.decode("utf-8").rstrip()
        if line_str.startswith("Time"):
            time_index = line_str.index("Time elapsed:") + len("Time elapsed:")
            end_time_index =  line_str.index("Progress:")
            progress_index = line_str.index("Progress:") + len("Progress:")
            time_elapsed = line_str[time_index:end_time_index].strip()
            progress_percentage = line_str[progress_index:-1].strip()
            processes_state[ue][selectedGnb] = {
                "t": time_elapsed,
                "p": progress_percentage
                }


    # wait for the simulation to finish
    process.wait()
    retCode = process.returncode
    if retCode != 0:
        processes_state[ue][selectedGnb] = {
                    "t": time_elapsed,
                    "p": retCode
                    }

    else:
        processes_state[ue][selectedGnb] = {
                    "t": time_elapsed,
                    "p": "100"
                    }





if __name__ == "__main__":


    # Define default values for parameters
    default_simTime = 10  # Default simulation time in seconds
    default_logging = False  # Default logging status
    default_MaxPackets = 0  # Default maximum number of packets
    default_selectedGnb = 0  # Default selected g-nodeB for simulation
    default_timeInterval = 0.1  # Default sample time interval in seconds
    default_randomSeed = 1234  # Default random number generator seed
    default_nUEs = 5  # Default number of UEs in the environment
    default_tolerance = 1  # Default tolerance for the mobility simulation
    default_errorModel = "ns3::NrEesmCcT1"  # Default error model type
    default_Hys = 5  # Default Hysterisis for NR Measurement Event in dBm
    default_NrMeasureInt = 0.1  # Default interval for NR Measurement Event in seconds
    default_packetSize = 1000  # Default packet size in bytes
    default_bitRate = 380e6  # Default bitrate in bits/s
    default_A3Offset = 3  # Default A3 NR Measurement Event offset in dBm
    default_path = "."  # Default path
    default_scFile = "../../handover-simulator/scenario/sc.txt"  # Default scenario definition filename
    default_wpFile = "../../handover-simulator/waypoints/wp.txt"  # Default waypoints filename
    default_timeToTrigger = 0.1  # Default time to trigger for NR Measurement Event in seconds
    default_HOInterval = 0.5  # Default handover interval in seconds
    default_speed = 10.0  # Default speed of the UEs in m/s
    default_trayectoryTime = 5.0  # Default time for the trajectory in seconds
    default_alpha = 5000.0  # Default alpha parameter for the scoring function
    default_beta = 1000.0  # Default beta parameter for the scoring function
    # Definition of the penalty dictionary to simulate the penalty for the handover
    penalty_dict = {}
    penalty_dict["Latency"] = 0.020 

    

    # Add command-line arguments
    parser.add_argument("--logging", type=int, default=default_logging,
                        help="If set to 1, log components will be enabled. (Default: 0)")
    parser.add_argument('--config', type=str, help='Path to a YAML configuration file')
    parser.add_argument("--simTime", type=float, default=default_simTime, help="The simulation time in seconds. If it is 0, the simulation time will be calculated from the waypoints.")
    parser.add_argument('--trace', type=str, help='Path to previous simulation trace. If it is provided the simulator is going to use previous traces to perform the high level simulation.')
    parser.add_argument("--speed", type=float, default=default_speed, help="The speed of the UEs in m/s.")
    parser.add_argument("--trayectoryTime", type=float, default=default_trayectoryTime, help="The time for the trayectory in seconds.")
    parser.add_argument("--MaxPackets", type=int, default=default_MaxPackets, help="The maximum number of packets.")
    parser.add_argument("--packetSize", type=int, default=default_packetSize, help="Packet size in bytes.")
    parser.add_argument("--bitRate", type=int, default=default_bitRate ,help="Bitrate in bits/s.")
    parser.add_argument("--gnb", type=int, default=default_selectedGnb, help="Selected g-nodeB for this simulation")
    parser.add_argument("--seed", type=int, default=default_randomSeed, help="Random number generator seed")
    parser.add_argument("--nUEs", type=int, default=default_nUEs, help="The number of UEs in the environment.")
    parser.add_argument("--int", type=float, default=default_timeInterval, help="The sample time interval in seconds.")
    parser.add_argument("--errorModel", default=default_errorModel,
                        help="Error model type: ns3::NrEesmCcT1, ns3::NrEesmCcT2, ns3::NrEesmIrT1, ns3::NrEesmIrT2, ns3::NrLteMiErrorModel")
    parser.add_argument("--sc", type=str, default=default_scFile, help="Scenario definition filename")
    parser.add_argument("--tolerance", type=float, default=default_tolerance, help="The tolerance for the mobility simulation.")
    parser.add_argument("--Hys",type=float, default=default_Hys, help="Hysterisis for NR Measurement Event in dBm")
    parser.add_argument("--NrMeasureInt",type=float, default=default_NrMeasureInt, help="Interval for NR Measurement Event in seconds")
    parser.add_argument("--A3Offset",type=float, default=default_A3Offset, help="A3 NR Measurement Event offset in dBm")
    parser.add_argument( "--ttt", type=float, default=default_timeToTrigger, help="Time to trigger for NR Measurement Event in seconds")
    parser.add_argument("--HOInterval", type=float, default=default_HOInterval, help="Handover interval in seconds")
    parser.add_argument("--alpha", type=float, default=default_alpha, help="Alpha parameter for the scoring function")
    parser.add_argument("--beta", type=float, default=default_beta, help="Beta parameter for the scoring function")
    parser.add_argument("--wp", type=str,  default=default_wpFile, help="Path to the waypoints file")
    args = parser.parse_args()

    # Load configuration from YAML file if provided
    if args.config:
        with open(args.config, 'r') as file:
            config = yaml.safe_load(file)
            # Update the corresponding variables in the args namespace
            for key, value in config.items():
                if hasattr(args, key):
                    setattr(args, key, value)
        
    # Set the parameters from the command-line arguments   
    debug = args.logging
    simTime = args.simTime
    max_packets = args.MaxPackets
    selectedGnb = args.gnb
    seed = args.seed
    nUEs = args.nUEs
    interval = args.int
    errorModel = args.errorModel
    tolerance = args.tolerance
    Hys = args.Hys
    NrMeasureInt = args.NrMeasureInt
    A3Offset = args.A3Offset
    packetSize = args.packetSize
    bitRate = args.bitRate
    timeToTrigger = args.ttt
    HOInterval = args.HOInterval
    speed = args.speed
    trayectoryTime = args.trayectoryTime
    packetSize = args.packetSize
    alpha = args.alpha
    beta = args.beta
    if args.wp:
        wp = os.path.abspath(args.wp)
    
    # Load the scenario file
    sc = os.path.abspath(args.sc)
    print(f"Scenario file: {sc}")
    scenario = parse_scenario_file(sc)
    
    
    nGnb = len(scenario["gnbs"])
    if not args.trace:
        
        for iUe in range(nUEs):
            processes_state[iUe] = {}
            for ignb in range(nGnb):
                processes_state[iUe][ignb] = {
                    "t": 0,
                    "p": 0
                    }
            
        cpu_threads_count =  multiprocessing.cpu_count()
        output_dir = os.path.dirname(os.path.realpath(__file__))
        directories = output_dir.split(os.sep)
        root_folder_path = os.sep.join(directories[:-2])
        traces_dir = os.path.join(os.sep.join(directories[:-1])+"/", 'traces')
        ns3_dir = os.path.join(root_folder_path+ "/","ns-3-dev/")
        ns3_executable = os.path.join(ns3_dir,"ns3")
        ns3_simulation_dir = os.path.join(ns3_dir,"build/scratch/network-simulator/")
        ns3_simulation_exec = os.path.join(ns3_simulation_dir,"ns3.41-sim-optimized")
        ns3_sim_src_folder = os.path.join("","scratch/network-simulator")
        ns3_sim_src_main_file = os.path.join(ns3_sim_src_folder,"sim.cc") 
        if  debug: 
            print("NS3 Dir: ",ns3_dir)
            print("NS3 Executable: ",ns3_executable)
            print("NS3 Simulation Dir: ",ns3_simulation_dir)
            print("NS3 Simulation Executable: ",ns3_simulation_exec)
            print("NS3 Simulation Src Folder: ",ns3_sim_src_folder)
            print("NS3 Simulation Src Main File: ",ns3_sim_src_main_file) 
        
        if not os.path.exists(traces_dir):
                os.makedirs(traces_dir)
        else:
            print('{} already exists'.format(traces_dir))

        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        traces_sim_folder = os.path.join(traces_dir,current_time)

        if os.path.exists(traces_sim_folder):
            print('{} already exists',traces_sim_folder)
        else:
            try:
                os.makedirs(traces_sim_folder)
            #    print('Created {}'.format(traces_sim_folder))
            except:
                    print('Failed to create {}'.format(traces_sim_folder))
        build_simulation()
        
        executor = ThreadPoolExecutor(max_workers=cpu_threads_count)
        processes = []
                
        # Launching the NS3 simulations threads
        for iUe in range(nUEs):
            for ignb in range(nGnb):
                    process = executor.submit(run_simulation, iUe*nGnb+ignb)
                    processes.append(process)
        while any(not process.done() for process in processes):
            
            print("Number of CPU threads:", cpu_threads_count)
            # Print the simulation parameters
            
            print("Simulation Parameters:")
            # Print scenario dimensions
            scenario_dimensions = scenario['scenario_dimensions']
            print("Scenario Dimensions:")
            print(f"  - Min X: {scenario_dimensions['min_x']}")
            print(f"  - Min Y: {scenario_dimensions['min_y']}")
            print(f"  - Max X: {scenario_dimensions['max_x']}")
            print(f"  - Max Y: {scenario_dimensions['max_y']}")
            bands = scenario['bands']
            for i, band in enumerate(bands, 1):
                print(f"Band {i}:")
                print(f"  - Band ID: {band['Band_ID']}")
                print(f"  - Central Frequency: {format_frequency(band['Central_Frequency_Hz'])}")
                print(f"  - Bandwidth: {format_frequency(band['User_Bandwidth_Hz'])}")
            gnbs = scenario['gnbs']
            print(f"- Logging: {'Enabled' if debug else 'Disabled'}")
            print(f"- Simulation Time: {simTime} seconds")
            print(f"- Number of gNodeBs: {nGnb}")

            
            output = ""
            for ue, ue_info in processes_state.items():
                for gnb, process_info in ue_info.items():
                    if process_info['p'] != "100":
                        output += f"[Node {ue}] Process {gnb}: Time elapsed: {process_info['t']}, Progress: {process_info['p']}%\n"
                    elif process_info is int:
                        output += f"[Node {ue}] Process {gnb}: Error {process_info['p']} \n"
                    else:
                        output += f"[Node {ue}] Process {gnb}: Finished \n"
                        output+="\r"
            print(output)
            time.sleep(2)
            clear_terminal()
        executor.shutdown(wait=True)
        print("NS3 simulations finished")
        parameters = {
            "debug": args.logging,
            "simTime": args.simTime,
            "max_packets": args.MaxPackets,
            "seed": args.seed,
            "nUEs": args.nUEs,
            "interval": args.int,
            "errorModel": args.errorModel,
            "tolerance": args.tolerance,
            "Hys": args.Hys,
            "NrMeasureInt": args.NrMeasureInt,
            "A3Offset": args.A3Offset,
            "packetSize": args.packetSize,
            "bitRate": args.bitRate,
            "timeToTrigger": args.ttt,
            "speed": args.speed,
            "trayectoryTime": args.trayectoryTime,
            
            
        }
        with open(traces_sim_folder+"/"+ PARAMETERS_FILE_NAME, 'w') as jsonfile:
            json.dump(parameters, jsonfile, indent=4)
    else:
        traces_sim_folder = args.trace
        print(f"Trace file provided: {traces_sim_folder}")
        with open(traces_sim_folder+"/"+ PARAMETERS_FILE_NAME, 'r') as jsonfile:
            parameters = json.load(jsonfile)
        simTime = parameters["simTime"]
        interval = parameters["interval"]
        debug = parameters["debug"]
        max_packets = parameters["max_packets"]
        seed = parameters["seed"]
        nUEs = parameters["nUEs"]
        errorModel = parameters["errorModel"]
        tolerance = parameters["tolerance"]
        Hys = parameters["Hys"]
        NrMeasureInt = parameters["NrMeasureInt"]
        A3Offset = parameters["A3Offset"]
        bitRate = parameters["bitRate"]
        speed = parameters["speed"]
        trayectoryTime = parameters["trayectoryTime"]
        packetSize = parameters["packetSize"]
        
        #timeToTrigger = parameters["timeToTrigger"]
    
    
    logging.info(f"Parameters: {parameters}")
    simDataframes = load_dataframes(traces_sim_folder, nUEs, nGnb)
    intervals = simDataframes[0][0]['Time'].unique()
    # Calculate the packets send and received by the UEs in the interval
    # as the traces extracted from the simulation are aggregated
    for user in range(nUEs):
        for gnb in range(nGnb):
            simDataframes[user][gnb]['TxPacketsDiff'] = simDataframes[user][gnb]['TxPackets'].diff()
            simDataframes[user][gnb]['TxBytesDiff'] = simDataframes[user][gnb]['TxBytes'].diff()
            simDataframes[user][gnb]['RxPacketsDiff'] = simDataframes[user][gnb]['RxPackets'].diff()
            simDataframes[user][gnb]['RxBytesDiff'] = simDataframes[user][gnb]['RxBytes'].diff()
            simDataframes[user][gnb]['LostPacketsDiff'] = simDataframes[user][gnb]['LostPackets'].diff()
            # for the first interval the difference is the same as the value, by default .diff() returns NaN
            simDataframes[user][gnb].loc[0, 'TxPacketsDiff'] = simDataframes[user][gnb].loc[0, 'TxPackets']
            simDataframes[user][gnb].loc[0, 'TxBytesDiff'] = simDataframes[user][gnb].loc[0, 'TxBytes']
            simDataframes[user][gnb].loc[0, 'RxPacketsDiff'] = simDataframes[user][gnb].loc[0, 'RxPackets']
            simDataframes[user][gnb].loc[0, 'RxBytesDiff'] = simDataframes[user][gnb].loc[0, 'RxBytes']
            simDataframes[user][gnb].loc[0, 'LostPacketsDiff'] = simDataframes[user][gnb].loc[0, 'LostPackets']
            # calculate the throughput
            simDataframes[user][gnb]['Throughput'] = (simDataframes[user][gnb]['RxBytesDiff'] * 8) / interval
            
    #plot all the throughput for each user
    #plot_throughput(simDataframes, nUEs, nGnb, traces_sim_folder)
    #plot_rsrp(simDataframes, nUEs, nGnb, traces_sim_folder)
    simulate_3gpp_handover(nUEs,debug,traces_sim_folder, nGnb, Hys, A3Offset, NrMeasureInt, interval, DECISION_PARAMETER, timeToTrigger, HOInterval,intervals, simDataframes, scenario, packetSize)
    simulate_sbgh_handover(nUEs,debug,traces_sim_folder, nGnb, interval ,simDataframes ,intervals ,scenario, packetSize, alpha, beta, penalty_dict)
    simulate_ideal_sbgh_handover(nUEs,debug,traces_sim_folder, nGnb, interval ,simDataframes ,intervals ,scenario, packetSize, alpha, beta, penalty_dict)
    simulate_gti_dqn_handover(nUEs,debug,traces_sim_folder, nGnb, interval ,simDataframes ,intervals ,scenario, packetSize,penalty_dict)

#!/usr/bin/env python3
# encoding: UTF-8
import pandas as pd
from utils import *
from occupation import *

def simulate_gnb(gnb, intervals, nUEs, ueResults_df, scenario=None, packetSize=int):
    gnbResults = []
    gnb_band = scenario['gnbs'][gnb]['Band_ID']
    gnb_bw = scenario["bands"][gnb_band]["GNB_Bandwidth_Hz"]
    gnb_capacity = get_datarate(gnb_bw)
    for index, interval in enumerate(intervals):
        interval_data = []
        for ue in range(nUEs):

            ue_data = ueResults_df[ue].iloc[index] if ueResults_df[ue].iloc[index]["GNodeB"] == gnb else None
            if ue_data is not None:
                interval_data.append(ue_data)

        if interval_data:
            connectedUEs = len(interval_data)
            throughput_sum = 0
            latency_sum = 0
            rx_packets_diff_sum = 0
            
            channel_packet_loss = 0

            for data in interval_data:
                throughput_sum += data["Throughput"]
                latency_sum += data["Latency"]*data["Throughput"]
                rx_packets_diff_sum += data["RxPacketsDiff"]
                
            
                channel_packet_loss += data["LostPackets"]
            latency_sum = latency_sum / throughput_sum
            occupation = calculate_occupation(gnb_capacity, throughput_sum)


            channel_delay = latency_sum / connectedUEs
            sim_packet_loss = calculate_lost_packets(occupation, rx_packets_diff_sum)
            total_packet_loss = sim_packet_loss + channel_packet_loss
            interval_data_aggregated = {
                "Time": interval,
                "Throughput": throughput_sum,
                "TxBytesDiff": sum(data["TxBytesDiff"] for data in interval_data),
                "TxPacketsDiff": sum(data["TxPacketsDiff"] for data in interval_data),
                "RxBytesDiff": sum(data["RxBytesDiff"] for data in interval_data),
                "RxPacketsDiff": rx_packets_diff_sum,
                "Latency": latency_sum,
                "Jitter": sum(data["Jitter"] for data in interval_data),
                "LostPackets": total_packet_loss,
                "simLostPackets": sim_packet_loss,
                "ConnectedUEs": connectedUEs,
                "MeanThroughput": throughput_sum / connectedUEs,
                "Occupation": occupation,
                "offeredRate": throughput_sum,
                "GnbCapacity": gnb_capacity,
                "ChannelDelay": channel_delay,
                "ChannelPacketLoss": channel_packet_loss,
                "PLostPackets": calculate_lost_packets(occupation, rx_packets_diff_sum, 0)/rx_packets_diff_sum if rx_packets_diff_sum != 0 else 0,
            }
            interval_data_aggregated = apply_channel_simulation(interval_data_aggregated, occupation, gnb_capacity, packet_length=packetSize)
            gnbResults.append(interval_data_aggregated)
        else:
            gnbResults.append({
                "Time": interval,
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
                "simLostPackets": 0,
                "ConnectedUEs": 0,
                "MeanThroughput": 0,
                "Occupation": 0,
                "SimLatency": 0,
                "PLostPackets": 0,
                "Handovers": 0,
            })
        
    # calculate the accumulated values
    accSimLoss = 0
    for i in range(0, len(gnbResults)):
        gnbResults[i]["RxPacketsAcc"] = sum(data["RxPacketsDiff"] for data in gnbResults[0:i])
        gnbResults[i]["RxBytesAcc"] = sum(data["RxBytesDiff"] for data in gnbResults[0:i])
        gnbResults[i]["TxPacketsAcc"] = sum(data["TxPacketsDiff"] for data in gnbResults[0:i])
        gnbResults[i]["TxBytesAcc"] = sum(data["TxBytesDiff"] for data in gnbResults[0:i])
        
        accSimLoss += gnbResults[i]["simLostPackets"]
        gnbResults[i]["RxPacketsAcc"] = gnbResults[i]["RxPacketsAcc"] - accSimLoss
        gnbResults[i]["RxBytesAcc"] = gnbResults[i]["RxBytesAcc"] - (accSimLoss * packetSize)
        
    return gnbResults



# Takes the results of the gNB and recalculates the metric for the UEs with the occupation model
def simulate_user_restricted(ueResults_df, gnbResults_list, ue, intervals, packetSize):
    # Initialize an empty DataFrame to store results
    results = []

    # Take the data from the UE
    ue_data = ueResults_df[ue]

    # Iterate over the intervals
    for i in range(len(intervals)):
        # Take the UE data for the interval (should be one and only one row)
        ue_interval_data = ue_data.iloc[i]

        # Take the gNB connected to the UE
        gnb =ue_interval_data["GNodeB"]

        # Check if the value is null or NaN
        if pd.isna(gnb) or pd.isnull(gnb):
            ue_interval_data = ue_interval_data.copy()
            ue_interval_data["Latency"] = 0
            ue_interval_data['PLostPackets'] = 0
            ue_interval_data['SimLatency'] = 0

            results.append(ue_interval_data)
            continue

        # Take the gNB data for the interval
        gnb_data =gnbResults_list[int(gnb)]
        gnb_interval_data = gnb_data.iloc[i]

        # Get the occupation
        occupation = gnb_interval_data["Occupation"]

        # Channel simulation for the UE
        ue_ideal_throughput = ue_interval_data["Throughput"]
        ue_interval_data = apply_channel_simulation(ue_interval_data, occupation, ue_ideal_throughput, packetSize)
        
        # Append the modified UE interval data to the results DataFrame
        results.append(ue_interval_data)
    results = pd.DataFrame(results)
    return results

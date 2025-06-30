#!/usr/bin/env python3
# encoding: UTF-8
import math


def calculate_occupation(gnb_capacity=float, gnb_traffic=float):
    """ @Auxiliar function for calculating the occupation of a gNB.

    - gnb_capacity in bps
    - gnb_traffic in bps
    
    returns occupation 
    """

    occupation = gnb_traffic / gnb_capacity
    return occupation



def calculate_system_waiting_time(gnb_capacity, occupation, packet_length):
    """ Auxiliar function for calculating the average waiting time for a packet transmitted through a gNB:
    It uses the M/D/1 queue model considering a constant packet length of "packet_length" bytes.

    - port_capacity in bps
    - occupation 
    - packet_length in bytes
    
    returns average_system_waiting_time in s
    """

    
    serving_rate = gnb_capacity / (packet_length * 8) # In packets per second
    if occupation < 1:
        # A runtime warning is expected here when the ocupation is near 1, but the error is handled
        average_system_waiting_time = 1.0 / serving_rate + (occupation / (2.0 * serving_rate * (1 - occupation)))
    else:
        occupation = 1-1e-5
        average_system_waiting_time = 1.0 / serving_rate + (occupation / (2.0 * serving_rate * (1 - occupation)))

    return average_system_waiting_time

def calculate_latency(average_system_waiting_time=float, channel_delay=float):
    """ Auxiliar function for calculating the mean latency of a packet transmitted through a gNB.
    
    average_system_waiting_time in s
    """

    latency = average_system_waiting_time + channel_delay

    return latency

def calculate_throughput(occupation=float, user_throughput=float):
    """ Auxiliar function for calculating the thoughput of a UE connected to a gNB with a given ocupation.
    
    - occupation
    - user_throughput in bps
    
    returns throughput in bps
    """

    if occupation < 1:
        throughput = user_throughput
    else:
        throughput = user_throughput * (1/occupation)

    return throughput


def calculate_lost_packets(occupation=float, rx_packets_diff=float, channel_packets_lost=0.0):
    """ Auxiliar function for calculating the lost packets of a gNB.
    
    - occupation
    - packet_length in bytes
    - gnb_capacity in bps
    - gnb_traffic in bps
    
    returns lost_packets
    """ 
    if occupation < 1:
        ocupation_lost_packets = 0
    else:
        ocupation_lost_packets = math.ceil(rx_packets_diff * (1-(1/ occupation)))
    # The lost packets due to the channel are added to the lost packets due to the occupation
    return ocupation_lost_packets + channel_packets_lost

def is_gnb_stable(occupation=float):
    """ Auxiliar function for checking if a gNB is stable or not.
    
    - occupation
    
    returns True if the gNB is stable, False otherwise.
    """

    if occupation < 1:
        return True
    else:
        return False
    

def apply_channel_simulation(interval_data=None, occupation=float, gnb_capacity=float, packet_length=int):
    """Auxiliary function for applying the channel delay.

    - interval_data: DataFrame with the data
    - gnb_capacity in bps
    - packet_length in bytes

    returns interval_data with the channel delay applied
    """

    average_system_waiting_time = calculate_system_waiting_time(gnb_capacity, occupation, packet_length)
    channel_delay = interval_data["Latency"]
    latency = calculate_latency(average_system_waiting_time, channel_delay)
    throughput = calculate_throughput(occupation, interval_data["Throughput"])
    rx_packets_diff = interval_data["RxPacketsDiff"]
    rx_bytes_diff = interval_data["RxBytesDiff"]
    lost_packets_channel = interval_data["LostPackets"]

    lost_packets_sim = min(calculate_lost_packets(occupation, rx_packets_diff,0), rx_packets_diff)
    rx_packets_diff -= lost_packets_sim
    rx_bytes_diff -= lost_packets_sim * packet_length
    interval_data = interval_data.copy()

    interval_data["Throughput"] = throughput
    interval_data["Latency"] = latency
    interval_data["RxPacketsDiff"] = rx_packets_diff
    interval_data["RxBytesDiff"] = rx_bytes_diff
    interval_data["LostPackets"] = lost_packets_sim + lost_packets_channel
    interval_data["SimLatency"] = average_system_waiting_time
    interval_data["PLostPackets"] = interval_data["LostPackets"] / (rx_packets_diff + interval_data["LostPackets"]) if rx_packets_diff + interval_data["LostPackets"] != 0 else 0

    return interval_data

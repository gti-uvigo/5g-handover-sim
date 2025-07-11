#!/usr/bin/env python3
# encoding: UTF-8
# This file contains the scoring functions for the handover simulator.
import math
# Constants
BW_MAX = 400.0 * 10**6  # 400 MHz
F_MAX = 74.0 * 10**9  # 74 GHz


def calculate_score(user_data, scenario_data, connected_gnb, alpha,beta):
    """Calculate a score for a possible connection between a given UE and a given cell.
    This is used to evaluate the expected performance of a given connection and to compare different handover strategies.

    Args:
    
        user_data (DataFrame): The user data for the UE, containing the data for the simulation of each connection. Format: the same as the ns-3 csv traces
        
        scenario_data (DataFrame): The scenario data for the cell. Format: scenario_info dictionary as defined in the utils.py file.

    Returns:
    
        float: The score for the connection.
    """

    # from the user data take the connected gNB and the distance
    if connected_gnb is None:
        return 0
    if user_data is None:
        return 0
    if user_data["Rsrp"] is None :
        return 0
    rsrp = float(user_data["Rsrp"])
    gnbs = scenario_data['gnbs']
    bands = scenario_data['bands']
    # take the band id from the connected gNB
    band_id = gnbs[connected_gnb]["Band_ID"]
    # get the bandwidth for the band
    band = next((band for band in bands if band["Band_ID"] == band_id), None)
    user_bandwidth = band["User_Bandwidth_Hz"]
    # get the Central_Frequency for the connected gNB
    central_frequency =band["Central_Frequency_Hz"]
    # get the max distance as x distance and y distance
    # being distance = sqrt(x^2 + y^2)
    # x = max_x - min_x
    # y = max_y - min_y
    x = scenario_data['scenario_dimensions']['max_x'] - scenario_data['scenario_dimensions']['min_x']
    y = scenario_data['scenario_dimensions']['max_y'] - scenario_data['scenario_dimensions']['min_y']
    max_distance = math.sqrt(x**2 + y**2)
    
    # normalize the bandwidth
    bw = user_bandwidth / BW_MAX
    # normalize the frequency
    f = central_frequency / F_MAX
    # power parameter
    min_rsrp = -100
    max_rsrp = -80
    if rsrp > max_rsrp:
        p = 1
    else:
        p =((rsrp - min_rsrp)/(max_rsrp - min_rsrp))

    score = alpha*(bw)*p 

    return score
    
    
def calculate_algorithm_score(gnbs_metrics):
    """
    Calculate the score for the algorithm based on the accumulated data transmitted by the gNBs.

    Parameters:
    gnbs_metrics (DataFrame): A DataFrame containing metrics about the gNBs.

    Returns:
    float: The calculated score.
    """
    # calculate the score as the sum of the last value of the TxBytesAcc column for each gNB
    score = gnbs_metrics['RxBytesAcc'].iloc[-1].sum()
    return score/10**6


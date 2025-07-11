import os
import pandas as pd
import logging

DECISION_PARAMETER = "Rsrp"
PARAMETERS_FILE_NAME ="parameters.json"
RESULTS_FILE_NAME ="results.csv"

MAX_DATARATE_PER_BANDWIDTH_REFERENCE = 98e6 #  aprox 77  Mbps
BANDWIDTH_REFERENCE = 20.0e6 # 20 MHz
SPECTRAL_EFFICIENCY = 4 # bps/Hz
# Max datarate is 75 Mbps, which is 7.5e7 bits per second per each 20 MHz bandwidth block (being almost lineal with the amount of bandwidth)

def clear_terminal():
    """Clear the terminal screen.
    
    Args:
        None
    Returns:
        None
    """
    if os.name == 'nt':  # For Windows
        _ = os.system('cls')
    else:  # For Linux and Mac
        _ = os.system('clear')

# Function to calculate the datarate based on the bandwidth

def get_datarate(bandwidth=float):
    """Calculate the maximum datarate expected from a ns-3/5G-LENA connection with a given bandwidth.
    
    Args:
        bandwidth (float): The bandwidth in Hz.
        
    Returns:
        float: The maximum datarate in bits per second.
    """
    return SPECTRAL_EFFICIENCY * bandwidth

def apply_penalty(connected_gnb, penalty_dict, time, interval):

    if connected_gnb is not None and penalty_dict is not None:
            for key in penalty_dict:
                if key in connected_gnb:
                    if time > interval:
                        penalty_value = penalty_dict[key]
                    else:
                        penalty_value = penalty_dict[key] * (time / interval)
                        
                    connected_gnb.loc[:, key] += penalty_value

    return connected_gnb


def get_gnb_data(gnb_id,dataframes, index):
    """Get the data of a gNB for a given interval.

    Args:
        gnb_id (int): The ID of the gNB.
        dataframes (list): A list of lists of dataframes containing the simulation data.
        index (float): index of the interval to be analyzed.

    Returns:
        DataFrame: The data of the gNB for the given interval.
    """
    return  dataframes[gnb_id].iloc[index]



def parse_scenario_file(filename):
    """Parse the scenario file and return the scenario information.

    Args:
        filename (str): The name of the scenario file.

    Returns:
        dict (scenario_info): A dictionary containing the scenario information.
        
        
        The scenario_info dictionary has the following structure:
            
            {
                'scenario_dimensions': {
                    'min_x': float,
                    'min_y': float,
                    'max_x': float,
                    'max_y': float
                },
                'bands': [
                    {
                        'Band_ID': int,
                        'Central_Frequency_Hz': float,
                        'User_Bandwidth_Hz': float,
                        'GNB_Bandwidth_Hz': float
                    },
                    ...
                ],
                'gnbs': [
                    {
                        'GNB_ID': int,
                        'Position_X': float,
                        'Position_Y': float,
                        'Position_Z': float,
                        'Band_ID': int,
                        'Transmission_Power_dBm': float,
                        'Type': str
                    },
                    ...
                ]
            }
    """
    
    
    scenario_info = {
        'scenario_dimensions': {},
        'bands': [],
        'gnbs': []
    }

    with open(filename, 'r') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith('#'):
                # Skip empty lines and comments
                continue
            elif line.startswith('!'):
                # Parse scenario dimensions
                dimensions = line[1:].split(" ")  # Skip the first element, it's a comment
                scenario_info['scenario_dimensions']['min_x'] = float(dimensions[0])
                scenario_info['scenario_dimensions']['max_x'] = float(dimensions[1])
                scenario_info['scenario_dimensions']['min_y'] = float(dimensions[2])
                scenario_info['scenario_dimensions']['max_y'] = float(dimensions[3])
            elif line.startswith('*'):
                # Parse band data
                band_info = line[1:].split()
                band_id, central_frequency, user_bw, gnb_bw = map(float, band_info)
                scenario_info['bands'].append({
                    'Band_ID': int(band_id),
                    'Central_Frequency_Hz': central_frequency,
                    'User_Bandwidth_Hz': user_bw,
                    'GNB_Bandwidth_Hz': gnb_bw
                })
            else:
                # Parse gNodeB data
                gnb_info = line.split()
                gnb_id, position_x, position_y, position_z, band_id, transmission_power, gnb_type = gnb_info
                scenario_info['gnbs'].append({
                    'GNB_ID': int(gnb_id),
                    'Position_X': position_x,
                    'Position_Y': position_y,
                    'Position_Z': position_z,
                    'Band_ID': int(band_id),
                    'Transmission_Power_dBm': transmission_power,
                    'Type': gnb_type
                })

    return scenario_info

def format_frequency(frequency):
    """Format a frequency in Hz, kHz, MHz or GHz.
    Args:
        frequency (int, float): The frequency to be formatted.

    Returns:
        str: The formatted frequency.
    """
    if isinstance(frequency, (int, float)):
        if frequency < 1e3:
            return f"{frequency:.2f} Hz"
        elif frequency < 1e6:
            return f"{frequency/1e3:.2f} kHz"
        elif frequency < 1e9:
            return f"{frequency/1e6:.2f} MHz"
        else:
            return f"{frequency/1e9:.2f} GHz"
    else:
        return "Invalid input. Please provide a numeric value."

def load_dataframes(traces_sim_folder, nUEs, nGnb):
    """
    Load the dataframes from the traces_sim_folder.
    Args:
    
        traces_sim_folder (str): The folder where the traces are stored.
        nUEs (int): The number of UEs.
        nGnb (int): The number of gNBs.

    Raises:
        FileNotFoundError: If the file is not found.

    Returns:
        list: A list of lists of dataframes.
    """
    dataframes = []
    for iUE in range(nUEs):
        node_dataframes = []
        for iGnb in range(nGnb):
            file_name = os.path.join(traces_sim_folder, str(iUE), str(iGnb), "traces.csv")
            if os.path.isfile(file_name):
                df = pd.read_csv(file_name)
                node_dataframes.append(df)
            else:
                raise FileNotFoundError(f"File {file_name} not found.")
        dataframes.append(node_dataframes)
    return dataframes
            


def debug_dataframes(dataframes):
    for index, df in enumerate(dataframes):
        logging.debug(f"Data from File {index + 1}:")
        logging.debug(df.head())



def print_progress(iteration=int, total=int, prefix='', suffix='', decimals=1, length=100, fill='█'):
    """
    Call in a loop to create terminal progress bar
    
    Args:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    bar = fill * filled_length + '-' * (length - filled_length)
    print('\r%s |%s| (%s/%s) %s%% %s' % (prefix, bar, iteration, total ,percent, suffix), end = '\r')
    if iteration == total: 
        print()

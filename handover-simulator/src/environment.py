from utils import *
from simulator_common import apply_channel_simulation
import numpy as np


NO_SATURATION = 1 # No saturation oc = 0
MILD_SATURATION = 2 #  0 < oc < 1- user throughput => 1- oc < user throughput
HIGH_SATURATION = 3 # 1- user throughput < oc < 1
EXTREME_SATURATION = 4 # oc = 1

SPECTRAL_EFFICIENCY = 4 # bps/Hz
class Environment:
# class Environment for the ddqn based handover simulator agent
# This class is used to serve as the environment abstraction for the DQN agent to interact with

    

    def __init__(self, dataframe, intervals, scenario, nUes, interval_duration, packet_size, simulatedSaturation=False, penalty_dict=None, penalty_time=0.1):
        """
        Initialize the Environment object.

        Args:
            dataframe (DataFrame): The input dataframe.
            intervals (list): List of intervals.
            scenario (dict): The scenario configuration.
            nUes (int): Number of UEs.
            interval_duration (int): Duration of each interval.

        Attributes:
            dataframe (DataFrame): The input dataframe.
            intervals (list): List of intervals.
            scenario (dict): The scenario configuration.
            interval_duration (int): Duration of each interval.
            current_interval (int): Current interval.
            timer (int): Timer.
            nUes (int): Number of UEs.
            ue_actions (list): List of UE actions.
            gnb_occupation (list): List of gNB occupation.

        """
        self.dataframe = dataframe
        self.intervals = intervals
        self.scenario = scenario
        self.consolidate_directly = False
        self.interval_duration = interval_duration
        self.current_interval = 0
        self.timer = 0
        self.saturationClock = 30
        self.saturationCounter = 0
        self.nUes = nUes
        self.ue_actions = [-1] * nUes  # -1 means that the UE is not connected to any gNB
        self.connections = [-1] * nUes
        self.gnb_occupation = [0] * len(scenario["gnbs"])
        self.gnb_occupation_agg = [0] * len(scenario["gnbs"])
        self.saturationLevel = [NO_SATURATION] * len(scenario["gnbs"])
        self.packetSize = packet_size
        self.simulatedSaturation = simulatedSaturation
        self.traces = []
        self.handover_timer = [0] * nUes
        self.isRecordingTraces = False
        self.penalty_dict = penalty_dict
        self.penalty_time = penalty_time
    def calculate_datarate_occupation(self, i):
        aggregated_datarate = 0
        for ue in range(len(self.connections)):
            if self.connections[ue] == i:
                df = get_gnb_data(i,self.dataframe[ue],self.current_interval)
                thr = df["Throughput"]
                aggregated_datarate += df["Throughput"]
        gnb_datarate = next((band["GNB_Bandwidth_Hz"] for band in self.scenario["bands"] if band["Band_ID"] == self.scenario["gnbs"][i]["Band_ID"]), None) * SPECTRAL_EFFICIENCY
        if gnb_datarate is not None:
            return aggregated_datarate / gnb_datarate
        else:
            return 0
        
        
        
        
    def calculate_bandwidth_occupation(self, i):
        # take the number of UEs connected to the gNB i
        connected_users = self.ue_actions.count(i)
        # used bandwidth is the number of UEs connected to the gNB i times the user bandwidth
        used_bandwidth = connected_users * next((band["User_Bandwidth_Hz"] for band in self.scenario["bands"] if band["Band_ID"] == self.scenario["gnbs"][i]["Band_ID"]), None)
        # the occupation is the used bandwidth divided by the gNB bandwidth
        return used_bandwidth / next((band["GNB_Bandwidth_Hz"] for band in self.scenario["bands"] if band["Band_ID"] == self.scenario["gnbs"][i]["Band_ID"]), None)
    
    def calculate_bandwidth_occupation_consolidated(self, i):
        # take the number of UEs connected to the gNB i
        connected_users = self.connections.count(i)
        # used bandwidth is the number of UEs connected to the gNB i times the user bandwidth
        used_bandwidth = connected_users * next((band["User_Bandwidth_Hz"] for band in self.scenario["bands"] if band["Band_ID"] == self.scenario["gnbs"][i]["Band_ID"]), None)
        # the occupation is the used bandwidth divided by the gNB bandwidth
        return used_bandwidth / next((band["GNB_Bandwidth_Hz"] for band in self.scenario["bands"] if band["Band_ID"] == self.scenario["gnbs"][i]["Band_ID"]), None)
        
    def __get_ue_dataframe(self, ue_id, interval=-1):
        """
        Get the dataframe for a specific UE.

        Args:
            ue_id (int): The ID of the UE.

        Returns:
            pandas.DataFrame: The dataframe containing the UE data.

        """
        if interval == -1:
            interval = self.current_interval
            
        gnb_id = self.ue_actions[ue_id]
        if gnb_id == -1:
            # if the UE is not connected to any gNB
            # take gNB 0 as the default gNB and return the data with the data transmitted set 0
            df = get_gnb_data(0,self.dataframe[ue_id],interval)
            df = df.copy()
            df["TxBytes"] = 0
            df["TxPackets"] = 0
            df["RxBytes"] = 0
            df["RxPackets"] = 0
            df["Distance"] = None
            df["LatencySum"] = 0
            df["LatencyLast"] = 0
            df["JitterSum"] = 0
            df["LostPackets"] = 0
            df["Rsrp"] = float("-inf")
            df["TxPacketsDiff"] = 0
            df["TxBytesDiff"] = 0
            df["RxPacketsDiff"] = 0
            df["RxBytesDiff"] = 0
            df["LostPacketsDiff"] = 0
            df["Throughput"] = 0
            return df
            
        else:
            df = get_gnb_data(gnb_id,self.dataframe[ue_id],self.current_interval)
            
        df = df.rename({"LatencySum": "Latency"})
        df = df.rename({"RxPackets": "RxPacketsAcc"})
        df = df.rename({"RxBytes": "RxBytesAcc"})
        df = df.rename({"TxPackets": "TxPacketsAcc"})
        df = df.rename({"TxBytes": "TxBytesAcc"})
        return df
    
    def __get_rsrp(self,ue_id):
        """ Returns the RSRP for all the gNBs in the scenario for a specific UE.
        Args:
            ue_id (int): The ID of the UE.
        Returns:
            list: The RSRP for all the gNBs in the scenario.
        """
        rsrp_list = []
        for i in range(len(self.scenario["gnbs"])):
            df = get_gnb_data(i,self.dataframe[ue_id],self.current_interval)
            rsrp = df["Rsrp"]
            if rsrp == None:
                rsrp = float("-inf")
            rsrp_list.append(rsrp)
        return rsrp_list
        
            
        
    def get_current_interval(self):
        """
        Returns the current interval and its corresponding value from the intervals list.

        Returns:
            tuple: A tuple containing the current interval and its corresponding value.
        """
        return self.current_interval, self.intervals[self.current_interval]
            
    def get_observation(self, ue_id):
        """
        Get the observation data for a specific UE (User Equipment).

        Args:
            ue_id (int): The ID of the UE.

        Returns:
            pandas.DataFrame: The observation data for the UE, including gNB information.
        """
        observation_list = self.__get_rsrp(ue_id)
        # discretize the RSRP values
        # 0 if RSRP < -60 dBm, 1 if -60 < RSRP < -80, 2 if -80 < RSRP < -100, 3 if -100 < RSRP < -120, 4 if RSRP > -120
        for i in range(len(observation_list)):
            if observation_list[i] < -60:
                observation_list[i] = 0
            elif observation_list[i] < -80:
                observation_list[i] = 1
            elif observation_list[i] < -100:
                observation_list[i] = 2
            elif observation_list[i] < -120:
                observation_list[i] = 3
            else:
                observation_list[i] = 4
        observation_list.append(self.connections[ue_id])
        # add the gNB occupation to the observation
        # observation_list.extend(self.gnb_occupation)
        # 0 if the gNB is not occupied, 1 if 0,5< occupation < 1, 2 if 0.5 < occ < 0.75 , 3 if 0.75 < occ < 1 , 4 if occ > 1
        for i in range(len(self.gnb_occupation)):
            if self.gnb_occupation[i] == 0:
                observation_list.append(0)
            elif self.gnb_occupation[i] < 0.5:
                observation_list.append(1)
            elif self.gnb_occupation[i] < 0.75:
                observation_list.append(2)
            elif self.gnb_occupation[i] < 1:
                observation_list.append(3)
            else:
                observation_list.append(4)

        
        observation = np.array(observation_list).astype(np.float32)
        return observation
        

        
    
    def set_action(self, ue_id, action):
        """
        Set the action for a specific UE.

        Args:
            ue_id (int): The ID of the UE.
            action (str): The action to be set.

        Returns:
            None
        """
        self.ue_actions[ue_id] = action

    def step(self):
        """
        Perform a step in the simulation environment.

        This method updates the occupation of the gNBs based on the number of UEs connected to each gNB.
        It calculates the used bandwidth for each gNB and updates the gNB occupation accordingly.
        It also updates the timer and the current interval.

        Returns:
            None
        """
        # take action for each UE and consolidate the actions if the occupation is less than 1, if not maintain the previous action
        for i in range(len(self.ue_actions)):
            if self.ue_actions[i] != -1:
                ue_datarate = get_gnb_data(self.ue_actions[i],self.dataframe[i],self.current_interval)["Throughput"]
                gnb_datarate = next((band["GNB_Bandwidth_Hz"] for band in self.scenario["bands"] if band["Band_ID"] == self.scenario["gnbs"][self.ue_actions[i]]["Band_ID"]), None) *SPECTRAL_EFFICIENCY
                oc_contrib = ue_datarate / gnb_datarate
                occupation = self.calculate_datarate_occupation(self.ue_actions[i])
                if self.consolidate_directly or occupation < 0.99 - oc_contrib:
                    self.connections[i] = self.ue_actions[i]
        # update the occupation of the gNBs
        for i in range(len(self.gnb_occupation)):
            self.gnb_occupation[i] = self.calculate_datarate_occupation(i)

            
                # add the level of external saturation to the gNB occupation
        print(f"Interval: {self.current_interval} {self.timer} {self.connections} {self.gnb_occupation}, {self.saturationLevel}, {self.saturationCounter}")
        self.saturationCounter += 1
        # update the timer
        self.timer += self.interval_duration
        if self.isRecordingTraces:
            self.get_internal_actions()

        # update the current interval
        self.current_interval +=1
        if self.isRecordingTraces and self.is_done():
            self.get_internal_actions()


    def reset(self):
        """
        Resets the environment to its initial state.
        """
        self.current_interval = 0 
        self.timer = 0
        self.ue_actions = [-1] * self.nUes
        self.connections = [-1] * self.nUes
        self.gnb_occupation = [0] * len(self.scenario["gnbs"])
    
    def is_done(self):
        """
        Check if the simulation is done.

        Returns:
            bool: True if the current interval is the last interval, False otherwise.
        """
        return self.current_interval >= len(self.intervals) -1
    
    def get_reward(self, ue_id):
        """
        Get the reward for a specific UE.
        

        Args:
            ue_id (int): The ID of the UE.

        Returns:
            float: The reward for the UE.
        """
        if not self.consolidate_directly and self.ue_actions[ue_id] != self.connections[ue_id]:
            return -1
        # get the dataframe for the UE
        df = self.__get_ue_dataframe(ue_id)
        # calculate the reward
        gnb = self.connections[ue_id]
        if gnb == -1:
            return -1
        occupation = self.gnb_occupation[gnb]
        
    
        if not self.consolidate_directly and occupation >= 1:
            return -1
        else:
            throughput = df["Throughput"]
            reward = throughput / 3.85e8
            if occupation > 1:
                degradation = (1 - (1/occupation))
                reward =reward*(1-(degradation))
                
            return reward
    
    
    def get_internal_actions(self):
        if self.isRecordingTraces:
            self.actions.append(self.connections.copy())
            
    def start_trace_recording(self):
        self.traces = []
        self.actions = []
        for i in range(self.nUes):
            self.traces.append([])
        self.isRecordingTraces = True
    
    
    def get_traces(self):
        i = 0        
        for a in self.actions:
            for ue in range(len(a)):
                trace = get_gnb_data(a[ue],self.dataframe[ue],i)
                trace = trace.copy()
                previous_actions = self.actions[i-1] if i > 0 else None
                # adapt the trace to the format of the traces
                trace["GNodeB"] =a[ue]
                # rename the LatencySum column to Latency
                trace = trace.rename({"LatencySum": "Latency"})
                # rename the JitterSum column to Jitter
                trace = trace.rename({"JitterSum": "Jitter"})
                # remove RX packets and RX bytes,TX packets and TX bytes
                if "RxPackets" in trace.index:
                    trace = trace.drop(["RxPackets"])
                if "RxBytes" in trace.index:
                    trace = trace.drop(["RxBytes"])
                if "TxPackets" in trace.index:
                    trace = trace.drop(["TxPackets"])
                if "TxBytes" in trace.index:
                    trace = trace.drop(["TxBytes"])
                if "LatencyLast" in trace.index:
                    trace = trace.drop(["LatencyLast"])
                if "LostPackets" in trace.index:
                    trace = trace.drop(["LostPackets"])
                # Rename the columns to the format of the traces
                # lostPacketsDiff  to LostPackets
                trace = trace.rename({"LostPacketsDiff": "LostPackets"})
                # add the  RX packets and RX bytes,TX packets and TX bytes Acc based on previous values + diff
                previous_trace = self.traces[ue][-1] if len(self.traces[ue]) > 0 else None
                if previous_trace is not None:
                    trace["RxPacketsAcc"] = previous_trace["RxPacketsAcc"] + trace["RxPacketsDiff"]
                    trace["RxBytesAcc"] = previous_trace["RxBytesAcc"] + trace["RxBytesDiff"]
                    trace["TxPacketsAcc"] = previous_trace["TxPacketsAcc"] + trace["TxPacketsDiff"]
                    trace["TxBytesAcc"] = previous_trace["TxBytesAcc"] + trace["TxBytesDiff"]
                    previous_handover = previous_trace["Handovers"]
                else:
                    trace["RxPacketsAcc"] = trace["RxPacketsDiff"]
                    trace["RxBytesAcc"] = trace["RxBytesDiff"]
                    trace["TxPacketsAcc"] = trace["TxPacketsDiff"]
                    trace["TxBytesAcc"] = trace["TxBytesDiff"]
                    previous_handover = 0
                if previous_actions is not None:
                    previous_action = previous_actions[ue]
                    if previous_action != a[ue]:
                        trace["Handovers"] = previous_handover + 1
                        self.handover_timer[ue] = self.penalty_time
                    else:
                        trace["Handovers"] = previous_handover
                else:
                    trace["Handovers"] = previous_handover
                if self.handover_timer[ue] > 0:
                    penalty_dict = {}
                    penalty_dict["Latency"] = 0.020
                    
                    if self.handover_timer[ue] >= self.interval_duration:
                        # apply the penalty
                        for key in self.penalty_dict:
                            trace[key] += penalty_dict[key]
                    else:
                        for key in self.penalty_dict:
                            trace[key] += penalty_dict[key] * (self.handover_timer[ue] / self.interval_duration)
                    self.handover_timer[ue] -= self.interval_duration


                self.traces[ue].append(trace)
                
            
            i += 1
        for ue in range(len(self.connections)):
            self.traces[ue] = pd.DataFrame(self.traces[ue])
            # add GNodeB column
        return self.traces

    
    def stop_trace_recording(self):
        self.isRecordingTraces = False
    


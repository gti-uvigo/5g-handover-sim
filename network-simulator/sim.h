#ifndef SIM_H
#define SIM_H

#include <cstdint>
#include <ns3/vector.h>
#include <string>
#include "ns3/core-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/flow-monitor.h"
#include "ns3/network-module.h"
#include <vector>

// Define constants for bandwidth reference and bitrate saturate reference
#define SIM_BANDWIDTH_REFERENCE 20e6 //Bandwidth reference for saturate channel
#define SIM_BITRATE_STATURATE_REFERENCE 75e6 // Bandwidth for saturate the reference channel

using namespace ns3;
/**
 * @brief Logs the progress of the simulation.
 *
 * callback function to log the progress of the simulation.
 *
 * @param simtime The total simulation time.
 */
void LogProgress(double simtime);

struct SimulationOutput{
    double currentTime; // current time
    uint64_t rxBytes; // received bytes
    uint64_t rxPackets; // received packets
    double latencySum; // sum of latencies
    double jitterSum; // sum of jitters
    double latencyLast; // last latency
    uint32_t lostPackets; // lost packets
    double distance; // distance
    double rsrp; // Reference Signal Received Power
};


// Waypoint structure in SI (System International) units
struct WaypointStruct {
    int id;
    double x;
    double y;
    double z;
};
//
struct SpawnPoint {
    int id;
};

struct LegalPath {
    int from;
    int to;
    std::vector<int> path;
};

struct SpeedInterval {
    double minSpeed;
    double maxSpeed;
};

//Movement structure, vector of waypoints, spawnpoints, legal movements and speed intervals
struct Movement {
    std::vector<WaypointStruct> waypoints;
    std::vector<SpawnPoint> spawnPoints;
    std::vector<LegalPath> legalPaths;
    SpeedInterval speedInterval;
};


// Flow statistics parameters
struct FlowStatsParams {
    ns3::Ptr<ns3::Ipv4FlowClassifier> classifier; // flow classifier
    double interval; // interval
    double simTime; // simulation time
    ns3::NodeContainer ueNodes; // UE nodes
    ns3::NodeContainer gnbNodes; // gNB nodes
    int selectedGnb; // selected gNB
    int id; // id
    ns3::NetDeviceContainer ueNetDev; // UE network devices
    ns3::NetDeviceContainer gnbNetDev; // gNB network devices
    double tolerance; // tolerance
    std::ofstream *file; // file
    std::vector<WaypointStruct> wp; // Waypoints for the UE
    Movement movement;
    bool isWaypointBasedMobility;
    int lastWaypointIndex;
};

// Scenario limits (in meters)
struct scenarioLimits{
    double MaxX;
    double MinX;
    double MaxY;
    double MinY;
};


// gNB information structure
struct gnbStruct{
    int id; // id
  // position
    double x;
    double y;
    double z;
    int bandID; // band associated to the gNB
    double txPower;  // Transmission power in dBm
    char gnbType; // gNB type
};

// Band information structure
struct Band {
    int bandID;
    double centralFrequency;
    double userBandwidth;
    double gnbBandwidth;
};
// Simulation parameters structure, used to store the parameters of the simulation and pass them to the simulation function
struct SimulationParameters
{
    std::string scenario;   // scenario
    scenarioLimits limits;  // scenario limits
    double frequency;       // central frequency
    double bandwidth;       // bandwidth
    double simTime;         // simulation time in seconds
    double speed;           // speed
    double trayectoryTime;  // trayectory time
    bool logging;           // whether to enable logging
    std::vector<gnbStruct> gnbs; // gNBs
    std::vector<Band> bands; // bands
    std::string errorModel; // error model
    int packetSize; // packet size
    int bitRate; // bit rate
    int nGnb;               // total number of gNBs
    int selectedGnb;        // selected gNB
    int randomSeed;         // seed for the random number generator
    int nUEs;               // number of UEs in the environment
    double tolerance;       // tolerance for the movility simulation
    bool fullBuffer;        // whether to enable full buffer
    bool useFixedMcs;       // whether to use fixed MCS
    int fixedMcs;           // fixed MCS
    uint64_t timeInterval;  // time interval in microseconds
    uint64_t MaxPackets;    // maximum number of packets to be transmitted
    ns3::Vector initialPos; // initial position
    Movement movement; // Waypoints for the UE
    std::vector<WaypointStruct> wp; // Waypoints for the UE
    bool isWaypointBasedMobility; // Mobility based on waypoints
    int lastWaypointIndex; // Last waypoint index
};

/**
 * @brief Closes an open ofstream object.
 *
 * This function checks if the provided ofstream object is open.
 * If it is, the function closes it.
 *
 * @param file A pointer to the ofstream object to close.
 */
void close_file(std::ofstream *file);


/**
 * @brief Measures and logs the flow statistics of a simulation.
 *
 * This function measures various flow statistics of a simulation, including transmitted and received bytes and packets,
 * latency, jitter, lost packets, and more. It also calculates the distance between the UE and the gNB and the RSRP.
 * The function logs these statistics to a file at regular intervals throughout the simulation.
 * The function also schedules itself to be called again after a certain amount of time, effectively creating a loop
 * that measures and logs the flow statistics at regular intervals.
 *
 * @param monitor A pointer to the FlowMonitor object used to measure the flow statistics.
 * @param params A FlowStatsParams object containing various parameters needed for the function, including the classifier,
 * the interval at which to log the statistics, the total simulation time, the UE and gNB nodes, the UE network device,
 * the ID of the gNB node, and the file to log the statistics to.( FlowStatsParams structure is defined in the sim.h , this file)
 */
void MeasureFlowStats(Ptr<FlowMonitor> monitor, FlowStatsParams params);

/**
 * @brief Logs the progress of the simulation.
 *
 * This function calculates the current time and the progress percentage of the simulation.
 * It then logs these values to the console.
 * The function also schedules itself to be called again after a certain amount of time,
 * so that it can continue to log the progress of the simulation.
 *
 * @param simtime The total simulation time.
 */
void LogProgress(double simtime);

/**
 * @brief Reads a scenario from a file and populates the provided data structures.
 * - Lines starting with '#' or empty lines are ignored.
 * - Lines starting with '!' contain dimension information.
 * - Lines starting with '*' contain band information.
 * - All other lines contain gnbStruct information.
 * After reading the file, the function prints out the band information and closes the file.
 *
 * @param filename The name of the file to read from.
 * @param gnbs A pointer to a vector of gnbStructs to populate with the gnbStruct information from the file.
 * @param dimensions A pointer to a scenarioLimits structure to populate with the dimension information from the file.
 * @param bands A pointer to a vector of Bands to populate with the band information from the file.
 */

void readScenario(std::string filename, std::vector<gnbStruct> *gnbs,
                  scenarioLimits *dimensions, std::vector<Band> *bands);


/**
 * Launches the NS3 simulation for each gNB.
 *
 * @param params The simulation parameters.
 * @return Returns an integer indicating the simulation status.
 */
int simulate_process(SimulationParameters params);



/**
 * @brief Finds the path between two nodes in a Movement struct.
 * @param movement A pointer to a Movement struct.
 * @param sourceId The ID of the source node.
 * @param targetId The ID of the target node.
 * @return Void.
 */
std::vector<int> find_mov_path(Movement* movement, int sourceId, int targetId);

/**
 * Main function of the simulation.
 *
 * @param argc   The number of command-line arguments.
 * @param argv   An array of command-line arguments.
 * @return Returns an integer indicating the simulation status.
 */
int main(int argc, char *argv[]);


#endif // SIM_H

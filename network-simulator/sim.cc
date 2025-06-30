/* -*-  Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */

// Based on the example cttc-3gpp-channel-example from 5G LENA

#include "sim.h"

#include "ns3/applications-module.h"
#include "ns3/channel-condition-model.h"
#include "ns3/config-store.h"
#include "ns3/core-module.h"
#include "ns3/flow-monitor-helper.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/flow-monitor.h"
#include "ns3/internet-module.h"
#include "ns3/ipv4-global-routing-helper.h"
#include "ns3/log.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"
#include "ns3/nr-helper.h"
#include "ns3/nr-mac-scheduler-tdma-rr.h"
#include "ns3/nr-module.h"
#include "ns3/nr-point-to-point-epc-helper.h"
#include "ns3/point-to-point-helper.h"
#include <ns3/antenna-module.h>
#include <ns3/buildings-helper.h>
#include <ns3/mobility-helper.h>
#include <ns3/object-factory.h>
#include <ns3/position-allocator.h>
#include <ns3/ptr.h>
#include <ns3/spectrum-analyzer.h>
#include <ns3/vector.h>
#include <ns3/waypoint.h>

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <dirent.h>
#include <iostream>
#include <ostream>
#include <random>
#include <sstream>
#include <string>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

using namespace ns3;

#define FILE_NAME "traces.csv"

std::vector<SimulationOutput> output;

/**
 * @brief Create a file object, open it and write the CSV header.
 *
 * @param file
 * @param file_name
 */
void
create_file(std::ofstream* file, std::string file_name)
{
    file->open(file_name.c_str());
    if (file->is_open())
    {
        *file << "Time,TxBytes,TxPackets,RxBytes,RxPackets,LatencySum,LatencyLast,JitterSum,"
                 "LostPackets,Distance,Rsrp,UE Position,System Time\n";
    }
}

/**
 * @brief Closes an open ofstream object.
 *
 * This function checks if the provided ofstream object is open.
 * If it is, the function closes it.
 *
 * @param file A pointer to the ofstream object to close.
 */
void
close_file(std::ofstream* file)
{
    if (file->is_open())
    {
        file->close();
    }
}

Vector
normalize(Vector input)
{
    Vector output;
    double magnitude = input.GetLength();
    output.x = input.x / magnitude;
    output.y = input.y / magnitude;
    output.z = input.z / magnitude;
    return output;
}


/**
 * @brief Finds the path between two nodes in a Movement struct.
 * @param movement A pointer to a Movement struct.
 * @param sourceId The ID of the source node.
 * @param targetId The ID of the target node.
 * @return Void.
 */
std::vector<int> find_mov_path(Movement* movement, int sourceId, int targetId)
{
    std::vector<int> path;
    for (auto legalPath : movement->legalPaths)
    {
        std::cout << "From: " << legalPath.from << " To: " << legalPath.to << std::endl;
        if (legalPath.from == sourceId && legalPath.to == targetId)
        {
            std::cout << "Path found" << std::endl;
            for (auto node : legalPath.path)
            {
                std::cout << node << " ";
            }
            path = legalPath.path;
            break;
        }

    }
    std::cout << "Path: " << path.size() << std::endl;
    return path;
}

void
update_mov_directions(std::vector<WaypointStruct>& waypoints,
                      Movement* movement,
                      Ptr<Node> ueNode,
                      double tolerance,
                      int* lastWaypointIndex)
{
    Ptr<ConstantVelocityMobilityModel> mobility =
        ueNode->GetObject<ConstantVelocityMobilityModel>();
    Vector currentPosition = mobility->GetPosition();
    std::cout << "Current position: " << currentPosition << std::endl;
    if (waypoints.empty())
    {
        // generate a new path to follow
        int sourceId = *lastWaypointIndex;

        // take the spawn points
        std::vector<SpawnPoint> spawnPoints = movement->spawnPoints;
        // remove the current position from the candidates
        for (uint i = 0; i < spawnPoints.size(); i++)
        {
            if (spawnPoints[i].id == sourceId)
            {
                spawnPoints.erase(spawnPoints.begin() + i);
                break;
            }
        }
        // select a random target
        int targetIndex = rand() % spawnPoints.size();
        if (spawnPoints[targetIndex].id == sourceId)
        {
            targetIndex = (targetIndex + 1) % spawnPoints.size();
        }
        int targetId = spawnPoints[targetIndex].id;
        std::cout << "Source: " << sourceId << " Target: " << targetId << std::endl;
        std::vector<int> path = find_mov_path(movement, sourceId, targetId);
        std::cout << "test: ";
        // take the waypoints from the path and add them to the waypoints vector
        for (uint i = 0; i < path.size(); i++)
        {
            WaypointStruct wp = movement->waypoints[path[i]];
            waypoints.push_back(wp);
            std::cout << wp.x << " " << wp.y << " " << wp.z << std::endl;
        }
    }

    WaypointStruct nextWp = waypoints[0];
    Vector nextWpPosition(nextWp.x, nextWp.y, nextWp.z);
    Vector directionVector = nextWpPosition - currentPosition;
    double distance = directionVector.GetLength();
    directionVector = normalize(directionVector);
    std::cout << "Distance: " << distance << std::endl;
    double speed = movement->speedInterval.minSpeed + (movement->speedInterval.maxSpeed - movement->speedInterval.minSpeed) * rand() / RAND_MAX;
    if (distance <= tolerance)
    {
        *lastWaypointIndex = waypoints[0].id;
        waypoints.erase(waypoints.begin());
    }
    directionVector.x = directionVector.x * speed;
    directionVector.y = directionVector.y * speed;
    directionVector.z = directionVector.z * speed;
    mobility->SetVelocity(directionVector);
}

/**
 * Loads waypoints from the definition file to in-memory struct.
 *
 * @param filename The name of the file to read from.
 * @param movement A pointer to a Movement struct to
 * @return Void.
 */
void
readWaypoints(std::string filename, Movement* movement )
{
    std::ifstream file(filename);
    std::cout << "Reading " << filename << "..." << std::endl;
    if (!file.is_open())
    {
        printf("Error reading the file");
        exit(EXIT_FAILURE);
    }
    std::string section;


    while (!file.eof())
    {
        std::string line;
        std::getline(file, line);
        std::istringstream iss(line);
        if (line == "WAYPOINTS")
        {
            section = "WAYPOINTS";
        }
        else if (line == "SPAWN_POINTS")
        {
            section = "SPAWN_POINTS";
        }
        else if (line == "LEGAL_PATHS")
        {
            section = "LEGAL_PATHS";
        }
        else if (line == "SPEED_INTERVAL")
        {
            section = "SPEED_INTERVAL";
        }
        else
        {
            // Filter \n and coments with #
            if (line[0] == '#' || line[0] == '\n')
            {
                continue;
            }

            if (section == "WAYPOINTS")
            {
                int id;
                double x, y, z;
                iss >> id >> x >> y >> z;
                movement->waypoints.push_back({id, x, y, z});
            }
            else if (section == "SPAWN_POINTS")
            {
                int id;
                iss >> id;
                movement->spawnPoints.push_back(SpawnPoint{id});
            }
            else if (section == "LEGAL_PATHS")
            {
                int from, to;
                iss >> from >> to;
                std::vector<int> path;
                int node;
                while (iss >> node)
                {
                    path.push_back(node);
                }


                movement->legalPaths.push_back(LegalPath{from, to, path});
            }
            else if (section == "SPEED_INTERVAL")
            {
                double minSpeed, maxSpeed;
                iss >> minSpeed >> maxSpeed;
                movement->speedInterval = {minSpeed, maxSpeed};
            }
        }
    }
}

/**
 * @brief Reads a scenario from a file and populates the provided data structures.
 * - Lines starting with '#' or empty lines are ignored.
 * - Lines starting with '!' contain dimension information.
 * - Lines starting with '*' contain band information.
 * - All other lines contain gnbStruct information.
 * After reading the file, the function prints out the band information and closes the file.
 *
 * @param filename The name of the file to read from.
 * @param gnbs A pointer to a vector of gnbStructs to populate with the gnbStruct information from
 * the file.
 * @param dimensions A pointer to a scenarioLimits structure to populate with the dimension
 * information from the file.
 * @param bands A pointer to a vector of Bands to populate with the band information from the file.
 */

void
readScenario(std::string filename,
             std::vector<gnbStruct>* gnbs,
             scenarioLimits* dimensions,
             std::vector<Band>* bands)
{
    std::ifstream file(filename);
    std::cout << "Reading " << filename << "..." << std::endl;
    if (!file.is_open())
    {
        std::cout << "Error reading the file" << std::endl;
        exit(EXIT_FAILURE);
    }

    std::string line;
    while (std::getline(file, line))
    {
        if (line.empty() || line[0] == '#' || line[0] == '\n')
        {
            continue;
        }
        else if (line[0] == '!')
        {
            line[0] = ' ';
            std::istringstream iss(line);
            if (!(iss >> dimensions->MinX >> dimensions->MaxX >> dimensions->MinY >>
                  dimensions->MaxY))
            {
                std::cout << "Error parsing dimensions line: " << line << std::endl;
                exit(EXIT_FAILURE);
            }

            continue;
        }
        else if (line[0] == '*')
        {
            Band band;
            line[0] = ' ';
            std::istringstream iss(line);
            iss >> band.bandID >> band.centralFrequency >> band.gnbBandwidth;
            bands->push_back(band);
            continue;
        }

        std::istringstream iss(line);
        gnbStruct gnb;
        if (!(iss >> gnb.id >> gnb.x >> gnb.y >> gnb.z >> gnb.bandID >> gnb.txPower >> gnb.gnbType))
        {
            std::cout << "Failed to parse line: " << line << std::endl;
            exit(EXIT_FAILURE);
        }
        gnbs->push_back(gnb);
    }

    for (const auto& band : *bands)
    {
        std::cout << "Band ID: " << band.bandID << ", Central Frequency: " << band.centralFrequency
                  << ", Bandwidth: " << band.gnbBandwidth << std::endl;
    }

    file.close();
}

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
void
LogProgress(double simtime)
{
    double currentTime = Simulator::Now().GetSeconds();
    int currentPercentage = 100 * (currentTime / simtime);
    std::cout << "Time elapsed:" << currentTime << " Progress: " << currentPercentage << "%"
              << std::endl;
    Simulator::Schedule(Seconds(simtime / 100), &LogProgress, simtime);
}

void
MeasureFlowStats(Ptr<ns3::FlowMonitor> monitor, FlowStatsParams params)
{
    Ptr<Ipv4FlowClassifier> classifier = params.classifier;
    double interval = params.interval / 1e6;
    double simTime = params.simTime;
    ns3::NodeContainer ueNodes = params.ueNodes;

    ns3::NodeContainer gnbNodes = params.gnbNodes;
    double currentTime = Simulator::Now().GetSeconds();

    monitor->CheckForLostPackets(ns3::Seconds(simTime));
    ns3::FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();
    if (params.isWaypointBasedMobility) {
        update_mov_directions(params.wp,&params.movement, ueNodes.Get(0), params.tolerance, &params.lastWaypointIndex);
    }

    Ptr<MobilityModel> UEmobilityModel = ueNodes.Get(0)->GetObject<MobilityModel>();
    Ptr<MobilityModel> GNBmobilityModel = gnbNodes.Get(params.id)->GetObject<MobilityModel>();
    Vector uePos = UEmobilityModel->GetPosition();
    Vector gnbPos = GNBmobilityModel->GetPosition();

    double distance = CalculateDistance(uePos, gnbPos);
    double rsrp = params.ueNetDev.Get(0)->GetObject<NrUeNetDevice>()->GetPhy(0)->GetRsrp();
    // Get SINR
    
    uint64_t txBytes;
    uint64_t txPackets;
    uint64_t rxBytes;
    uint64_t rxPackets;
    double latencySum;
    double jitterSum;
    double latencyLast;
    uint32_t lostPackets;
    // add current time to the file
    std::time_t now = std::time(nullptr);
    std::tm* localTime = std::localtime(&now);
    char timeBuffer[100];

    for (std::map<FlowId, ns3::FlowMonitor::FlowStats>::const_iterator i = stats.begin();
         i != stats.end();
         ++i)
    {
        std::stringstream protStream;
        if (i->second.rxPackets > 0)
        {
            rxBytes = i->second.rxBytes;
            rxPackets = i->second.rxPackets;
            latencySum = double(i->second.delaySum.GetSeconds() / rxPackets);
            latencyLast = i->second.lastDelay.GetSeconds();
            jitterSum = double(i->second.jitterSum.GetSeconds() / rxPackets);
            lostPackets = i->second.lostPackets;
        }
        else
        {
            rxBytes = 0;
            rxPackets = 0;
            latencySum = 0;
            jitterSum = 0;
            lostPackets = 0;
            latencyLast = 0;
            rsrp = -INFINITY;
        }
        txBytes = i->second.txBytes;
        txPackets = i->second.txPackets;

        now = std::time(nullptr);
        localTime = std::localtime(&now);
        std::strftime(timeBuffer, sizeof(timeBuffer), "%Y-%m-%d %H:%M:%S", localTime);

        *(params.file) << currentTime << "," << txBytes << "," << txPackets << "," << rxBytes << ","
                       << rxPackets << "," << latencySum << "," << latencyLast << "," << jitterSum
                       << "," << lostPackets << "," << distance << "," << rsrp << "," << uePos
                       << "," << timeBuffer << "\n";
        params.file->flush();
    }

    if (currentTime + interval <= simTime)
    {
        // Schedule the next measurement
        Simulator::Schedule(Seconds(interval), &MeasureFlowStats, monitor, params);
    }
}

int
process_result(const std::string& filename)
{
    std::ofstream file(filename);

    return 0;
}

BandwidthPartInfo::Scenario getScenario(const std::string& scenarioModel) {
    if (scenarioModel == "InH_OfficeMixed")
    {
        return BandwidthPartInfo::InH_OfficeMixed;
    }
    else if (scenarioModel == "InH_OfficeMixed_LoS")
    {
        return BandwidthPartInfo::InH_OfficeMixed_LoS;
    }
    else if (scenarioModel == "InH_OfficeMixed_nLoS")
    {
        return BandwidthPartInfo::InH_OfficeMixed_nLoS;
    }
    else if (scenarioModel == "InH_OfficeOpen")
    {
        return BandwidthPartInfo::InH_OfficeOpen;
    }
    else if (scenarioModel == "InH_OfficeOpen_LoS")
    {
        return BandwidthPartInfo::InH_OfficeOpen_LoS;
    }
    else if (scenarioModel == "InH_OfficeOpen_nLoS")
    {
        return BandwidthPartInfo::InH_OfficeOpen_nLoS;
    }
    else if (scenarioModel == "RMa")
    {
        return BandwidthPartInfo::RMa;
    }
    else if (scenarioModel == "RMa_LoS")
    {
        return BandwidthPartInfo::RMa_LoS;
    }
    else if (scenarioModel == "RMa_nLoS")
    {
        return BandwidthPartInfo::RMa_nLoS;
    }
    else if (scenarioModel == "UMa")
    {
        return BandwidthPartInfo::UMa;
    }
    else if (scenarioModel == "UMa_Buildings")
    {
        return BandwidthPartInfo::UMa_Buildings;
    }
    else if (scenarioModel == "UMa_LoS")
    {
        return BandwidthPartInfo::UMa_LoS;
    }
    else if (scenarioModel == "UMa_nLoS")
    {
        return BandwidthPartInfo::UMa_nLoS;
    }
    else if (scenarioModel == "UMi_Buildings")
    {
        return BandwidthPartInfo::UMi_Buildings;
    }
    else if (scenarioModel == "UMi_StreetCanyon")
    {
        return BandwidthPartInfo::UMi_StreetCanyon;
    }
    else if (scenarioModel == "UMi_StreetCanyon_LoS")
    {
        return BandwidthPartInfo::UMi_StreetCanyon_LoS;
    }
    else if (scenarioModel == "UMi_StreetCanyon_nLoS")
    {
        return BandwidthPartInfo::UMi_StreetCanyon_nLoS;
    }
    else
    {
        throw std::invalid_argument("Invalid scenario model");
    }
}

int
simulate_process(SimulationParameters params, std::ofstream* file)
{
    enum BandwidthPartInfo::Scenario scenarioEnum;
    scenarioEnum = getScenario(params.scenario);

    Config::SetDefault("ns3::LteRlcUm::MaxTxBufferSize", UintegerValue(1000 *200));

    // enable logging
    if (params.logging)
    {
        LogComponentEnable("UdpClient", LOG_LEVEL_INFO);
        LogComponentEnable("UdpServer", LOG_LEVEL_INFO);
    }

    // create base stations and mobile terminals
    std::vector<NodeContainer> enbNodes;
    for (size_t i = 0; i < params.bands.size(); i++)
    {
        NodeContainer nodes;
        int bandID = params.bands[i].bandID;
        int nGnbBand = 0;
        for (int i = 0; i < params.nGnb; i++)
        {
            if (params.gnbs.at(i).bandID == bandID)
            {
                nGnbBand++;
            }
        }
        nodes.Create(nGnbBand);
        std::cout << "Creating " << nGnbBand << " GNBs for band " << bandID << std::endl;
        enbNodes.push_back(nodes);
    }

    NodeContainer ueNodes;
    ueNodes.Create(1);

    // position the base stations
    Ptr<ListPositionAllocator> enbPositionAlloc = CreateObject<ListPositionAllocator>();

    for (int i = 0; i < params.nGnb; i++)
    {
        gnbStruct actualGnb = params.gnbs[i];
        if (params.logging)
        {
            std::cout << "[(debug)]: Positioning base station in (" << actualGnb.x << ","
                      << actualGnb.y << "," << actualGnb.z << ") m" << " on band"
                      << actualGnb.bandID << " with " << actualGnb.txPower << " dbm" << std::endl;
        }
        enbPositionAlloc->Add(Vector(actualGnb.x, actualGnb.y, actualGnb.z));
    }

    MobilityHelper enbmobility;
    enbmobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    enbmobility.SetPositionAllocator(enbPositionAlloc);

    for (size_t i = 0; i < enbNodes.size(); i++)
    {
        // Install mobility for eNBs in the current NodeContainer
        enbmobility.Install(enbNodes[i]);
    }

    // Position the mobile terminals and enable the mobility random walk model, both the initial
    // position and waypoints must be contained in the scenario limits, z=1.5m
    MobilityHelper uemobility;

    // if the waypoints are provided, use the waypoint model, otherwise use the random walk model
    // random walk model
    if (params.isWaypointBasedMobility)
    {
        uemobility.SetMobilityModel("ns3::ConstantVelocityMobilityModel");
        uemobility.Install(ueNodes);
        // get the mobility model
        Ptr<ConstantVelocityMobilityModel> mobility =
            ueNodes.Get(0)->GetObject<ConstantVelocityMobilityModel>();
        // set the initial position
        mobility->SetPosition(params.initialPos);
    }
    else
    {
        std::cout << "Limits: " << params.limits.MinX << " " << params.limits.MaxX << " "
                  << params.limits.MinY << " " << params.limits.MaxY << std::endl;

        uemobility.SetMobilityModel(
            "ns3::RandomWalk2dMobilityModel",
            "Bounds",
            RectangleValue(Rectangle(params.limits.MinX,
                                     params.limits.MaxX,
                                     params.limits.MinY,
                                     params.limits.MaxY)),
            "Mode",
            ns3::StringValue("Time"),
            "Time",
            ns3::StringValue(std::to_string(params.trayectoryTime) + "s"),
            "Speed",
            ns3::StringValue(
                "ns3::ConstantRandomVariable[Constant=" + std::to_string(params.speed) + "]"),
            "Direction",
            ns3::StringValue("ns3::UniformRandomVariable[Min=0.0|Max=6.283185307]"));

        uemobility.SetPositionAllocator(
            "ns3::RandomRectanglePositionAllocator",
            "X",
            ns3::StringValue(
                "ns3::UniformRandomVariable[Min=" + std::to_string(params.limits.MinX) +
                "|Max=" + std::to_string(params.limits.MaxX) + "]"),
            "Y",
            ns3::StringValue(
                "ns3::UniformRandomVariable[Min=" + std::to_string(params.limits.MinY) +
                "|Max=" + std::to_string(params.limits.MaxY) + "]"));

        uemobility.Install(ueNodes);
    }

    // Set the z-coordinate (height) for all nodes
    // Set the z-coordinate (height) for all nodes
    for (NodeContainer::Iterator j = ueNodes.Begin(); j != ueNodes.End(); ++j)
    {
        Ptr<Node> object = *j;
        Ptr<MobilityModel> position = object->GetObject<MobilityModel>();
        Vector pos = position->GetPosition();
        pos.z = 1.5; // Set the z-coordinate to 1.5m
        position->SetPosition(pos);
    }

    /*
     * Create NR simulation helpers
     */
    Ptr<NrPointToPointEpcHelper> epcHelper = CreateObject<NrPointToPointEpcHelper>();
    Ptr<IdealBeamformingHelper> idealBeamformingHelper = CreateObject<IdealBeamformingHelper>();
    Ptr<NrHelper> nrHelper = CreateObject<NrHelper>();
    nrHelper->SetSchedulerTypeId(TypeId::LookupByName("ns3::NrMacSchedulerTdmaRR"));
    nrHelper->SetBeamformingHelper(idealBeamformingHelper);
    nrHelper->SetEpcHelper(epcHelper);

    /*
     * Set the error model for the NR simulation
     */

    nrHelper->SetDlErrorModel(params.errorModel);
    nrHelper->SetUlErrorModel(params.errorModel);

    // Config::SetDefault("ns3::ThreeGppChannelModel::UpdatePeriod",
    // TimeValue(MicroSeconds(params.timeInterval)));
    // nrHelper->SetPhasedArraySpectrumPropagationLossModelTypeId(ThreeGppRmaChannelConditionModel::GetTypeId());
    // nrHelper->SetChannelConditionModelAttribute("UpdatePeriod",
    // TimeValue(MicroSeconds(params.timeInterval)));
    /*
     * Set the channel model for the NR simulation
     */
    Config::SetDefault("ns3::ThreeGppChannelModel::UpdatePeriod", TimeValue(MilliSeconds(0)));
    nrHelper->SetChannelConditionModelAttribute("UpdatePeriod", TimeValue(MilliSeconds(0)));
    nrHelper->SetPathlossAttribute("ShadowingEnabled", BooleanValue(false));

    nrHelper->SetSchedulerAttribute("FixedMcsDl", BooleanValue(params.useFixedMcs));
    nrHelper->SetSchedulerAttribute("FixedMcsUl", BooleanValue(params.useFixedMcs));
    if (params.useFixedMcs)
    {
        nrHelper->SetSchedulerAttribute("StartingMcsDl", UintegerValue(params.fixedMcs));
        nrHelper->SetSchedulerAttribute("StartingMcsUl", UintegerValue(params.fixedMcs));
    }

    nrHelper->SetGnbDlAmcAttribute(
        "AmcModel",
        EnumValue(NrAmc::ErrorModel)); // NrAmc::ShannonModel or NrAmc::ErrorModel
    nrHelper->SetGnbUlAmcAttribute(
        "AmcModel",
        EnumValue(NrAmc::ErrorModel)); // NrAmc::ShannonModel or NrAmc::ErrorModel

    /*
     * Spectrum configuration.  We are using a single band connected to the selected gNB
     */
    BandwidthPartInfoPtrVector allBwps;
    std::vector<BandwidthPartInfoPtrVector> bwps;
    std::vector<std::unique_ptr<OperationBandInfo>> operationBands;
    CcBwpCreator ccBwpCreator;
    const uint8_t numCcPerBand = 1;
    if (params.logging)
    {
        for (const auto& band : params.bands)
        {
            std::cout << "Band ID: " << band.bandID
                      << ", Central Frequency: " << band.centralFrequency
                      << ", Bandwidth: " << band.gnbBandwidth << std::endl;
        }
    }
    for (size_t bandID = 0; bandID < params.bands.size(); bandID++)
    {
        Band bandInfo = params.bands[bandID];

        // Create the configuration for the CcBwpHelper
        CcBwpCreator::SimpleOperationBandConf bandConfig(bandInfo.centralFrequency,
                                                         bandInfo.gnbBandwidth,
                                                         numCcPerBand,
                                                         scenarioEnum);

        // Create operation band for the current gNB
        std::unique_ptr<OperationBandInfo> bandOb = std::make_unique<OperationBandInfo>(
            ccBwpCreator.CreateOperationBandContiguousCc(bandConfig));

        // Initialize channel and pathloss, plus other things inside the band
        nrHelper->InitializeOperationBand(bandOb.get());

        // Create a separate BandwidthPartInfoPtrVector for each band
        BandwidthPartInfoPtrVector bandBwps;
        bandBwps = CcBwpCreator::GetAllBwps(
            std::vector<std::reference_wrapper<OperationBandInfo>>({std::ref(*bandOb)}));
        bwps.push_back(bandBwps);

        operationBands.push_back(std::move(bandOb));
    }
    std::vector<std::reference_wrapper<OperationBandInfo>> bands_ref;
    for (auto& bandOb : operationBands)
    {
        bands_ref.push_back(std::ref(*bandOb));
    }
    allBwps = CcBwpCreator::GetAllBwps(bands_ref);

    idealBeamformingHelper->SetAttribute("BeamformingMethod",
                                         TypeIdValue(DirectPathBeamforming::GetTypeId()));

    // Configure scheduler
    nrHelper->SetSchedulerTypeId(NrMacSchedulerTdmaRR::GetTypeId());

    // Antennas for the UEs
    nrHelper->SetUeAntennaAttribute("NumRows", UintegerValue(2));
    nrHelper->SetUeAntennaAttribute("NumColumns", UintegerValue(4));
    nrHelper->SetUeAntennaAttribute("AntennaElement",
                                    PointerValue(CreateObject<IsotropicAntennaModel>()));

    // Antennas for the gNbs
    nrHelper->SetGnbAntennaAttribute("NumRows", UintegerValue(8));
    nrHelper->SetGnbAntennaAttribute("NumColumns", UintegerValue(8));
    // if gnb_type is 'I' then set the antenna element to isotropic
    // if gnb_type is 'H' then set the antenna elemen to 3GGP antenna model
    for (size_t i = 0; i < params.gnbs.size(); i++)
    {
        if (params.gnbs[i].gnbType == 'I')
        {
            nrHelper->SetGnbAntennaAttribute("AntennaElement",
                                             PointerValue(CreateObject<IsotropicAntennaModel>()));
        }
        else if (params.gnbs[i].gnbType == 'H')
        {
            nrHelper->SetGnbAntennaAttribute("AntennaElement",
                                             PointerValue(CreateObject<ThreeGppAntennaModel>()));
        }
    }
    // install NR net devices
    std::vector<NetDeviceContainer> enbNetDevPerBand;
    for (size_t bandID = 0; bandID < params.bands.size(); bandID++)
    {
        Band bandInfo = params.bands[bandID];
        // Create a separate NetDeviceContainer for each band
        NetDeviceContainer enbNetDev =
            nrHelper->InstallGnbDevice(enbNodes[bandInfo.bandID], bwps[bandInfo.bandID]);
        enbNetDevPerBand.push_back(enbNetDev);

        // Store the NetDeviceContainer for this band
    }
    int selectedBandID = -1;
    for (size_t bandID = 0; bandID < params.bands.size(); bandID++)
    {
        if (params.gnbs[params.selectedGnb].bandID == params.bands[bandID].bandID)
        {
            selectedBandID = bandID;
        }
    }
    std::cout << "Selected band: " << selectedBandID << std::endl;
    NetDeviceContainer ueNetDev = nrHelper->InstallUeDevice(ueNodes, bwps[selectedBandID]);

    int64_t randomStream = 1;

    for (size_t bandID = 0; bandID < params.bands.size(); bandID++)
    {
        Band bandInfo = params.bands[bandID];

        // Assign random streams for each NetDeviceContainer separately
        randomStream += nrHelper->AssignStreams(enbNetDevPerBand[bandInfo.bandID], randomStream);
    }
    randomStream += nrHelper->AssignStreams(ueNetDev, randomStream);
    int gnbId = 0;
    for (size_t i = 0; i < enbNetDevPerBand.size(); i++)
    {
        for (auto it = enbNetDevPerBand[i].Begin(); it != enbNetDevPerBand[i].End(); ++it)
        {
            DynamicCast<NrGnbNetDevice>(*it)->UpdateConfig();
            // Convert the txPower from dBm to W
            nrHelper->GetGnbPhy(DynamicCast<NetDevice>(*it), 0)
                ->SetTxPower(params.gnbs[gnbId].txPower);
            gnbId++;
        }
    }

    for (auto it = ueNetDev.Begin(); it != ueNetDev.End(); ++it)
    {
        DynamicCast<NrUeNetDevice>(*it)->UpdateConfig();
    }

    Ptr<Node> pgw = epcHelper->GetPgwNode();
    NodeContainer remoteHostContainer;
    remoteHostContainer.Create(1);
    Ptr<Node> remoteHost = remoteHostContainer.Get(0);
    InternetStackHelper internet;
    internet.Install(remoteHostContainer);

    // connect a remoteHost to pgw. Setup routing too
    PointToPointHelper p2ph;
    p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("100Gb/s")));
    p2ph.SetDeviceAttribute("Mtu", UintegerValue(2500));
    p2ph.SetChannelAttribute("Delay", TimeValue(Seconds(0.010)));
    NetDeviceContainer internetDevices = p2ph.Install(pgw, remoteHost);

    Ipv4AddressHelper ipv4h;
    ipv4h.SetBase("1.0.0.0", "255.0.0.0");
    Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign(internetDevices);
    Ipv4StaticRoutingHelper ipv4RoutingHelper;

    Ptr<Ipv4StaticRouting> remoteHostStaticRouting =
        ipv4RoutingHelper.GetStaticRouting(remoteHost->GetObject<Ipv4>());
    remoteHostStaticRouting->AddNetworkRouteTo(Ipv4Address("7.0.0.0"), Ipv4Mask("255.0.0.0"), 1);
    internet.Install(ueNodes);

    Ipv4InterfaceContainer ueIpIface, otherUEIpIface;
    ueIpIface = epcHelper->AssignUeIpv4Address(NetDeviceContainer(ueNetDev));

    // assign IP address to UEs, and install UDP downlink applications
    uint16_t dlPort = 1234;
    ApplicationContainer clientApps;
    ApplicationContainer serverApps;

    int bandid = params.gnbs[params.selectedGnb].bandID;
    int id = 0;
    for (int i = 0; i < params.selectedGnb; i++)
    {
        if (params.gnbs[i].bandID == bandid)
        {
            id++;
        }
    }
    std::cout << "Band " << bandid << " Selected GNB: " << id << std::endl;
    std::cout << enbNetDevPerBand[bandid].Get(id)->GetChannel() << std::endl;
    nrHelper->AttachToEnb(ueNetDev.Get(0), enbNetDevPerBand[bandid].Get(id));
    double bitrate = params.bitRate;

    double packetsPerSecond = bitrate / (params.packetSize * 8);
    double packetInterval = 1 / packetsPerSecond;
    for (uint32_t u = 0; u < ueNodes.GetN(); ++u)
    {
        Ptr<Node> ueNode = ueNodes.Get(u);
        // Set the default gateway for the UE
        Ptr<Ipv4StaticRouting> ueStaticRouting =
            ipv4RoutingHelper.GetStaticRouting(ueNode->GetObject<Ipv4>());
        ueStaticRouting->SetDefaultRoute(epcHelper->GetUeDefaultGatewayAddress(), 1);

        UdpServerHelper dlPacketSinkHelper(dlPort);
        serverApps.Add(dlPacketSinkHelper.Install(ueNodes.Get(u)));
        UdpClientHelper dlClient(ueIpIface.GetAddress(u), dlPort);

        dlClient.SetAttribute("Interval", TimeValue(Seconds(packetInterval)));
        dlClient.SetAttribute("MaxPackets", UintegerValue(params.MaxPackets));
        dlClient.SetAttribute("PacketSize", UintegerValue(params.packetSize));
        clientApps.Add(dlClient.Install(remoteHost));
    }

    std::cout << "Simulation runnning\n" << std::endl;
    // start server and client apps
    serverApps.Start(Seconds(0));
    serverApps.Stop(Seconds(params.simTime));
    clientApps.Start(Seconds(0));
    clientApps.Stop(Seconds(params.simTime));

    FlowMonitorHelper flowmonHelper;
    NodeContainer endpointNodes;
    endpointNodes.Add(remoteHost);
    endpointNodes.Add(ueNodes);
    Ptr<ns3::FlowMonitor> monitor = flowmonHelper.Install(endpointNodes);
    monitor->SetAttribute("DelayBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("JitterBinWidth", DoubleValue(0.001));
    monitor->SetAttribute("PacketSizeBinWidth", DoubleValue(20));
    Ptr<Ipv4FlowClassifier> classifier =
        DynamicCast<Ipv4FlowClassifier>(flowmonHelper.GetClassifier());
    FlowMonitor::FlowStatsContainer stats = monitor->GetFlowStats();

    FlowStatsParams flowStats;
    flowStats.classifier = classifier;
    flowStats.interval = params.timeInterval;
    flowStats.simTime = params.simTime;
    flowStats.ueNodes = ueNodes;
    flowStats.gnbNodes = enbNodes[bandid];
    flowStats.id = id;
    flowStats.selectedGnb = params.selectedGnb;
    flowStats.ueNetDev = ueNetDev;
    flowStats.gnbNetDev = enbNetDevPerBand[bandid];
    flowStats.movement = params.movement;
    flowStats.file = file;
    flowStats.isWaypointBasedMobility = params.isWaypointBasedMobility;
    flowStats.tolerance = params.tolerance;
    flowStats.lastWaypointIndex = params.lastWaypointIndex;

    Ptr<NetDevice> ueNetDevice = ueNetDev.Get(0);
    Ptr<NetDevice> enbNetDevice = enbNetDevPerBand[bandid].Get(id);
    Simulator::Schedule(MicroSeconds(params.timeInterval), &MeasureFlowStats, monitor, flowStats);

    Simulator::Schedule(Seconds(params.simTime / 100), &LogProgress, params.simTime);
    // Ptr<NrRadioEnvironmentMapHelper> remHelper = CreateObject<NrRadioEnvironmentMapHelper>();
    // int xRes = 50;
    // int yRes = 50;
    // remHelper->SetMinX(params.limits.MinX);
    // remHelper->SetMaxX(params.limits.MaxX);
    // remHelper->SetResX(xRes);
    // remHelper->SetMinY(params.limits.MinY);
    // remHelper->SetMaxY(params.limits.MaxY);
    // remHelper->SetResY(yRes);
    // //remHelper->SetSimTag(std::to_string(bandid));
    // remHelper->SetRemMode(NrRadioEnvironmentMapHelper::COVERAGE_AREA);

    // create the Radio Environment Map
    //remHelper->CreateRem(enbNetDevPerBand[1],ueNetDev.Get(0), 0);

    Simulator::Stop(Seconds(params.simTime * 1.01));
    Simulator::Run();
    std::cout << "Simulation done" << std::endl;
    Simulator::Destroy();
    return 0;
}

int
main(int argc, char* argv[])
{
    // File Pointer
    std::ofstream traceFile;

    // default values
    SimulationParameters params;
    params.scenario = "InH_OfficeOpen_LoS";
    params.simTime = 10;
    params.speed = 10;
    params.logging = false;
    params.MaxPackets = 0;
    params.packetSize = 1000;
    params.bitRate = 380e6;
    params.selectedGnb = 0;
    params.timeInterval = 1e5;
    params.randomSeed = 1234;
    params.nUEs = 500;
    params.tolerance = 1;
    params.fullBuffer = true;
    params.errorModel = "ns3::NrEesmCcT1";
    params.useFixedMcs = false;
    params.fixedMcs = 28;
    params.trayectoryTime = 5;

    std::string path = ".";
    std::string scFile = "../handover-simulator/scenario/sc.txt";
    std::string wpFile = "";

    CommandLine cmd(__FILE__);
    cmd.AddValue("path", "traces directory", path);
    cmd.AddValue("scenario",
                 "The scenario for the simulation. Choose among 'RMa', 'UMa', "
                 "'UMi-StreetCanyon','InH-OfficeMixed', 'InH-OfficeOpen',...",
                 params.scenario);
    cmd.AddValue("logging", "If set to 0, log components will be disabled.", params.logging);
    cmd.AddValue("simTime", "The simulation time in seconds.", params.simTime);
    cmd.AddValue("speed", "The speed of the UEs in m/s.", params.speed);
    cmd.AddValue("trayectoryTime",
                 "The time for the trayectory in seconds.",
                 params.trayectoryTime);
    cmd.AddValue("MaxPackets", "The maximum number of packets.", params.MaxPackets);
    cmd.AddValue("packetSize", "Packet size in bytes.", params.packetSize);
    cmd.AddValue("bitRate", "Bitrate in bits/s.", params.bitRate);
    cmd.AddValue("gnb", "selected g-nodeB for this simulation", params.selectedGnb);
    cmd.AddValue("seed", "Random number generator seed", params.randomSeed);
    cmd.AddValue("nUEs", "The number of UEs in the environment.", params.nUEs);
    cmd.AddValue("int", "The sample time interval in microseconds.", params.timeInterval);
    cmd.AddValue("packetSize", "The packet size in bytes.", params.packetSize);
    cmd.AddValue("fullBuffer",
                 "Provides enough bitrate to saturate the simulation.",
                 params.fullBuffer);
    cmd.AddValue("errorModel",
                 "Error model type: ns3::NrEesmCcT1, ns3::NrEesmCcT2, ns3::NrEesmIrT1, "
                 "ns3::NrEesmIrT2, ns3::NrLteMiErrorModel",
                 params.errorModel);
    cmd.AddValue("sc", "Scenario definition file path", scFile);
    cmd.AddValue("wp", "Waypoints definition file path", wpFile);
    cmd.AddValue("tolerance", "The tolerance for the mobility simulation.", params.tolerance);

    cmd.Parse(argc, argv);
    // Scenario file read----------

    // set the random seed
    RngSeedManager::SetSeed(params.randomSeed);
    srand(params.randomSeed);

    readScenario(scFile, &(params.gnbs), &(params.limits), &(params.bands));
    params.nGnb = params.gnbs.size();

    if (params.selectedGnb < 0 || params.selectedGnb >= params.nGnb)
    {
        std::cout << "selected g-nodeB is out of range" << std::endl;
        return -1;
    }

    create_file(&traceFile, path + FILE_NAME);
    if (wpFile != "")
    {

    readWaypoints(wpFile, &(params.movement));
        std::cout << "Waypoints loaded" << std::endl;
        params.isWaypointBasedMobility = true;
        // Select a random spawn point as initial position
        int spawnPointIndex = rand() % params.movement.spawnPoints.size();
        printf("Spawn point index: %d\n", spawnPointIndex);
        int spawnPointId = params.movement.spawnPoints[spawnPointIndex].id;
        std::cout << "Spawn point index: " << spawnPointId << std::endl;
        params.initialPos = Vector(params.movement.waypoints[spawnPointId].x,
                            params.movement.waypoints[spawnPointId].y,
                            params.movement.waypoints[spawnPointId].z);
        std::cout << "Initial position: " << params.initialPos << std::endl;
        params.lastWaypointIndex = spawnPointId;
    }
    else
    {
        params.isWaypointBasedMobility = false;
    }
    simulate_process(params, &traceFile);
    close_file(&traceFile);

    return 0;
}

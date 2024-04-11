#
# Copyright (c) 2014-2024 Key4hep-Project.
#
# This file is part of Key4hep.
# See https://key4hep.github.io/key4hep-doc/ for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
from Gaudi.Configuration import INFO, WARNING, DEBUG

from Configurables import k4DataSvc, MarlinProcessorWrapper
from k4MarlinWrapper.inputReader import create_reader, attach_edm4hep2lcio_conversion
from k4FWCore.parseArgs import parser
from py_utils import SequenceLoader


parser.add_argument("--inputFiles", action="extend", nargs="+", metavar=("file1", "file2"), help="One or multiple input files")
parser.add_argument("--outputBasename", help="Basename of the output file(s)", default="output")
parser.add_argument("--trackingOnly", action="store_true", help="Run only track reconstruction", default=False)
reco_args = parser.parse_known_args()[0]

algList = []
svcList = []

evtsvc = k4DataSvc("EventDataSvc")
svcList.append(evtsvc)

CONFIG = {
             "CalorimeterIntegrationTimeWindow": "10ns",
             "CalorimeterIntegrationTimeWindowChoices": ["10ns", "400ns"],
             "Overlay": "False",
             "OverlayChoices": ["False", "91GeV", "365GeV"],
             "Tracking": "Conformal",
             "TrackingChoices": ["Truth", "Conformal"],
             "VertexUnconstrained": "OFF",
             "VertexUnconstrainedChoices": ["ON", "OFF"],
             "OutputMode": "EDM4Hep",
             "OutputModeChoices": ["LCIO", "EDM4hep"] #, "both"] FIXME: both is not implemented yet
}

from Configurables import GeoSvc, TrackingCellIDEncodingSvc
geoservice = GeoSvc("GeoSvc")
geoservice.detectors = [os.environ["K4GEO"]+"/FCCee/CLD/compact/CLD_o2_v05/CLD_o2_v05.xml"]
geoservice.OutputLevel = INFO
geoservice.EnableGeant4Geo = False
svcList.append(geoservice)

cellIDSvc = TrackingCellIDEncodingSvc("CellIDSvc")
cellIDSvc.EncodingStringParameterName = "GlobalTrackerReadoutID"
cellIDSvc.GeoSvcName = geoservice.name()
cellIDSvc.OutputLevel = INFO
svcList.append(cellIDSvc)

if len(geoservice.detectors) > 1:
    # we are making assumptions for reconstruction parameters based on the detector option, so we limit the possibilities
    raise RuntimeError("Too many XML files for the detector path, please only specify the main file!")

sequenceLoader = SequenceLoader(
    algList,
    # global_vars can be used in sequence-loaded modules without explicit import
    global_vars={"CONFIG": CONFIG, "geoservice": geoservice},
)

if reco_args.inputFiles:
    read = create_reader(reco_args.inputFiles, evtsvc)
    read.OutputLevel = INFO
    algList.append(read)
else:
    read = None

MyAIDAProcessor = MarlinProcessorWrapper("MyAIDAProcessor")
MyAIDAProcessor.OutputLevel = WARNING
MyAIDAProcessor.ProcessorType = "AIDAProcessor"
MyAIDAProcessor.Parameters = {
                              "Compress": ["1"],
                              "FileName": [f"{reco_args.outputBasename}_aida"],
                              "FileType": ["root"]
                              }

OverlayParameters = {
    "MCParticleCollectionName": ["MCParticle"],
    "MCPhysicsParticleCollectionName": ["MCPhysicsParticles"],
    "Delta_t": ["20"],
    "NBunchtrain": ["20"],
    "Collection_IntegrationTimes": [
        "VertexBarrelCollection", "380",
        "VertexEndcapCollection", "380",
        "InnerTrackerBarrelCollection", "380",
        "InnerTrackerEndcapCollection", "380",
        "OuterTrackerBarrelCollection", "380",
        "OuterTrackerEndcapCollection", "380",
        "ECalBarrelCollection", "380",
        "ECalEndcapCollection", "380",
        "HCalBarrelCollection", "380",
        "HCalEndcapCollection", "380",
        "HCalRingCollection", "380",
        "YokeBarrelCollection", "380",
        "YokeEndcapCollection", "380",
        "LumiCalCollection", "380"
     ],
    "PhysicsBX": ["1"],
    "Poisson_random_NOverlay": ["false"],
    "RandomBx": ["false"],
    "TPCDriftvelocity": ["0.05"],
    "BackgroundFileNames": ["pairs_Z_sim.slcio"],
}
Overlay = {}

Overlay["False"] = MarlinProcessorWrapper("OverlayFalse")
Overlay["False"].OutputLevel = WARNING
Overlay["False"].ProcessorType = "OverlayTimingGeneric"
Overlay["False"].Parameters = OverlayParameters.copy()
Overlay["False"].Parameters |= {
                           "BackgroundFileNames": [],
                           "NBunchtrain": ["0"],
                           "NumberBackground": ["0."],
                           }

# XXX: Caution, this probably needs an update
Overlay["91GeV"] = MarlinProcessorWrapper("Overlay91GeV")
Overlay["91GeV"].OutputLevel = WARNING
Overlay["91GeV"].ProcessorType = "OverlayTimingGeneric"
Overlay["91GeV"].Parameters = OverlayParameters.copy()
Overlay["91GeV"].Parameters |= {
                           "NumberBackground": ["1."],
                           }

# XXX: Caution, this probably needs an update
Overlay["365GeV"] = MarlinProcessorWrapper("Overlay365GeV")
Overlay["365GeV"].OutputLevel = WARNING
Overlay["365GeV"].ProcessorType = "OverlayTimingGeneric"
Overlay["365GeV"].Parameters = OverlayParameters.copy()
Overlay["365GeV"].Parameters |= {
                            "Delta_t": ["3396"],
                            "NBunchtrain": ["3"],
                            "NumberBackground": ["1."],
                            }

MyTruthTrackFinder = MarlinProcessorWrapper("MyTruthTrackFinder")
MyTruthTrackFinder.OutputLevel = WARNING
MyTruthTrackFinder.ProcessorType = "TruthTrackFinder"
MyTruthTrackFinder.Parameters = {
                                 "FitForward": ["true"],
                                 "MCParticleCollectionName": ["MCParticle"],
                                 "SiTrackCollectionName": ["SiTracks"],
                                 "SiTrackRelationCollectionName": ["SiTrackRelations"],
                                 "SimTrackerHitRelCollectionNames": ["VXDTrackerHitRelations", "InnerTrackerBarrelHitsRelations", "OuterTrackerBarrelHitsRelations", "VXDEndcapTrackerHitRelations", "InnerTrackerEndcapHitsRelations", "OuterTrackerEndcapHitsRelations"],
                                 "TrackerHitCollectionNames": ["VXDTrackerHits", "ITrackerHits", "OTrackerHits", "VXDEndcapTrackerHits", "ITrackerEndcapHits", "OTrackerEndcapHits"],
                                 "UseTruthInPrefit": ["false"]
                                 }

Refit = MarlinProcessorWrapper("Refit")
Refit.OutputLevel = WARNING
Refit.ProcessorType = "RefitFinal"
Refit.Parameters = {
                    "EnergyLossOn": ["true"],
                    "InputRelationCollectionName": ["SiTrackRelations"],
                    "InputTrackCollectionName": ["SiTracks"],
                    "Max_Chi2_Incr": ["1.79769e+30"],
                    "MinClustersOnTrackAfterFit": ["3"],
                    "MultipleScatteringOn": ["true"],
                    "OutputRelationCollectionName": ["SiTracks_Refitted_Relation"],
                    "OutputTrackCollectionName": ["SiTracks_Refitted"],
                    "ReferencePoint": ["-1"],
                    "SmoothOn": ["false"],
                    "extrapolateForward": ["true"]
                    }

MyClicEfficiencyCalculator = MarlinProcessorWrapper("MyClicEfficiencyCalculator")
MyClicEfficiencyCalculator.OutputLevel = WARNING
MyClicEfficiencyCalculator.ProcessorType = "ClicEfficiencyCalculator"
MyClicEfficiencyCalculator.Parameters = {
                                         "MCParticleCollectionName": ["MCParticle"],
                                         "MCParticleNotReco": ["MCParticleNotReco"],
                                         "MCPhysicsParticleCollectionName": ["MCPhysicsParticles"],
                                         "TrackCollectionName": ["SiTracks_Refitted"],
                                         "TrackerHitCollectionNames": ["VXDTrackerHits", "VXDEndcapTrackerHits", "ITrackerHits", "OTrackerHits", "ITrackerEndcapHits", "OTrackerEndcapHits"],
                                         "TrackerHitRelCollectionNames": ["VXDTrackerHitRelations", "VXDEndcapTrackerHitRelations", "InnerTrackerBarrelHitsRelations", "OuterTrackerBarrelHitsRelations", "InnerTrackerEndcapHitsRelations", "OuterTrackerEndcapHitsRelations"],
                                         "efficiencyTreeName": ["trktree"],
                                         "mcTreeName": ["mctree"],
                                         "morePlots": ["false"],
                                         "purityTreeName": ["puritytree"],
                                         "reconstructableDefinition": ["ILDLike"],
                                         "vertexBarrelID": ["1"]
                                         }

MyTrackChecker = MarlinProcessorWrapper("MyTrackChecker")
MyTrackChecker.OutputLevel = WARNING
MyTrackChecker.ProcessorType = "TrackChecker"
MyTrackChecker.Parameters = {
                             "MCParticleCollectionName": ["MCParticle"],
                             "TrackCollectionName": ["SiTracks_Refitted"],
                             "TrackRelationCollectionName": ["SiTracksMCTruthLink"],
                             "TreeName": ["checktree"],
                             "UseOnlyTree": ["true"]
                             }

MyDDSimpleMuonDigi = MarlinProcessorWrapper("MyDDSimpleMuonDigi")
MyDDSimpleMuonDigi.OutputLevel = WARNING
MyDDSimpleMuonDigi.ProcessorType = "DDSimpleMuonDigi"
MyDDSimpleMuonDigi.Parameters = {
                                 "CalibrMUON": ["70.1"],
                                 "MUONCollections": ["YokeBarrelCollection", "YokeEndcapCollection"],
                                 "MUONOutputCollection": ["MUON"],
                                 "MaxHitEnergyMUON": ["2.0"],
                                 "MuonThreshold": ["1e-06"],
                                 "RelationOutputCollection": ["RelationMuonHit"]
                                 }

MyStatusmonitor = MarlinProcessorWrapper("MyStatusmonitor")
MyStatusmonitor.OutputLevel = WARNING
MyStatusmonitor.ProcessorType = "Statusmonitor"
MyStatusmonitor.Parameters = {
                              "HowOften": ["100"]
                              }

MyRecoMCTruthLinker = MarlinProcessorWrapper("MyRecoMCTruthLinker")
MyRecoMCTruthLinker.OutputLevel = WARNING
MyRecoMCTruthLinker.ProcessorType = "RecoMCTruthLinker"
MyRecoMCTruthLinker.Parameters = {
                                  "BremsstrahlungEnergyCut": ["1"],
                                  "CalohitMCTruthLinkName": ["CalohitMCTruthLink"],
                                  "ClusterCollection": ["PandoraClusters"],
                                  "ClusterMCTruthLinkName": ["ClusterMCTruthLink"],
                                  "FullRecoRelation": ["true"],
                                  "InvertedNonDestructiveInteractionLogic": ["false"],
                                  "KeepDaughtersPDG": ["22", "111", "310", "13", "211", "321", "3120"],
                                  "MCParticleCollection": ["MCPhysicsParticles"],
                                  "MCParticlesSkimmedName": ["MCParticlesSkimmed"],
                                  "MCTruthClusterLinkName": ["MCTruthClusterLink"],
                                  "MCTruthRecoLinkName": ["MCTruthRecoLink"],
                                  "MCTruthTrackLinkName": ["MCTruthSiTracksLink"],
                                  "RecoMCTruthLinkName": ["RecoMCTruthLink"],
                                  "RecoParticleCollection": ["PandoraPFOs"],
                                  "SaveBremsstrahlungPhotons": ["true"],
                                  "SimCaloHitCollections": ["ECalBarrelCollection", "ECalEndcapCollection", "HCalBarrelCollection", "HCalEndcapCollection", "HCalRingCollection", "YokeBarrelCollection", "YokeEndcapCollection", "LumiCalCollection"],
                                  "SimCalorimeterHitRelationNames": ["RelationCaloHit", "RelationMuonHit"],
                                  "SimTrackerHitCollections": ["VertexBarrelCollection", "VertexEndcapCollection", "InnerTrackerBarrelCollection", "OuterTrackerBarrelCollection", "InnerTrackerEndcapCollection", "OuterTrackerEndcapCollection"],
                                  "TrackCollection": ["SiTracks_Refitted"],
                                  "TrackMCTruthLinkName": ["SiTracksMCTruthLink"],
                                  "TrackerHitsRelInputCollections": ["VXDTrackerHitRelations", "VXDEndcapTrackerHitRelations", "InnerTrackerBarrelHitsRelations", "OuterTrackerBarrelHitsRelations", "InnerTrackerEndcapHitsRelations", "OuterTrackerEndcapHitsRelations"],
                                  "UseTrackerHitRelations": ["true"],
                                  "UsingParticleGun": ["false"],
                                  "daughtersECutMeV": ["10"]
                                  }

MyHitResiduals = MarlinProcessorWrapper("MyHitResiduals")
MyHitResiduals.OutputLevel = WARNING
MyHitResiduals.ProcessorType = "HitResiduals"
MyHitResiduals.Parameters = {
                             "EnergyLossOn": ["true"],
                             "MaxChi2Increment": ["1000"],
                             "MultipleScatteringOn": ["true"],
                             "SmoothOn": ["false"],
                             "TrackCollectionName": ["SiTracks_Refitted"],
                             "outFileName": ["residuals.root"],
                             "treeName": ["restree"]
                             }

LumiCalReco = MarlinProcessorWrapper("LumiCalReco")
LumiCalReco.OutputLevel = WARNING
LumiCalReco.ProcessorType = "MarlinLumiCalClusterer"
LumiCalReco.Parameters = {
                          "ClusterMinNumHits": ["15"],
                          "ElementsPercentInShowerPeakLayer": ["0.03"],
                          "EnergyCalibConst": ["0.01213"],
                          "LogWeigthConstant": ["6.5"],
                          "LumiCal_Clusters": ["LumiCalClusters"],
                          "LumiCal_Collection": ["LumiCalCollection"],
                          "LumiCal_RecoParticles": ["LumiCalRecoParticles"],
                          "MaxRecordNumber": ["10"],
                          "MemoryResidentTree": ["0"],
                          "MiddleEnergyHitBoundFrac": ["0.01"],
                          "MinClusterEngy": ["2.0"],
                          "MinHitEnergy": ["20e-06"],
                          "MoliereRadius": ["20"],
                          "NumEventsTree": ["500"],
                          "NumOfNearNeighbor": ["6"],
                          "OutDirName": ["rootOut"],
                          "OutRootFileName": [],
                          "SkipNEvents": ["0"],
                          "WeightingMethod": ["LogMethod"],
                          "ZLayerPhiOffset": ["0.0"]
                          }

RenameCollection = MarlinProcessorWrapper("RenameCollection")
RenameCollection.OutputLevel = WARNING
RenameCollection.ProcessorType = "MergeCollections"
RenameCollection.Parameters = {
                               "CollectionParameterIndex": ["0"],
                               "InputCollectionIDs": [],
                               "InputCollections": ["PandoraPFOs"],
                               "OutputCollection": ["PFOsFromJets"]
                               }

MyFastJetProcessor = MarlinProcessorWrapper("MyFastJetProcessor")
MyFastJetProcessor.OutputLevel = WARNING
MyFastJetProcessor.ProcessorType = "FastJetProcessor"
MyFastJetProcessor.Parameters = {
                                 "algorithm": ["ValenciaPlugin", "1.2", "1.0", "0.7"],
                                 "clusteringMode": ["ExclusiveNJets", "2"],
                                 "jetOut": ["JetsAfterGamGamRemoval"],
                                 "recParticleIn": ["TightSelectedPandoraPFOs"],
                                 "recParticleOut": ["PFOsFromJets"],
                                 "recombinationScheme": ["E_scheme"],
                                 "storeParticlesInJets": ["true"]
                                 }

JetClusteringAndRefiner = MarlinProcessorWrapper("JetClusteringAndRefiner")
JetClusteringAndRefiner.OutputLevel = WARNING
JetClusteringAndRefiner.ProcessorType = "LcfiplusProcessor"
JetClusteringAndRefiner.Parameters = {
                                      "Algorithms": ["JetClustering", "JetVertexRefiner"],
                                      "JetClustering.AlphaParameter": ["1.0"],
                                      "JetClustering.BetaParameter": ["1.0"],
                                      "JetClustering.GammaParameter": ["1.0"],
                                      "JetClustering.InputVertexCollectionName": ["BuildUpVertices"],
                                      "JetClustering.JetAlgorithm": ["ValenciaVertex"],
                                      "JetClustering.MaxNumberOfJetsForYThreshold": ["10"],
                                      "JetClustering.MuonIDExternal": ["0"],
                                      "JetClustering.MuonIDMaximum3DImpactParameter": ["5.0"],
                                      "JetClustering.MuonIDMinimumD0Significance": ["5.0"],
                                      "JetClustering.MuonIDMinimumEnergy": ["0"],
                                      "JetClustering.MuonIDMinimumProbability": ["0.5"],
                                      "JetClustering.MuonIDMinimumZ0Significance": ["5.0"],
                                      "JetClustering.NJetsRequested": ["2"],
                                      "JetClustering.OutputJetCollectionName": ["VertexJets"],
                                      "JetClustering.OutputJetStoresVertex": ["0"],
                                      "JetClustering.PrimaryVertexCollectionName": ["PrimaryVertices"],
                                      "JetClustering.RParameter": ["1.0"],
                                      "JetClustering.UseBeamJets": ["1"],
                                      "JetClustering.UseMuonID": ["1"],
                                      "JetClustering.VertexSelectionK0MassWidth": ["0.02"],
                                      "JetClustering.VertexSelectionMaximumDistance": ["30."],
                                      "JetClustering.VertexSelectionMinimumDistance": ["0.3"],
                                      "JetClustering.YAddedForJetLeptonLepton": ["100"],
                                      "JetClustering.YAddedForJetLeptonVertex": ["100"],
                                      "JetClustering.YAddedForJetVertexLepton": ["0"],
                                      "JetClustering.YAddedForJetVertexVertex": ["100"],
                                      "JetClustering.YCut": ["0."],
                                      "JetVertexRefiner.BNessCut": ["-0.80"],
                                      "JetVertexRefiner.BNessCutE1": ["-0.15"],
                                      "JetVertexRefiner.InputJetCollectionName": ["VertexJets"],
                                      "JetVertexRefiner.InputVertexCollectionName": ["BuildUpVertices"],
                                      "JetVertexRefiner.MaxAngleSingle": ["0.5"],
                                      "JetVertexRefiner.MaxCharmFlightLengthPerJetEnergy": ["0.1"],
                                      "JetVertexRefiner.MaxPosSingle": ["30."],
                                      "JetVertexRefiner.MaxSeparationPerPosSingle": ["0.1"],
                                      "JetVertexRefiner.MinEnergySingle": ["1."],
                                      "JetVertexRefiner.MinPosSingle": ["0.3"],
                                      "JetVertexRefiner.OneVertexProbThreshold": ["0.001"],
                                      "JetVertexRefiner.OutputJetCollectionName": ["RefinedVertexJets"],
                                      "JetVertexRefiner.OutputVertexCollectionName": ["RefinedVertices"],
                                      "JetVertexRefiner.PrimaryVertexCollectionName": ["PrimaryVertices"],
                                      "JetVertexRefiner.V0VertexCollectionName": ["BuildUpVertices_V0"],
                                      "JetVertexRefiner.mind0sigSingle": ["5."],
                                      "JetVertexRefiner.minz0sigSingle": ["5."],
                                      "JetVertexRefiner.useBNess": ["0"],
                                      "MCPCollection": ["MCParticle"],
                                      "MCPFORelation": ["RecoMCTruthLink"],
                                      "MagneticField": ["2.0"],
                                      "PFOCollection": ["PFOsFromJets"],
                                      "PrintEventNumber": ["1"],
                                      "ReadSubdetectorEnergies": ["0"],
                                      "TrackHitOrdering": ["2"],
                                      "UpdateVertexRPDaughters": ["0"],
                                      "UseMCP": ["0"]
                                      }

MyDDCaloDigiParameters = {
                                "Histograms": ["0"],
                                "RootFile": ["Digi_SiW.root"],
                                "RelationOutputCollection": ["RelationCaloHit"],
                                "energyPerEHpair": ["3.6"],
                                # ECAL
                                "ECALCollections": ["ECalBarrelCollection", "ECalEndcapCollection"],
                                "ECALOutputCollection0": ["ECALBarrel"],
                                "ECALOutputCollection1": ["ECALEndcap"],
                                "ECALOutputCollection2": [""],
                                "IfDigitalEcal": ["0"],
                                "ECALLayers": ["41", "100"],
                                "ECAL_default_layerConfig": ["000000000000000"],
                                "StripEcal_default_nVirtualCells": ["9"],
                                "CalibECALMIP": ["0.0001"],
                                "ECALThreshold": ["5e-05"],
                                "ECALThresholdUnit": ["GeV"],
                                "ECALGapCorrection": ["1"],
                                "ECALGapCorrectionFactor": ["1"],
                                "ECALModuleGapCorrectionFactor": ["0.0"],
                                "MapsEcalCorrection": ["0"],
                                "ECAL_PPD_N_Pixels": ["10000"],
                                "ECAL_PPD_N_Pixels_uncertainty": ["0.05"],
                                "ECAL_PPD_PE_per_MIP": ["7"],
                                "ECAL_apply_realistic_digi": ["0"],
                                "ECAL_deadCellRate": ["0"],
                                "ECAL_deadCell_memorise": ["false"],
                                "ECAL_elec_noise_mips": ["0"],
                                "ECAL_maxDynamicRange_MIP": ["2500"],
                                "ECAL_miscalibration_correl": ["0"],
                                "ECAL_miscalibration_uncorrel": ["0"],
                                "ECAL_miscalibration_uncorrel_memorise": ["false"],
                                "ECAL_pixel_spread": ["0.05"],
                                "ECAL_strip_absorbtionLength": ["1e+06"],
                                "UseEcalTiming": ["1"],
                                "ECALCorrectTimesForPropagation": ["1"],
                                "ECALTimeWindowMin": ["-1"],
                                "ECALSimpleTimingCut": ["true"],
                                "ECALDeltaTimeHitResolution": ["10"],
                                "ECALTimeResolution": ["10"],
                                # HCAL
                                "HCALCollections": ["HCalBarrelCollection", "HCalEndcapCollection", "HCalRingCollection"],
                                "HCALOutputCollection0": ["HCALBarrel"],
                                "HCALOutputCollection1": ["HCALEndcap"],
                                "HCALOutputCollection2": ["HCALOther"],
                                "IfDigitalHcal": ["0"],
                                "HCALLayers": ["100"],
                                "CalibHCALMIP": ["0.0001"],
                                "HCALThreshold": ["0.00025"],
                                "HCALThresholdUnit": ["GeV"],
                                "HCALEndcapCorrectionFactor": ["1.000"],
                                "HCALGapCorrection": ["1"],
                                "HCALModuleGapCorrectionFactor": ["0.5"],
                                "HCAL_PPD_N_Pixels": ["400"],
                                "HCAL_PPD_N_Pixels_uncertainty": ["0.05"],
                                "HCAL_PPD_PE_per_MIP": ["10"],
                                "HCAL_apply_realistic_digi": ["0"],
                                "HCAL_deadCellRate": ["0"],
                                "HCAL_deadCell_memorise": ["false"],
                                "HCAL_elec_noise_mips": ["0"],
                                "HCAL_maxDynamicRange_MIP": ["200"],
                                "HCAL_miscalibration_correl": ["0"],
                                "HCAL_miscalibration_uncorrel": ["0"],
                                "HCAL_miscalibration_uncorrel_memorise": ["false"],
                                "HCAL_pixel_spread": ["0"],
                                "UseHcalTiming": ["1"],
                                "HCALCorrectTimesForPropagation": ["1"],
                                "HCALTimeWindowMin": ["-1"],
                                "HCALSimpleTimingCut": ["true"],
                                "HCALDeltaTimeHitResolution": ["10"],
                                "HCALTimeResolution": ["10"],
}

MyDDCaloDigi = {}

MyDDCaloDigi["10ns"] = MarlinProcessorWrapper("MyDDCaloDigi_10ns")
MyDDCaloDigi["10ns"].OutputLevel = WARNING
MyDDCaloDigi["10ns"].ProcessorType = "DDCaloDigi"
MyDDCaloDigi["10ns"].Parameters = MyDDCaloDigiParameters.copy()
MyDDCaloDigi["10ns"].Parameters |= {
                                "CalibrECAL": ["37.5227197175", "37.5227197175"],
                                "ECALEndcapCorrectionFactor": ["1.03245503522"],
                                "ECALBarrelTimeWindowMax": ["10"],
                                "ECALEndcapTimeWindowMax": ["10"],
                                "CalibrHCALBarrel": ["45.9956826061"],
                                "CalibrHCALEndcap": ["46.9252540291"],
                                "CalibrHCALOther": ["57.4588011802"],
                                "HCALBarrelTimeWindowMax": ["10"],
                                "HCALEndcapTimeWindowMax": ["10"],
                                }

MyDDCaloDigi["400ns"] = MarlinProcessorWrapper("MyDDCaloDigi_400ns")
MyDDCaloDigi["400ns"].OutputLevel = WARNING
MyDDCaloDigi["400ns"].ProcessorType = "DDCaloDigi"
MyDDCaloDigi["400ns"].Parameters = MyDDCaloDigiParameters.copy()
MyDDCaloDigi["400ns"].Parameters |= {
                                 "CalibrECAL": ["37.4591745147", "37.4591745147"],
                                 "ECALEndcapCorrectionFactor": ["1.01463983425"],
                                 "ECALBarrelTimeWindowMax": ["400"],
                                 "ECALEndcapTimeWindowMax": ["400"],
                                 "CalibrHCALBarrel": ["42.544403752"],
                                 "CalibrHCALEndcap": ["42.9667604345"],
                                 "CalibrHCALOther": ["51.3503963688"],
                                 "HCALBarrelTimeWindowMax": ["400"],
                                 "HCALEndcapTimeWindowMax": ["400"],
                                 }

MyDDMarlinPandoraParameters = {
                                     "FinalEnergyDensityBin": ["110."],
                                     "MaxClusterEnergyToApplySoftComp": ["200."],
                                     "TrackCollections": ["SiTracks_Refitted"],
                                     "ECalCaloHitCollections": ["ECALBarrel", "ECALEndcap"],
                                     "HCalCaloHitCollections": ["HCALBarrel", "HCALEndcap", "HCALOther"],
                                     "LCalCaloHitCollections": [],
                                     "LHCalCaloHitCollections": [],
                                     "MuonCaloHitCollections": ["MUON"],
                                     "MCParticleCollections": ["MCParticle"],
                                     "RelCaloHitCollections": ["RelationCaloHit", "RelationMuonHit"],
                                     "RelTrackCollections": ["SiTracks_Refitted_Relation"],
                                     "KinkVertexCollections": ["KinkVertices"],
                                     "ProngVertexCollections": ["ProngVertices"],
                                     "SplitVertexCollections": ["SplitVertices"],
                                     "V0VertexCollections": ["V0Vertices"],
                                     "ClusterCollectionName": ["PandoraClusters"],
                                     "PFOCollectionName": ["PandoraPFOs"],
                                     "UseOldTrackStateCalculation": ["0"],
                                     "NEventsToSkip": ["0"],
                                     "CreateGaps": ["false"],
                                     "MinBarrelTrackerHitFractionOfExpected": ["0"],
                                     "MinFtdHitsForBarrelTrackerHitFraction": ["0"],
                                     "MinFtdTrackHits": ["0"],
                                     "MinMomentumForTrackHitChecks": ["0"],
                                     "MinTpcHitFractionOfExpected": ["0"],
                                     "MinTrackECalDistanceFromIp": ["0"],
                                     "MinTrackHits": ["0"],
                                     "ReachesECalBarrelTrackerOuterDistance": ["-100"],
                                     "ReachesECalBarrelTrackerZMaxDistance": ["-50"],
                                     "ReachesECalFtdZMaxDistance": ["1"],
                                     "ReachesECalMinFtdLayer": ["0"],
                                     "ReachesECalNBarrelTrackerHits": ["0"],
                                     "ReachesECalNFtdHits": ["0"],
                                     "UnmatchedVertexTrackMaxEnergy": ["5"],
                                     "UseNonVertexTracks": ["1"],
                                     "UseUnmatchedNonVertexTracks": ["0"],
                                     "UseUnmatchedVertexTracks": ["1"],
                                     "Z0TrackCut": ["200"],
                                     "Z0UnmatchedVertexTrackCut": ["5"],
                                     "ZCutForNonVertexTracks": ["250"],
                                     "MaxTrackHits": ["5000"],
                                     "MaxTrackSigmaPOverP": ["0.15"],
                                     "CurvatureToMomentumFactor": ["0.00015"],
                                     "D0TrackCut": ["200"],
                                     "D0UnmatchedVertexTrackCut": ["5"],
                                     "StartVertexAlgorithmName": ["PandoraPFANew"],
                                     "StartVertexCollectionName": ["PandoraStartVertices"],
                                     "YokeBarrelNormalVector": ["0", "0", "1"],
                                     "HCalBarrelNormalVector": ["0", "0", "1"],
                                     "ECalBarrelNormalVector": ["0", "0", "1"],
                                     "MuonBarrelBField": ["-1.0"],
                                     "MuonEndCapBField": ["0.01"],
                                     "EMConstantTerm": ["0.01"],
                                     "EMStochasticTerm": ["0.17"],
                                     "HadConstantTerm": ["0.03"],
                                     "HadStochasticTerm": ["0.6"],
                                     "InputEnergyCorrectionPoints": [],
                                     "LayersFromEdgeMaxRearDistance": ["250"],
                                     "NOuterSamplingLayers": ["3"],
                                     "TrackStateTolerance": ["0"],
                                     "MaxBarrelTrackerInnerRDistance": ["200"],
                                     "MinCleanCorrectedHitEnergy": ["0.1"],
                                     "MinCleanHitEnergy": ["0.5"],
                                     "MinCleanHitEnergyFraction": ["0.01"],
                                     "MuonHitEnergy": ["0.5"],
                                     "ShouldFormTrackRelationships": ["1"],
                                     "TrackCreatorName": ["DDTrackCreatorCLIC"],
                                     "TrackSystemName": ["DDKalTest"],
                                     "OutputEnergyCorrectionPoints": [],
                                     "UseEcalScLayers": ["0"],
                                     "ECalScMipThreshold": ["0"],
                                     "ECalScToEMGeVCalibration": ["1"],
                                     "ECalScToHadGeVCalibrationBarrel": ["1"],
                                     "ECalScToHadGeVCalibrationEndCap": ["1"],
                                     "ECalScToMipCalibration": ["1"],
                                     "ECalSiMipThreshold": ["0"],
                                     "ECalSiToEMGeVCalibration": ["1"],
                                     "ECalSiToHadGeVCalibrationBarrel": ["1"],
                                     "ECalSiToHadGeVCalibrationEndCap": ["1"],
                                     "ECalSiToMipCalibration": ["1"],
                                     "StripSplittingOn": ["0"],
}

MyDDMarlinPandora = {}

MyDDMarlinPandora["10ns"] = MarlinProcessorWrapper("MyDDMarlinPandora_10ns")
MyDDMarlinPandora["10ns"].OutputLevel = WARNING
MyDDMarlinPandora["10ns"].ProcessorType = "DDPandoraPFANewProcessor"
MyDDMarlinPandora["10ns"].Parameters = MyDDMarlinPandoraParameters.copy()
MyDDMarlinPandora["10ns"].Parameters |= {
                                     "PandoraSettingsXmlFile": ["PandoraSettingsCLD/PandoraSettingsDefault.xml"],
                                     "SoftwareCompensationWeights": ["2.40821", "-0.0515852", "0.000711414", "-0.0254891", "-0.0121505", "-1.63084e-05", "0.062149", "0.0690735", "-0.223064"],
                                     "ECalToMipCalibration": ["175.439"],
                                     "HCalToMipCalibration": ["45.6621"],
                                     "ECalMipThreshold": ["0.5"],
                                     "HCalMipThreshold": ["0.3"],
                                     "ECalToEMGeVCalibration": ["1.01776966108"],
                                     "HCalToEMGeVCalibration": ["1.01776966108"],
                                     "ECalToHadGeVCalibrationBarrel": ["1.11490774181"],
                                     "ECalToHadGeVCalibrationEndCap": ["1.11490774181"],
                                     "HCalToHadGeVCalibration": ["1.00565042407"],
                                     "MuonToMipCalibration": ["20703.9"],
                                     "DigitalMuonHits": ["0"],
                                     "MaxHCalHitHadronicEnergy": ["10000000."],
                                     }

MyDDMarlinPandora["400ns"] = MarlinProcessorWrapper("MyDDMarlinPandora_400ns")
MyDDMarlinPandora["400ns"].OutputLevel = WARNING
MyDDMarlinPandora["400ns"].ProcessorType = "DDPandoraPFANewProcessor"
MyDDMarlinPandora["400ns"].Parameters = MyDDMarlinPandoraParameters.copy()
MyDDMarlinPandora["400ns"].Parameters |= {
                                      "PandoraSettingsXmlFile": ["PandoraSettingsCLD/PandoraSettingsDefault_400nsCalTimeWindow.xml"],
                                      "SoftwareCompensationWeights": ["2.43375", "-0.0430951", "0.000244914", "-0.145478", "-0.00044577", "-8.37222e-05", "0.237484", "0.243491", "-0.0713701"],
                                      "ECalToMipCalibration": ["175.439"],
                                      "HCalToMipCalibration": ["49.7512"],
                                      "ECalMipThreshold": ["0.5"],
                                      "HCalMipThreshold": ["0.3"],
                                      "ECalToEMGeVCalibration": ["1.02513816926"],
                                      "HCalToEMGeVCalibration": ["1.02513816926"],
                                      "ECalToHadGeVCalibrationBarrel": ["1.07276660331"],
                                      "ECalToHadGeVCalibrationEndCap": ["1.07276660331"],
                                      "HCalToHadGeVCalibration": ["1.01147686143"],
                                      "MuonToMipCalibration": ["20703.9"],
                                      "DigitalMuonHits": ["0"],
                                      "MaxHCalHitHadronicEnergy": ["10000000."],
                                      }

MyCLICPfoSelectorDefault = MarlinProcessorWrapper("MyCLICPfoSelectorDefault")
MyCLICPfoSelectorDefault.OutputLevel = WARNING
MyCLICPfoSelectorDefault.ProcessorType = "CLICPfoSelector"
MyCLICPfoSelectorDefault.Parameters = {
                                       "ChargedPfoLooseTimingCut": ["3"],
                                       "ChargedPfoNegativeLooseTimingCut": ["-1"],
                                       "ChargedPfoNegativeTightTimingCut": ["-0.5"],
                                       "ChargedPfoPtCut": ["0"],
                                       "ChargedPfoPtCutForLooseTiming": ["4"],
                                       "ChargedPfoTightTimingCut": ["1.5"],
                                       "CheckKaonCorrection": ["0"],
                                       "CheckProtonCorrection": ["0"],
                                       "ClusterLessPfoTrackTimeCut": ["10"],
                                       "CorrectHitTimesForTimeOfFlight": ["0"],
                                       "DisplayRejectedPfos": ["1"],
                                       "DisplaySelectedPfos": ["1"],
                                       "FarForwardCosTheta": ["0.975"],
                                       "ForwardCosThetaForHighEnergyNeutralHadrons": ["0.95"],
                                       "ForwardHighEnergyNeutralHadronsEnergy": ["10"],
                                       "HCalBarrelLooseTimingCut": ["20"],
                                       "HCalBarrelTightTimingCut": ["10"],
                                       "HCalEndCapTimingFactor": ["1"],
                                       "InputPfoCollection": ["PandoraPFOs"],
                                       "KeepKShorts": ["1"],
                                       "MaxMomentumForClusterLessPfos": ["2"],
                                       "MinECalHitsForTiming": ["5"],
                                       "MinHCalEndCapHitsForTiming": ["5"],
                                       "MinMomentumForClusterLessPfos": ["0.5"],
                                       "MinPtForClusterLessPfos": ["0.5"],
                                       "MinimumEnergyForNeutronTiming": ["1"],
                                       "Monitoring": ["0"],
                                       "MonitoringPfoEnergyToDisplay": ["1"],
                                       "NeutralFarForwardLooseTimingCut": ["2"],
                                       "NeutralFarForwardTightTimingCut": ["1"],
                                       "NeutralHadronBarrelPtCutForLooseTiming": ["3.5"],
                                       "NeutralHadronLooseTimingCut": ["2.5"],
                                       "NeutralHadronPtCut": ["0"],
                                       "NeutralHadronPtCutForLooseTiming": ["8"],
                                       "NeutralHadronTightTimingCut": ["1.5"],
                                       "PhotonFarForwardLooseTimingCut": ["2"],
                                       "PhotonFarForwardTightTimingCut": ["1"],
                                       "PhotonLooseTimingCut": ["2"],
                                       "PhotonPtCut": ["0"],
                                       "PhotonPtCutForLooseTiming": ["4"],
                                       "PhotonTightTimingCut": ["1"],
                                       "PtCutForTightTiming": ["0.75"],
                                       "SelectedPfoCollection": ["SelectedPandoraPFOs"],
                                       "UseClusterLessPfos": ["1"],
                                       "UseNeutronTiming": ["0"]
                                       }

MyCLICPfoSelectorLoose = MarlinProcessorWrapper("MyCLICPfoSelectorLoose")
MyCLICPfoSelectorLoose.OutputLevel = WARNING
MyCLICPfoSelectorLoose.ProcessorType = "CLICPfoSelector"
MyCLICPfoSelectorLoose.Parameters = {
                                     "ChargedPfoLooseTimingCut": ["3"],
                                     "ChargedPfoNegativeLooseTimingCut": ["-2.0"],
                                     "ChargedPfoNegativeTightTimingCut": ["-2.0"],
                                     "ChargedPfoPtCut": ["0"],
                                     "ChargedPfoPtCutForLooseTiming": ["4"],
                                     "ChargedPfoTightTimingCut": ["1.5"],
                                     "CheckKaonCorrection": ["0"],
                                     "CheckProtonCorrection": ["0"],
                                     "ClusterLessPfoTrackTimeCut": ["1000."],
                                     "CorrectHitTimesForTimeOfFlight": ["0"],
                                     "DisplayRejectedPfos": ["1"],
                                     "DisplaySelectedPfos": ["1"],
                                     "FarForwardCosTheta": ["0.975"],
                                     "ForwardCosThetaForHighEnergyNeutralHadrons": ["0.95"],
                                     "ForwardHighEnergyNeutralHadronsEnergy": ["10"],
                                     "HCalBarrelLooseTimingCut": ["20"],
                                     "HCalBarrelTightTimingCut": ["10"],
                                     "HCalEndCapTimingFactor": ["1"],
                                     "InputPfoCollection": ["PandoraPFOs"],
                                     "KeepKShorts": ["1"],
                                     "MaxMomentumForClusterLessPfos": ["2"],
                                     "MinECalHitsForTiming": ["5"],
                                     "MinHCalEndCapHitsForTiming": ["5"],
                                     "MinMomentumForClusterLessPfos": ["0.0"],
                                     "MinPtForClusterLessPfos": ["0.25"],
                                     "MinimumEnergyForNeutronTiming": ["1"],
                                     "Monitoring": ["0"],
                                     "MonitoringPfoEnergyToDisplay": ["1"],
                                     "NeutralFarForwardLooseTimingCut": ["2.5"],
                                     "NeutralFarForwardTightTimingCut": ["1.5"],
                                     "NeutralHadronBarrelPtCutForLooseTiming": ["3.5"],
                                     "NeutralHadronLooseTimingCut": ["2.5"],
                                     "NeutralHadronPtCut": ["0"],
                                     "NeutralHadronPtCutForLooseTiming": ["8"],
                                     "NeutralHadronTightTimingCut": ["1.5"],
                                     "PhotonFarForwardLooseTimingCut": ["2"],
                                     "PhotonFarForwardTightTimingCut": ["1"],
                                     "PhotonLooseTimingCut": ["2."],
                                     "PhotonPtCut": ["0"],
                                     "PhotonPtCutForLooseTiming": ["4"],
                                     "PhotonTightTimingCut": ["2."],
                                     "PtCutForTightTiming": ["0.75"],
                                     "SelectedPfoCollection": ["LooseSelectedPandoraPFOs"],
                                     "UseClusterLessPfos": ["1"],
                                     "UseNeutronTiming": ["0"]
                                     }

MyCLICPfoSelectorTight = MarlinProcessorWrapper("MyCLICPfoSelectorTight")
MyCLICPfoSelectorTight.OutputLevel = WARNING
MyCLICPfoSelectorTight.ProcessorType = "CLICPfoSelector"
MyCLICPfoSelectorTight.Parameters = {
                                     "ChargedPfoLooseTimingCut": ["2.0"],
                                     "ChargedPfoNegativeLooseTimingCut": ["-0.5"],
                                     "ChargedPfoNegativeTightTimingCut": ["-0.25"],
                                     "ChargedPfoPtCut": ["0"],
                                     "ChargedPfoPtCutForLooseTiming": ["4"],
                                     "ChargedPfoTightTimingCut": ["1.0"],
                                     "CheckKaonCorrection": ["0"],
                                     "CheckProtonCorrection": ["0"],
                                     "ClusterLessPfoTrackTimeCut": ["10"],
                                     "CorrectHitTimesForTimeOfFlight": ["0"],
                                     "DisplayRejectedPfos": ["1"],
                                     "DisplaySelectedPfos": ["1"],
                                     "FarForwardCosTheta": ["0.95"],
                                     "ForwardCosThetaForHighEnergyNeutralHadrons": ["0.95"],
                                     "ForwardHighEnergyNeutralHadronsEnergy": ["10"],
                                     "HCalBarrelLooseTimingCut": ["20"],
                                     "HCalBarrelTightTimingCut": ["10"],
                                     "HCalEndCapTimingFactor": ["1"],
                                     "InputPfoCollection": ["PandoraPFOs"],
                                     "KeepKShorts": ["1"],
                                     "MaxMomentumForClusterLessPfos": ["1.5"],
                                     "MinECalHitsForTiming": ["5"],
                                     "MinHCalEndCapHitsForTiming": ["5"],
                                     "MinMomentumForClusterLessPfos": ["0.5"],
                                     "MinPtForClusterLessPfos": ["1.0"],
                                     "MinimumEnergyForNeutronTiming": ["1"],
                                     "Monitoring": ["0"],
                                     "MonitoringPfoEnergyToDisplay": ["1"],
                                     "NeutralFarForwardLooseTimingCut": ["1.5"],
                                     "NeutralFarForwardTightTimingCut": ["1"],
                                     "NeutralHadronBarrelPtCutForLooseTiming": ["3.5"],
                                     "NeutralHadronLooseTimingCut": ["2.5"],
                                     "NeutralHadronPtCut": ["0.5"],
                                     "NeutralHadronPtCutForLooseTiming": ["8"],
                                     "NeutralHadronTightTimingCut": ["1.5"],
                                     "PhotonFarForwardLooseTimingCut": ["2"],
                                     "PhotonFarForwardTightTimingCut": ["1"],
                                     "PhotonLooseTimingCut": ["2"],
                                     "PhotonPtCut": ["0.2"],
                                     "PhotonPtCutForLooseTiming": ["4"],
                                     "PhotonTightTimingCut": ["1"],
                                     "PtCutForTightTiming": ["1.0"],
                                     "SelectedPfoCollection": ["TightSelectedPandoraPFOs"],
                                     "UseClusterLessPfos": ["0"],
                                     "UseNeutronTiming": ["0"]
                                     }

VertexFinder = MarlinProcessorWrapper("VertexFinder")
VertexFinder.OutputLevel = WARNING
VertexFinder.ProcessorType = "LcfiplusProcessor"
VertexFinder.Parameters = {
                           "Algorithms": ["PrimaryVertexFinder", "BuildUpVertex"],
                           "BeamSizeX": ["38.2E-3"],
                           "BeamSizeY": ["68E-6"],
                           "BeamSizeZ": ["1.97"],
                           "BuildUpVertex.AVFTemperature": ["5.0"],
                           "BuildUpVertex.AssocIPTracks": ["1"],
                           "BuildUpVertex.AssocIPTracksChi2RatioSecToPri": ["2.0"],
                           "BuildUpVertex.AssocIPTracksMinDist": ["0."],
                           "BuildUpVertex.MassThreshold": ["10."],
                           "BuildUpVertex.MaxChi2ForDistOrder": ["1.0"],
                           "BuildUpVertex.MinDistFromIP": ["0.3"],
                           "BuildUpVertex.PrimaryChi2Threshold": ["25."],
                           "BuildUpVertex.SecondaryChi2Threshold": ["9."],
                           "BuildUpVertex.TrackMaxD0": ["10."],
                           "BuildUpVertex.TrackMaxD0Err": ["0.1"],
                           "BuildUpVertex.TrackMaxZ0": ["20."],
                           "BuildUpVertex.TrackMaxZ0Err": ["0.1"],
                           "BuildUpVertex.TrackMinFtdHits": ["1"],
                           "BuildUpVertex.TrackMinPt": ["0.1"],
                           "BuildUpVertex.TrackMinTpcHits": ["1"],
                           "BuildUpVertex.TrackMinTpcHitsMinPt": ["999999"],
                           "BuildUpVertex.TrackMinVxdFtdHits": ["1"],
                           "BuildUpVertex.TrackMinVxdHits": ["1"],
                           "BuildUpVertex.UseAVF": ["false"],
                           "BuildUpVertex.UseV0Selection": ["1"],
                           "BuildUpVertex.V0VertexCollectionName": ["BuildUpVertices_V0"],
                           "BuildUpVertexCollectionName": ["BuildUpVertices"],
                           "MCPCollection": ["MCParticle"],
                           "MCPFORelation": ["RecoMCTruthLink"],
                           "MagneticField": ["2.0"],
                           "PFOCollection": ["PFOsFromJets"],
                           "PrimaryVertexCollectionName": ["PrimaryVertices"],
                           "PrimaryVertexFinder.BeamspotConstraint": ["1"],
                           "PrimaryVertexFinder.BeamspotSmearing": ["false"],
                           "PrimaryVertexFinder.Chi2Threshold": ["25."],
                           "PrimaryVertexFinder.TrackMaxD0": ["20."],
                           "PrimaryVertexFinder.TrackMaxInnermostHitRadius": ["61"],
                           "PrimaryVertexFinder.TrackMaxZ0": ["20."],
                           "PrimaryVertexFinder.TrackMinFtdHits": ["999999"],
                           "PrimaryVertexFinder.TrackMinTpcHits": ["999999"],
                           "PrimaryVertexFinder.TrackMinTpcHitsMinPt": ["999999"],
                           "PrimaryVertexFinder.TrackMinVtxFtdHits": ["1"],
                           "PrimaryVertexFinder.TrackMinVxdHits": ["999999"],
                           "PrintEventNumber": ["1"],
                           "ReadSubdetectorEnergies": ["0"],
                           "TrackHitOrdering": ["2"],
                           "UpdateVertexRPDaughters": ["0"],
                           "UseMCP": ["0"]
                           }

VertexFinderUnconstrained = MarlinProcessorWrapper("VertexFinderUnconstrained")
VertexFinderUnconstrained.OutputLevel = WARNING
VertexFinderUnconstrained.ProcessorType = "LcfiplusProcessor"
VertexFinderUnconstrained.Parameters = {
                                        "Algorithms": ["PrimaryVertexFinder", "BuildUpVertex"],
                                        "BeamSizeX": ["38.2E-3"],
                                        "BeamSizeY": ["68E-6"],
                                        "BeamSizeZ": ["1.97"],
                                        "BuildUpVertex.AVFTemperature": ["5.0"],
                                        "BuildUpVertex.AssocIPTracks": ["1"],
                                        "BuildUpVertex.AssocIPTracksChi2RatioSecToPri": ["2.0"],
                                        "BuildUpVertex.AssocIPTracksMinDist": ["0."],
                                        "BuildUpVertex.MassThreshold": ["10."],
                                        "BuildUpVertex.MaxChi2ForDistOrder": ["1.0"],
                                        "BuildUpVertex.MinDistFromIP": ["0.3"],
                                        "BuildUpVertex.PrimaryChi2Threshold": ["25."],
                                        "BuildUpVertex.SecondaryChi2Threshold": ["9."],
                                        "BuildUpVertex.TrackMaxD0": ["10."],
                                        "BuildUpVertex.TrackMaxD0Err": ["0.1"],
                                        "BuildUpVertex.TrackMaxZ0": ["20."],
                                        "BuildUpVertex.TrackMaxZ0Err": ["0.1"],
                                        "BuildUpVertex.TrackMinFtdHits": ["1"],
                                        "BuildUpVertex.TrackMinPt": ["0.1"],
                                        "BuildUpVertex.TrackMinTpcHits": ["1"],
                                        "BuildUpVertex.TrackMinTpcHitsMinPt": ["999999"],
                                        "BuildUpVertex.TrackMinVxdFtdHits": ["1"],
                                        "BuildUpVertex.TrackMinVxdHits": ["1"],
                                        "BuildUpVertex.UseAVF": ["false"],
                                        "BuildUpVertex.UseV0Selection": ["1"],
                                        "BuildUpVertex.V0VertexCollectionName": ["BuildUpVertices_V0_res"],
                                        "BuildUpVertexCollectionName": ["BuildUpVertices_res"],
                                        "MCPCollection": ["MCParticle"],
                                        "MCPFORelation": ["RecoMCTruthLink"],
                                        "MagneticField": ["2.0"],
                                        "PFOCollection": ["TightSelectedPandoraPFOs"],
                                        "PrimaryVertexCollectionName": ["PrimaryVertices_res"],
                                        "PrimaryVertexFinder.BeamspotConstraint": ["0"],
                                        "PrimaryVertexFinder.BeamspotSmearing": ["false"],
                                        "PrimaryVertexFinder.Chi2Threshold": ["25."],
                                        "PrimaryVertexFinder.TrackMaxD0": ["20."],
                                        "PrimaryVertexFinder.TrackMaxInnermostHitRadius": ["61"],
                                        "PrimaryVertexFinder.TrackMaxZ0": ["20."],
                                        "PrimaryVertexFinder.TrackMinFtdHits": ["999999"],
                                        "PrimaryVertexFinder.TrackMinTpcHits": ["999999"],
                                        "PrimaryVertexFinder.TrackMinTpcHitsMinPt": ["999999"],
                                        "PrimaryVertexFinder.TrackMinVtxFtdHits": ["1"],
                                        "PrimaryVertexFinder.TrackMinVxdHits": ["999999"],
                                        "PrintEventNumber": ["1"],
                                        "ReadSubdetectorEnergies": ["0"],
                                        "TrackHitOrdering": ["2"],
                                        "UpdateVertexRPDaughters": ["0"],
                                        "UseMCP": ["0"]
                                        }

EventNumber = MarlinProcessorWrapper("EventNumber")
EventNumber.OutputLevel = WARNING
EventNumber.ProcessorType = "Statusmonitor"
EventNumber.Parameters = {
                          "HowOften": ["1"]
                          }

# TODO: put this somewhere else, needs to be in front of the output for now :(
# setup AIDA histogramming and add eventual background overlay
algList.append(MyAIDAProcessor)
algList.append(Overlay[CONFIG["Overlay"]])
# tracker hit digitisation
sequenceLoader.load("Tracking/TrackingDigi")

# tracking
if CONFIG["Tracking"] == "Truth":
    algList.append(MyTruthTrackFinder)
elif CONFIG["Tracking"] == "Conformal":
    sequenceLoader.load("Tracking/ConformalTracking")

algList.append(Refit)

# calorimeter digitization and pandora
if not reco_args.trackingOnly:
    algList.append(MyDDCaloDigi[CONFIG["CalorimeterIntegrationTimeWindow"]])
    algList.append(MyDDSimpleMuonDigi)
    algList.append(MyDDMarlinPandora[CONFIG["CalorimeterIntegrationTimeWindow"]])
    algList.append(LumiCalReco)
# monitoring and Reco to MCTruth linking
algList.append(MyClicEfficiencyCalculator)
algList.append(MyRecoMCTruthLinker)
algList.append(MyTrackChecker)
# pfo selector (might need re-optimisation)
if not reco_args.trackingOnly:
    algList.append(MyCLICPfoSelectorDefault)
    algList.append(MyCLICPfoSelectorLoose)
    algList.append(MyCLICPfoSelectorTight)
# misc.
    if CONFIG["Overlay"] == "False":
        algList.append(RenameCollection)
    else:
        algList.append(MyFastJetProcessor)

    algList.append(VertexFinder)
    algList.append(JetClusteringAndRefiner)
    if CONFIG["VertexUnconstrained"] == "True":
        algList.append(VertexFinderUnconstrained)
# event number processor, down here to attach the conversion back to edm4hep to it
algList.append(EventNumber)

if CONFIG["OutputMode"] == "LCIO":
    Output_REC = MarlinProcessorWrapper("Output_REC")
    Output_REC.OutputLevel = WARNING
    Output_REC.ProcessorType = "LCIOOutputProcessor"
    Output_REC.Parameters = {
                             "DropCollectionNames": [],
                             "DropCollectionTypes": [],
                             "FullSubsetCollections": ["EfficientMCParticles", "InefficientMCParticles"],
                             "KeepCollectionNames": [],
                             "LCIOOutputFile": [f"{reco_args.outputBasename}_REC.slcio"],
                             "LCIOWriteMode": ["WRITE_NEW"]
                             }

    Output_DST = MarlinProcessorWrapper("Output_DST")
    Output_DST.OutputLevel = WARNING
    Output_DST.ProcessorType = "LCIOOutputProcessor"
    Output_DST.Parameters = {
                             "DropCollectionNames": [],
                             "DropCollectionTypes": ["MCParticle", "LCRelation", "SimCalorimeterHit", "CalorimeterHit", "SimTrackerHit", "TrackerHit", "TrackerHitPlane", "Track", "ReconstructedParticle", "LCFloatVec"],
                             "FullSubsetCollections": ["EfficientMCParticles", "InefficientMCParticles", "MCPhysicsParticles"],
                             "KeepCollectionNames": ["MCParticlesSkimmed", "MCPhysicsParticles", "RecoMCTruthLink", "SiTracks", "SiTracks_Refitted", "PandoraClusters", "PandoraPFOs", "SelectedPandoraPFOs", "LooseSelectedPandoraPFOs", "TightSelectedPandoraPFOs", "RefinedVertexJets", "RefinedVertexJets_rel", "RefinedVertexJets_vtx", "RefinedVertexJets_vtx_RP", "BuildUpVertices", "BuildUpVertices_res", "BuildUpVertices_RP", "BuildUpVertices_res_RP", "BuildUpVertices_V0", "BuildUpVertices_V0_res", "BuildUpVertices_V0_RP", "BuildUpVertices_V0_res_RP", "PrimaryVertices", "PrimaryVertices_res", "PrimaryVertices_RP", "PrimaryVertices_res_RP", "RefinedVertices", "RefinedVertices_RP"],
                             "LCIOOutputFile": [f"{reco_args.outputBasename}_DST.slcio"],
                             "LCIOWriteMode": ["WRITE_NEW"]
                             }
    algList.append(Output_REC)
    algList.append(Output_DST)

if CONFIG["OutputMode"] == "EDM4Hep":
    from Configurables import Lcio2EDM4hepTool
    lcioConvTool = Lcio2EDM4hepTool("lcio2EDM4hep")
    lcioConvTool.convertAll = True
    lcioConvTool.collNameMapping = {
        "MCParticle": "MCParticles"
    }
    lcioConvTool.OutputLevel = DEBUG
# attach to the last non output processor
    EventNumber.Lcio2EDM4hepTool = lcioConvTool

    from Configurables import PodioOutput
    out = PodioOutput("PodioOutput", filename = f"{reco_args.outputBasename}_edm4hep.root")
    out.outputCommands = ["keep *"]
    algList.append(out)

# We need to convert the inputs in case we have EDM4hep input
attach_edm4hep2lcio_conversion(algList, read)

from Configurables import ApplicationMgr
ApplicationMgr( TopAlg = algList,
                EvtSel = 'NONE',
                EvtMax = 3, # Overridden by the --num-events switch to k4run
                ExtSvc = svcList,
                OutputLevel=WARNING
              )

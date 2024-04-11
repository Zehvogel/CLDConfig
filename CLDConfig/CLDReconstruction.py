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
    sequenceLoader.load("Tracking/TruthTracking")
elif CONFIG["Tracking"] == "Conformal":
    sequenceLoader.load("Tracking/ConformalTracking")

sequenceLoader.load("Tracking/Refit")

# calorimeter digitization and pandora
if not reco_args.trackingOnly:
    sequenceLoader.load("CaloDigi/CaloDigi")
    sequenceLoader.load("CaloDigi/MuonDigi")
    sequenceLoader.load("ParticleFlow/Pandora")
    sequenceLoader.load("CaloDigi/LumiCal")
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

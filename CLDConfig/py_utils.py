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
from typing import Union, Optional, Dict, Any
import importlib.util
import importlib.abc
from importlib.machinery import SourceFileLoader
from Configurables import PodioOutput, MarlinProcessorWrapper
from typing import Iterable
from Gaudi.Configuration import WARNING


def import_from(
    filename: Union[str, os.PathLike],
    module_name: Optional[str] = None,
    global_vars: Optional[Dict[str, Any]] = None,
) -> Any:
    """Dynamically imports a module from the specified file path.

    This function imports a module from a given filename, with the option to
    specify the module's name and inject global variables into the module before
    it is returned. If `module_name` is not provided, the filename is used as
    the module name after replacing '.' with '_'. Global variables can be passed
    as a dictionary to `global_vars`, which will be injected into the module's
    namespace.

    Args:
        filename (str): The path to the file from which to import the module.
        module_name (Optional[str]): The name to assign to the module. Defaults
            to None, in which case the filename is used as the module name.
        global_vars (Optional[Dict[str, Any]]): A dictionary of global variables
            to inject into the module's namespace. Defaults to None.

    Returns:
        Any: The imported module with the specified modifications.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ImportError: If there is an error during the import process.

    """
    filename = os.path.abspath(filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"No such file: '{filename}'")

    module_name = module_name or os.path.basename(filename).replace(".", "_")
    loader = SourceFileLoader(module_name, filename)
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    if global_vars:
        module.__dict__.update(global_vars)
    loader.exec_module(module)
    return module


class SequenceLoader:
    """A class for loading algorithm sequences onto a list of algorithms

    It dynamically loads algorithms from Python files based on the given
    sequence names. In the import process it will look for a Sequence of
    algorithms which might have configuration constants that depend on some
    global calibration configuration. These constants are provided during the
    import of a sequence, such that the imported python files do not need to
    define all of them.
    """

    def __init__(
        self, alg_list: list, global_vars: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize the SequenceLoader

        This initializes a SequenceLoader with the list of algorithms to which
        dynamically loaded algorithms should be appended to. It optionally takes
        some global calibration constants that should be injected during import
        of the sequence files

        Args:
            alg_list (List): A list to store loaded sequence algorithms.
            global_vars (Optional[Dict[str, Any]]): A dictionary of global
                variables for the sequences. Defaults to None. The keys in this
                dictionary will be the available variables in the imported
                module and the values will be the values of these variables.
        """
        self.alg_list = alg_list
        self.global_vars = global_vars

    def load(self, sequence: str) -> None:
        """Loads a sequence algorithm from a specified Python file and appends
        it to the algorithm list

        The method constructs the filename from the sequence parameter name and
        imports the sequence from the imported module.

        Args:
            sequence (str): The name of the sequence to load. The sequence name
                should correspond to a Python file and class name following the
                pattern `{sequence}.py` and `{sequence}Sequence`, respectively.

        Examples:
            >>> alg_list = []
            >>> seq_loader = SequenceLoader(alg_list)
            >>> seq_loader.load("Tracking/TrackingDigi")

            This will import the file `Tracking/TrackingDigi.py` and add the
            sequence of algorithms that is defined in `TrackingDigiSequence` in
            that file to the alg_list
        """
        filename = f"{sequence}.py"
        seq_name = f"{sequence.split('/')[-1]}Sequence"

        seq_module = import_from(
            filename,
            global_vars=self.global_vars,
        )

        seq = getattr(seq_module, seq_name)
        self.alg_list.extend(seq)



def attach_lcio2edm4hep_conversion(algList: list) -> None:
    """Attaches a conversion from lcio to edm4hep at the last MarlinWrapper in algList if necessary
    """
    # need to attach a conversion if there are edm4hep outputs and marlin wrappers
    if not any((isinstance(alg, PodioOutput) for alg in algList)):
        # no edm4hep output -> no conversion :)
        return
    # find last marlin wrapper
    for alg in reversed(algList):
        if isinstance(alg, MarlinProcessorWrapper):
            break

    from Configurables import Lcio2EDM4hepTool
    lcioConvTool = Lcio2EDM4hepTool("lcio2EDM4hep")
    lcioConvTool.convertAll = True
    lcioConvTool.collNameMapping = {
        "MCParticle": "MCParticles"
    }

    alg.Lcio2EDM4hepTool = lcioConvTool



def _create_writer_lcio(writer_name: str, output_name: str, keep_list: Iterable = (), full_subset_list: Iterable = ()):
    # hmpf writer needs a name
    writer = MarlinProcessorWrapper(writer_name)
    writer.OutputLevel = WARNING
    writer.ProcessorType = "LCIOOutputProcessor"

    # convert iterables to "real" lists
    _full_subset_list = list(full_subset_list)
    _keep_list = list(keep_list)

    dropped_types = []
    if _keep_list:
        # drop collections of all types
        dropped_types = ["MCParticle", "LCRelation", "SimCalorimeterHit", "CalorimeterHit", "SimTrackerHit", "TrackerHit", "TrackerHitPlane", "Track", "ReconstructedParticle", "LCFloatVec"]

    writer.Parameters = {
        "DropCollectionNames": [],
        "DropCollectionTypes": dropped_types,
        "FullSubsetCollections": _full_subset_list,
        "KeepCollectionNames": _keep_list,
        "LCIOOutputFile": [f"{output_name}.slcio"],
        "LCIOWriteMode": ["WRITE_NEW"]
    }

    return writer


def _create_writer_edm4hep(writer_name: str, output_name: str, keep_list: Iterable = ()):
    writer = PodioOutput(writer_name, filename = f"{output_name}.edm4hep.root")

    if keep_list:
        writer.outputCommands = ["drop *"] + [f"keep {col}" for col in keep_list]
    else:
        writer.outputCommands = ["keep *"]

    return writer


# FIXME: keep this or just use the two internal functions directly?
def create_writer(format: str, writer_name: str, output_name: str, keep_list: Iterable = (), full_subset_list: Iterable = ()):
    """
    fancy docstring that completely describes this...

    so far the only thing noteworthy:
    In contrast to its name an empty keep_list means keep everything
    """
    if format == "lcio":
        return _create_writer_lcio(writer_name, output_name, keep_list, full_subset_list)
    elif format == "edm4hep":
        return _create_writer_edm4hep(writer_name, output_name, keep_list) # edm4hep has no concept of subsets
    else:
        return None
        # TODO: warn about format being unsupported but without killing --help

#
# Copyright (c) 2014-2023 Key4hep-Project.
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
import subprocess
from decorator import decorator

@decorator
def _CLDConfig(test_fun):
    os.chdir("CLDConfig")
    test_fun()
    os.chdir("..")


@_CLDConfig
def test_lcio_edm4hep():
    command = "k4run --inputFiles=../test.slcio --outputBasename=rec_test CLDReconstruction.py".split()
    detectorModel = os.path.join(os.environ["K4GEO"], "FCCee/CLD/compact/FCCee_o1_v04/FCCee_o1_v04.xml")
    command.extend(["--GeoSvc.detectors", detectorModel])
    res = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    assert res.returncode == 0, res.stdout

# Copyright (c) 2021-2022, NVIDIA CORPORATION. All rights reserved.
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

from typing import TYPE_CHECKING, List

from model_navigator.framework_api.commands.core import Command
from model_navigator.framework_api.commands.data_dump.samples import (
    DumpInputModelData,
    DumpOutputModelData,
    FetchInputModelData,
)
from model_navigator.framework_api.commands.infer_metadata import InferInputMetadata, InferOutputMetadata
from model_navigator.framework_api.commands.load import LoadMetadata, LoadSamples
from model_navigator.framework_api.config import Config
from model_navigator.framework_api.pipelines.pipeline import Pipeline

if TYPE_CHECKING:
    from model_navigator.framework_api.package_descriptor import PackageDescriptor


def preprocessing_builder(config: Config, package_descriptor: "PackageDescriptor") -> Pipeline:

    commands: List[Command] = []
    if config.from_source:
        infer_input = InferInputMetadata()
        fetch_input = FetchInputModelData(requires=(infer_input,))
        infer_output = InferOutputMetadata(requires=(infer_input, fetch_input))
        commands.extend([infer_input, fetch_input, infer_output])
        commands.append(DumpInputModelData(requires=(infer_input, fetch_input)))
        commands.append(DumpOutputModelData(requires=(fetch_input, infer_output)))
    else:
        load_metadata = LoadMetadata()
        load_samples = LoadSamples(requires=(load_metadata,))
        commands.extend([load_metadata, load_samples])

    return Pipeline(name="Preprocessing", commands=commands)

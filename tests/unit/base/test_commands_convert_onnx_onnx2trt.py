# Copyright (c) 2021-2023, NVIDIA CORPORATION. All rights reserved.
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
"""Tests for ConvertONNX2TRT conversion.

Note:
     Those test do not execute the conversion.
     The tests are checking if correct paths are executed on input arguments.
"""
import json
import pathlib
import shutil
import tempfile
from unittest.mock import MagicMock

import numpy as np

from model_navigator import TensorRTPrecision, TensorRTPrecisionMode
from model_navigator.api.config import TensorRTProfile
from model_navigator.commands.base import CommandStatus
from model_navigator.commands.convert.onnx import ConvertONNX2TRT
from model_navigator.commands.execution_context import ExecutionContext
from model_navigator.core.tensor import TensorMetadata, TensorSpec
from model_navigator.core.workspace import Workspace
from tests.utils import get_assets_path


def test_run_execute_conversion_when_model_not_support_batching(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        input_model_path = workspace / "onnx" / "model.onnx"
        input_model_path.parent.mkdir(parents=True)
        input_model_path.touch()

        output_model_path = workspace / "trt-fp16" / "model.plan"
        output_model_path.parent.mkdir(parents=True)

        with mocker.patch.object(ConvertONNX2TRT, "_execute_conversion"), mocker.patch.object(
            ConvertONNX2TRT, "_get_onnx_input_metadata"
        ), mocker.patch("model_navigator.utils.devices.get_available_gpus", return_value=[0]):
            result = ConvertONNX2TRT().run(
                workspace=Workspace(workspace),
                parent_path=input_model_path,
                path=output_model_path,
                input_metadata=TensorMetadata(
                    {"input__1": TensorSpec(name="input__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                output_metadata=TensorMetadata(
                    {"output__1": TensorSpec(name="output__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                batch_dim=None,
                dataloader_trt_profile=TensorRTProfile(),
                precision=TensorRTPrecision.FP16,
                precision_mode=TensorRTPrecisionMode.HIERARCHY,
            )

            assert result is not None
            assert result.status == CommandStatus.OK
            assert ConvertONNX2TRT._execute_conversion.called is True  # pytype: disable=attribute-error


def test_run_execute_conversion_when_trt_profile_provided(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        input_model_path = workspace / "onnx" / "model.onnx"
        input_model_path.parent.mkdir(parents=True)
        input_model_path.touch()

        output_model_path = workspace / "trt-fp16" / "model.plan"
        output_model_path.parent.mkdir(parents=True)

        with mocker.patch.object(ConvertONNX2TRT, "_execute_conversion"), mocker.patch.object(
            ConvertONNX2TRT, "_get_onnx_input_metadata"
        ), mocker.patch("model_navigator.utils.devices.get_available_gpus", return_value=[0]):
            result = ConvertONNX2TRT().run(
                workspace=Workspace(workspace),
                parent_path=input_model_path,
                path=output_model_path,
                input_metadata=TensorMetadata(
                    {"input__1": TensorSpec(name="input__1", shape=(-1, -1), dtype=np.dtype("float32"))}
                ),
                output_metadata=TensorMetadata(
                    {"output__1": TensorSpec(name="output__1", shape=(-1, -1), dtype=np.dtype("float32"))}
                ),
                dataloader_trt_profile=TensorRTProfile().add("input__0", (1, 224), (16, 224), (128, 224)),
                batch_dim=0,
                trt_profile=TensorRTProfile(),
                precision=TensorRTPrecision.FP16,
                precision_mode=TensorRTPrecisionMode.HIERARCHY,
            )

            assert result is not None
            assert result.status == CommandStatus.OK
            assert ConvertONNX2TRT._execute_conversion.called is True  # pytype: disable=attribute-error


def test_run_execute_conversion_when_dataloader_and_device_max_batch_size_is_invalid(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        input_model_path = workspace / "onnx" / "model.onnx"
        input_model_path.parent.mkdir(parents=True)
        input_model_path.touch()

        output_model_path = workspace / "trt-fp16" / "model.plan"
        output_model_path.parent.mkdir(parents=True)

        with mocker.patch.object(ConvertONNX2TRT, "_execute_conversion"), mocker.patch.object(
            ConvertONNX2TRT, "_get_onnx_input_metadata"
        ), mocker.patch("model_navigator.utils.devices.get_available_gpus", return_value=[0]):
            result = ConvertONNX2TRT().run(
                workspace=Workspace(workspace),
                parent_path=input_model_path,
                path=output_model_path,
                input_metadata=TensorMetadata(
                    {"input__1": TensorSpec(name="input__1", shape=(-1, -1), dtype=np.dtype("float32"))}
                ),
                output_metadata=TensorMetadata(
                    {"output__1": TensorSpec(name="output__1", shape=(-1, -1), dtype=np.dtype("float32"))}
                ),
                dataloader_max_batch_size=-1,
                device_max_batch_size=0,
                batch_dim=0,
                dataloader_trt_profile=TensorRTProfile(),
                precision=TensorRTPrecision.FP16,
                precision_mode=TensorRTPrecisionMode.HIERARCHY,
            )

            assert result is not None
            assert result.status == CommandStatus.OK
            assert ConvertONNX2TRT._execute_conversion.called is True  # pytype: disable=attribute-error


def test_run_execute_conversion_with_max_batch_size_search_when_dataloader_max_batch_size_provided(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        input_model_path = workspace / "onnx" / "model.onnx"
        input_model_path.parent.mkdir(parents=True)
        input_model_path.touch()

        output_model_path = workspace / "trt-fp16" / "model.plan"
        output_model_path.parent.mkdir(parents=True)

        with mocker.patch.object(
            ConvertONNX2TRT, "_execute_conversion_with_max_batch_size_search"
        ), mocker.patch.object(ConvertONNX2TRT, "_get_onnx_input_metadata"), mocker.patch(
            "model_navigator.utils.devices.get_available_gpus", return_value=[0]
        ):
            result = ConvertONNX2TRT().run(
                workspace=Workspace(workspace),
                parent_path=input_model_path,
                path=output_model_path,
                input_metadata=TensorMetadata(
                    {"input__1": TensorSpec(name="input__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                output_metadata=TensorMetadata(
                    {"output__1": TensorSpec(name="output__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                batch_dim=0,
                dataloader_max_batch_size=16,
                dataloader_trt_profile=TensorRTProfile(),
                precision=TensorRTPrecision.FP16,
                precision_mode=TensorRTPrecisionMode.HIERARCHY,
            )

            assert result is not None
            assert result.status == CommandStatus.OK
            assert (
                ConvertONNX2TRT._execute_conversion_with_max_batch_size_search.called
                is True  # pytype: disable=attribute-error
            )


def test_run_execute_conversion_with_max_batch_size_search_when_device_max_batch_size_provided(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        input_model_path = workspace / "onnx" / "model.onnx"
        input_model_path.parent.mkdir(parents=True)
        input_model_path.touch()

        output_model_path = workspace / "trt-fp16" / "model.plan"
        output_model_path.parent.mkdir(parents=True)

        with mocker.patch.object(
            ConvertONNX2TRT, "_execute_conversion_with_max_batch_size_search"
        ), mocker.patch.object(ConvertONNX2TRT, "_get_onnx_input_metadata"), mocker.patch(
            "model_navigator.utils.devices.get_available_gpus", return_value=[0]
        ):
            result = ConvertONNX2TRT().run(
                workspace=Workspace(workspace),
                parent_path=input_model_path,
                path=output_model_path,
                input_metadata=TensorMetadata(
                    {"input__1": TensorSpec(name="input__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                output_metadata=TensorMetadata(
                    {"output__1": TensorSpec(name="output__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                batch_dim=0,
                device_max_batch_size=16,
                dataloader_trt_profile=TensorRTProfile(),
                precision=TensorRTPrecision.FP16,
                precision_mode=TensorRTPrecisionMode.HIERARCHY,
            )

            assert result is not None
            assert result.status == CommandStatus.OK
            assert (
                ConvertONNX2TRT._execute_conversion_with_max_batch_size_search.called
                is True  # pytype: disable=attribute-error
            )


def test_run_execute_conversion_with_max_batch_size_search_when_both_max_batch_size_provided(mocker):
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        input_model_path = workspace / "onnx" / "model.onnx"
        input_model_path.parent.mkdir(parents=True)
        input_model_path.touch()

        output_model_path = workspace / "trt-fp16" / "model.plan"
        output_model_path.parent.mkdir(parents=True)

        with mocker.patch.object(
            ConvertONNX2TRT, "_execute_conversion_with_max_batch_size_search"
        ), mocker.patch.object(ConvertONNX2TRT, "_get_onnx_input_metadata"), mocker.patch(
            "model_navigator.utils.devices.get_available_gpus", return_value=[0]
        ):
            result = ConvertONNX2TRT().run(
                workspace=Workspace(workspace),
                parent_path=input_model_path,
                path=output_model_path,
                input_metadata=TensorMetadata(
                    {"input__1": TensorSpec(name="input__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                output_metadata=TensorMetadata(
                    {"output__1": TensorSpec(name="output__1", shape=(-1,), dtype=np.dtype("float32"))}
                ),
                batch_dim=0,
                dataloader_max_batch_size=16,
                device_max_batch_size=32,
                dataloader_trt_profile=TensorRTProfile(),
                precision=TensorRTPrecision.FP16,
                precision_mode=TensorRTPrecisionMode.HIERARCHY,
            )

            assert result is not None
            assert result.status == CommandStatus.OK
            assert (
                ConvertONNX2TRT._execute_conversion_with_max_batch_size_search.called
                is True  # pytype: disable=attribute-error
            )


def test_get_shape_args_return_correct_arguments_when_batch_dim_is_none():
    profile = TensorRTProfile().add(
        "input_1",
        min=(224, 224, 3),
        opt=(224, 224, 3),
        max=(224, 224, 3),
    )
    result = ConvertONNX2TRT._get_shape_args(
        onnx_input_metadata=TensorMetadata(
            {"input_1": TensorSpec(name="input_1", shape=(-1, -1, -1), dtype=np.dtype("float32"))}
        ),
        batch_dim=None,
        trt_profile=profile,
    )
    expected_result = [
        "--trt-min-shapes",
        "input_1:[224,224,3]",
        "--trt-opt-shapes",
        "input_1:[224,224,3]",
        "--trt-max-shapes",
        "input_1:[224,224,3]",
    ]
    assert result == expected_result


def test_get_shape_args_return_correct_arguments_when_max_batch_size_is_zero():
    profile = TensorRTProfile().add(
        "input_1",
        min=(224, 224, 3),
        opt=(224, 224, 3),
        max=(224, 224, 3),
    )
    result = ConvertONNX2TRT._get_shape_args(
        onnx_input_metadata=TensorMetadata(
            {"input_1": TensorSpec(name="input_1", shape=(-1, -1, -1), dtype=np.dtype("float32"))}
        ),
        batch_dim=0,
        max_batch_size=0,
        trt_profile=profile,
    )
    expected_result = [
        "--trt-min-shapes",
        "input_1:[224,224,3]",
        "--trt-opt-shapes",
        "input_1:[224,224,3]",
        "--trt-max-shapes",
        "input_1:[224,224,3]",
    ]
    assert result == expected_result


def test_get_shape_args_return_correct_arguments_when_batch_dim_and_max_batch_size_provided():
    profile = TensorRTProfile()
    profile.add(
        "input_1",
        min=(1, 224, 224, 3),
        opt=(64, 224, 224, 3),
        max=(256, 224, 224, 3),
    )
    profile.add(
        "input_2",
        min=(1, 1),
        opt=(64, 64),
        max=(256, 256),
    )
    input_metadata = TensorMetadata()
    input_metadata.add(name="input_1", shape=(-1, -1, -1, -1), dtype=np.dtype("float32"))
    input_metadata.add(name="input_2", shape=(-1, -1), dtype=np.dtype("float32"))

    result = ConvertONNX2TRT._get_shape_args(
        onnx_input_metadata=input_metadata,
        batch_dim=0,
        max_batch_size=128,
        trt_profile=profile,
    )
    expected_result = [
        "--trt-min-shapes",
        "input_1:[1,224,224,3]",
        "input_2:[1,1]",
        "--trt-opt-shapes",
        "input_1:[64,224,224,3]",
        "input_2:[64,64]",
        "--trt-max-shapes",
        "input_1:[128,224,224,3]",
        "input_2:[128,256]",
    ]
    assert result == expected_result


def test_get_onnx_input_metadata_return_filled_metadata_when_successfully_read_from_file(mocker):
    with mocker.patch.object(
        ExecutionContext, "execute_external_runtime_script"
    ), tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        results_file = tmpdir / "results.json"
        workspace = tmpdir / "navigator_workspace"

        mock = MagicMock()
        mock.__enter__.return_value.name = results_file.as_posix()
        mocker.patch("tempfile.NamedTemporaryFile", return_value=mock)

        assets_path = get_assets_path()
        model_path = assets_path / "models" / "identity.onnx"

        onnx_model_path = workspace / "onnx" / "model.onnx"
        onnx_model_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(model_path, onnx_model_path)

        input_metadata = TensorMetadata()
        input_metadata.add(name="X", shape=(-1, 3, 8, 8), dtype=np.float32())

        output_metadata = TensorMetadata()
        output_metadata.add(name="Y", shape=(-1, 3, 8, 8), dtype=np.float32())

        data = [{"name": "X", "shape": [-1, 3, -1, -1], "dtype": "float32"}]
        with results_file.open("w") as fp:
            json.dump(data, fp)

        metadata = ConvertONNX2TRT()._get_onnx_input_metadata(
            workspace=Workspace(workspace),
            input_model_path=onnx_model_path,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            reproduce_script_path=workspace,
            verbose=False,
        )

        assert "X" in metadata
        assert metadata["X"] == TensorSpec(name="X", shape=(-1, 3, -1, -1), dtype=np.float32().dtype)


def test_get_onnx_input_metadata_return_empty_metadata_when_no_file(mocker):
    with mocker.patch.object(
        ExecutionContext, "execute_external_runtime_script"
    ), tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = pathlib.Path(tmpdir)
        workspace = tmpdir / "navigator_workspace"

        assets_path = get_assets_path()
        model_path = assets_path / "models" / "identity.onnx"

        onnx_model_path = workspace / "onnx" / "model.onnx"
        onnx_model_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(model_path, onnx_model_path)

        input_metadata = TensorMetadata()
        input_metadata.add(name="X", shape=(-1, 3, 8, 8), dtype=np.float32())

        output_metadata = TensorMetadata()
        output_metadata.add(name="Y", shape=(-1, 3, 8, 8), dtype=np.float32())

        metadata = ConvertONNX2TRT()._get_onnx_input_metadata(
            workspace=Workspace(workspace),
            input_model_path=onnx_model_path,
            input_metadata=input_metadata,
            output_metadata=output_metadata,
            reproduce_script_path=workspace,
            verbose=False,
        )

        assert metadata == {}

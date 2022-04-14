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
# pytype: disable=import-error
import tempfile
from pathlib import Path

import torch

import model_navigator as nav

# pytype: enable=import-error


def check_model_dir(model_dir: Path, format: nav.Format, only_config: bool = False) -> bool:
    if not model_dir.is_dir():
        return False
    if not Path(model_dir / "config.yaml").is_file():
        return False
    if only_config:
        return True
    if format == nav.Format.ONNX:
        model_path = model_dir / "model.onnx"
    elif format == nav.Format.TENSORRT:
        model_path = model_dir / "model.plan"
    else:
        model_path = model_dir / "model.pt"
    if not model_path.exists():
        return False

    return True


model = torch.nn.Linear(3, 5)
dataloader = [torch.rand(2, 3)]
numpy_dataloader = [torch.rand(2, 3).numpy()]
device = "cuda" if torch.cuda.is_available() else "cpu"


def test_pyt_save_load_no_retest():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        load_workdir = Path(tmp_dir) / "load_navigator_workdir"
        nav_package_path = workdir / f"{model_name}.nav"
        loaded_package_dir = load_workdir / f"{model_name}.nav.workspace"
        status_file = loaded_package_dir / "status.yaml"
        model_input_dir = loaded_package_dir / "model_input"
        model_output_dir = loaded_package_dir / "model_output"
        navigator_log_file = loaded_package_dir / "navigator.log"

        pkg_desc = nav.torch.export(
            model=model,
            dataloader=dataloader,
            override_workdir=True,
            workdir=workdir,
            model_name=model_name,
        )

        pkg_desc.set_verified(nav.Format.TENSORRT, nav.RuntimeProvider.TRT, precision=nav.TensorRTPrecision.FP32)
        pkg_desc.save(nav_package_path)
        nav.load(nav_package_path, workdir=load_workdir, retest_conversions=False)

        assert status_file.is_file()
        assert model_input_dir.is_dir()
        assert all(
            [path.suffix == ".npz" for samples_dir in model_input_dir.iterdir() for path in samples_dir.iterdir()]
        )
        assert model_output_dir.is_dir()
        assert all(
            [path.suffix == ".npz" for samples_dir in model_output_dir.iterdir() for path in samples_dir.iterdir()]
        )
        assert navigator_log_file.is_file()

        # Exported formats
        assert check_model_dir(model_dir=loaded_package_dir / "onnx", format=nav.Format.ONNX)
        assert check_model_dir(
            model_dir=loaded_package_dir / "torchscript-script", format=nav.Format.TORCHSCRIPT_SCRIPT
        )
        assert check_model_dir(model_dir=loaded_package_dir / "torchscript-trace", format=nav.Format.TORCHSCRIPT_TRACE)

        # Converted formats
        assert check_model_dir(model_dir=loaded_package_dir / "trt-fp32", format=nav.Format.TENSORRT, only_config=True)
        assert check_model_dir(
            model_dir=loaded_package_dir / "torch-trt-script", format=nav.Format.TORCH_TRT_SCRIPT, only_config=True
        )
        assert check_model_dir(
            model_dir=loaded_package_dir / "torch-trt-trace", format=nav.Format.TORCH_TRT_TRACE, only_config=True
        )
        assert check_model_dir(model_dir=loaded_package_dir / "trt-fp16", format=nav.Format.TENSORRT, only_config=True)


def test_pyt_save_load_retest():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        load_workdir = Path(tmp_dir) / "load_navigator_workdir"
        nav_package_path = workdir / f"{model_name}.nav"
        loaded_package_dir = load_workdir / f"{model_name}.nav.workspace"
        status_file = loaded_package_dir / "status.yaml"
        model_input_dir = loaded_package_dir / "model_input"
        model_output_dir = loaded_package_dir / "model_output"
        navigator_log_file = loaded_package_dir / "navigator.log"

        pkg_desc = nav.torch.export(
            model=model,
            dataloader=dataloader,
            override_workdir=True,
            workdir=workdir,
            model_name=model_name,
        )

        pkg_desc.set_verified(nav.Format.TENSORRT, nav.RuntimeProvider.TRT, precision=nav.TensorRTPrecision.FP32)
        pkg_desc.save(nav_package_path)
        nav.load(nav_package_path, workdir=load_workdir)

        assert status_file.is_file()
        assert model_input_dir.is_dir()
        assert all(
            [path.suffix == ".npz" for samples_dir in model_input_dir.iterdir() for path in samples_dir.iterdir()]
        )
        assert model_output_dir.is_dir()
        assert all(
            [path.suffix == ".npz" for samples_dir in model_output_dir.iterdir() for path in samples_dir.iterdir()]
        )
        assert navigator_log_file.is_file()

        # Output formats
        assert check_model_dir(model_dir=loaded_package_dir / "onnx", format=nav.Format.ONNX)
        assert check_model_dir(
            model_dir=loaded_package_dir / "torchscript-script", format=nav.Format.TORCHSCRIPT_SCRIPT
        )
        assert check_model_dir(model_dir=loaded_package_dir / "torchscript-trace", format=nav.Format.TORCHSCRIPT_TRACE)
        assert check_model_dir(model_dir=loaded_package_dir / "torch-trt-script", format=nav.Format.TORCH_TRT_SCRIPT)
        assert check_model_dir(model_dir=loaded_package_dir / "torch-trt-trace", format=nav.Format.TORCH_TRT_TRACE)
        assert check_model_dir(model_dir=loaded_package_dir / "trt-fp16", format=nav.Format.TENSORRT)
        assert check_model_dir(model_dir=loaded_package_dir / "trt-fp32", format=nav.Format.TENSORRT)


def test_onnx_save_load_retest():
    with tempfile.TemporaryDirectory() as tmp_dir:
        model_name = "navigator_model"

        workdir = Path(tmp_dir) / "navigator_workdir"
        onnx_model_path = Path(tmp_dir) / "dummy_onnx.onnx"
        load_workdir = Path(tmp_dir) / "load_navigator_workdir"
        nav_package_path = workdir / f"{model_name}.nav"
        loaded_package_dir = load_workdir / f"{model_name}.nav.workspace"
        status_file = loaded_package_dir / "status.yaml"
        model_input_dir = loaded_package_dir / "model_input"
        model_output_dir = loaded_package_dir / "model_output"
        navigator_log_file = loaded_package_dir / "navigator.log"

        torch.onnx.export(
            model.to(device),
            dataloader[0].to(device),
            onnx_model_path.as_posix(),
            opset_version=13,
            dynamic_axes={"input_0": {0: "batch"}},
            input_names=["input_0"],
        )

        pkg_desc = nav.onnx.export(
            model=onnx_model_path,
            dataloader=numpy_dataloader,
            override_workdir=True,
            workdir=workdir,
            model_name=model_name,
        )

        pkg_desc.set_verified(nav.Format.TENSORRT, nav.RuntimeProvider.TRT, precision=nav.TensorRTPrecision.FP32)
        pkg_desc.save(nav_package_path)
        nav.load(nav_package_path, workdir=load_workdir)

        assert status_file.is_file()
        assert model_input_dir.is_dir()
        assert all(
            [path.suffix == ".npz" for samples_dir in model_input_dir.iterdir() for path in samples_dir.iterdir()]
        )
        assert model_output_dir.is_dir()
        assert all(
            [path.suffix == ".npz" for samples_dir in model_output_dir.iterdir() for path in samples_dir.iterdir()]
        )
        assert navigator_log_file.is_file()

        # Output formats
        assert check_model_dir(model_dir=loaded_package_dir / "onnx", format=nav.Format.ONNX)
        assert check_model_dir(model_dir=loaded_package_dir / "trt-fp16", format=nav.Format.TENSORRT)
        assert check_model_dir(model_dir=loaded_package_dir / "trt-fp32", format=nav.Format.TENSORRT)

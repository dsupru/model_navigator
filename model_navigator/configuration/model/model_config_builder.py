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


"""This module contains builder class that generates all possible model configs."""

import collections
from itertools import product
from typing import Dict, List, Optional, Sequence, Type, TypeVar

from model_navigator.api import Format
from model_navigator.api import config as config_api
from model_navigator.configuration.model import model_config
from model_navigator.frameworks import Framework
from model_navigator.utils.format_helpers import get_base_format

C = TypeVar("C", bound=config_api.CustomConfigForFormat)


def _get_custom_config(
    custom_configs: Sequence[config_api.CustomConfigForFormat],
    custom_config_cls: Type[C],
    framework: Optional[Framework] = None,
) -> C:
    for custom_config in custom_configs:
        if isinstance(custom_config, custom_config_cls):
            return custom_config

    if custom_config_cls is config_api.TensorFlowConfig and framework == Framework.JAX:
        return custom_config_cls(
            jit_compile=(True, False),
            enable_xla=(True, False),
        )
    return custom_config_cls()


class ModelConfigBuilder:
    """Class used for generating model configuraitons."""

    @staticmethod
    def generate_model_config(
        framework: Framework,
        target_formats: Sequence[Format],
        custom_configs: Optional[Sequence[config_api.CustomConfig]],
    ) -> Dict[Format, List[model_config.ModelConfig]]:
        """Generates all valid checkpoint configurations that can be exported and converted.

        Args:
            framework: Framework in which the source model is implemented
            target_formats: Formats to which model has to be converted
            custom_configs: Additional parameters per conversion

        Raises:
            NotImplementedError: When any of the custom configs is not an instance of CustomConfigForFormat.

        Returns:
            Dictionary with mapping of Formats to lists of ModelConfigs
        """
        custom_configs_for_format: List[config_api.CustomConfigForFormat] = []
        for custom_config in custom_configs or []:
            if isinstance(custom_config, config_api.CustomConfigForFormat):
                custom_configs_for_format.append(custom_config)
            else:
                raise NotImplementedError("Currently only custom configs for formats are implemented.")

        base_formats = []
        for target_format in target_formats:
            base_format = get_base_format(target_format, framework)
            if base_format is not None:
                base_formats.append(base_format)
        target_formats = tuple(set(base_formats + list(target_formats)))

        model_configs = collections.defaultdict(list)

        if Format.PYTHON in target_formats:
            ModelConfigBuilder.get_source_python_config(model_configs)

        if Format.TORCH in target_formats:
            ModelConfigBuilder.get_source_torch_config(model_configs)

        if Format.TENSORFLOW in target_formats:
            ModelConfigBuilder.get_source_tensorflow_config(model_configs)

        if Format.JAX in target_formats:
            ModelConfigBuilder.get_source_jax_config(model_configs)

        onnx_custom_config = _get_custom_config(custom_configs_for_format, config_api.OnnxConfig, framework=framework)
        extended_onnx_export = Format.ONNX in target_formats and onnx_custom_config.onnx_extended_conversion
        if framework == Framework.TORCH and (Format.TORCHSCRIPT in target_formats or extended_onnx_export):
            ModelConfigBuilder.get_torchscript_config(custom_configs_for_format, model_configs)

        if Format.TORCH_TRT in target_formats:
            ModelConfigBuilder.get_torch_trt_config(custom_configs_for_format, model_configs)

        if Format.TF_SAVEDMODEL in target_formats:
            ModelConfigBuilder.get_savedmodel_config(custom_configs_for_format, model_configs, framework=framework)

        if Format.ONNX in target_formats:
            ModelConfigBuilder.get_onnx_config(framework, custom_configs_for_format, model_configs)

        if Format.TENSORRT in target_formats:
            ModelConfigBuilder.get_trt_config(custom_configs_for_format, model_configs)

        if Format.TF_TRT in target_formats:
            ModelConfigBuilder.get_tf_trt_config(custom_configs_for_format, model_configs)

        return model_configs

    @staticmethod
    def get_source_python_config(model_configs: Dict[Format, List[model_config.ModelConfig]]):
        """Append source Python model configuration to model_configs dictionary.

        Args:
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        model_configs[Format.PYTHON].append(model_config.PythonModelConfig())

    @staticmethod
    def get_source_torch_config(model_configs: Dict[Format, List[model_config.ModelConfig]]):
        """Append source Torch model configuration to model_configs dictionary.

        Args:
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        model_configs[Format.TORCH].append(model_config.TorchModelConfig())

    @staticmethod
    def get_source_tensorflow_config(model_configs: Dict[Format, List[model_config.ModelConfig]]):
        """Append source TensorFlow model configuration to model_configs dictionary.

        Args:
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        model_configs[Format.TENSORFLOW].append(model_config.TensorFlowModelConfig())

    @staticmethod
    def get_source_jax_config(model_configs: Dict[Format, List[model_config.ModelConfig]]):
        """Append source Jax model configuration to model_configs dictionary.

        Args:
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        model_configs[Format.JAX].append(model_config.JAXModelConfig())

    @staticmethod
    def get_torchscript_config(
        custom_configs: Sequence[config_api.CustomConfigForFormat],
        model_configs: Dict[Format, List[model_config.ModelConfig]],
    ):
        """Append TorchScript model configurations to model_configs dictionary.

        Args:
            custom_configs: Format configurations provided by the user
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        torch_config = _get_custom_config(custom_configs=custom_configs, custom_config_cls=config_api.TorchConfig)
        for jit_type in torch_config.jit_type:
            model_configs[Format.TORCHSCRIPT].append(
                model_config.TorchScriptConfig(jit_type=jit_type, strict=torch_config.strict)
            )

    @staticmethod
    def get_torch_trt_config(
        custom_configs: Sequence[config_api.CustomConfigForFormat],
        model_configs: Dict[Format, List[model_config.ModelConfig]],
    ):
        """Append TorchTensorRT model configurations to model_configs dictionary.

        Args:
            custom_configs: Format configurations provided by the user
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        torch_trt_config = _get_custom_config(
            custom_configs=custom_configs, custom_config_cls=config_api.TorchTensorRTConfig
        )
        for model_configuration, precision in product(model_configs[Format.TORCHSCRIPT], torch_trt_config.precision):
            model_configs[Format.TORCH_TRT].append(
                model_config.TorchTensorRTConfig(
                    parent=model_configuration,
                    precision=precision,
                    precision_mode=torch_trt_config.precision_mode,
                    max_workspace_size=torch_trt_config.max_workspace_size,
                    trt_profile=torch_trt_config.trt_profile,
                )
            )

    @staticmethod
    def get_savedmodel_config(
        custom_configs: Sequence[config_api.CustomConfigForFormat],
        model_configs: Dict[Format, List[model_config.ModelConfig]],
        framework: Optional[Framework] = None,
    ):
        """Append Savedmodel model configuration to model_configs dictionary.

        Args:
            custom_configs: Format configurations provided by the user
            model_configs: Dictionary mapping model formats to lists of model configs
            framework: Framework used for source model
        """
        tf_config = _get_custom_config(
            custom_configs=custom_configs, custom_config_cls=config_api.TensorFlowConfig, framework=framework
        )
        for jit_compile_option, enable_xla_option in product(tf_config.jit_compile, tf_config.enable_xla):
            model_configs[Format.TF_SAVEDMODEL].append(
                model_config.TensorFlowSavedModelConfig(jit_compile=jit_compile_option, enable_xla=enable_xla_option)
            )

    @staticmethod
    def get_tf_trt_config(
        custom_configs: Sequence[config_api.CustomConfigForFormat],
        model_configs: Dict[Format, List[model_config.ModelConfig]],
    ):
        """Append TensorFlowTensorRT model configurations to model_configs dictionary.

        Args:
            custom_configs: Format configurations provided by the user
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        tf_trt_config = _get_custom_config(
            custom_configs=custom_configs, custom_config_cls=config_api.TensorFlowTensorRTConfig
        )
        for model_configuration, precision in product(model_configs[Format.TF_SAVEDMODEL], tf_trt_config.precision):
            model_configs[Format.TF_TRT].append(
                model_config.TensorFlowTensorRTConfig(
                    parent=model_configuration,
                    precision=precision,
                    max_workspace_size=tf_trt_config.max_workspace_size,
                    minimum_segment_size=tf_trt_config.minimum_segment_size,
                    trt_profile=tf_trt_config.trt_profile,
                )
            )

    @staticmethod
    def get_onnx_config(
        framework: Framework,
        custom_configs: Sequence[config_api.CustomConfigForFormat],
        model_configs: Dict[Format, List[model_config.ModelConfig]],
    ):
        """Append ONNX model configurations to model_configs dictionary.

        Args:
            framework: source framework
            custom_configs: Format configurations provided by the user
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        onnx_config = _get_custom_config(custom_configs=custom_configs, custom_config_cls=config_api.OnnxConfig)
        if framework in (Framework.TENSORFLOW, Framework.JAX):
            for model_configuration in model_configs[Format.TF_SAVEDMODEL]:
                model_configs[Format.ONNX].append(
                    model_config.ONNXConfig(
                        parent=model_configuration,
                        opset=onnx_config.opset,
                        dynamic_axes=onnx_config.dynamic_axes,
                    )
                )
        if framework in (Framework.TORCH, Framework.ONNX):
            model_configs[Format.ONNX].append(
                model_config.ONNXConfig(
                    parent=None,
                    opset=onnx_config.opset,
                    dynamic_axes=onnx_config.dynamic_axes,
                )
            )
        if framework == Framework.TORCH and onnx_config.onnx_extended_conversion:
            for model_configuration in model_configs[Format.TORCHSCRIPT]:
                model_configs[Format.ONNX].append(
                    model_config.ONNXConfig(
                        parent=model_configuration,
                        opset=onnx_config.opset,
                        dynamic_axes=onnx_config.dynamic_axes,
                    )
                )

    @staticmethod
    def get_trt_config(
        custom_configs: Sequence[config_api.CustomConfigForFormat],
        model_configs: Dict[Format, List[model_config.ModelConfig]],
    ):
        """Append TensorRT model configurations to model_configs dictionary.

        Args:
            custom_configs: Format configurations provided by the user
            model_configs: Dictionary mappint model formats to lists of model configs
        """
        trt_config = _get_custom_config(custom_configs=custom_configs, custom_config_cls=config_api.TensorRTConfig)
        for model_configuration, precision in product(model_configs[Format.ONNX], trt_config.precision):
            model_configs[Format.TENSORRT].append(
                model_config.TensorRTConfig(
                    parent=model_configuration,
                    precision=precision,
                    precision_mode=trt_config.precision_mode,
                    max_workspace_size=trt_config.max_workspace_size,
                    trt_profile=trt_config.trt_profile,
                    optimization_level=trt_config.optimization_level,
                    compatibility_level=trt_config.compatibility_level,
                )
            )

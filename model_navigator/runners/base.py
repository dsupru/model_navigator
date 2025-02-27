# Copyright (c) 2022, NVIDIA CORPORATION. All rights reserved.
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
"""Base runners definition for Model Navigator."""

import abc
import time
from typing import Any, Dict, List, Optional

import numpy as np

from model_navigator.api.config import DeviceKind, Format, TensorType
from model_navigator.core.logger import LOGGER
from model_navigator.core.tensor import TensorMetadata, TensorSpec, get_tensor_type
from model_navigator.utils.dataloader import validate_sample_output


class NavigatorRunner(abc.ABC):
    """Base abstract runner.

    Example usage:

        with RunnerType(...) as runner:
                runner.infer(...)
    """

    def __init__(
        self,
        model: Any,
        input_metadata: TensorMetadata,
        output_metadata: TensorMetadata,
        input_metadata_mapping: Optional[Dict[str, str]] = None,
        return_type: TensorType = TensorType.NUMPY,
        *args,
        **kwargs,
    ) -> None:
        """Initialize object.

        Args:
            model: A model for which runner has to be initialized
            input_metadata: A model inputs metadata
            output_metadata: A model outputs metadata
            input_metadata_mapping: Optional mapping for input metadata
            return_type: A type of return value
        """
        self._model = model
        self._input_metadata = input_metadata
        self._output_metadata = output_metadata
        self._input_metadata_mapping = input_metadata_mapping

        self._check_return_type(return_type)
        self._return_type = return_type

        self.inference_time = None
        self.is_active = False

        self.init_impl()

    @property
    def model(self) -> Any:
        """Property for obtaining model object."""
        return self._model

    @property
    def input_metadata(self) -> TensorMetadata:
        """Property for obtaining model input metadata object."""
        return self._input_metadata

    @property
    def output_metadata(self) -> TensorMetadata:
        """Property for obtaining model output metadata object."""
        return self._output_metadata

    @property
    def input_metadata_mapping(self) -> Optional[Dict[str, str]]:
        """Property for obtaining model input metadata mapping."""
        return self._input_metadata_mapping

    @property
    def return_type(self) -> TensorType:
        """Property for obtaining runner return type."""
        return self._return_type

    @classmethod
    def name(cls) -> str:
        """Return name of the runner."""
        return cls.__name__

    @classmethod
    @abc.abstractmethod
    def format(cls) -> Format:  # noqa N805
        """Return format for which runner was created."""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def devices_kind(cls) -> List[DeviceKind]:  # noqa N805
        """Return supported devices kind."""
        raise NotImplementedError

    def init_impl(self):  # noqa B027
        """Implementation for runner initialization.

        Derived classes should override this function rather than ``__init__()``.
        """
        pass

    def activate_impl(self):  # noqa B027
        """Implementation for runner activation.

        Derived classes should override this function rather than ``activate()``.

        Example usage: this may involve allocating CPU or GPU memory.
        """
        pass

    @abc.abstractmethod
    def infer_impl(self, feed_dict: Dict, *args: Any, **kwargs: Any) -> Dict[str, np.ndarray]:
        """Implementation for runner inference.

        Derived classes should override this function rather than ``infer()``

        Args:
            feed_dict: A dictionary with profiling samples
        """
        raise NotImplementedError("NavigatorRunner is an abstract class")

    def deactivate_impl(self):  # noqa B027
        """Implementation for runner deactivation.

        Derived classes should override this function rather than ``deactivate()``.
        """
        pass

    @classmethod
    def is_stabilized(cls) -> bool:
        """Flag indicating if runner implements own measurement stabilization mechanism.

        Returns:
            True if runner self stabilize measurement, False otherwise
        """
        return False

    def __enter__(self):
        """Activate the runner on entering runner context."""
        self.activate()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Deactivate the runner on exiting runner context."""
        self.deactivate()

    def get_input_metadata(self) -> TensorMetadata:
        """Returns information about the inputs of the model.

        Shapes here may include dynamic dimensions, represented by ``-1``.
        Must be called only after ``activate()`` and before ``deactivate()``.

        Returns: A ``TensorMetadata`` object describing the inputs of the model.
        """
        return self.get_input_metadata_impl()

    def get_input_metadata_impl(self) -> TensorMetadata:  # noqa B027
        """Implementation for getting input metadata.

        Derived classes should override this function rather than ``get_input_metadata()``.
        """
        pass  # pytype: disable=bad-return-type

    def activate(self):
        """Activate the runner for inference.

        The method do basic activation and call `activate_impl` method.
        """
        if self.is_active:
            LOGGER.warning(
                f"{self.name()} | Already active; will not activate again. "
                "If you really want to activate this runner again, call activate_impl() directly"
            )
            return

        self.activate_impl()
        self.is_active = True

    def infer(self, feed_dict: Dict[str, Any], check_inputs: bool = True, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        """Runs inference using the provided feed_dict.

        Must be called only after ``activate()`` and before ``deactivate()``.

        NOTE: Some runners may accept additional parameters in infer().
        For details on these, see the documentation for their `infer_impl()` methods.

        Args:
            feed_dict: A mapping of input tensor names to corresponding input NumPy arrays.
            check_inputs: Whether to check that the provided ``feed_dict`` and generated outputs includes the expected
                inputs / outputs with the expected data types and shapes. Disabling this may improve performance.
                Defaults to True.

        Returns:
            A dictionary with mapping of output tensor names to their corresponding NumPy arrays.

            IMPORTANT: Runners may reuse these output buffers. Thus, if you need to save
            outputs from multiple inferences, you should make a copy with ``copy.deepcopy(outputs)``.
        """
        if not self.is_active:
            LOGGER.error(f"{self.name()} | Must be activated prior to calling infer()")

        if check_inputs:
            input_metadata = self.input_metadata
            LOGGER.debug(f"Runner input metadata is: {input_metadata}")

            for name in input_metadata:
                if name not in feed_dict:
                    LOGGER.warning("Input tensor: {name} | Missing input in `feed_dict`: {name}.")

            for name, inp in feed_dict.items():
                if get_tensor_type(inp) not in self.get_available_input_types():
                    LOGGER.warning(
                        f"Input tensor: {name} | Received unexpected type: {get_tensor_type(inp)}.\n"
                        f"Note: Expected one of: {self.get_available_input_types()}"
                    )

                meta = input_metadata[name]
                inp_spec = TensorSpec.from_tensor(inp, name)
                if not meta.is_dtype_compatible(inp_spec):
                    LOGGER.warning(
                        f"Input tensor: {name} | Received unexpected dtype: {inp_spec.dtype}.\n"
                        f"Note: Expected type: {meta.dtype}"
                    )

                if not meta.is_shape_compatible(inp_spec):
                    LOGGER.warning(
                        f"Input tensor: {name} | Received incompatible shape: {inp_spec.shape}.\n"
                        f"Note: Expected a shape compatible with: {meta.shape}"
                    )

        start_time = time.monotonic()
        output = self.infer_impl(feed_dict, *args, **kwargs)
        end_time = time.monotonic()

        if check_inputs:
            validate_sample_output(output, self.return_type)

        self.inference_time = end_time - start_time
        return output

    def last_inference_time(self) -> Optional[float]:
        """Returns the total inference time in seconds required during the last call to ``infer()``.

        Must be called only after ``activate()`` and before ``deactivate()``.

        Returns:
            The time in seconds, or None if runtime was not measured by the runner.
        """
        if self.inference_time is None:
            msg = f"{self.name()} | `inference_time` was not set. Inference time will be incorrect! "
            msg += "To correctly compare runtimes, please set the `inference_time` attribute in `infer_impl()`"

            LOGGER.error(msg)
            return None
        return self.inference_time

    def deactivate(self):
        """Deactivate the runner. For example, this may involve freeing CPU or GPU memory."""
        if not self.is_active:
            LOGGER.warning(
                f"{self.name()} | Not active; will not deactivate. "
                "If you really want to deactivate this runner, "
                "call deactivate_impl() directly"
            )
            return

        self.inference_time = None
        self.is_active = None

        self.deactivate_impl()
        self.is_active = False

    def get_available_return_types(self) -> List[TensorType]:
        """Returns a list of available return types.

        Returns:
            A list of available return types.
        """
        return self.get_available_return_types_impl()

    def get_available_return_types_impl(self) -> List[TensorType]:
        """Implementation for getting available return types.

        Derived classes should override this function rather than ``get_available_return_types()``.
        """
        return [TensorType.NUMPY]

    def get_available_input_types(self) -> List[TensorType]:
        """Returns a list of available input types.

        Returns:
            A list of available input types.
        """
        return self.get_available_input_types_impl()

    def get_available_input_types_impl(self) -> List[TensorType]:
        """Implementation for getting available input types.

        Derived classes should override this function rather than ``get_available_input_types()``.
        """
        return [TensorType.NUMPY]

    def __del__(self):
        """Cleanup of object removal. Log warning when `deactivate` was not called before runner was removed."""
        if self.is_active:
            # __del__ is not guaranteed to be called, but when it is, this could be a useful warning.
            LOGGER.warning(f"{self.name()} | Was activated but never deactivated. This could cause a memory leak!")

    def _check_return_type(self, return_type: TensorType) -> None:
        """Check if return type is available.

        Args:
            return_type: TensorType to check.

        Raises:
            ValueError: If return_type is not available.
        """
        available_return_types = self.get_available_return_types()
        if return_type not in available_return_types:
            raise ValueError(
                f"{self.name()} | `return_type` must be one of {available_return_types}, but got: {return_type}"
            )


class NavigatorStabilizedRunner(NavigatorRunner):
    """Stabilized runner base class."""

    @classmethod
    def is_stabilized(cls) -> bool:
        """Override is_stabilized class method and always return True."""
        return True

    @abc.abstractmethod
    def avg_latency(self) -> float:
        """Returns average latency of stabilized measurement."""
        raise NotImplementedError

    @abc.abstractmethod
    def std_latency(self) -> float:
        """Returns standard deviation for average latency of stabilized measurement."""
        raise NotImplementedError

    @abc.abstractmethod
    def p50_latency(self) -> float:
        """Returns 50 median percentile for latency of stabilized measurement."""
        raise NotImplementedError

    @abc.abstractmethod
    def p90_latency(self) -> float:
        """Returns 90 median percentile for latency of stabilized measurement."""
        raise NotImplementedError

    @abc.abstractmethod
    def p95_latency(self) -> float:
        """Returns 95 median percentile for latency of stabilized measurement."""
        raise NotImplementedError

    @abc.abstractmethod
    def p99_latency(self) -> float:
        """Returns 99 median percentile for latency of stabilized measurement."""
        raise NotImplementedError

    @abc.abstractmethod
    def request_count(self) -> int:
        """Returns number of queries performed during measurement."""
        raise NotImplementedError

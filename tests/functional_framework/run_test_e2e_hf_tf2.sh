#!/usr/bin/env bash
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

set -ex

TEMPDIR=$(mktemp -d)

function cleanup {
    echo "Cleanup..."
    rm -r ${TEMPDIR}
}

trap cleanup EXIT

if [ -z "$1" ]
then
    WORKDIR=${TEMPDIR}/workdir
else
    WORKDIR=${1}
fi

./tests/functional_framework/test_e2e_hf_tf2.py --model-name distilbert-base-uncased --workdir ${WORKDIR}
./tests/functional_framework/test_e2e_hf_tf2.py --model-name distilgpt2 --workdir ${WORKDIR}

#coding:utf-8
#   Copyright (c) 2019  PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"
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
"""Setup for pip package."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import platform
import os
import six
from setuptools import setup

with open(os.path.join('./', 'requirements.txt')) as f:
    setup_requires = f.read().splitlines()

packages = [
    'paddle',
    'paddle.libs',
    'paddle.utils',
    'paddle.dataset',
    'paddle.reader',
    'paddle.distributed',
    'paddle.incubate',
    'paddle.incubate.complex',
    'paddle.incubate.complex.tensor',
    'paddle.distributed.fleet',
    'paddle.distributed.fleet.base',
    'paddle.distributed.fleet.meta_optimizers',
    'paddle.distributed.fleet.runtime',
    'paddle.distributed.fleet.dataset',
    'paddle.distributed.fleet.metrics',
    'paddle.distributed.fleet.proto',
    'paddle.distributed.fleet.utils',
    'paddle.framework',
    'paddle.jit',
    'paddle.fluid',
    'paddle.fluid.inference',
    'paddle.fluid.dygraph',
    'paddle.fluid.dygraph.dygraph_to_static',
    'paddle.fluid.dygraph.amp',
    'paddle.fluid.proto',
    'paddle.fluid.proto.profiler',
    'paddle.fluid.distributed',
    'paddle.fluid.layers',
    'paddle.fluid.dataloader',
    'paddle.fluid.contrib',
    'paddle.fluid.contrib.decoder',
    'paddle.fluid.contrib.quantize',
    'paddle.fluid.contrib.reader',
    'paddle.fluid.contrib.slim',
    'paddle.fluid.contrib.slim.quantization',
    'paddle.fluid.contrib.slim.quantization.imperative',
    'paddle.fluid.contrib.utils',
    'paddle.fluid.contrib.extend_optimizer',
    'paddle.fluid.contrib.mixed_precision',
    'paddle.fluid.contrib.layers',
    'paddle.fluid.transpiler',
    'paddle.fluid.transpiler.details',
    'paddle.fluid.incubate',
    'paddle.fluid.incubate.data_generator',
    'paddle.fluid.incubate.fleet',
    'paddle.fluid.incubate.checkpoint',
    'paddle.fluid.incubate.fleet.base',
    'paddle.fluid.incubate.fleet.parameter_server',
    'paddle.fluid.incubate.fleet.parameter_server.distribute_transpiler',
    'paddle.fluid.incubate.fleet.parameter_server.pslib',
    'paddle.fluid.incubate.fleet.parameter_server.ir',
    'paddle.fluid.incubate.fleet.collective',
    'paddle.fluid.incubate.fleet.utils',
    'paddle.hapi',
    'paddle.vision',
    'paddle.vision.models',
    'paddle.vision.transforms',
    'paddle.vision.datasets',
    'paddle.text',
    'paddle.text.datasets',
    'paddle.incubate',
    'paddle.io',
    'paddle.optimizer',
    'paddle.nn',
    'paddle.nn.functional',
    'paddle.nn.layer',
    'paddle.nn.initializer',
    'paddle.nn.utils',
    'paddle.metric',
    'paddle.static',
    'paddle.static.nn',
    'paddle.tensor',
]

if '${WITH_GPU}' == 'ON':
    os.environ['PACKAGE_NAME'] = "paddlebot-gpu"
else:
    os.environ['PACKAGE_NAME'] = "paddlebot"

setup(
    name='paddlebot',
    version='${PADDLEBOT_VERSION}',
    description='Parallel Distributed Deep Learning',
    url='https://github.com/PaddlePaddle/Paddle',
    author='PaddlePaddle Author',
    author_email='paddle-dev@baidu.com',
    install_requires=setup_requires,
    packages=packages,
    include_package_data=True,
    # PyPI package information.
    classifiers=[
        'Development Status :: 2 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Mathematics',
        'Topic :: Scientific/Engineering :: Artificial Intelligence',
        'Topic :: Software Development',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    entry_points={
        'console_scripts':
        ['fleetrun = paddle.distributed.fleet.launch:launch']
    })

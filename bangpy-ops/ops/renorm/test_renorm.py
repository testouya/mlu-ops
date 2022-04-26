# Copyright (C) [2021] by Cambricon, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
# pylint: disable=missing-docstring, invalid-name, too-many-locals
"""A multi-platform code link example test for BANGPy TCP."""
from cmath import pi
from traceback import print_tb
import numpy as np
import torch
import pytest
import math

import bangpy
import bangpy as bp
from bangpy import tcp
from bangpy.common import utils, load_op_by_type
from bangpy.platform.bang_config import ALIGN_LENGTH, TARGET
from bangpy.tcp.runtime import TaskType
from renorm import DTYPES, KERNEL_NAME, TARGET_LIST

import time

@pytest.mark.parametrize(
    "shape", 
    [        
        ((1, 1121, 301, 2), (1121, 301, 2))
    ],
)

@pytest.mark.parametrize(
    "dtype", DTYPES,
)

@pytest.mark.parametrize(
    "p", [3.],
)

@pytest.mark.parametrize(
    "eps", [0.000001,],
)

@pytest.mark.parametrize(
    "keepdim", [False],
)



def test_pairwise_distance(target, shape, p, eps, keepdim, dtype): 
    if target not in TARGET_LIST:
        return 

    def mlu_pairwise_distance(p, eps, keepdim):
        def get_total_size(shp):
            size = 1
            for s in shp:
                size *= s
            return size

        def f(a, b):
            #拿到shape
            if len(a.shape) > len(b.shape):
                _shape1 = a.shape
                _shape2 = b.shape
            else:
                _shape1 = b.shape
                _shape2 = a.shape
            
            _dev = bp.device(0)

            shp_len = len(_shape1)
            dim_index = shp_len - 1

            # mlu 输入参数
            _pd_len = _shape1[shp_len - 1]
            _pd_height = 1
            _pd_width = 1

            for i in range(0, dim_index + 1):
                _pd_height *= _shape1[i]

            if dim_index == shp_len - 1:
                pass
            else:
                for i in range(dim_index + 1, shp_len):
                    _pd_width *= _shape1[i] 

            # mlu 输入
            _mlu_input1 = bp.Array(a.flatten(), _dev)
            _mlu_input2 = bp.Array(b.flatten(), _dev)
            paras = np.array([p, eps]).astype(dtype.as_numpy_dtype) # 这里需要考虑
            _mlu_paras = bp.Array(paras, _dev)

            # mlu 输出
            _output_len = get_total_size(_shape1) // _shape1[dim_index]
            output_buffer = np.zeros(_output_len, dtype=dtype.as_numpy_dtype)
            _mlu_output = bp.Array(output_buffer, _dev)

            output_count = 256
            output_buffer2 = np.zeros(output_count, dtype=dtype.as_numpy_dtype)
            _mlu_border_output = bp.Array(output_buffer2, _dev)

            output_buffer3 = -np.ones(output_count, dtype=np.int32)
            _mlu_border_idx_output = bp.Array(output_buffer3, _dev)

            # 调用mlu
            func = load_op_by_type(KERNEL_NAME, dtype.name)
            func(_mlu_input1, _mlu_input2,
                 _mlu_paras, 
                 get_total_size(_shape1), get_total_size(_shape2),
                 _pd_len, _pd_height, _pd_width, _output_len
                 , _mlu_border_output, _mlu_border_idx_output, _mlu_output)

            result = _mlu_output.numpy()
            result_border = _mlu_border_output.numpy()
            result_border_idx = _mlu_border_idx_output.numpy()

            #收尾
            s = set()
            for i in result_border_idx:
                s.add(i)

            for item in s:
                result[item] = math.pow(result[item], 1 / p)

            outputshape = []
            if keepdim:
                for item in _shape1:
                    outputshape.append(item)
                outputshape[dim_index] = 1
            else:
                for i in range(0, len(_shape1) - 1):
                    outputshape.append(_shape1[i])

            ret = result.reshape(outputshape)
            return ret

        return f


    shape1 = np.array(shape[0]).astype('int32')
    shape2 = np.array(shape[1]).astype('int32')
    _ori_input1 = np.random.uniform(low=1.5, high=1.5, size=shape1).astype(dtype.as_numpy_dtype)
    _ori_input2 = np.random.uniform(low=0, high=0, size=shape2).astype(dtype.as_numpy_dtype)

    mlu_start = time.time()
    pdist = mlu_pairwise_distance(p=p, eps=eps, keepdim=keepdim)
    mlu_ret = pdist(_ori_input1, _ori_input2)
    print('mlu cost ', time.time() - mlu_start)
    print(mlu_ret)

    
    print("============torch calc==================")

    cpu_start = time.time()
    pdist = torch.nn.PairwiseDistance(p=p, eps=eps, keepdim=keepdim)
    tensor1 = torch.Tensor(_ori_input1)
    tensor2 = torch.Tensor(_ori_input2)
    cpu_ret = pdist(tensor1, tensor2)
    print('cpu cost ', time.time() - cpu_start)

    print(cpu_ret)
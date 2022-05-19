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
import sys
import random
import numpy as np
import pytest
import bangpy
import bangpy as bp
from bangpy import tcp
from bangpy.common import load_op_by_type
from bangpy.platform.bang_config import TARGET
from bangpy.tcp.runtime import TaskType
from logaddexp import DTYPES,TARGET_LIST
sys.path.append("..")
from create_shape import *


test_shape_list = CreatShapeList(
    nram_single_buffer_size_by_byte = (512 - 40) * 1024 // 8,
    append_test_count = 50,
    max_dim_length = 5,
    each_dim_max_length = 64
)
@pytest.mark.parametrize(
    "shape",
    test_shape_list,
    #[(65,),]
)
@pytest.mark.parametrize(
    "dtype", DTYPES,
)

def test_logaddexp(target, shape, dtype):
    if target not in TARGET_LIST:
        return
    print("dtype->",dtype,"___shape->",shape)
    # origin input
    sub_shape = shape[random.randint(0, len(shape) - 1):len(shape)]
    data_x = np.random.uniform(low=-1000, high=1000, size=shape)
    data_y = np.random.uniform(low=-1000, high=1000, size=sub_shape)
    # data_x = np.random.uniform(low=-1000, high=1000, size=(1,))
    # data_y = np.random.uniform(low=-1000, high=1000, size=(9,2))
    def logaddexp(input_x,input_y):
        max_size_buffer = input_x
        min_size_buffer = input_y
        is_sub = True #是否是子集
        scale_up = 1 #缩放倍数
        is_single_element = False #是否存在单元素
        if len(max_size_buffer.shape) - len(min_size_buffer.shape) < 0 :#不同维度找出高维的
            max_size_buffer = input_y
            min_size_buffer = input_x
        if len(max_size_buffer.shape) ==1 and len(min_size_buffer.shape) == 1:#当同为一维时 根据数组长度确定哪个是大的
            if max_size_buffer.shape[0] - min_size_buffer.shape[0] < 0 :
                max_size_buffer = input_y
                min_size_buffer = input_x
        for i in range(len(min_size_buffer.shape)): #倒序比较 shape各元素
            #循环未结束 出现不同 说明短的不是长的子集  不能进行计算
            if max_size_buffer.shape[-1 - i] != min_size_buffer.shape[-1 - i] :
                is_sub = False
                break
        #特殊情况  当短的只有一个元素时是可以计算的
        if len(min_size_buffer.shape) == 1 and min_size_buffer.shape[0] == 1 :
            is_sub = True
            is_single_element =True
        if is_sub :
            if not is_single_element :#如果是多个元素 计算差值部分的乘积作为缩放短的缩放倍数
                for j in range(len(max_size_buffer.shape) - len(min_size_buffer.shape)) :
                    scale_up *= max_size_buffer.shape[ -1*len(min_size_buffer.shape) -j -1]
            else:#如果只有一个元素 则缩放倍数为长的shape各元素的乘积
                for k in max_size_buffer.shape:
                    scale_up *= k
            dev = bp.device(0)
            x = bp.Array(max_size_buffer.astype(dtype.as_numpy_dtype).flatten(), dev)
            y = bp.Array(
                np.tile(min_size_buffer.astype(dtype.as_numpy_dtype).flatten(),scale_up),
                dev
            )
            output_dev = bp.Array(np.zeros(max_size_buffer.size, dtype=dtype.as_numpy_dtype), dev)
            task_type = TaskType(TARGET(target).cluster_num)
            log_add_exp_func = load_op_by_type("LogAddExp", dtype.name)
            with tcp.runtime.Run(task_type):
                log_add_exp_func(x, y, output_dev)
            return output_dev.numpy().reshape(max_size_buffer.shape)
        else :
            print("need the same shape or sub shape")
    mlu_ret = logaddexp(data_x,data_y)
    ret2 = np.logaddexp(data_x, data_y)
    if dtype.name == "float16":
        bangpy.assert_allclose(mlu_ret, ret2.astype(dtype.as_numpy_dtype),rtol = 0.01, atol = 0.01)
    else:
        bangpy.assert_allclose(mlu_ret, ret2.astype(dtype.as_numpy_dtype),rtol = 0.001, atol = 0.01)

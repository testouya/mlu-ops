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
import numpy as np
import pytest
import time
import bangpy
from bangpy import tcp
from bangpy.common import utils, load_op_by_type
from bangpy.platform.bang_config import ALIGN_LENGTH, TARGET
from bangpy.tcp.runtime import TaskType
from sum import DTYPES, KERNEL_NAME, TARGET_LIST


@pytest.mark.parametrize(
    "shape", 
    [    
        #(268435456,),# 即(256*1024*1024)  float32 下 刚好为1G 两输入一输出 总共3G
        (3072,),
        # (10259,),
        # (1089,),
        #  (259,),
         #(992,),
        #  (31,)
    ],
)
@pytest.mark.parametrize(
    "dtype", DTYPES,
)
def test_sum(target, shape, dtype):
    if target not in TARGET_LIST:
        return
    
   
    a = []
    for i in range(shape[0]):
        a.append(i)
    data_in0 = np.array(a)
    #data_in0 = np.ones(shape)
    #data_in0 = np.random.uniform(low=-10,high=10,size=shape)
   

    data_out =data_in0.astype(dtype.as_numpy_dtype)
    dev = bangpy.device(0)
    # set I/O data
    data_in0_dev = bangpy.Array(data_in0.astype(dtype.as_numpy_dtype), dev)
    data_out_dev = bangpy.Array(np.zeros(data_out.shape, dtype.as_numpy_dtype), dev)
    f1 = load_op_by_type(KERNEL_NAME, dtype.name)
    f1(data_in0_dev,1024,3, data_out_dev)

    #print("input：",data_in0_dev)
    print("output",data_out_dev.asnumpy()[0])
    print("np_sum->",np.sum(data_in0))
    # print("shape is ->",shape)
    # evaluator = f1.time_evaluator(number=10,repeat=1,min_repeat_ms=0)#使用 evaluator进行分析
    # print('time consuming : %f ms' % (evaluator(data_in0_dev, data_out_dev).mean* 1e3))#测试并打印

    

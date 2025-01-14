# BANGPy PairwiseDistance 算子开发设计方案

- #### 文档基本信息

| 算子名称     | PairwiseDistance              |
| ----------- | -------------- |
| 编制人/日期  | testouya/2022-5-18 |
| 审批人/日期  |              |

- #### 修改记录

| 修订人           | 修订日期    | 修订描述 |
| --------------- | ---------- | ------- |
| testouya  | 2022-5-18 | 首次提交 |

- #### 内容描述

本文档为 `PairwiseDistance` 算子的设计文档，包括需求分析、接口设计、方案设计、性能优化记录和方案实施部分。

## 1 需求分析

### 1.1 算子需求分析

| 算子功能简介               | 计算两个张量的pairwise_distance                   |
| ------------------------ | ----------------------------------------|
| 需求来源                  | 为bangpy-ops提供算子demo                  |
| 应用网络                  |                                  |
| 输入数据类型               | 支持float和half                            |
| 输入 Shape                | input1: [ length, N ]; input2: [ length, N ]  |
| 输入 Layout               | input1: ARRAY; input2: ARRAY            |
| 输出数据类型               | float,half                             |
| 输出 Shape                | [ length, N ]                               |
| 输出 Layout               | ARRAY                                    |

### 1.2 算子功能和应用场景描述

功能：计算两个张量的pairwise_distance

应用场景：ResNet等

### 1.3 算子输入输出参数要求

| 参数   | 语义                  | 类型（输入/输出）| 支持类型     | 物理布局 | 规模限制      |
| ------ | --------------------- | -------------    | -----------  | ------   | --------      |
| input1 | 多维buffer | 输入     |  float,half              | ARRAY        |  无      | --------      |
| input2 | 多维buffer | 输入     |  float,half              | ARRAY        |  无      | --------      |
| output | 多维buffer | 输出     |  float,half              | ARRAY        |  无      | --------      |

### 1.4 算子限制

| 限制类型       | 详细说明                    |
| ------------   | -----------------------     |
| 数据类型限制   | float,half   |
| 布局限制       | 仅支持ARRAY的layout         |
| 规模限制       | 无                            |

### 1.5 验收标准

#### 1.5.1 精度验收标准

本算子属于 `算术` 类算子，验收标准为 diff3=3e-3。

#### 1.5.2 性能验收标准

待定。

## 2 算子接口设计

### 2.1 参考接口

- pytorch

```python
torch.nn.PairwiseDistance(p=2.0, eps=1e-06, keepdim=False)
```

### 2.2 接口设计

```python
pdist = PairwiseDistance(p=2.0, eps=1e-06, keepdim=False)
```

p 为计算范数时，指数的值
eps 为避免除零而给结果加的微小偏移
keepdim 为bool值，决定是否保留原始数据维度

## 3 实现方案设计

### 3.1 实现方案

1 将输入数据压平为一维张量后，传入mlu，将数据平均分配在多核中。
首先计算两个张量的差，如果其中a张量比b张量长，则将b连续拷贝多份，变成和a长度相等（a的长度必须是b的整数倍）
每个核会算出自己要计算的数据起止地址，将数据拷贝到nram中，进行计算。


a: |-----------------------|
b: |-------|

==>

a: |-----------------------|
b: |-------|-------|-------|


2 按照最后一个维度，将该tensor划分，拿到所有子张量
比如最后一个维度长度为2，张量总长为30，那么子张量就有15个。
t: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
将这些子张量平均分配给多核，分别计算(这里可能存在某个子张量过长，以至于分配到了两个，甚至多个核上面)

如果一个张量x, 维度是 [2, 3, 4]
如果要在第二个维度处理子张量，
第i, j 个子张量为
t = [
x[i, 0, j], 
x[i, 1, j], 
x[i, 2, j] 
]

3 每个核计算时候检查一下子张量的长度是不是超过了nram的大小，如果超过了，跳转到4，否则，跳转到6

4 将该子张量的数据分段拷贝到nram中，计算范数，缓存，然后再拷贝下一段，直到一个子张量计算完毕

5 某些张量很长，可能跨越了核，单个核可能只会计算一个子张量的前半部分，中间，或者后半部分，将其缓存到 mlu_border_output 中，跳转到8

6 将若干子张量拷贝到nram中，计算范数

7 某些子张量可能跨越了核，将这部分数据缓存
子张量跨越core了，前后两部分分别在不同core上计算的，前半部分和后半部分要保存

.----tensor---.----tensor---.----tensor---.----tensor---.----tensor---.----tensor---.----tensor---.
|----------core1---------|----------core2--------|-----------core3-------|-------------core4------|

8 统一处理，将 mlu_border_output 中缓存的数据拼接起来，得到这个子张量最终的distance

9 拷贝回cpu，执行reshape操作。


### 3.3 拆分(任务拆分，多核拆分)

采用的tasktype固定为UNION1，数据拆分到多核内计算。

### 3.4 性能优化设计
### 3.2 伪代码实现

```python

subtract_tensor = input_tensor1 - intput_tensor2

sub_tensors = get_last_dim(subtract_tensor)  #按照最后一个维度，将该tensor划分，拿到所有子张量

for t in sub_tensors:
    length = calc_distance(t)
    _mlu_output.append(length)
```

### 3.5 可维护性设计


### 3.6 测试用例设计
参见test_pairwise_distance测试报告

### 3.7 算子防呆检查

除host端自动生成的部分参数防呆检查外，暂不需要进行其他的防呆检查。

## 4 算子性能优化记录

### 4.1 当前存在问题的规模说明

| 提交日期  | 问题规模 | 问题描述 | 是否已修复 |
| --------- | -------- | -------- | ---------- |
|           |          |          |            |

### 4.2 已经过优化的规模说明

| 提交日期  | 修复规模 | 修复问题 |
| --------- | -------- | -------- |
|           |          |          |

## 5 方案实施

### 5.1 开发测试计划

2022.6.30 算子入库

### 5.2 风险分析

暂无。
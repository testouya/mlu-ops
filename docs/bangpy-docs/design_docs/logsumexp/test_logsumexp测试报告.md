**_本测试报告模板是希望能帮助算子开发者在完成算子开发后进行有效充分的自检，开发出功能、性能都满足要求的高质量算子。_**

# 1. 功能测试
测试以下输入场景

1 子向量长度超过nram容量  
2 输入张量总长度小于核数  
3 子向量长度小于nram容量  
4 输入张量维度大于10  
5 输入子向量正好填满一个nram，总数为1（128字节对齐）  
6 输入子向量正好等于一个nram的长度减一，总数为1（先按128字节对齐再减一）  
7 输入子向量长度为1，但是数量很大  
8 随机生成用例，反复执行1000遍，检查有无segment fault  
9 随机生成shape



### 1.1 精度验收标准

暂无

### 1.2 新特性测例 CheckList（新特性添加必填）

暂无

### **1.3 算子防呆测试**

| 测试点                       | 验收标准 | 测试结果（出错信息）   |
| -----------------------------| -------- | -------------------- |
| 输入维度数值超出输入张量维度   |正常报错  |     通过               |


# 2. 性能测试（输出 2 个部分内容）

暂无

### 2.1 输出算子的 io 利用率、计算效率

暂无

# 3. 总结分析

1 该算子用到了指数函数，该函数计算准确性存疑，需要进一步确认  
2 计算速度并不会随着核数线性增长  
3 大循环会造成程序吊死  
4 对大量短向量求和缺乏相应api，用基础函数计算，速度较慢

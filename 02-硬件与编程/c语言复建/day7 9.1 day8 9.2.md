# Day 7：宏与预处理器

## 1. 宏是文本替换

```
#define GPIO_PIN_5 (1u << 5u)
#define ADD(a, b) ((a) + (b))
```

宏在编译前展开，通常不单独占用RAM。

```
ADD(3u, 5u)
```

展开：

```
((3u) + (5u))
```

结果为8。

---

## 2. 宏参数要加括号

推荐：

```
#define ADD(a, b) ((a) + (b))
```

原则：

```
每个参数加括号
整个表达式再加括号
```

避免运算符优先级改变原本含义。

---

## 3. STM32位操作宏

```
#define SET_BIT(REG, BIT)   ((REG) |= (BIT))
#define CLEAR_BIT(REG, BIT) ((REG) &= ~(BIT))
#define READ_BIT(REG, BIT)  ((REG) & (BIT))
```

作用：

```
SET_BIT    → 目标位置1
CLEAR_BIT  → 目标位清0
READ_BIT   → 读取目标位
```

`READ_BIT`结果：

```
0      → 目标位为0
非0    → 目标位为1
```

结果不一定等于数字1，可能等于掩码值。

---

## 4. 重点：修改寄存器和读取寄存器

修改第2位：

```
RCC->APB2ENR |= 1u << 2u;
```

执行：

```
读取APB2ENR
→ 将第2位置1
→ 写回APB2ENR
```

它会修改寄存器。

读取第2位：

```
tmpreg =
    RCC->APB2ENR & (1u << 2u);
```

执行：

```
读取APB2ENR第2位
→ 将结果保存到tmpreg
```

它不会修改`APB2ENR`。

在时钟宏中，这次读回同时形成一个短延迟。

> `|=`表示读取、修改、写回；单独的`&`只进行读取和计算。

---

## 5. 重点：`(void)tmpreg`

```
(void)tmpreg;
```

作用：

```
明确表示故意忽略tmpreg的值
→ 避免“变量未使用”警告
```

它不会：

- 清零`tmpreg`；
    
- 删除`tmpreg`；
    
- 把它变成空指针；
    
- 修改硬件寄存器。
    

```
(void)0u;
```

表示一个合法的“什么也不做”表达式。

---

## 6. 多语句宏

```
#define DEVICE_START()     \
    do                      \
    {                       \
        EnableClock();      \
        EnableDevice();     \
    } while (0)
```

`do...while(0)`：

```
只执行一次
把多条语句包装成一个整体
可以安全放入if/else中
调用后可以正常添加分号
```

重点：

> 宏中不是只能写`do...while`。宏内部可以包含`if`、`for`等语句；多语句宏只是通常用`do...while(0)`进行外层包装。

---

## 7. 宏的副作用

```
#define SQUARE(x) ((x) * (x))
```

危险调用：

```
SQUARE(i++)
```

展开：

```
((i++) * (i++))
```

一次宏调用中，`i++`已经执行了两次，并且执行顺序不可靠，属于未定义行为。

> 不要把`i++`、`i--`或有副作用的函数调用传给会重复使用参数的宏。

安全写法：

```
uint32_t temp = i++;
uint32_t result = SQUARE(temp);
```

---

## 8. 条件编译

```
#ifdef DEBUG
printf("debug\n");
#endif
```

```
定义DEBUG
→ 调试代码参与编译

没有定义DEBUG
→ 调试代码不会进入最终程序
```

区别：

```
if      → 程序运行时判断
#ifdef  → 编译前选择代码
```

---

## 9. 重点：断言宏

```
#ifdef USE_FULL_ASSERT

#define assert_param(expr) \
    ((expr) ? (void)0u : assert_failed())

#else

#define assert_param(expr) ((void)0u)

#endif
```

启用`USE_FULL_ASSERT`：

```
expr为真  → 什么也不做
expr为假  → 调用assert_failed()
```

未启用`USE_FULL_ASSERT`：

```
assert_param(expr)
```

展开为：

```
((void)0u)
```

不执行检查。

> 两个`assert_param`定义不会同时存在，预处理器只保留符合条件的一个。

---

## 10. STM32时钟使能宏流程

```
SET_BIT(APB2ENR, IOPAEN)
→ 设置第2位，开启GPIOA时钟

tmpreg = READ_BIT(APB2ENR, IOPAEN)
→ 读回第2位并形成短延迟

(void)tmpreg
→ 故意忽略读取结果，避免警告

do...while(0)
→ 将多条语句包装成安全整体
```

---

## 11. 今日学习成果

已经掌握：

- 宏是编译前的文本替换；
    
- 带参数宏的括号规则；
    
- `SET_BIT`、`CLEAR_BIT`和`READ_BIT`；
    
- 修改寄存器与读回寄存器的区别；
    
- `(void)tmpreg`的作用；
    
- 多语句宏使用`do...while(0)`的原因；
    
- 宏参数重复求值的风险；
    
- `#ifdef`条件编译；
    
- STM32时钟使能宏的完整流程。
    

需要继续巩固：

```
READ_BIT只是读取，不会修改寄存器。

读回寄存器不只是延时，
它会真正读取目标位并保存到tmpreg。

SQUARE(i++)一次展开就包含两个i++，
不是因为宏以后被调用了多次。

条件编译只保留一个宏定义，
不是运行时在两个定义中选择。
```
# Day 8：作用域、生命周期与内存区域

## 1. 作用域与生命周期

```
作用域   → 在代码的哪些位置可以使用变量名
生命周期 → 变量在内存中存在多长时间
```

普通局部变量：

```
void Test(void)
{
    uint32_t value = 0u;
}
```

```
作用域：函数内部
生命周期：本次函数调用期间
通常位于：栈
```

---

## 2. `static`局部变量

```
void Count(void)
{
    static uint32_t count = 0u;
    count++;
}
```

```
作用域：仍然只在函数内部
生命周期：整个程序运行期间
初始化：通常只进行一次
```

连续调用：

```
第1次：count = 1
第2次：count = 2
第3次：count = 3
```

重点：

> `static`局部变量的作用域仍是局部，但生命周期变成整个程序。

---

## 3. 文件级 `static` 与 `extern`

在`device.c`中：

```
static uint32_t count = 0u;
```

表示：

```
生命周期：整个程序
可见范围：只在device.c内部
其他.c文件不能通过extern访问
```

普通全局变量：

```
uint32_t system_tick = 0u;
```

其他文件可以声明：

```
extern uint32_t system_tick;
```

区别：

```
uint32_t system_tick = 0u;
→ 定义，真正分配空间

extern uint32_t system_tick;
→ 声明，表示变量在其他文件中定义
```

---

## 4. 程序区域与物理存储器

这是最容易混淆的地方：

```
Flash、SRAM
→ 芯片中的物理存储器

.text、.rodata、.data、.bss、栈、堆
→ 程序对存储空间的用途划分
```

典型关系：

```
Flash
├── .text：程序指令
├── .rodata：只读数据
└── .data的初始值副本

SRAM
├── .data
├── .bss
├── 栈
└── 堆
```

---

## 5. `.data`与`.bss`

全局变量或`static`变量：

```
uint32_t a = 5u;        // .data
uint32_t b;             // .bss
static uint32_t c = 0u; // .bss
```

判断规则：

```
非零初始化
→ .data

初始化为0或没有显式初始化
→ .bss
```

程序启动时：

```
.data
→ 从Flash复制初始值到SRAM

.bss
→ 在SRAM中清零
```

---

## 6. 栈与堆

### 栈

通常保存：

- 普通局部变量；
    
- 函数调用信息；
    
- 部分临时数据。
    

```
进入函数 → 使用栈空间
退出函数 → 栈空间可以被重新使用
```

过大的局部数组和过深的递归可能造成栈溢出。

### 堆

使用`malloc()`动态申请：

```
uint8_t *buffer = malloc(32u);
```

使用后释放：

```
free(buffer);
buffer = NULL;
```

STM32中应谨慎使用堆，因为可能出现：

- 内存不足；
    
- 内存泄漏；
    
- 内存碎片；
    
- 运行时间和内存占用不确定。
    

---

## 7. 指针变量与目标数据的位置

```
void Test(void)
{
    uint8_t *buffer = malloc(32u);
}
```

```
指针变量buffer本身
→ 普通局部变量
→ 通常在栈中

buffer指向的32字节空间
→ 由malloc申请
→ 位于堆中
```

重点：

> 指针变量的位置，不等于它指向的数据的位置。

---

## 8. 快速判断口诀

```
普通局部变量 → 栈

全局/static且非零初始化 → .data

全局/static且为0或未初始化 → .bss

程序指令 → .text

只读常量 → .rodata

malloc申请 → 堆
```

## 9. 学习成果

已经掌握：

- 区分作用作用域和生命周期；
    
- 理解普通局部变量与`static`局部变量；
    
- 理解文件级`static`与`extern`；
    
- 能判断`.data`和`.bss`；
    
- 能区分Flash、SRAM与程序区域；
    
- 能区分栈中的指针变量和堆中的动态数据。
    

重点复习：

```
static局部变量：
作用域是局部，生命周期是整个程序。

文件级static：
只允许当前.c文件访问。

.data和.bss运行时通常都在SRAM。

指针变量可以在栈中，
但它指向的数据可以在堆中。
```
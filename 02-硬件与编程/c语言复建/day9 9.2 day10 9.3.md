# Day 9：C语言多文件工程

## 1. 文件分工

```
.h文件   → 对外声明“有什么功能”
.c文件   → 具体实现“功能怎么完成”
main.c   → 调用各个模块
```

例如：

```
Project
├── main.c
├── led.c
└── led.h
```

---

## 2. 函数声明与定义

函数声明：

```
void LED_On(void);
```

只告诉编译器函数的名称、参数和返回类型。

函数定义：

```
void LED_On(void)
{
    // 函数具体实现
}
```

包含函数体，真正生成函数代码。

通常：

```
led.h → 放公开函数声明
led.c → 放函数定义
```

---

## 3. 头文件保护

```
#ifndef LED_H
#define LED_H

void LED_On(void);

#endif
```

逐行理解：

```
#ifndef LED_H
→ 如果LED_H还没有定义

#define LED_H
→ 定义LED_H，标记头文件已经处理过

// 头文件内容

#endif
→ 结束条件区域
```

第一次包含：

```
LED_H未定义
→ 保留头文件内容
→ 定义LED_H
```

再次包含：

```
LED_H已经定义
→ 跳过头文件内容
```

重点：

> `LED_H`只是“头文件已经处理过”的宏标记，不是变量或文件对象。

---

## 4. 头文件保护的范围

头文件保护可以防止：

```
同一个.c文件中重复包含同一个头文件
```

但不能防止：

```
不同.c文件分别包含头文件后，
各自得到头文件中的变量定义
```

所以普通头文件中不应该直接定义全局变量。

---

## 5. 全局变量与 `extern`

错误写法：

```
// led.h
uint32_t led_state = 0u;
```

如果多个`.c`文件包含`led.h`，可能产生多个`led_state`定义，链接时报重复定义。

正确做法：

```
// led.c：定义一次
uint32_t led_state = 0u;
```

```
// led.h：只声明
extern uint32_t led_state;
```

区别：

```
uint32_t led_state = 0u;
→ 定义，真正分配存储空间

extern uint32_t led_state;
→ 声明，表示变量在其他文件中定义
```

---

## 6. 使用 `static`封装模块

推荐把模块内部状态隐藏在`.c`文件中：

```
// led.c
static uint32_t led_state = 0u;
```

其他文件不能直接访问，只能通过公开函数操作：

```
void LED_On(void);
void LED_Off(void);
uint32_t LED_GetState(void);
```

文件级`static`：

```
static变量 → 模块私有数据
static函数 → 模块私有功能
```

例如：

```
// led.c
static void LED_WriteHardware(void)
{
    // 模块内部辅助函数
}
```

它应该留在`led.c`中，不放在`led.h`中。

---

## 7. `.h`文件应该放什么

适合放：

- 对外函数声明；
    
- 对外使用的结构体和枚举；
    
- 必要的宏；
    
- 必要的`extern`声明。
    

通常不放：

- 普通函数的完整实现；
    
- 全局变量定义；
    
- 模块私有变量；
    
- `static`私有辅助函数。
    

原则：

```
外部需要知道 → 放.h
仅当前模块使用 → 放.c
```

---

## 8. 头文件依赖

如果头文件使用`uint32_t`：

```
#ifndef LED_H
#define LED_H

#include <stdint.h>

void LED_SetDelay(uint32_t delay_ms);

#endif
```

头文件应该自己包含所需依赖。

> 不要依赖调用者碰巧提前包含了其他头文件。

---

## 9. 编译与链接

多文件工程通常分两步：

```
main.c → 编译 → main.o
led.c  → 编译 → led.o
                  ↓
                链接
                  ↓
               最终程序
```

编译阶段：

```
检查单个.c文件的语法和类型
```

链接阶段：

```
把不同目标文件中的函数和变量连接起来
```

只有声明，没有实现：

```
void LED_On(void);
```

但没有任何`.c`文件定义`LED_On()`：

```
编译可能通过
链接时报未定义引用
```

多个地方定义同一个全局符号：

```
链接时报重复定义
```

---

## 10. GCC编译多文件

目录：

```
day09
├── main.c
├── led.c
└── led.h
```

编译：

```
gcc -std=c17 -Wall -Wextra -Wpedantic main.c led.c -o main.exe
```

运行：

```
.\main.exe
```

如果忘记加入`led.c`：

```
gcc main.c -o main.exe
```

链接器可能找不到`LED_On()`的实现。

---

## 11. STM32模块结构

### `led.h`

```
#ifndef LED_H
#define LED_H

typedef enum
{
    LED_OFF = 0,
    LED_ON
} LED_State;

void LED_On(void);
void LED_Off(void);
LED_State LED_GetState(void);

#endif
```

### `led.c`

```
#include "led.h"

static LED_State led_state = LED_OFF;

static void LED_WriteHardware(void)
{
    // 私有硬件操作
}

void LED_On(void)
{
    led_state = LED_ON;
    LED_WriteHardware();
}

void LED_Off(void)
{
    led_state = LED_OFF;
    LED_WriteHardware();
}

LED_State LED_GetState(void)
{
    return led_state;
}
```

---

## 12. 重点记忆

```
.h负责公开声明，
.c负责具体实现。

函数声明没有函数体，
函数定义具有函数体。

头文件保护防止重复包含，
但不能防止不同.c文件重复定义变量。

全局变量：
在一个.c中定义一次，
需要时在.h中使用extern声明。

模块私有变量和函数：
使用static并留在.c中。

只有声明没有实现：
通常在链接阶段报错。
```

## 13. 学习成果

已经掌握：

- `.c`与`.h`的职责；
    
- 函数声明和定义；
    
- 头文件保护；
    
- `extern`全局变量声明；
    
- 文件级`static`模块封装；
    
- 编译与链接的区别；
    
- GCC多文件编译方法。
    

重点复习：

```
头文件保护宏只是标记。

static私有函数应放在.c中，
不应该公开到.h中。

extern通常只是声明，
真正定义只能保留一份。

编译器分别处理.c文件，
链接器最后寻找函数和变量的实现。
```
# Day 10：数组、字符串与 UART 缓冲区

## 1. 数组容量与下标

```
uint8_t buffer[5];
```

- 数组容量：5个元素
    
- 有效下标：`0～4`
    
- 最后一个有效下标：`容量 - 1`
    
- `buffer[5]`属于越界访问
    

C语言通常不会自动检查数组边界。

## 2. 计算数组元素数量

```
uint32_t values[5];

uint32_t count =
    sizeof(values) / sizeof(values[0]);
```

结果：

```
sizeof(values) = 20
sizeof(values[0]) = 4
count = 5
```

## 3. 数组传入函数

函数形参中的数组：

```
void Process(uint8_t data[])
```

会调整为指针，等价于：

```
void Process(uint8_t *data)
```

所以函数内部：

```
sizeof(data)
```

得到的是指针大小，不是原数组大小。

正确做法：

```
void Process(
    const uint8_t *data,
    uint16_t length);
```

- `data`：数组首元素地址
    
- `length`：有效数据长度
    
- `const`：函数不能通过`data`修改数组
    

## 4. 字符串结束符

```
char text[] = "OK";
```

实际内容：

```
'O' 'K' '\0'
```

所以：

```
sizeof(text) // 3
strlen(text) // 2
```

区别：

- `sizeof`：数组占用的总字节数，包含`\0`
    
- `strlen`：`\0`之前的字符数量，不包含`\0`
    

```
'\0' // 数值0，字符串结束符
'0'  // 字符0，ASCII值通常为48
```

## 5. 字符数组不一定是字符串

```
char data[5] =
{
    'H', 'e', 'l', 'l', 'o'
};
```

它没有`\0`，所以只是字符数组，不能安全地用于：

```
strlen(data);
printf("%s", data);
```

正确写法：

```
char data[] = "Hello";
```

或者：

```
char data[6] =
{
    'H', 'e', 'l', 'l', 'o', '\0'
};
```

## 6. 字符串与二进制数据

二进制数据中的`0x00`可能是有效数据：

```
uint8_t packet[] =
{
    0xAAu,
    0x00u,
    0x55u
};
```

不能使用：

```
strlen((char *)packet);
```

因为`strlen()`遇到`0x00`就会停止。

应该使用明确长度：

```
sizeof(packet) // 3
```

区别：

```
字符串 → 使用\0表示结束
二进制 → 0x00也可能是有效数据
```

## 7. 缓冲区容量与有效长度

```
uint8_t rx_buffer[16];
uint16_t rx_length = 0u;
```

```
sizeof(rx_buffer) → 总容量16字节
rx_length         → 当前有效字符数量
```

容量不等于有效数据长度。

## 8. 字符如何逐个存入

核心代码：

```
rx_buffer[rx_length++] = byte;
rx_buffer[rx_length] = '\0';
```

假设：

```
rx_length = 0
byte = 'L'
```

第一句等价于：

```
rx_buffer[0] = 'L';
rx_length = 1u;
```

第二句：

```
rx_buffer[1] = '\0';
```

结果：

```
'L' '\0'
```

继续收到`'E'`：

```
'L' 'E' '\0'
rx_length = 2
```

重点：

> 新字符覆盖原来的`\0`，长度增加后，再在新位置补上`\0`。

## 9. 接收 `"LED ON"`

依次接收：

```
'L' 'E' 'D' ' ' 'O' 'N'
```

缓冲区变化：

```
收到'L' → "L"      length=1
收到'E' → "LE"     length=2
收到'D' → "LED"    length=3
收到' ' → "LED "   length=4
收到'O' → "LED O"  length=5
收到'N' → "LED ON" length=6
```

空格也是普通字符，需要存入数组。

## 10. 处理 `\r\n`

串口工具可能发送：

```
LED ON\r\n
```

收到`\r`：

```
确认字符串末尾有\0
→ 处理"LED ON"
→ rx_length清零
→ rx_buffer[0]写入\0
```

紧接着收到`\n`：

```
rx_length已经是0
→ 不重复处理空命令
```

因此需要判断：

```
if (rx_length > 0u)
{
    ProcessCommand(rx_buffer);

    rx_length = 0u;
    rx_buffer[0] = '\0';
}
```

`\r`和`\n`作为结束标志，通常不存入命令字符串。

## 11. 防止字符串越界

对于：

```
uint8_t buffer[8];
```

字符串最多保存：

```
7个普通字符 + 1个'\0'
```

正确检查：

```
if (length < sizeof(buffer) - 1u)
{
    buffer[length++] = byte;
    buffer[length] = '\0';
}
```

不能写成：

```
if (length < sizeof(buffer))
```

因为当`length == 7`时：

```
buffer[7]写入字符
length变成8
buffer[8]写入\0 → 越界
```

## 12. 二进制缓冲区的边界

二进制缓冲区不需要给`\0`预留空间：

```
uint8_t packet[8];

if (length < sizeof(packet))
{
    packet[length++] = byte;
}
```

```
字符串缓冲区 → 最多保存capacity - 1个字符
二进制缓冲区 → 最多保存capacity个字节
```

## 13. 清空缓冲区

逻辑清空：

```
rx_length = 0u;
rx_buffer[0] = '\0';
```

旧字符可能仍在后面的内存中，但字符串函数看到第一个`\0`就会停止，因此逻辑上已经为空。

完全清零：

```
memset(
    rx_buffer,
    0,
    sizeof(rx_buffer));

rx_length = 0u;
```

## 14. 字符串比较

```
if (strcmp(
        (char *)rx_buffer,
        "LED ON") == 0)
{
    // 两个字符串相同
}
```

`strcmp()`返回`0`表示内容相同。

不能这样比较：

```
rx_buffer == "LED ON"
```

因为`==`比较的是地址，不是字符串中的字符。

强制转换：

```
(char *)rx_buffer
```

只改变编译器解释地址的方式，不会复制或修改数组。

## 15. 简化版UART接收流程

```
void UART_ReceiveByte(uint8_t byte)
{
    if ((byte == '\r') || (byte == '\n'))
    {
        if (rx_length > 0u)
        {
            rx_buffer[rx_length] = '\0';

            ProcessCommand(rx_buffer);

            rx_length = 0u;
            rx_buffer[0] = '\0';
        }

        return;
    }

    if (rx_length < sizeof(rx_buffer) - 1u)
    {
        rx_buffer[rx_length++] = byte;
        rx_buffer[rx_length] = '\0';
    }
    else
    {
        rx_length = 0u;
        rx_buffer[0] = '\0';
    }
}
```

流程：

```
收到普通字符
→ 检查剩余空间
→ 存入当前length位置
→ length增加1
→ 在新位置补\0

收到\r或\n
→ 判断是否存在有效命令
→ 处理命令
→ 清空缓冲区
→ 等待下一条命令
```

## 16. 重点记忆

```
数组下标从0开始。

数组传入函数后会变成指针，
所以必须额外传入有效长度。

字符串必须以\0结尾。

字符串容量为N时，
最多保存N-1个普通字符。

二进制数据可以包含0x00，
不能使用strlen计算长度。

新字符覆盖旧的\0，
length增加后再补新的\0。

\r和\n表示命令结束，
通常不存入字符串。

strcmp返回0表示字符串相同。

指针变量保存地址，
缓冲区本身保存实际字符。
```

## 17. 今日学习成果

已经掌握：

- 数组容量、元素数量和有效下标
    
- 数组越界风险
    
- 数组传参后变成指针
    
- `sizeof`与`strlen`的区别
    
- 字符串结束符`\0`
    
- 字符串与二进制数据的区别
    
- UART逐字节保存字符
    
- `rx_length++`的执行顺序
    
- 字符串缓冲区的边界检查
    
- `\r\n`命令结束处理
    
- 缓冲区清空
    
- 使用`strcmp()`识别命令
    

需要重点复习：

```
rx_buffer[rx_length++] = byte
→ 先用旧length作为下标
→ 再把length加1

rx_buffer[rx_length] = '\0'
→ 在新位置补字符串结束符

字符串缓冲区必须预留一个位置给\0。

数组传入函数后只有首地址，
函数不会自动知道数组长度。
```
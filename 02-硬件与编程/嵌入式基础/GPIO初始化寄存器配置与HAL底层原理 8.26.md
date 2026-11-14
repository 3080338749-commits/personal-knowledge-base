---

tags:

- STM32
    
- GPIO
    
- HAL库
    
- 寄存器
    
- C语言  
    date: 2026-08-26
    

---

# STM32 GPIO初始化与输出控制

## 1. 使用GPIO的完整流程

以PA5输出高电平为例：

```
开启GPIOA时钟
→ 配置PA5的工作模式
→ 将配置写入GPIOA寄存器
→ 控制PA5输出高低电平
```

HAL代码：

```
GPIO_InitTypeDef GPIO_InitStruct = {0};

/* 开启GPIOA时钟 */
__HAL_RCC_GPIOA_CLK_ENABLE();

/* 配置PA5 */
GPIO_InitStruct.Pin   = GPIO_PIN_5;
GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
GPIO_InitStruct.Pull  = GPIO_NOPULL;
GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;

HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

/* PA5输出高电平 */
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
```

---

## 2. 开启GPIOA时钟

```
__HAL_RCC_GPIOA_CLK_ENABLE();
```

这是一个宏，不是普通函数。

底层核心操作：

```
RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
```

GPIOA时钟使能位是`APB2ENR`的第2位：

```
RCC->APB2ENR |= (1u << 2);
```

最底层可理解为：

```
*(volatile uint32_t *)0x40021018u |= 0x00000004u;
```

执行过程：

```
读取APB2ENR原值
→ 将第2位置1
→ 保持其他位不变
→ 写回APB2ENR
→ GPIOA获得工作时钟
```

之所以使用`|=`而不是`=`，是为了避免清除其他已经开启的外设时钟。

---

## 3. 时钟宏中的其他代码

官方宏还会读回一次寄存器：

```
volatile uint32_t tmpreg;

tmpreg = RCC->APB2ENR & RCC_APB2ENR_IOPAEN;
(void)tmpreg;
```

作用：

- 读回寄存器，形成一个短延迟；
    
- 确保时钟开启操作已经到达外设总线；
    
- `volatile`防止编译器随意删除读取操作；
    
- `(void)tmpreg`避免“变量未使用”警告。
    

宏使用：

```
do
{
    /* 多条语句 */
}
while (0);
```

是为了让多条语句组成的宏能够像一条普通语句一样安全使用。
# HAL时钟宏的保护代码

```
volatile uint32_t tmpreg;

tmpreg = RCC->APB2ENR & RCC_APB2ENR_IOPAEN;
(void)tmpreg;
```

作用：

```
开启GPIOA时钟
→ 读回时钟寄存器
→ 产生短暂等待
→ 确保时钟设置已经生效
```

- `tmpreg`：临时保存读取结果。
    
- `volatile`：保证操作不会被编译器省略。
    
- `(void)tmpreg`：避免“变量未使用”警告。
    

## `do while (0)`

```
do
{
    /* 多条宏语句 */
}
while (0);
```

作用：

- `while (0)`使代码只执行一次，不会循环；
    
- 将宏中的多条语句包装成一条完整语句；
    
- 让宏能够安全地用于`if/else`等位置。
    

## 总结

```
tmpreg：确保时钟操作可靠生效
do while(0)：安全包装多条宏语句
```

---

## 4. GPIO端口与引脚的选择

```
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
```

其中：

```
GPIOA                  → 选择GPIOA端口
GPIO_InitStruct.Pin    → 选择端口中的引脚
```

例如：

```
GPIO_InitStruct.Pin = GPIO_PIN_5;
```

两者结合：

```
GPIOA + GPIO_PIN_5 = PA5
```

同一个引脚掩码配合不同端口：

```
GPIOA + GPIO_PIN_5 = PA5
GPIOB + GPIO_PIN_5 = PB5
GPIOC + GPIO_PIN_5 = PC5
```

---

## 5. GPIO_PIN_5是位掩码

```
GPIO_PIN_5
```

不是数字5，而是：

```
GPIO_PIN_5 == (1u << 5)
GPIO_PIN_5 == 0x0020
```

二进制：

```
0000 0000 0010 0000
```

只有第5位为1，因此可以准确选择5号引脚。

---

## 6. GPIO_TypeDef与GPIO_InitTypeDef

### GPIO_TypeDef

用于描述GPIO硬件寄存器的排列：

```
typedef struct
{
    volatile uint32_t CRL;
    volatile uint32_t CRH;
    volatile uint32_t IDR;
    volatile uint32_t ODR;
    volatile uint32_t BSRR;
    volatile uint32_t BRR;
    volatile uint32_t LCKR;
} GPIO_TypeDef;
```

`GPIOA`是一个`GPIO_TypeDef *`类型的结构体指针表达式：

```
#define GPIOA ((GPIO_TypeDef *)0x40010800)
```

作用：

> 通过结构体成员偏移找到真实硬件寄存器。

### GPIO_InitTypeDef

用于保存用户希望使用的配置：

```
typedef struct
{
    uint32_t Pin;
    uint32_t Mode;
    uint32_t Pull;
    uint32_t Speed;
} GPIO_InitTypeDef;
```

```
GPIO_InitTypeDef GPIO_InitStruct;
```

这里的`GPIO_InitStruct`是普通结构体变量，位于RAM中，本身不会直接修改硬件。

最短区别：

```
GPIO_InitTypeDef → 保存“想怎么配置”
GPIO_TypeDef     → 找到“硬件应该写到哪里”
```

---

## 7. CRL和CRH的作用

STM32F103中，每个引脚需要4位配置工作模式。

```
CRL：配置0～7号引脚
CRH：配置8～15号引脚
```

### CRL布局

```
位31～28 → PA7
位27～24 → PA6
位23～20 → PA5
位19～16 → PA4
位15～12 → PA3
位11～8  → PA2
位7～4   → PA1
位3～0   → PA0
```

PA5配置起始位：

```
5 × 4 = 20
```

所以PA5使用CRL第20～23位。

---

## 8. 每个引脚的4个配置位

```
CNF1 CNF0 MODE1 MODE0
```

### MODE位

|MODE|含义|
|---|---|
|`00`|输入模式|
|`01`|10 MHz输出|
|`10`|2 MHz输出|
|`11`|50 MHz输出|

### 输出模式下的CNF位

|   |   |
|---|---|
|CNF|含义|
|`00`|通用推挽输出|
|`01`|通用开漏输出|
|`10`|复用推挽输出|
|`11`|复用开漏输出|

2 MHz通用推挽输出：

```
CNF  = 00
MODE = 10
组合 = 0010
```

底层配置PA5：

```
GPIOA->CRL &= ~(0x0Fu << 20);
GPIOA->CRL |=  (0x02u << 20);
```

---

## 9. 为什么PA5有时对应第5位，有时对应第20～23位

不同寄存器保存的信息不同。

### CRL/CRH

用于配置工作模式，每个引脚占4位：

```
PA5 → CRL第20～23位
```

### IDR、ODR、BSRR

用于表示或控制电平，每个引脚只需1位：

```
PA5 → 第5位
```

因此：

```
CRL中的PA5：第20～23位
BSRR中的PA5：第5位
```

两者不矛盾。

---

## 10. HAL_GPIO_WritePin参数

函数原型：

```
void HAL_GPIO_WritePin(GPIO_TypeDef *GPIOx,
                       uint16_t GPIO_Pin,
                       GPIO_PinState PinState);
```

调用：

```
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
```

参数含义：

|   |   |
|---|---|
|参数|含义|
|`GPIOA`|选择GPIOA端口|
|`GPIO_PIN_5`|选择5号引脚|
|`GPIO_PIN_SET`|输出高电平|

枚举：

```
typedef enum
{
    GPIO_PIN_RESET = 0u,
    GPIO_PIN_SET
} GPIO_PinState;
```

因此：

```
GPIO_PIN_RESET = 0
GPIO_PIN_SET   = 1
```

---

## 11. BSRR寄存器

`BSRR`是操作命令寄存器，不是保存全部输出状态的普通寄存器。

```
低16位写1  → 对应引脚置为高电平
高16位写1  → 对应引脚置为低电平
对应位写0  → 不操作对应引脚
```

所以直接赋值不会清除其他引脚：

```
GPIOA->BSRR = GPIO_PIN_5;
```

表示：

```
第5位写1 → PA5置1
其他位写0 → 其他引脚保持不变
```

不需要写：

```
GPIOA->BSRR |= GPIO_PIN_5;
```

因为BSRR只需要接收操作命令，不需要读取旧值。

---

## 12. PA5输出高电平

HAL写法：

```
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_SET);
```

函数内部核心操作：

```
GPIOx->BSRR = GPIO_Pin;
```

代入参数：

```
GPIOA->BSRR = GPIO_PIN_5;
```

继续展开：

```
GPIOA->BSRR = (1u << 5);
GPIOA->BSRR = 0x00000020;
```

BSRR低半区第5位写1，PA5输出高电平。

---

## 13. PA5输出低电平

HAL写法：

```
HAL_GPIO_WritePin(GPIOA, GPIO_PIN_5, GPIO_PIN_RESET);
```

函数内部：

```
GPIOx->BSRR = (uint32_t)GPIO_Pin << 16u;
```

代入PA5：

```
GPIOA->BSRR = (uint32_t)(1u << 5) << 16u;
```

等价于：

```
GPIOA->BSRR = (1u << 21);
GPIOA->BSRR = 0x00200000;
```

BSRR高半区的对应位写1，PA5输出低电平。

---

## 14. 完整底层代码

```
/* 1. 开启GPIOA时钟 */
RCC->APB2ENR |= (1u << 2);

/* 2. 配置PA5为2 MHz推挽输出 */
GPIOA->CRL =
    (GPIOA->CRL & ~(0x0Fu << 20)) |
    (0x02u << 20);

/* 3. PA5输出高电平 */
GPIOA->BSRR = (1u << 5);

/* 4. PA5输出低电平 */
GPIOA->BSRR = (1u << 21);
```

---

## 核心总结

```
RCC决定GPIOA能否工作。

GPIOA选择A端口。

GPIO_PIN_5选择端口中的5号引脚。

HAL_GPIO_Init配置PA5的工作模式。

CRL中的PA5占第20～23位。

HAL_GPIO_WritePin控制PA5的输出电平。

BSRR低半区写1表示置高电平。

BSRR高半区写1表示置低电平。
```

完整路径：

```
开启GPIOA时钟
→ 填写GPIO配置结构体
→ HAL_GPIO_Init修改CRL
→ PA5成为推挽输出
→ HAL_GPIO_WritePin修改BSRR
→ PA5输出高电平或低电平
```
# Day 5：结构体指针与函数传参

## 1. C语言只有值传递

传普通变量：

```
void Set(uint32_t value)
{
    value = 20u;
}
```

调用：

```
uint32_t number = 10u;
Set(number);
```

函数只修改副本，`number`仍为10。

传指针：

```
void Set(uint32_t *p)
{
    *p = 20u;
}
```

调用：

```
Set(&number);
```

函数复制的是`number`的地址，可以通过`*p`修改原变量。

```
传变量 → 复制数据
传指针 → 复制地址
```

---

## 2. 结构体指针传参

```
typedef struct
{
    uint32_t pin;
    uint32_t mode;
} Config;

void SetMode(Config *p)
{
    p->mode = 3u;
}
```

调用：

```
Config config = {5u, 1u};
SetMode(&config);
```

结果：

```
config.pin  = 5
config.mode = 3
```

关系：

```
p->mode == (*p).mode
```

结构体指针传参的优点：

- 可以修改原结构体；
    
- 不需要复制整个结构体；
    
- 一个指针可以访问多个成员。
    

---

## 3. 理解 `HAL_GPIO_Init`

```
HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);
```

函数参数大致为：

```
void HAL_GPIO_Init(
    GPIO_TypeDef *GPIOx,
    GPIO_InitTypeDef *GPIO_Init
);
```

两个参数的作用：

```
GPIOA
→ 已经是GPIO_TypeDef *结构体指针表达式
→ 指向GPIOA真实硬件寄存器
→ 不需要加&

GPIO_InitStruct
→ RAM中的普通结构体变量
→ 需要用&取得地址
```

函数内部：

```
GPIO_Init->Pin;   // 读取用户配置
GPIO_Init->Mode;
GPIO_Init->Speed;

GPIOx->CRL;       // 修改硬件寄存器
GPIOx->CRH;
```

完整流程：

```
GPIO_InitStruct保存用户配置
          ↓
函数读取Pin、Mode、Speed
          ↓
计算对应寄存器位
          ↓
通过GPIOx修改CRL或CRH
```

---

## 4. `const`结构体指针

```
const Config *p;
```

表示：

```
p可以改变指向
不能通过p修改目标数据
```

允许：

```
uint32_t mode = p->mode;
p = &other_config;
```

不允许：

```
p->mode = 3u;
```

如果限制指针自身：

```
Config * const p = &config;
```

表示：

```
p不能改变指向
可以通过p修改数据
```

记忆：

```
const在*左边  → 限制指向的数据
const在*右边  → 限制指针本身
```

---

## 5. 空指针检查

错误调用可能传入：

```
SetMode(NULL);
```

直接解引用可能造成HardFault。

安全写法：

```
void SetMode(Config *p)
{
    if (p == NULL)
    {
        return;
    }

    p->mode = 3u;
}
```

多个指针参数：

```
if ((GPIOx == NULL) || (config == NULL))
{
    return;
}
```

---

## 6. 简化版GPIO配置函数

```
void GPIO_Configure(
    GPIO_TypeDef *GPIOx,
    const Config *config)
{
    if ((GPIOx == NULL) || (config == NULL))
    {
        return;
    }

    GPIOx->ODR |= 1u << config->pin;
}
```

职责：

```
config
→ 指向RAM中的用户配置
→ 只负责提供引脚号等信息

GPIOx
→ 指向真实GPIO寄存器
→ 负责修改硬件
```

最后一行：

```
读取config->pin
→ 生成引脚掩码
→ 修改GPIOx->ODR
```

---

## 7. 重点记忆

```
C语言参数始终按值传递。

传普通变量复制数据，
传指针复制地址。

结构体变量用.，
结构体指针用->。

GPIOA已经是硬件结构体指针，
GPIO_InitStruct是普通变量，需要加&。

const Config *p：
不能通过p修改配置数据。

解引用指针参数前，
应先检查是否为NULL。
```
# Day 6：枚举与GPIO状态

## 1. 枚举基础

```
typedef enum
{
    GPIO_PIN_RESET = 0,
    GPIO_PIN_SET
} GPIO_PinState;
```

区别：

```
GPIO_PinState   → 枚举类型名称
GPIO_PIN_RESET  → 枚举常量，数值0
GPIO_PIN_SET    → 枚举常量，数值1
state           → 自己声明的枚举变量名称
```

声明：

```
GPIO_PinState state = GPIO_PIN_SET;
```

枚举常量只是有意义的整数名称，本身不会操作硬件。

---

## 2. GPIO写入函数

```
HAL_GPIO_WritePin(
    GPIOA,
    GPIO_PIN_5,
    GPIO_PIN_SET
);
```

参数：

```
GPIOA         → 选择GPIOA端口
GPIO_PIN_5    → 选择第5号引脚
GPIO_PIN_SET  → 选择输出高电平
```

简化实现：

```
void HAL_GPIO_WritePin(
    GPIO_TypeDef *GPIOx,
    uint16_t GPIO_Pin,
    GPIO_PinState PinState)
{
    if (PinState != GPIO_PIN_RESET)
    {
        GPIOx->BSRR = GPIO_Pin;
    }
    else
    {
        GPIOx->BSRR =
            (uint32_t)GPIO_Pin << 16u;
    }
}
```

---

## 3. BSRR置位与复位

```
BSRR低16位写1  → 对应引脚置高
BSRR高16位写1  → 对应引脚置低
写入0           → 不操作对应引脚
```

固定公式：

```
PAn置高 → BSRR第n位写1
PAn置低 → BSRR第(n + 16)位写1
```

例如PA6：

```
GPIOA->BSRR = 1u << 6u;  // PA6置高
GPIOA->BSRR = 1u << 22u; // PA6置低
```

因为：

```
6 + 16 = 22
```

重点：

```
BSRR低半区负责Set：置高
BSRR高半区负责Reset：置低
```

不能使用取反让引脚置低：

```
GPIOA->BSRR = ~(1u << 6u); // 错误
```

---

## 4. 为什么转换为 `uint32_t`

```
(uint32_t)GPIO_Pin << 16u
```

过程：

```
将16位GPIO_Pin扩展为32位
→ 左移16位
→ 得到BSRR高半区复位掩码
```

真正写入寄存器的是完整赋值：

```
GPIOx->BSRR =
    (uint32_t)GPIO_Pin << 16u;
```

---

## 5. GPIO读取函数

```
GPIO_PinState HAL_GPIO_ReadPin(
    GPIO_TypeDef *GPIOx,
    uint16_t GPIO_Pin)
{
    if ((GPIOx->IDR & GPIO_Pin) != 0u)
    {
        return GPIO_PIN_SET;
    }

    return GPIO_PIN_RESET;
}
```

流程：

```
读取IDR
→ 使用GPIO_Pin掩码检查目标位
→ 非0：返回GPIO_PIN_SET
→ 为0：返回GPIO_PIN_RESET
```

---

## 6. 位编号

二进制位从最右边开始编号：

```
位编号：7 6 5 4 3 2 1 0
位权值：128 64 32 16 8 4 2 1
位数据：0 0 1 0 0 0 0 0
              ↑
             第5位
```

所以：

```
0010 0000 = 第5位为1
```

GPIO对应关系：

```
PA0 → 第0位
PA1 → 第1位
PA2 → 第2位
PA5 → 第5位
```

---

## 7. 枚举与 `switch`

```
switch (state)
{
    case GPIO_PIN_RESET:
        // 处理低电平
        break;

    case GPIO_PIN_SET:
        // 处理高电平
        break;

    default:
        // 处理非法状态
        break;
}
```

`break`用于结束当前分支。遗漏后会继续执行下一个`case`。

C语言仍允许强制传入非法枚举值：

```
(GPIO_PinState)5
```

所以枚举提高可读性，但不能完全代替参数检查。

---

## 8. 重点记忆

```
枚举类型不是变量，
枚举常量只是有名字的整数。

GPIO_PIN_RESET = 0
GPIO_PIN_SET   = 1

PAn置高：
BSRR第n位写1。

PAn置低：
BSRR第(n + 16)位写1。

读取引脚：
使用IDR和引脚掩码进行按位与。

二进制位编号：
永远从最右边的第0位开始。
```
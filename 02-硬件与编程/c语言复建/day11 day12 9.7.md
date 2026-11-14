
````
# 第11天：环形缓冲区与UART接收

## 1. 基本结构

```c
typedef struct
{
    uint8_t data[BUFFER_SIZE];
    volatile uint16_t head;
    volatile uint16_t tail;
} RingBuffer;
````

- `head`：指向下一次写入的位置；
- `tail`：指向下一次读取的位置；
- 写入后移动`head`；
- 读取后移动`tail`。

## 2. 环形移动

```
next = (index + 1u) % BUFFER_SIZE;
```

例如数组大小为4：

```
0 → 1 → 2 → 3 → 0
```

`%`让下标到达末尾后返回0。

## 3. 空与满的判断

采用“空出一格”的设计：

```
head == tail
```

表示缓冲区为空。

```
next_head == tail
```

表示缓冲区已满。

实际容量：

```
有效容量 = BUFFER_SIZE - 1u
```

例如数组大小为4，最多保存3个数据。

> [!important] 易混淆点  
> 判断空和满必须看`head`与`tail`，不能只看数组中残留的数据。

## 4. 写入数据

```
bool RingBuffer_Write(RingBuffer *rb, uint8_t value)
{
    uint16_t next_head;

    next_head = (rb->head + 1u) % BUFFER_SIZE;

    if (next_head == rb->tail)
    {
        return false;
    }

    rb->data[rb->head] = value;
    rb->head = next_head;

    return true;
}
```

写入过程：

```
检查是否已满
→ 写入data[head]
→ 移动head
```

## 5. 读取数据

```
bool RingBuffer_Read(RingBuffer *rb, uint8_t *value)
{
    if (rb->head == rb->tail)
    {
        return false;
    }

    *value = rb->data[rb->tail];
    rb->tail = (rb->tail + 1u) % BUFFER_SIZE;

    return true;
}
```

读取过程：

```
检查是否为空
→ 读取data[tail]
→ 移动tail
```

> [!important] 易混淆点  
> 数据被读取后不一定会从数组中清零，但它在逻辑上已经无效，之后可以被覆盖。

## 6. 有效数据的顺序

假设：

```
head = 0
tail = 1

下标：  0   1   2   3
数据：  E   B   C   D
```

有效数据不是从下标0开始，而是从`tail`开始：

```
B → C → D
```

## 7. UART中的使用

```
UART中断
→ 读取USART1->DR
→ RingBuffer_Write()
→ 立即退出中断

主程序
→ RingBuffer_Read()
→ 处理收到的数据
```

中断函数应尽量短，否则后续数据到达时可能发生溢出或丢失。

## 8. volatile与原子操作

```
volatile uint32_t count;
```

`volatile`只保证每次真正访问内存，不保证操作不会被中断。

```
count++;
```

大致包含：

```
读取count
→ 加1
→ 写回count
```

因此，`count++`不是一个不可分割的操作。

必要时使用短临界区：

```
uint32_t primask = __get_PRIMASK();

__disable_irq();
count++;
__set_PRIMASK(primask);
```

> [!important] 易混淆点  
> `volatile`不等于原子操作，也不能自动解决多个执行过程同时修改数据的问题。

## 9. 中断接收与DMA接收

普通中断接收：

```
CPU读取DR
→ CPU把数据写入内存
```

DMA接收：

```
DMA控制器读取DR
→ DMA自动把数据写入内存
```

DMA相当于数据搬运助手，但CPU仍需负责：

- 初始化DMA；
- 设置源地址和目标地址；
- 设置传输长度；
- 处理传输完成等事件。

## 核心口诀

```
head负责写，tail负责读
相等表示空，下一格追上tail表示满
写完移动head，读完移动tail
volatile保证真访问，不保证原子性
中断由CPU搬，DMA由硬件搬
```
# 第12天：函数指针与回调

## 一、函数指针

函数指针用于保存函数的地址。

```
typedef void (*UART_Callback_t)(uint8_t byte);

UART_Callback_t rx_callback = NULL;
```

这里：

- `UART_Callback_t`：函数指针类型名；
- `rx_callback`：函数指针变量；
- `void`：目标函数没有返回值；
- `uint8_t`：目标函数接收的参数类型。

符合要求的函数：

```
void ProcessByte(uint8_t byte)
{
    /* 处理数据 */
}
```

## 二、保存函数地址与调用函数

```
rx_callback = ProcessByte;
```

这句只是把 `ProcessByte`的地址保存到 `rx_callback`，不会执行函数。

```
rx_callback('A');
```

这句才真正调用函数，实际效果相当于：

```
ProcessByte('A');
```

重点记忆：

```
ProcessByte       /* 函数地址 */
ProcessByte('A')  /* 直接调用函数 */

rx_callback       /* 函数指针 */
rx_callback('A')  /* 通过指针间接调用函数 */
```

## 三、注册不等于触发

注册函数：

```
void UART_RegisterCallback(UART_Callback_t callback)
{
    rx_callback = callback;
}
```

初始化时注册：

```
UART_RegisterCallback(ProcessByte);
```

这里只保存地址，并不会立即执行 `ProcessByte()`。

事件发生后才触发：

```
void UART_ReceiveByte(uint8_t byte)
{
    if (rx_callback != NULL)
    {
        rx_callback(byte);
    }
}
```

完整过程：

```
定义回调类型
→ 定义函数指针变量
→ 用户编写处理函数
→ 初始化时注册函数地址
→ 等待事件发生
→ 事件发生后调用回调
```

## 四、`NULL`不是空类型

```
static UART_Callback_t rx_callback = NULL;
```

准确含义是：

> `rx_callback`暂时没有保存任何有效函数地址。

它不是“指向空类型”。

需要区分：

```
void             /* 无返回值类型 */
NULL             /* 空指针值 */
UART_Callback_t  /* 函数指针类型 */
rx_callback      /* 函数指针变量 */
```

调用前必须检查：

```
if (rx_callback != NULL)
{
    rx_callback(byte);
}
```

如果函数指针等于 `NULL`却仍然调用，CPU会跳转到无效地址，在STM32上通常会导致 HardFault。

## 五、HAL弱函数回调

HAL可能提供默认弱函数：

```
__weak void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    UNUSED(GPIO_Pin);
}
```

用户编写同名的普通函数：

```
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    /* 用户代码 */
}
```

链接器会在链接阶段选择用户提供的强定义。

这不是“程序运行时优先调用用户函数”，而是：

```
HAL提供弱定义
→ 用户提供同名强定义
→ 链接器选择强定义
→ 最终程序中使用用户版本
```

## 六、弱函数与函数指针回调的区别

|机制|是否需要注册|何时确定目标函数|运行时能否更换|
|---|---|---|---|
|HAL弱函数回调|通常不需要|链接阶段|通常不能|
|函数指针回调|需要|运行阶段赋值时|可以|

函数指针可以重新注册：

```
user_callback = ButtonPressed;
user_callback = SensorReady;
user_callback = NULL;
```

弱函数最终使用哪个实现，在程序链接完成时就已经确定。

## 七、EXTI中断调用链

典型调用顺序：

```
外部引脚产生中断
→ EXTI0_IRQHandler()
→ HAL_GPIO_EXTI_IRQHandler(GPIO_PIN_0)
→ HAL_GPIO_EXTI_Callback(GPIO_PIN_0)
→ EXTI_Dispatch(GPIO_PIN_0)
→ user_callback(GPIO_PIN_0)
→ ButtonPressed(GPIO_PIN_0)
```

其中：

```
EXTI_Dispatch(GPIO_PIN_0);
```

只是调用分发函数。

真正通过函数指针调用用户函数的是：

```
user_callback(pin);
```

实际效果相当于：

```
ButtonPressed(GPIO_PIN_0);
```

## 八、完整的EXTI函数指针回调

```
#include <stdint.h>
#include <stddef.h>

typedef void (*EXTI_Callback_t)(uint16_t pin);

static EXTI_Callback_t user_callback = NULL;

void EXTI_RegisterCallback(EXTI_Callback_t callback)
{
    user_callback = callback;
}

void EXTI_Dispatch(uint16_t pin)
{
    if (user_callback != NULL)
    {
        user_callback(pin);
    }
}

void ButtonPressed(uint16_t pin)
{
    if (pin == GPIO_PIN_0)
    {
        HAL_GPIO_TogglePin(GPIOA, GPIO_PIN_5);
    }
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    EXTI_Dispatch(GPIO_Pin);
}

int main(void)
{
    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    /* 只注册函数地址，不会立即调用 */
    EXTI_RegisterCallback(ButtonPressed);

    while (1)
    {
    }
}
```

## 九、`GPIO_PIN_5`不是数字5

`GPIO_Pin`通常是引脚位掩码：

```
GPIO_PIN_5 == (1u << 5) == 0x0020u
```

因此应该写：

```
if (GPIO_Pin == GPIO_PIN_5)
```

不能写：

```
if (GPIO_Pin == 5u)
```

## 十、中断回调为什么不能耗时

执行中断回调时，主程序通常处于暂停状态。中断执行太久会：

- 长时间暂停主程序；
- 推迟其他无法抢占当前中断的中断；
- 降低系统响应速度。

尤其不建议在中断中执行：

```
HAL_Delay(1000u);
```

`HAL_Delay()`通常依赖 SysTick 中断更新时间：

```
HAL_Delay等待系统时间增加
→ SysTick负责更新时间
→ 当前中断阻止SysTick执行
→ 系统时间无法增加
→ HAL_Delay可能永远无法结束
```

推荐在中断中只设置标志：

```
volatile uint8_t button_pressed = 0u;

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_0)
    {
        button_pressed = 1u;
    }
}
```

主循环再执行复杂处理：

```
while (1)
{
    if (button_pressed != 0u)
    {
        button_pressed = 0u;

        /* 执行耗时处理 */
    }
}
```

`volatile`要求每次真正访问变量，但不保证原子性或线程安全。

## 十一、本日重点

```
注册 = 保存函数地址，不执行函数
触发 = 通过函数指针真正调用函数

NULL = 没有有效目标地址，不是空类型
void = 函数没有返回值

弱函数回调 = 链接阶段确定
函数指针回调 = 运行阶段注册，可以更换

EXTI中断入口
→ HAL中断处理
→ HAL回调
→ 分发函数
→ 函数指针
→ 用户处理函数

中断回调应尽量简短
复杂处理交给主循环
```
# Day 13：枚举状态机

## 1. 状态机的核心

状态机根据“当前状态”和“发生的事件”决定下一步：

```
当前状态 + 事件
→ 执行动作
→ 更新状态
```

例如：

```
IDLE + START → 启动电机 → RUNNING
RUNNING + FAULT → 停止电机并报警 → ALARM
ALARM + RESET → 关闭报警 → IDLE
```

## 2. 状态、事件和动作的区别

### 状态

表示系统现在所处的情况，并会持续一段时间：

```
SYSTEM_STATE_IDLE
SYSTEM_STATE_RUNNING
SYSTEM_STATE_ALARM
```

### 事件

表示刚刚发生的事情：

```
SYSTEM_EVENT_START
SYSTEM_EVENT_STOP
SYSTEM_EVENT_FAULT
SYSTEM_EVENT_RESET
```

### 动作

表示程序需要实际执行的操作：

```
Motor_Start();
Motor_Stop();
Alarm_On();
Alarm_Off();
```

重点：

```
状态负责记录
事件负责触发
动作负责操作硬件
```

下面这句只修改RAM中的状态变量：

```
system_state = SYSTEM_STATE_RUNNING;
```

它不会自动启动电机。真正操作硬件的是：

```
Motor_Start();
```

## 3. 用枚举定义状态和事件

```
typedef enum
{
    SYSTEM_STATE_IDLE = 0,
    SYSTEM_STATE_RUNNING,
    SYSTEM_STATE_ALARM
} SystemState_t;

typedef enum
{
    SYSTEM_EVENT_NONE = 0,
    SYSTEM_EVENT_START,
    SYSTEM_EVENT_STOP,
    SYSTEM_EVENT_FAULT,
    SYSTEM_EVENT_RESET
} SystemEvent_t;
```

其中：

```
SystemState_t       状态类型
SystemEvent_t       事件类型

SYSTEM_STATE_IDLE   状态枚举常量
SYSTEM_EVENT_START  事件枚举常量

system_state        保存当前状态的变量
```

## 4. 初始状态从哪里确定

初始状态由初始化语句明确决定：

```
static SystemState_t system_state = SYSTEM_STATE_IDLE;
```

这表示：

```
程序启动时，系统状态为IDLE
```

如果写成：

```
static SystemState_t system_state = SYSTEM_STATE_RUNNING;
```

初始状态才是 `RUNNING`。

判断初始状态时，必须查看状态变量的初始化语句，不能凭事件名称猜测。

## 5. 完整状态机

```
static SystemState_t system_state = SYSTEM_STATE_IDLE;

void System_ProcessEvent(SystemEvent_t event)
{
    switch (system_state)
    {
        case SYSTEM_STATE_IDLE:
            if (event == SYSTEM_EVENT_START)
            {
                Motor_Start();
                system_state = SYSTEM_STATE_RUNNING;
            }
            break;

        case SYSTEM_STATE_RUNNING:
            if (event == SYSTEM_EVENT_STOP)
            {
                Motor_Stop();
                system_state = SYSTEM_STATE_IDLE;
            }
            else if (event == SYSTEM_EVENT_FAULT)
            {
                Motor_Stop();
                Alarm_On();
                system_state = SYSTEM_STATE_ALARM;
            }
            break;

        case SYSTEM_STATE_ALARM:
            if (event == SYSTEM_EVENT_RESET)
            {
                Alarm_Off();
                system_state = SYSTEM_STATE_IDLE;
            }
            break;

        default:
            Motor_Stop();
            Alarm_On();
            system_state = SYSTEM_STATE_ALARM;
            break;
    }
}
```

判断顺序：

```
switch判断当前状态
→ if判断当前事件
→ 执行动作
→ 修改状态
```

## 6. 同一个事件在不同状态下结果不同

例如 `START`事件：

```
IDLE + START
→ Motor_Start()
→ RUNNING
```

但是：

```
ALARM + START
→ 没有对应处理
→ 仍然保持ALARM
```

不能看到 `START`就直接认为系统一定进入 `RUNNING`。

状态机的结果取决于：

```
当前状态 + 当前事件
```

而不是只取决于事件。

## 7. 无效事件为什么会被忽略

报警状态代码：

```
case SYSTEM_STATE_ALARM:
    if (event == SYSTEM_EVENT_RESET)
    {
        Alarm_Off();
        system_state = SYSTEM_STATE_IDLE;
    }
    break;
```

这里没有处理 `START`事件。因此：

```
ALARM + START → ALARM
```

程序不会进入任何 `if`，状态变量也不会被修改，所以保持原状态。

## 8. 状态变量为什么使用 `static`

正确：

```
static SystemState_t system_state = SYSTEM_STATE_IDLE;
```

它只初始化一次，可以记住上一次处理完成后的状态。

错误写法：

```
void System_ProcessEvent(SystemEvent_t event)
{
    SystemState_t system_state = SYSTEM_STATE_IDLE;
}
```

普通局部变量每次调用函数都会重新创建并初始化：

```
第一次调用 → IDLE
第二次调用 → 又变回IDLE
第三次调用 → 又变回IDLE
```

这样状态机无法记住之前已经进入 `RUNNING`或 `ALARM`。

## 9. `default`与故障安全

枚举变量仍可能因为错误赋值或内存破坏而出现非法值：

```
system_state = (SystemState_t)99;
```

因此使用：

```
default:
    Motor_Stop();
    Alarm_On();
    system_state = SYSTEM_STATE_ALARM;
    break;
```

含义是：

```
发现未知状态
→ 立即停止危险设备
→ 打开报警
→ 回到一个已知的安全状态
```

这不是因为“未知状态天然等于报警状态”，而是程序设计者主动选择安全策略。

## 10. 中断事件如何交给状态机

中断回调中只记录事件：

```
static volatile uint8_t fault_pending = 0u;

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == GPIO_PIN_1)
    {
        fault_pending = 1u;
    }
}
```

主循环再处理：

```
while (1)
{
    if (fault_pending != 0u)
    {
        fault_pending = 0u;
        System_ProcessEvent(SYSTEM_EVENT_FAULT);
    }
}
```

调用过程：

```
硬件产生中断
→ 中断回调设置fault_pending
→ 退出中断
→ 主循环发现标志
→ 清除标志
→ 把FAULT事件交给状态机
```

中断中只设置标志，可以避免复杂处理长时间占用中断。

## 11. 多个事件的处理顺序

```
if (fault_pending != 0u)
{
    fault_pending = 0u;
    System_ProcessEvent(SYSTEM_EVENT_FAULT);
}

if (start_pending != 0u)
{
    start_pending = 0u;
    System_ProcessEvent(SYSTEM_EVENT_START);
}
```

这里先处理故障，再处理启动，表示：

```
FAULT优先级高于START
```

假设初始状态为 `RUNNING`，两个标志同时为1：

```
先处理FAULT
→ RUNNING变成ALARM

再处理START
→ ALARM不接受START
→ 最终保持ALARM
```

## 12. 事件标志的局限

```
fault_pending = 1u;
```

只能表示：

```
至少有一个故障事件等待处理
```

如果连续发生三次故障：

```
fault_pending = 1u;
fault_pending = 1u;
fault_pending = 1u;
```

最终仍然只是1，无法记录事件发生了三次。

需要保存多个事件时，应使用计数器或事件队列。

## 13. Day 13核心总结

```
状态：系统现在是什么情况
事件：刚刚发生了什么
动作：真正执行什么操作

状态机：
当前状态 + 当前事件
→ 执行动作
→ 更新状态

初始状态：
由状态变量的初始化语句决定

无效事件：
没有匹配的处理代码，所以保持原状态

static状态变量：
跨函数调用保存上一次状态

default：
处理非法状态，进入安全状态

中断：
只记录事件

主循环：
读取事件并运行状态机
```

# Day 14：非阻塞时间管理

## 1. 核心思想

阻塞式延时：

```
HAL_Delay(500u);
```

会让当前代码停在这里，期间主循环无法继续处理其他任务。

非阻塞时间判断：

```
uint32_t now = HAL_GetTick();

if ((uint32_t)(now - last_tick) >= period)
{
    last_tick = now;
    Task_Run();
}
```

不会停下来等待，而是让主循环不断运行，到时间后才执行任务。

```
HAL_Delay()：停下来等待时间经过
HAL_GetTick()：读取时间，没到就继续做其他事情
```

## 2. 完整示例程序

下面程序组合了：

- `HAL_GetTick()`非阻塞计时；
- 函数指针任务调度；
- 按键非阻塞消抖；
- 事件标志；
- 第13天的状态机；
- EXTI故障事件；
- PF9/PF10 LED控制。

示例假设：

```
PA0：按键输入，低电平按下
PA1：故障EXTI输入
PF9：运行LED，低电平点亮
PF10：报警LED，低电平点亮
```

实际使用时应根据开发板原理图调整引脚。

```
#include "stm32f4xx_hal.h"
#include <stdint.h>
#include <stddef.h>

#define KEY_DEBOUNCE_MS  20u
#define KEY_PERIOD_MS    1u
#define LED_PERIOD_MS    500u

#define KEY_PORT         GPIOA
#define KEY_PIN          GPIO_PIN_0

#define FAULT_PIN        GPIO_PIN_1

#define RUN_LED_PORT     GPIOF
#define RUN_LED_PIN      GPIO_PIN_9

#define ALARM_LED_PORT   GPIOF
#define ALARM_LED_PIN    GPIO_PIN_10

typedef enum
{
    SYSTEM_STATE_IDLE = 0,
    SYSTEM_STATE_RUNNING,
    SYSTEM_STATE_ALARM
} SystemState_t;

typedef enum
{
    SYSTEM_EVENT_START = 0,
    SYSTEM_EVENT_FAULT
} SystemEvent_t;

typedef struct
{
    GPIO_PinState raw_state;
    GPIO_PinState stable_state;
    uint32_t changed_tick;
} Key_t;

typedef void (*TaskCallback_t)(void);

typedef struct
{
    uint32_t period;
    uint32_t last_tick;
    TaskCallback_t callback;
} PeriodicTask_t;

/* 系统当前状态 */
static SystemState_t system_state = SYSTEM_STATE_IDLE;

/* 中断或按键任务与主循环共享的事件标志 */
static volatile uint8_t start_pending = 0u;
static volatile uint8_t fault_pending = 0u;

/* 按键消抖数据 */
static Key_t key;

/* 函数声明 */
static void Motor_Start(void);
static void Motor_Stop(void);
static void Alarm_On(void);
static void Alarm_Off(void);

static void Button_PressedEvent(void);
static void System_ProcessEvent(SystemEvent_t event);

static void Key_Task(void);
static void LED_Task(void);

static void Scheduler_RunTask(
    PeriodicTask_t *task,
    uint32_t now
);

/* 周期任务对象 */
static PeriodicTask_t key_task =
{
    .period = KEY_PERIOD_MS,
    .last_tick = 0u,
    .callback = Key_Task
};

static PeriodicTask_t led_task =
{
    .period = LED_PERIOD_MS,
    .last_tick = 0u,
    .callback = LED_Task
};

static void Motor_Start(void)
{
    /*
     * 这里填写启动电机的GPIO或PWM代码。
     * 当前示例只保留接口。
     */
}

static void Motor_Stop(void)
{
    /*
     * 这里填写停止电机的代码。
     */
}

static void Alarm_On(void)
{
    /*
     * PF10低电平点亮。
     */
    HAL_GPIO_WritePin(
        ALARM_LED_PORT,
        ALARM_LED_PIN,
        GPIO_PIN_RESET
    );
}

static void Alarm_Off(void)
{
    HAL_GPIO_WritePin(
        ALARM_LED_PORT,
        ALARM_LED_PIN,
        GPIO_PIN_SET
    );
}

static void Button_PressedEvent(void)
{
    /*
     * 只记录启动事件，不在这里直接启动电机。
     */
    start_pending = 1u;
}

static void System_ProcessEvent(SystemEvent_t event)
{
    switch (system_state)
    {
        case SYSTEM_STATE_IDLE:
            if (event == SYSTEM_EVENT_START)
            {
                Motor_Start();
                system_state = SYSTEM_STATE_RUNNING;
            }
            else if (event == SYSTEM_EVENT_FAULT)
            {
                Motor_Stop();
                Alarm_On();
                system_state = SYSTEM_STATE_ALARM;
            }
            break;

        case SYSTEM_STATE_RUNNING:
            if (event == SYSTEM_EVENT_FAULT)
            {
                Motor_Stop();
                Alarm_On();
                system_state = SYSTEM_STATE_ALARM;
            }
            break;

        case SYSTEM_STATE_ALARM:
            /*
             * 报警状态不接受START事件。
             * 后续可增加RESET事件。
             */
            break;

        default:
            Motor_Stop();
            Alarm_On();
            system_state = SYSTEM_STATE_ALARM;
            break;
    }
}

static void Key_Task(void)
{
    uint32_t now = HAL_GetTick();

    GPIO_PinState current_state =
        HAL_GPIO_ReadPin(KEY_PORT, KEY_PIN);

    /*
     * 原始电平变化时重新开始消抖计时。
     */
    if (current_state != key.raw_state)
    {
        key.raw_state = current_state;
        key.changed_tick = now;
    }

    /*
     * 原始电平持续稳定20毫秒后，
     * 才更新已经确认的稳定状态。
     */
    if ((uint32_t)(now - key.changed_tick) >=
        KEY_DEBOUNCE_MS)
    {
        if (key.stable_state != key.raw_state)
        {
            key.stable_state = key.raw_state;

            /*
             * 本示例假设低电平表示按下。
             */
            if (key.stable_state == GPIO_PIN_RESET)
            {
                Button_PressedEvent();
            }
        }
    }
}

static void LED_Task(void)
{
    if (system_state == SYSTEM_STATE_RUNNING)
    {
        /*
         * 这个函数每500毫秒被调度一次，
         * 每次翻转PF9。
         */
        HAL_GPIO_TogglePin(
            RUN_LED_PORT,
            RUN_LED_PIN
        );
    }
    else
    {
        /*
         * 非运行状态关闭PF9 LED。
         */
        HAL_GPIO_WritePin(
            RUN_LED_PORT,
            RUN_LED_PIN,
            GPIO_PIN_SET
        );
    }
}

static void Scheduler_RunTask(
    PeriodicTask_t *task,
    uint32_t now
)
{
    if ((uint32_t)(now - task->last_tick) >=
        task->period)
    {
        /*
         * 记录本次实际调度时间。
         */
        task->last_tick = now;

        /*
         * 函数指针不为空时才调用任务。
         */
        if (task->callback != NULL)
        {
            task->callback();
        }
    }
}

/*
 * PA1故障输入的HAL外部中断回调。
 */
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == FAULT_PIN)
    {
        /*
         * 中断中只设置标志，然后尽快退出。
         */
        fault_pending = 1u;
    }
}

int main(void)
{
    uint32_t start_tick;

    HAL_Init();
    SystemClock_Config();
    MX_GPIO_Init();

    /*
     * 初始化LED。
     * PF9/PF10低电平点亮，所以SET表示关闭。
     */
    HAL_GPIO_WritePin(
        RUN_LED_PORT,
        RUN_LED_PIN,
        GPIO_PIN_SET
    );

    Alarm_Off();

    /*
     * 根据实际GPIO电平初始化按键状态，
     * 避免程序启动时误认为发生按键变化。
     */
    key.raw_state =
        HAL_GPIO_ReadPin(KEY_PORT, KEY_PIN);

    key.stable_state = key.raw_state;
    key.changed_tick = HAL_GetTick();

    /*
     * 两个任务从同一个时间点开始计时。
     */
    start_tick = HAL_GetTick();

    key_task.last_tick = start_tick;
    led_task.last_tick = start_tick;

    while (1)
    {
        uint32_t now = HAL_GetTick();

        /*
         * 每1毫秒检查一次按键。
         */
        Scheduler_RunTask(&key_task, now);

        /*
         * 每500毫秒运行一次LED任务。
         */
        Scheduler_RunTask(&led_task, now);

        /*
         * 故障事件优先处理。
         */
        if (fault_pending != 0u)
        {
            fault_pending = 0u;

            System_ProcessEvent(
                SYSTEM_EVENT_FAULT
            );
        }

        /*
         * 然后处理启动事件。
         */
        if (start_pending != 0u)
        {
            start_pending = 0u;

            System_ProcessEvent(
                SYSTEM_EVENT_START
            );
        }
    }
}
```

## 3. 调度器如何工作

调用：

```
Scheduler_RunTask(&led_task, now);
```

表示：

```
把led_task结构体的地址
和当前时间now
传给通用调度函数
```

其中：

```
&led_task
```

是 `led_task`结构体变量的地址。

进入函数后：

```
task->period
```

相当于：

```
led_task.period
```

```
task->last_tick
```

相当于：

```
led_task.last_tick
```

```
task->callback
```

相当于：

```
led_task.callback
```

因为：

```
led_task.callback = LED_Task;
```

所以：

```
task->callback();
```

最终执行：

```
LED_Task();
```

结构体只是把这些信息放在一起：

```
period      多久执行一次
last_tick   上次何时执行
callback    到时间执行哪个函数
```

调度思想没有改变。

## 4. 为什么传入结构体地址

```
Scheduler_RunTask(&led_task, now);
```

传入地址后，调度器可以修改原任务对象：

```
task->last_tick = now;
```

实际修改的是：

```
led_task.last_tick = now;
```

如果按值传递整个结构体，函数修改的只是副本，原来的 `last_tick`不会更新。

## 5. 时间判断

```
if ((uint32_t)(now - task->last_tick) >=
    task->period)
```

含义：

```
已经经过的时间 >= 任务周期
```

到时间后：

```
task->last_tick = now;
task->callback();
```

例如：

```
last_tick = 1000
period = 500
now = 1500
```

计算：

```
1500 - 1000 = 500
```

达到周期，执行任务并更新：

```
last_tick = 1500
```

下一次 `now = 1800`：

```
1800 - 1500 = 300
```

还没到500毫秒，所以不执行。

## 6. 为什么使用时间差

推荐：

```
(uint32_t)(now - last_tick) >= period
```

不推荐：

```
now >= last_tick + period
```

`HAL_GetTick()`使用 `uint32_t`，大约49.7天后会回绕到0。

无符号减法能够正确处理正常的计数器回绕。

## 7. 非阻塞按键消抖

按键消抖使用三个数据：

```
raw_state       最近读到的原始电平
stable_state    已确认的稳定电平
changed_tick    原始电平最近一次变化时间
```

过程：

```
检测到电平变化
→ 更新raw_state
→ 记录changed_tick
→ 不停下等待
→ 主循环继续运行
→ 稳定20毫秒后更新stable_state
→ 只产生一次按键事件
```

关键判断：

```
if (key.stable_state != key.raw_state)
```

只有确认状态真正变化时才产生事件，因此按住按键不会在每轮循环中重复触发。

## 8. `last_tick = now`与固定节拍

```
last_tick = now;
```

表示：

> 从本次实际执行时刻重新计时。

适合普通轮询任务。

```
last_tick += period;
```

表示：

> 按原来的理论节拍继续计时。

适合要求较稳定周期的采样或控制任务，但任务延迟太久时可能连续补执行。

## 9. 为什么中断只设置标志

```
void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)
{
    if (GPIO_Pin == FAULT_PIN)
    {
        fault_pending = 1u;
    }
}
```

中断中只记录：

```
发生了故障
```

主循环再处理：

```
System_ProcessEvent(SYSTEM_EVENT_FAULT);
```

这样可以：

- 快速退出中断；
- 避免长时间暂停主程序；
- 避免其他中断响应延迟；
- 避免在中断中调用阻塞函数。

## 10. `volatile`的作用

```
static volatile uint8_t fault_pending;
```

变量由中断修改、由主循环读取，所以使用 `volatile`要求每次都真实访问内存。

但它不保证：

- 操作原子性；
- 线程安全；
- 多个重复事件不丢失；
- 自动解决并发问题。

## 11. 整个程序的执行链

```
主循环读取HAL_GetTick
→ 调度Key_Task
→ 按键稳定20ms后设置start_pending
→ 主循环把START交给状态机
→ IDLE变为RUNNING
→ 电机启动

主循环继续运行
→ 每500ms调度LED_Task
→ PF9周期翻转

PA1发生故障中断
→ 回调设置fault_pending
→ 返回主循环
→ 状态机处理FAULT
→ 停止电机
→ 打开报警
→ 进入ALARM
```

## 12. Day 14核心总结

```
HAL_Delay：
停下来等待，属于阻塞式

HAL_GetTick：
读取时间，不阻塞程序

非阻塞判断：
now - last_tick >= period

任务结构体：
保存周期、上次执行时间和函数地址

函数指针：
决定到时间调用哪个任务

按键消抖：
记录变化时间，稳定20ms后确认

中断：
只设置事件标志

主循环：
调度任务并处理事件

状态机：
根据当前状态和事件决定动作
```
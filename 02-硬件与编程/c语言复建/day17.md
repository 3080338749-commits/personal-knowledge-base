# Day17：固定队列、数组栈与CAN消息结构体

## 1. 固定队列

队列遵守FIFO：

```
先进先出
```

```
入队：10 → 20 → 30
出队：10 → 20 → 30
```

队列结构：

```
typedef struct
{
    uint32_t items[3];
    uint8_t write_index;
    uint8_t read_index;
    uint8_t count;
} Queue_t;
```

成员作用：

```
write_index：下一次写入位置
read_index：下一次读取位置
count：当前有效数据数量
```

初始化：

```
Queue_t queue = {0};
```

表示所有成员初始化为0：

```
items = {0, 0, 0}
write_index = 0
read_index = 0
count = 0
```

## 2. 入队与出队

入队：

```
检查是否已满
→ 写入items[write_index]
→ 环形移动write_index
→ count++
```

出队：

```
检查是否为空
→ 读取items[read_index]
→ 环形移动read_index
→ count--
```

环形移动：

```
index = (index + 1u) % CAPACITY;
```

判断：

```
count == 0         // 空
count == CAPACITY  // 满
```

使用`count`后，容量为3的数组可以保存完整的3个数据。

## 3. 物理数组与逻辑顺序

数组可能是：

```
{40, 20, 30}
```

但如果：

```
read_index = 1
count = 3
```

真正队列顺序是：

```
20 → 30 → 40
```

> 队列顺序由`read_index`和`count`决定，不能只看数组表面。

出队后旧数值可以继续留在数组中，但它已经逻辑无效。

---

## 4. 数组栈

栈遵守LIFO：

```
后进先出
```

```
入栈：10 → 20 → 30
出栈：30 → 20 → 10
```

结构：

```
typedef struct
{
    uint32_t items[3];
    uint8_t count;
} Stack_t;
```

入栈：

```
stack->items[stack->count] = value;
stack->count++;
```

即：

```
先写，后加
```

出栈：

```
stack->count--;
*value = stack->items[stack->count];
```

即：

```
先减，后读
```

如果`count = 3`，最后一个有效下标是2，所以必须先把`count`减到2再读取。

---

## 5. 队列与栈的区别

```
队列：先进先出，适合CAN待发送消息
栈：后进先出，适合撤销、返回路径等操作
```

CAN消息使用栈会把发送顺序反过来，因此通常使用队列。

---

## 6. CAN消息结构体

```
typedef struct
{
    uint32_t id;
    uint8_t length;
    uint8_t data[8];
} CanMessage_t;
```

成员含义：

```
id：CAN消息编号
length：本次有效数据长度
data[8]：最多保存8字节
```

例如：

```
length = 3
```

只有：

```
data[0]～data[2]
```

有效。

```
data[8]：数组容量
length：实际有效长度
```

---

## 7. CAN消息队列

```
typedef struct
{
    CanMessage_t items[3];

    uint8_t write_index;
    uint8_t read_index;
    uint8_t count;
} CanQueue_t;
```

这里：

```
items[0]：一整条CAN消息
items[1]：一整条CAN消息
items[2]：一整条CAN消息
```

队列能够保存3条完整消息。

---

## 8. `message`与`*message`

函数参数：

```
const CanMessage_t *message;
```

含义：

```
message：结构体指针，保存CAN消息的地址
*message：这个地址指向的一整条CAN消息
message->id：消息的id成员
```

例如：

```
CanQueue_Push(&queue, &message_a);
```

进入函数以后：

```
message = &message_a
*message = message_a结构体本身
```

注意：

```
&：取得地址
*：根据地址找到目标对象
```

---

## 9. 结构体复制方向

入队：

```
queue->items[queue->write_index] = *message;
```

数据方向：

```
原消息 → 队列
```

出队：

```
*message = queue->items[queue->read_index];
```

数据方向：

```
队列 → 调用者消息变量
```

记忆：

```
赋值号右边：数据来源
赋值号左边：接收位置
```

结构体赋值会复制：

```
id
length
整个data[8]
```

队列保存的是独立副本。入队以后修改原消息，不会改变队列中的消息。

---

## 10. 剩余消息数量

两条消息入队：

```
count：0 → 1 → 2
```

连续出队两次：

```
count：2 → 1 → 0
```

所以最后：

```
count = 0
```

不能根据数组中是否还残留旧数据判断队列数量。

---

## 11. 中断共享队列

如果：

```
中断负责入队
主程序负责出队
```

两边共同修改：

```
items
write_index
read_index
count
```

`volatile`不能保证整个队列操作不被打断。

正确处理：

```
临界区内：
复制消息
修改下标
修改count

临界区外：
处理消息
CAN_Send
```

示例：

```
old_irq = __get_PRIMASK();
__disable_irq();

success = CanQueue_Pop(&queue, &message);

__set_PRIMASK(old_irq);

if (success == true)
{
    CAN_Send(&message);
}
```

`CAN_Send()`可能耗时，因此不能放在关闭中断的临界区中。

## 核心总结

```
队列：先进先出
栈：后进先出
CanMessage_t：表示一条CAN消息
CanQueue_t：保存多条CAN消息
message：消息地址
*message：完整消息
临界区：保护共享队列操作
```

最重要的一句话：

> CAN队列保存的是消息结构体副本；队列操作放在短临界区内，真正发送放在临界区外。
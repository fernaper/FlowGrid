import asyncio

from flowgrid import FlowGrid

fg = FlowGrid()


@fg.task
async def async_add(x: float, y: float) -> float:
    # Simulate an async operation with asyncio.sleep
    await asyncio.sleep(2)
    return x + y


@fg.task
async def async_multiply(x: float, y: float) -> float:
    # Another async function with a different async operation
    await asyncio.sleep(1)
    return x * y


def main():
    # Create async tasks
    task1 = async_add(10, 20)
    task2 = async_multiply(5, 6)

    # Wait for the tasks and get their results
    response1 = fg.wait(task1)
    response2 = fg.wait(task2)

    print('ASYNC ADD RESPONSE:', response1)  # Expected: 30
    print('ASYNC MULTIPLY RESPONSE:', response2)  # Expected: 30

    # Demonstrate task chaining with async functions
    chained_task = async_multiply(async_add(10, 20), 2)
    chained_response = fg.wait(chained_task)
    # Expected: (10 + 20) * 2 = 60
    print('CHAINED ASYNC TASK RESPONSE:', chained_response)


if __name__ == '__main__':
    main()

import time

from flowgrid import FlowGrid

fg = FlowGrid()


@fg.task
def add(x: float, y: float) -> float:
    # Simulate a long running task
    time.sleep(2)
    return x + y


@fg.task
def multiply(*values: float, times: int = 10) -> float:
    print('VALUES:', values)
    time.sleep(3)
    return sum(
        values
    ) * times


def main():
    task = multiply(add(10, 20), add(20, 30), times=add(2, 3))
    response = fg.wait(task)
    print('RESPONSE TASK:', response)
    print('Ideal execution time:', 2 + 3)


if __name__ == '__main__':
    main()

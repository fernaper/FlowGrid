import time
from flowgrid import FlowGrid

fg = FlowGrid()


@fg.task
def add_multiple(x: float, y: float, times: int = 10) -> float:
    response = x
    for i in range(times):
        time.sleep(1)
        fg.update(progress=i, total=times, percent=100*i/times)
        response += y
    return response


def main():
    task = add_multiple(10, 5, times=5)
    response = fg.wait(task)  # Expected: 10 + 5*5 = 35
    print('RESPONSE:', response)


if __name__ == '__main__':
    main()

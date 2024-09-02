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
    task_group = fg.group(*[
        add_multiple(0, 10, times=i)
        for i in range(4)
    ])
    responses = fg.wait(task_group)
    print('RESPONSES:', responses)


if __name__ == '__main__':
    main()

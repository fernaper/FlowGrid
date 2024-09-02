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
    task = fg.launch(add_multiple(10, 5, times=5))

    time.sleep(3)

    # Simulating a user cancelling the task
    print('CANCELLING TASK')
    # force=True will terminate the task immediately
    # even if it already started executing
    # It could cause data corruption or unexpected state
    fg.revoke(task, force=True)


if __name__ == '__main__':
    main()

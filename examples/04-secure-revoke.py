import time
from flowgrid import FlowGrid

fg = FlowGrid()


@fg.task
def add_multiple(x: float, y: float, times: int = 10) -> float:
    response = x
    for i in range(times):
        # Here we could decide the exact moment to check if the task was
        # revoked and stop the execution managing the state of the task
        if fg.is_revoked():
            print('CANCELLED')
            return
        time.sleep(1)
        fg.update(progress=i, total=times, percent=100*i/times)
        response += y
    return response


def main():
    task = fg.launch(add_multiple(10, 5, times=5))
    print('TASK:', task.task_id)

    time.sleep(3)

    # Simulating a user cancelling the task
    print('CANCELLING TASK')
    # Note that we are not using force=True
    # The task will be cancelled immediately if it hasn't started executing
    # If it already started executing, it will be cancelled when it
    # checks for revocation
    fg.revoke(task)


if __name__ == '__main__':
    main()

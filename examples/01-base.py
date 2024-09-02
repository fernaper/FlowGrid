import time
from flowgrid import FlowGrid

fg = FlowGrid()


@fg.task
def add(x: float, y: float) -> float:
    # Simulate a long running task
    time.sleep(10)
    return x + y


def main():
    task = add(1, 2)
    # Task id is none because it is not launched
    print('TASK:', task.task_id)

    # You can explicitly launch the task or let the
    # wait function do it for you
    # task = fg.launch(task)  # Can be uncommented

    # At this point the task id is available
    # print('TASK:', task.task_id)  # Can be uncommented
    response = fg.wait(task)
    print('RESPONSE:', response)


if __name__ == '__main__':
    main()

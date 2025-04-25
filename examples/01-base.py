import time
from flowgrid import FlowGrid

fg = FlowGrid(queue='datasmol')


@fg.task
def add(x: float, y: float) -> float:
    # Simulate a long running task
    time.sleep(4)
    if fg.is_revoked():
        return -1
    time.sleep(4)
    return x + y


def main():
    task = add(1, 2)
    # Task id is none because it is not launched
    print('TASK:', task.task_id)

    # You can explicitly launch the task or let the
    # wait function do it for you
    task = fg.launch(task, metadata={
        'name': 'Addition',
        'description': 'Add two numbers'
    })  # Can be uncommented

    print('Task metadata:', task.metadata)

    time.sleep(3)
    fg.revoke(task)

    # At this point the task id is available
    # print('TASK:', task.task_id)  # Can be uncommented
    response = fg.wait(task)
    print('RESPONSE:', response)


if __name__ == '__main__':
    main()

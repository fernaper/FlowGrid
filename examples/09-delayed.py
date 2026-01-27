import time
from datetime import datetime, timedelta, timezone
from flowgrid import FlowGrid

fg = FlowGrid()


@fg.task
def delayed_hello(name: str) -> str:
    print(f'Executing task for {name} at {datetime.now()}')
    return f'Hello {name}!'


def main():
    print(f'Current time: {datetime.now(timezone.utc)}')

    # Example 1: Using delay (countdown)
    print('\n--- Example 1: Using delay (5 seconds) ---')
    print('Launching task with 5 seconds delay...')
    task1 = delayed_hello('Delay User')

    # We launch it explicitly with delay
    start_time = time.time()
    fg.launch(task1, delay=5)

    # Waiting for result (this will block until task is done)
    # The task itself shouldn't start processing until 5 seconds passed
    result1 = fg.wait(task1)
    end_time = time.time()

    print(f'Task 1 result: {result1}')
    print(
        f'Time elapsed: {end_time - start_time:.2f} seconds (Expected ~5s + execution time)'
    )

    # Example 2: Using ETA (Estimated Time of Arrival)
    print('\n--- Example 2: Using ETA (3 seconds from now) ---')
    eta_time = datetime.now(timezone.utc) + timedelta(seconds=3)
    print(f'Launching task with ETA: {eta_time}')

    task2 = delayed_hello('ETA User')
    start_time_eta = time.time()
    fg.launch(task2, eta=eta_time)

    result2 = fg.wait(task2)
    end_time_eta = time.time()

    print(f'Task 2 result: {result2}')
    print(
        f'Time elapsed: {end_time_eta - start_time_eta:.2f} seconds (Expected ~3s + execution time)'
    )


if __name__ == '__main__':
    main()


# FlowGrid

**FlowGrid** is a Python library designed to improve parallelization across multiple machines with a powerful and user-friendly interface, allowing you to focus on your application logic without worrying about the complexities of task distribution and management.

## Motivation

The primary goal of **FlowGrid** is to provide an easy-to-use interface for parallelizing Python tasks across multiple workers.

In Python, a common design pattern is to launch asynchronous tasks while instantly responding to the user—*FastAPI*, for instance, addresses this with `background_tasks`, though it acknowledges this method may not be the most reliable, especially for long-running tasks.

**FlowGrid** abstracts the complexity of task management, progress tracking, and task cancellation, making it easier to build scalable and robust distributed systems. This library is also designed to seamlessly integrate with popular frameworks like *FastAPI*, *Flask*, and *Django*, solving common concurrency challenges effortlessly.

While other solutions like **Celery** (which FlowGrid uses under the hood) are available, they often require more configuration and are more challenging to use. FlowGrid simplifies the process while maintaining the full power of Celery, with additional enhancements such as native task state checking and improved handling of task cancellations, even for tasks in progress.

## Installation

> **Note:** FlowGrid will soon be available on PyPI. You will be able to install it using pip:
> ```bash
> pip install flowgrid
> ```
> FlowGrid requires Python 3.7 or higher.

## Basic Usage

### Defining and Launching Tasks

FlowGrid simplifies task management in Celery by allowing you to define tasks using decorators and manage them seamlessly. Here's an example:

```python
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
```

### Real-Time Progress Updates

FlowGrid supports real-time progress tracking for your tasks. You can update and monitor the progress easily:

```python
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
```

### Task Cancellation

FlowGrid allows you to cancel tasks, either forcefully or gracefully:

#### Forceful Cancellation

```python
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
    fg.revoke(task, force=True)

if __name__ == '__main__':
    main()
```

#### Graceful Cancellation

```python
import time
from flowgrid import FlowGrid

fg = FlowGrid()

@fg.task
def add_multiple(x: float, y: float, times: int = 10) -> float:
    response = x
    for i in range(times):
        # Check for revocation and stop if needed
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
    # Graceful cancellation
    fg.revoke(task)

if __name__ == '__main__':
    main()
```

## Worker Management

FlowGrid workers can be launched with the command:

```bash
flowgrid worker --app <path-to-your-flowgrid-class>
```

You can also use the `-A` shorthand for `--app`:

```bash
flowgrid worker -A <path-to-your-flowgrid-class>
```

For example in order to prepare workers to launch the initial example from this repository, you can run:

```bash
flowgrid worker -A examples.01-base.fg
```

The `.fg` must be included because it is the variable name of my FlowGrid instance in the file `examples/01-base.py`.


To view all available options, use:

```bash
flowgrid worker -h
```

Some useful options include:

- **Concurrency**: Control the number of worker processes with `--concurrency` or `-c`.
- **Log Level**: Set the logging level with `--loglevel` or `-l`.

## Example

Here's a basic example that demonstrates how to define and launch tasks using FlowGrid:

```python
import time
from flowgrid import FlowGrid

fg = FlowGrid()

@fg.task
def add(x: float, y: float) -> float:
    time.sleep(10)
    return x + y

def main():
    task = add(1, 2)
    print('TASK:', task.task_id)
    response = fg.wait(task)
    print('RESPONSE:', response)

if __name__ == '__main__':
    main()
```

## Future Enhancements

- **PyPI Release**: Soon, FlowGrid will be available for installation via pip.
- **Extended Documentation**: More detailed documentation and examples will be added as the project evolves.
- **Support chaining tasks without waiting**: Currently, you have to wait for a task to finish before chaining another task. You can check the example `examples/06-chaining.py` to see how to chain tasks. With the next solution it will look in the exact same way but if you use `fg.launch` the response will be instant and you can return the task to the user from the beginning.
- **Support task sequence without relationship**: Right now you can only chain tasks just by including them as paramteres, but what if the response of a task is not needed for the next one. We will create an interface called: `fg.sequence` that will allow you to define a sequence of tasks that will be executed in order.

## License

FlowGrid is licensed under the MIT License. See `LICENSE` for more information.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request to contribute to FlowGrid.

## Contact

For any questions or inquiries, please contact the maintainers via [your email/contact information].
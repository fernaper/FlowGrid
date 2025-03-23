import uuid
import asyncio

from functools import wraps
from typing import (
    Callable,
    Coroutine,
    Dict,
    List,
    Optional,
    TYPE_CHECKING,
    Union,
)

from celery import Celery, Task as CeleryTask, group
from celery.result import GroupResult

from .celery_app import make_celery

try:
    import redis
except ImportError:
    redis = None

if TYPE_CHECKING:
    from celery.local import Proxy


class Task():
    '''
    Represents a Celery task with additional management capabilities.

    This class provides an abstraction layer over Celery's AsyncResult,
    allowing for more complex task handling, including dependency management
    and lazy execution.

    Attributes:
        _args (Optional[tuple]): Arguments to be passed to the task.
        _kwargs (Optional[dict]): Keyword arguments to be passed to the task.
        launched (bool): Indicates whether the task has been launched.
        value (Any): The result of the task after completion.
        celery_task (Union[Celery.AsyncResult, 'Proxy']): The underlying
            Celery task.
    '''

    def __init__(
        self,
        celery_task: Celery.AsyncResult,
    ):
        '''
        Initialize a Task instance.

        Args:
            celery_task (Celery.AsyncResult): The Celery task to be managed.
        '''
        self._args = None
        self._kwargs = None
        self.launched = False
        self.value = None
        self.celery_task: Union[Celery.AsyncResult, 'Proxy'] = celery_task

        try:
            self.launched = self.celery_task.id is not None
        except Exception:
            pass

    @property
    def task_id(self) -> Optional[str]:
        if self.launched:
            return self.celery_task.id

    @property
    def status(self) -> str:
        if self.launched:
            return self.celery_task.status
        return 'NOT LAUNCHED'

    def get_signature(self):
        '''
        Get the Celery signature of the task.

        Returns:
            Celery.signature: The Celery signature of the task.
        '''
        return self.celery_task.s(*self._args, **self._kwargs)

    def prepare(self, *args, **kwargs) -> 'Task':
        '''
        Prepare the task for execution

        Args:
            *args (Any): Arguments to be passed to the task.
            **kwargs (Any): Keyword arguments to be passed to the task.

        Returns:
            Task: The Task instance
        '''
        self._args = args
        self._kwargs = kwargs
        return self

    def launch(self, timeout: Optional[float] = None) -> 'Task':
        '''
        Launch the task. This is the most important method of the class, as it
        triggers the execution of the task.

        Args:
            timeout (Optional[float]): The maximum time to wait for the task to
                complete.

        Returns:
            Task: The Task instance

        Raises:
            TimeoutError: If the task does not complete within the specified
                timeout.
        '''
        if self.launched:
            return self

        position_to_dependant_task = {}
        args = list(self._args)
        for i, arg in enumerate(self._args):
            if not isinstance(arg, Task):
                continue
            if arg.launched:
                args[i] = arg.value
            else:
                position_to_dependant_task[i] = arg

        for key, arg in self._kwargs.items():
            if not isinstance(arg, Task):
                continue
            if arg.launched:
                self._kwargs[key] = arg.value
            else:
                position_to_dependant_task[key] = arg

        if position_to_dependant_task:
            dependant_tasks = list(position_to_dependant_task.values())

            task_group = TaskGroup()
            for dependant_task in dependant_tasks:
                task_group.add(dependant_task.get_signature())
            responses = task_group.gather(
                timeout=timeout,
            )

            # I can use the same order because the dict is ordered
            for response, k in zip(
                responses,
                position_to_dependant_task.keys(),
            ):
                if isinstance(k, int):
                    args[k] = response
                else:
                    self._kwargs[k] = response

        self.celery_task = self.celery_task.apply_async(
            args,
            self._kwargs,
        )
        self.launched = True
        # Just to save RAM
        self._args = None
        self._kwargs = None
        return self

    def wait(self, timeout: Optional[float] = None):
        '''
        Wait for the task to complete.

        Args:
            timeout (Optional[float]): The maximum time to wait for the task to
                complete.

        Returns:
            Any: The result of the task.

        Raises:
            TimeoutError: If the task does not complete within the specified
                timeout.
        '''
        if not self.launched:
            self.launch(timeout=timeout)
        self.value = self.celery_task.get(timeout=timeout)
        return self.value


class TaskGroup():
    '''
    Represents a group of Celery tasks with additional management capabilities.

    This class provides an abstraction layer over Celery's GroupResult,
    allowing for more complex task handling, including dependency management
    and lazy execution.

    Attributes:
        group_result (Optional[GroupResult]): The result of the group of tasks.
            In detail, it contains the id of the group and the results of the
            tasks when they complete.
        launched (bool): Indicates whether the group of tasks has been
            launched.
        value (Any): The result of the group of tasks after completion.
    '''

    def __init__(self, group_result: Optional[GroupResult] = None):
        self._group_tasks = []
        self.group_result = group_result
        self.launched = False
        self.value = None

    @classmethod
    def launch_from_list(
        cls,
        tasks: List[Union[Task, 'TaskGroup']],
        group_id: Optional[str] = None,
    ) -> 'TaskGroup':
        '''
        Launch a group of tasks.

        Args:
            tasks (List[Union[Task, TaskGroup]]): The tasks to be launched.
            group_id (Optional[str]): The id of the group of tasks.

        Returns:
            TaskGroup: The TaskGroup instance.
        '''
        results = []
        for task in tasks:
            if isinstance(task, Task):
                if not task.launched:
                    task.launch()
                results.append(task.celery_task)
            elif isinstance(task, TaskGroup):
                results.extend([
                    t.celery_task
                    for t in task.get_tasks()
                ])
        group_result = GroupResult(
            id=str(uuid.uuid4()) if group_id is None else group_id,
            results=results,
        )
        return cls(group_result)

    @property
    def group_id(self) -> str:
        return self.group_result.id

    @property
    def status(self) -> Dict[str, str]:
        if not self.group_result or not self.group_result.results:
            return []
        return {
            task.id: task.status
            for task in self.group_result.results
        }

    def get_tasks(self) -> List[Task]:
        '''
        Get the tasks in the group.

        Returns:
            List[Task]: The tasks in the group.
        '''
        if not self.group_result or not self.group_result.results:
            return []
        return [
            Task(task)
            for task in self.group_result.results
        ]

    def get_task_ids(self) -> List[str]:
        '''
        Get the ids of the tasks in the group.

        Returns:
            List[str]: The ids of the tasks in the group.
        '''
        if not self.group_result or not self.group_result.results:
            return []
        return [
            task.id
            for task in self.group_result.results
        ]

    def add(self, task_signature: Celery.signature) -> None:
        '''
        Add a task to the group.

        Args:
            task_signature (Celery.signature): The signature of the task to be
                added.
        '''
        self._group_tasks.append(task_signature)

    def launch(self) -> 'TaskGroup':
        '''
        Launch the group of tasks.

        Returns:
            TaskGroup: The TaskGroup instance.
        '''
        if self._group_tasks:
            self.group_result = group(self._group_tasks).apply_async()
            self.launched = True
        else:
            self.group_result = None
        return self

    def gather(self, timeout: Optional[float] = None):
        '''
        Wait for all tasks in the group to complete.

        Args:
            timeout (Optional[float]): The maximum time to wait for the tasks
                to complete.

        Returns:
            List[Any]: The results of the tasks in the group.
        '''
        if not self.launched:
            self.launch()
        response = self.group_result.get(timeout=timeout)
        self.value = response
        return response


class FlowGrid():
    '''
    Represents a FlowGrid instance, which is responsible for managing tasks.

    This class provides an abstraction layer over Celery, allowing for more
    complex task handling, including dependency management and lazy execution.

    This class will be instantiated in the producer and consumer applications
    to manage tasks.

    Example:

    ```python
    from flowgrid import FlowGrid

    fg = FlowGrid()

    @fg.task
    def add(x, y):
        return x + y

    task: Task = add(1, 2)

    # This will launch the task (if not already launched it) and wait for it
    response = fg.wait(task)
    print(response)

    second_task: Task = add(3, 4)
    third_task: Task = add(5, 6)

    # You can create a group of tasks
    task_group = fg.group(second_task, third_task)

    # And launch (or wait) all at the same time
    fg.launch(task_group)

    # It can also be done on the same step
    # task_group = fg.launch(fg.group(second_task, third_task))

    fg.wait(task_group, timeout=10)
    ```

    Attributes:
        celery_app (Celery): The Celery application.
        _group_tasks (Optional[List[Celery.Signature]]): The tasks in the
            group.

    Args:
        celery_app (Optional[Celery]): The Celery application to be used.
    '''

    def __init__(
        self,
        celery_app: Optional[Celery] = None,
    ):
        if celery_app is None:
            celery_app = make_celery()
        self.celery_app: Celery = celery_app
        self._group_tasks = None

    def task(self, func: Union[Callable, Coroutine]) -> Callable[..., Task]:
        '''
            Decorator for creating a task.

            Args:
                func (Union[Callable, Coroutine]): The function to be
                    decorated.

            Returns:
                Callable[..., Task]: The decorated function.
        '''

        fg = self
        is_async = asyncio.iscoroutinefunction(func)

        class ManagedCeleryTask(CeleryTask):
            '''
            Inherits from CeleryTask to add custom behavior to tasks.

            This class provides an abstraction layer over Celery's Task class,

            Args:
                *args (Any): Arguments to be passed to the task.
                **kwargs (Any): Keyword arguments to be passed to the task.
            '''

            def before_task(self, *args, **kwargs) -> bool:
                '''
                Execute custom behavior before the task is executed.

                Args:
                    *args (Any): Arguments to be passed to the task.
                    **kwargs (Any): Keyword arguments to be passed to the
                        task.
                '''
                # TODO: Add possible Triggers
                if fg.is_revoked():
                    return True
                # task = fg.celery_app.current_task
                # task.update_state(state='PROGRESS')
                return False

            def after_task(self, *args, **kwargs):
                '''
                Execute custom behavior after the task is executed.

                Args:
                    *args (Any): Arguments to be passed to the task.
                    **kwargs (Any): Keyword arguments to be passed to the
                        task.
                '''
                # TODO: Add possible Callbacks
                pass

            def __call__(self, *args, **kwargs):
                '''
                Execute the task.

                Args:
                    *args (Any): Arguments to be passed to the task.
                    **kwargs (Any): Keyword arguments to be passed to the
                        task.

                Returns:
                    Any: The result of the task.
                '''
                is_revoked = self.before_task(*args, **kwargs)
                if is_revoked:
                    print('CANCELLED BEFORE START')
                    return
                result = super(ManagedCeleryTask, self).__call__(
                    *args, **kwargs,
                )
                self.after_task(*args, **kwargs)
                return result

        def __inner_func(config, *args, **kwargs):
            '''
            Inner function to be executed by the task.

            Args:
                config (Any): Configuration used internally to detect if we
                    have chords.
                *args (Any): Arguments to be passed to the task.
                **kwargs (Any): Keyword arguments to be passed to the task.
            '''
            if is_async:
                # Use asyncio.run for async functions
                return asyncio.run(func(*args, **kwargs))
            return func(*args, **kwargs)

        task_name = func.__name__
        celery_task = self.celery_app.task(
            name=task_name,
            base=ManagedCeleryTask,
        )(__inner_func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Task]:
            '''
            Wrapper function (decorator) for the task.

            Args:
                *args (Any): Arguments to be passed to the task.
                **kwargs (Any): Keyword arguments to be passed to the task.
            '''
            current_task = self.celery_app.current_task
            if current_task is not None:
                current_task.subtask = celery_task

            # task = celery_task.apply_async(args, kwargs)
            task = Task(celery_task)

            # TODO: This None will be the chord configuration
            task.prepare(None, *args, **kwargs)

            return task

        return wrapper

    def launch(self, task: Union[Task, TaskGroup]) -> Union[Task, TaskGroup]:
        '''
        Launch a task. Proxy method to Task.launch() and TaskGroup.launch().
        It is a convenience method to avoid having to check the type of the
        task.

        Args:
            task (Union[Task, TaskGroup]): The task(s) to be launched.

        Returns:
            Union[Task, TaskGroup]: The task(s) instance(s).
        '''
        return task.launch()

    def revoke(
        self,
        task: Union[str, Task],
        force: bool = False,
    ) -> None:
        '''
        Revoke a task.

        Args:
            task (Union[str, Task]): The task to be revoked.
            force (bool): Whether to force the task to stop. Defaults to False.
                If True, the task will be terminated immediately, in other case
                it will wait until the task finishes its current
                iteration/execution (when the task checks if it was revoked).

        Raises:
            ImportError: If the Redis library is not installed and the result
                backend is a Redis instance.
        '''
        if isinstance(task, str):
            task = self.get_task(task)
        if not task.launched:
            return
        task.celery_task.revoke(terminate=force)
        backend = self.celery_app.conf.result_backend
        if backend.startswith('redis://'):
            if redis is None:
                raise ImportError('Redis is not installed')
            redis_conn = redis.Redis.from_url(backend)
            redis_conn.set(f'flowgrid-revoked-{task.task_id}', '1',  ex=3600)

    def is_revoked(self, task: Optional[Union[str, Task]] = None) -> bool:
        '''
        Check if a task has been revoked.

        Args:
            task (Optional[Union[str, Task]]): The task to be checked. Defaults
                to None, in which case the current task is checked.
                Can only be none in worker context.

        Returns:
            bool: Whether the task has been revoked.
        '''
        if task is None:
            task = self.celery_app.current_task
        elif isinstance(task, str):
            task = self.get_task(task)
        if isinstance(task, Task):
            task = task.celery_task

        i = self.celery_app.control.inspect()
        revoked = i.revoked()
        if revoked is not None:
            for tasks in revoked.values():
                if task.request.id in tasks:
                    return True

        backend = self.celery_app.conf.result_backend
        if backend.startswith('redis://'):
            if redis is None:
                raise ImportError('Redis is not installed')
            redis_conn = redis.Redis.from_url(backend)
            value = redis_conn.get(f'flowgrid-revoked-{task.request.id}')
            return value is not None

        return False

    def update(self, *_, **kwargs):
        '''
        Update the task state. It supports metadate to indicate progress.
        Can only be used inside worker context.

        Example:

        ```python
        @fg.task
        def add(x, y):
            for i in range(10):
                fg.update(progress=i, total=10, percent=100*i/10)
                time.sleep(1)
            return x + y
        ```

        Args:
            *_: Ignored arguments.
            **kwargs (Any): Keyword arguments to be passed to the task.
        '''
        task = self.celery_app.current_task
        print(f'TASK: ({task}) Type: {type(task)}')
        if task is not None:
            # t = self.celery_app.AsyncResult(task.request.id)
            # print(f'ALL ABOUR T: {t}; t.state: {t.state}')
            task.update_state(state='PROGRESS', meta=kwargs)

    def get_task(self, task_id: str) -> Task:
        '''
        Get a task by its id.

        Args:
            task_id (str): The id of the task.

        Returns:
            Task: The task instance.
        '''
        return Task(
            self.celery_app.AsyncResult(task_id)
        )

    def group(
        self,
        *tasks: List[Task],
    ) -> TaskGroup:
        '''
        Get a task group by its ids.

        Args:
            *tasks (List[Task]): The tasks to be grouped.

        Returns:
            TaskGroup: The task group instance.
        '''
        task_group = TaskGroup()
        for task in tasks:
            task_group.add(task.get_signature())
        return task_group

    def wait(
        self,
        *tasks: Union[str, Task, TaskGroup],
        timeout: Optional[float] = None,
    ):
        '''
        Wait for all tasks to finish.

        Args:
            *tasks (Union[str, Task, TaskGroup]): The tasks to wait for.
            timeout (Optional[float]): The maximum time to wait for the tasks
                to complete.

        Returns:
            Any: The results of the tasks.

        Raises:
            TimeoutError: If the tasks do not complete within the specified
                timeout.
        '''
        parsed_tasks = []
        for task in tasks:
            if isinstance(task, (Task, TaskGroup)):
                parsed_tasks.append(task)
            elif isinstance(task, str):
                parsed_tasks.append(self.get_task(task))

        if len(parsed_tasks) == 0:
            return

        if len(parsed_tasks) == 1:
            task = parsed_tasks[0]
            if isinstance(task, Task):
                return task.wait(timeout=timeout)
            elif isinstance(task, TaskGroup):
                return task.gather(timeout=timeout)

        return TaskGroup.launch_from_list(parsed_tasks).gather(
            timeout=timeout,
        )

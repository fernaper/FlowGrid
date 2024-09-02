import uuid

from celery import Celery, Task as CeleryTask, group
from celery.result import GroupResult
from functools import wraps
from typing import Callable, Dict, List, Optional, TYPE_CHECKING, Union

from .celery_app import make_celery

try:
    import redis
except ImportError:
    redis = None

if TYPE_CHECKING:
    from celery.local import Proxy


class Task():

    def __init__(
        self,
        celery_task: Celery.AsyncResult,
    ):
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
        return self.celery_task.s(*self._args, **self._kwargs)

    def prepare(self, *args, **kwargs) -> 'Task':
        self._args = args
        self._kwargs = kwargs
        return self

    def launch(self, timeout: Optional[float] = None) -> 'Task':
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
        if not self.launched:
            self.launch(timeout=timeout)
        self.value = self.celery_task.get(timeout=timeout)
        return self.value


class TaskGroup():

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
        if not self.group_result or not self.group_result.results:
            return []
        return [
            Task(task)
            for task in self.group_result.results
        ]

    def get_task_ids(self) -> List[str]:
        if not self.group_result or not self.group_result.results:
            return []
        return [
            task.id
            for task in self.group_result.results
        ]

    def add(self, task_signature):
        self._group_tasks.append(task_signature)

    def launch(self) -> 'TaskGroup':
        if self._group_tasks:
            self.group_result = group(self._group_tasks).apply_async()
            self.launched = True
        else:
            self.group_result = None
        return self

    def gather(self, timeout: Optional[float] = None):
        if not self.launched:
            self.launch()
        response = self.group_result.get(timeout=timeout)
        self.value = response
        return response


class FlowGrid():

    def __init__(
        self,
        celery_app: Optional[Celery] = None,
    ):
        if celery_app is None:
            celery_app = make_celery()
        self.celery_app: Celery = celery_app
        self._group_tasks = None

    def task(self, func: Callable) -> Callable[..., Task]:
        """Decorator for creating a task."""

        fg = self

        class ManagedCeleryTask(CeleryTask):

            def before_task(self, *args, **kwargs) -> bool:
                # TODO: Add possible Triggers
                if fg.is_revoked():
                    return True
                # task = fg.celery_app.current_task
                # task.update_state(state='PROGRESS')
                return False

            def after_task(self, *args, **kwargs):
                # TODO: Add possible Callbacks
                pass

            def __call__(self, *args, **kwargs):
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
            # Config is user internally to detect and now if we have chords
            return func(*args, **kwargs)

        task_name = func.__name__
        celery_task = self.celery_app.task(
            name=task_name,
            base=ManagedCeleryTask,
        )(__inner_func)

        @wraps(func)
        def wrapper(*args, **kwargs) -> Optional[Task]:
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
        """Launch a task."""
        return task.launch()

    def revoke(
        self,
        task: Union[str, Task],
        force: bool = False,
    ) -> None:
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
        task = self.celery_app.current_task
        print(f'TASK: ({task}) Type: {type(task)}')
        if task is not None:
            # t = self.celery_app.AsyncResult(task.request.id)
            # print(f'ALL ABOUR T: {t}; t.state: {t.state}')
            task.update_state(state='PROGRESS', meta=kwargs)

    def get_task(self, task_id: str) -> Task:
        """Get a task by its id."""
        return Task(
            self.celery_app.AsyncResult(task_id)
        )

    def group(
        self,
        *tasks: List[Task],
    ) -> TaskGroup:
        """Get a task group by its ids."""
        task_group = TaskGroup()
        for task in tasks:
            task_group.add(task.get_signature())
        return task_group

    def wait(
        self,
        *tasks: Union[str, Task, TaskGroup],
        timeout: Optional[float] = None,
    ):
        """Wait for all tasks to finish."""
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

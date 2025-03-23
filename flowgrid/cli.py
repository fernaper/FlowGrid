import argparse
import os
import sys
import time
import multiprocessing

from typing import Optional, List

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from flowgrid import FlowGrid
from flowgrid.lazy_import import lazy


def start_celery_worker(
    app: str,
    concurrency: int,
    loglevel: str,
) -> None:
    '''
    Start a Celery worker process.

    Args:
        app: FlowGrid app name
        concurrency: Number of concurrent workers
        loglevel: Logging level
    '''
    # This is to ensure that lazy import works
    cwd = os.getcwd()
    sys.path.append(cwd)

    try:
        data = app.rsplit('.', 1)
        if len(data) != 2:
            raise ValueError('Invalid app name')
        app_module = data[0]
        app_name = data[1]
        module = lazy(app_module)
        fg = getattr(module, app_name)
    except Exception as e:
        print(f'Error loading app: {app}')
        print(e)
        sys.exit(1)

    if not isinstance(fg, FlowGrid):
        print(
            f'Invalid app. {app} is not a FlowGrid instance it is a {type(fg)}'
        )
        sys.exit(1)

    fg.celery_app.worker_main([
        'worker',
        f'--concurrency={concurrency}',
        f'--loglevel={loglevel}'
    ])


def main():
    parser = argparse.ArgumentParser(description='FlowGrid')
    subparsers = parser.add_subparsers(dest='command')

    worker_parser = subparsers.add_parser(
        'worker',
        help='Launch a FlowGrid worker'
    )

    worker_parser.add_argument(
        '--app', '-A',
        type=str,
        default=None,
        help='Flowgrid app name'
    )
    worker_parser.add_argument(
        '--concurrency', '-c',
        type=int,
        default=2,
        help='Number of concurrent workers'
    )
    worker_parser.add_argument(
        '--loglevel', '-l',
        type=str,
        default='info',
        help='Logging level (info, debug, warning, error).'
    )
    worker_parser.add_argument(
        '--reload', '-r',
        action='store_true',
        help='Enable auto-reload when Python files change'
    )
    worker_parser.add_argument(
        '--watch-dir', '-w',
        type=str,
        action='append',
        help=(
            'Additional directories to watch for changes '
            '(can be specified multiple times)'
        )
    )

    args = parser.parse_args()
    if args.command == 'worker':
        start_worker(
            args.app,
            args.concurrency,
            args.loglevel,
            args.reload,
            args.watch_dir,
        )
    else:
        parser.print_help()
        sys.exit(1)


class ReloadableWorker:
    '''
    A worker that can be reloaded when Python files change.

    Args:
        app: FlowGrid app name
        concurrency: Number of concurrent workers
        loglevel: Logging level (info, debug, warning, error)
        reload: Enable auto-reload when Python files change
        watch_dirs: Additional directories to watch for changes
    '''

    def __init__(
        self,
        app: str,
        concurrency: int,
        loglevel: str,
        reload: bool = False,
        watch_dirs: Optional[List[str]] = None,
    ):
        self.app = app
        self.concurrency = concurrency
        self.loglevel = loglevel
        self.reload = reload
        self.watch_dirs = watch_dirs or [os.getcwd()]
        self.worker_process = None
        self.stop_event = multiprocessing.Event()

    def _start_worker(self):
        '''Start a new worker process.'''
        # Terminate existing process if it exists
        if self.worker_process and self.worker_process.is_alive():
            self.worker_process.terminate()
            self.worker_process.join(timeout=5)
            if self.worker_process.is_alive():
                self.worker_process.kill()

        # Create and start a new worker process
        self.worker_process = multiprocessing.Process(
            target=start_celery_worker,
            args=(self.app, self.concurrency, self.loglevel)
        )
        self.worker_process.start()

    def _create_file_handler(self):
        '''Create a file system event handler for detecting changes.'''
        class ReloadHandler(FileSystemEventHandler):
            def __init__(self, stop_event):
                self.stop_event = stop_event

            def on_modified(self, event):
                if not event.is_directory and event.src_path.endswith('.py'):
                    print(
                        f'Detected change in {event.src_path}. '
                        'Restarting worker...'
                    )
                    self.stop_event.set()

        return ReloadHandler(self.stop_event)

    def run(self):
        '''Run the worker, with optional file watching and reloading.'''
        if not self.reload:
            # If reload is not enabled, just run the worker once
            # In current process
            start_celery_worker(self.app, self.concurrency, self.loglevel)
            return

        # Start initial worker
        self._start_worker()

        # Set up file watching
        event_handler = self._create_file_handler()
        observer = Observer()
        for watch_dir in self.watch_dirs:
            observer.schedule(event_handler, watch_dir, recursive=True)
        observer.start()

        try:
            while True:
                # Wait for file changes
                while not self.stop_event.is_set():
                    time.sleep(0.5)
                    # Check if worker process is still alive
                    if not self.worker_process.is_alive():
                        break

                # Restart worker on file change
                self._start_worker()
                self.stop_event.clear()

        except KeyboardInterrupt:
            print('Stopping worker...')
        finally:
            # Clean up
            if self.worker_process and self.worker_process.is_alive():
                self.worker_process.terminate()
            observer.stop()
            observer.join()


def start_worker(
    app: str,
    concurrency: int,
    loglevel: str,
    reload: bool = False,
    watch_dirs: Optional[List[str]] = None
) -> None:
    '''
    Start a FlowGrid worker.

    Args:
        app: FlowGrid app name
        concurrency: Number of concurrent workers
        loglevel: Logging level (info, debug, warning, error)
        reload: Enable auto-reload when Python files change
        watch_dirs: Additional directories to watch for changes
    '''
    worker = ReloadableWorker(app, concurrency, loglevel, reload, watch_dirs)
    worker.run()


if __name__ == '__main__':
    main()

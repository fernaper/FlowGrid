import argparse
import os
import sys

from flowgrid import FlowGrid
from flowgrid.lazy_import import lazy


def main():
    parser = argparse.ArgumentParser(description='FlowGrid')
    subparsers = parser.add_subparsers(dest='command')

    worker_parser = subparsers.add_parser(
        'worker',
        help="Launch a FlowGrid worker"
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
        help='Loggign level (info, debug, warning, error).'
    )

    args = parser.parse_args()
    if args.command == 'worker':
        start_worker(args.app, args.concurrency, args.loglevel)
    else:
        parser.print_help()
        sys.exit(1)


def start_worker(
    app: str,
    concurrency: int,
    loglevel: str,
):
    # This is to ensure that lazy import works
    cwd = os.getcwd()
    sys.path.append(cwd)

    try:
        data = app.rsplit('.', 1)
        if len(data) != 2:
            raise ValueError('Invalid app name')
        app = data[0]
        module = lazy(app)
        fg = getattr(module, data[1])
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


if __name__ == '__main__':
    main()

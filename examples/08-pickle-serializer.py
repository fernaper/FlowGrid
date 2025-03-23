import os
import pathlib

# os.environ['FLOWGRID_TASK_SERIALIZER'] = 'pickle'
# os.environ['FLOWGRID_RESULT_SERIALIZER'] = 'pickle'
# os.environ['FLOWGRID_ACCEPT_CONTENT'] = 'pickle'
# Equivalent to:
os.environ['FLOWGRID_SERIALIZER'] = 'pickle'

from flowgrid import FlowGrid  # noqa E402

fg = FlowGrid()


@fg.task
def dummy_example(path: pathlib.Path) -> pathlib.Path:
    '''
    A dummy example of a non-JSON serializable task, since
    pathlib.Path is not serializable by JSON.
    '''
    return path / 'new_file.txt'


def main():
    result = fg.wait(
        dummy_example(pathlib.Path.cwd())
    )
    print(result)
    # Expected: /path/to/current/directory/new_file.txt


if __name__ == '__main__':
    main()

from setuptools import setup, find_packages
try:
    from flowgrid import __version__
except ImportError:
    __version__ = '0.3.1'

if __name__ == '__main__':
    with open('README.md', 'r', encoding='utf8') as f:
        long_description = f.read()

    with open('requirements.txt', 'r') as f:
        requirements = f.read().split('\n')

    setup(
        name='py-flowgrid',
        version=__version__,
        license='MIT',
        description='A simplified, powerful interface for distributed task management in Python, built on Celery.',  # noqa E501
        long_description=long_description,
        long_description_content_type='text/markdown',
        author='Fernando Pérez',
        author_email='fernaperg@gmail.com',
        url='https://github.com/fernaper/flowgrid',
        packages=find_packages(),
        install_requires=requirements,
        entry_points='''
            [console_scripts]
            flowgrid=flowgrid.cli:main
        ''',
    )

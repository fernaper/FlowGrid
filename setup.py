from setuptools import setup, find_packages
from flowgrid import __version__

if __name__ == '__main__':
    with open('README.md', 'r', encoding='utf8') as f:
        long_description = f.read()

    with open('requirements.txt', 'r') as f:
        requirements = f.read().split('\n')

    setup(
        name='flowgrid',
        version=__version__,
        license='MIT',
        description='Flowgrid is a simple task queue for Python',
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

from setuptools import setup, find_packages
import pathlib
import re


def get_version():
    version_regex = re.compile(r"^__version__ = ['\"]([^'\"]*)['\"]")
    for line in pathlib.Path('exman', '__init__.py').open('rt').readlines():
        mo = version_regex.match(line)
        if mo:
            return mo.group(1)
    raise RuntimeError('Unable to find version in %s.' % ('exman/__init__',))


if __name__ == '__main__':
    setup(
        name='exman',
        packages=find_packages(),
        version=get_version(),
        description='Simple and minimalistic utility to manage many '
                    'experiments runs and custom analysis of results',
        long_description=open('README.rst').read(),
        python_requires='>=3.5',
        author='Max Kochurov',
        scripts=['bin/exman'],
        author_email='maxim.v.kochurov@gmail.com',
        install_requires=open('requirements.txt').readlines(),
        tests_require=open('requirements-dev.txt').readlines()
    )

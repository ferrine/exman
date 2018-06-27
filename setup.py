from setuptools import setup, find_packages

if __name__ == '__main__':
    setup(
        name='exman',
        packages=find_packages(),
        author='Max Kochurov',
        author_email='maxim.v.kochurov@gmail.com',
        install_requires=open('requirements.txt').readlines(),
        tests_require=['pytest']
    )

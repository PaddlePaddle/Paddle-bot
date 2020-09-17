import os
from setuptools import setup
from setuptools import find_packages

setup(
    name='paddlebot',
    version='0.0.0',
    description='PaddlePaddle bot',
    author='PaddlePaddle Author',
    author_email='paddle-dev@baidu.com',
    url='https://github.com/PaddlePaddle/Paddle-bot',
    packages=find_packages(),
    license="GPL3 License",
    install_requires=['pip', 'setuptools>=18.0'],
    dependency_links=[],
    classifiers=[
        "Development Status :: 1 - Planning", "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",
        "License :: Other/Proprietary License",
        "Operating System :: POSIX :: Linux", "Programming Language :: Cython",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules"
    ], )

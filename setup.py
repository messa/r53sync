#!/usr/bin/env python

from setuptools import setup, find_packages


setup(
    name='r53sync',
    version='0.0.1',
    description='',
    url='https://github.com/messa/r53sync',
    author='Petr Messner',
    author_email='petr.messner@gmail.com',
    license='MIT',
    classifiers=[
        'Programming Language :: Python :: 3.4',
    ],
    keywords='route53',
    packages=find_packages(exclude=['contrib', 'doc', 'test*']),
    install_requires=[
        'boto3',
        'click',
        'pyyaml',
    ],
    entry_points={
        'console_scripts': [
            'r53sync=r53sync:main',
        ],
    },
)

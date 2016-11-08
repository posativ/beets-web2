#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup


setup(
    name='beets-web2',
    version='0.2',
    description='alternate web API using Bottle.py',
    author='Martin Zimmermann',
    author_email='info@posativ.org',
    license='MIT',

    packages=[
        'beetsplug',
    ],

    install_requires=[
        'bottle>=0.12',
    ],

    extras_require={
        'waitress': ['waitress'],
    },

    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],
)

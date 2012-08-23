#!/usr/bin/python2
# -*- coding: utf-8 -*-

"""
Zabbix API
"""
import os
from setuptools import setup, find_packages, findall


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='zabbix-api',
    url='https://github.com/gescheit/scripts',
    version='0.1',
    license='GNU LGPL 2.1',
    author='Aleksandr Balezin',
    author_email='gescheit@list.ru',
    description='Zabbix API',
    long_description=read('README'),
    packages=find_packages(exclude=['bin', 'tests']),
    include_package_data=True,
    zip_safe=False,
    platforms='any',
    entry_points={
        'console_scripts': [
            'zabbix-client = zabbix.client:main',
        ]
    },
)

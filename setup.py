#!/usr/bin/env python
import codecs
import re
import os
#from importlib_metadata import entry_points
from setuptools import setup, find_packages


with open("README.md", 'r', encoding="utf-8") as fh:
    long_description = fh.read()

def read(*parts):
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()

requirements = ['paho-mqtt>=1.0', 'pyyaml>=6.0','schema>=0.7.2','netifaces>=0.10.0','jsonpath-ng>=1.5.2', 'pyuci']

setup(
    name='mqttled',
    version='0.1.0',
    description='MQTT control of OpenWRT LEDs with optional Home Assistant Discovery',
    author='Tom Grime',
    author_email='tom.grime@gmail.com',
    url='https://github.com/trevortrevor/mqttled',
    include_package_data=True,
    install_requires=requirements,
    license='MIT',
    zip_safe=False,
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords=['OpenWRT, mqtt, Home Assistant'],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: BSD",
    ],
    packages=find_packages(where='src'),
    package_dir={"": "src"},
    python_requires=">=3.9",
    entry_points={
        'console_scripts': [
            'mqttled=mqttled.__main__:run'
        ]
    }
)
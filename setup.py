#!/usr/bin/python2
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import re

with open('README.md', 'r') as fd:
    long_description = fd.read()

import os, re;
with open(os.path.join(os.path.dirname(__file__), 'pythonvideoannotator_module_virtualobjectgenerator','__init__.py')) as fd:
	version = re.search(r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]', fd.read(), re.MULTILINE).group(1)


setup(
	name='Python video annotator - module - virtual object generator',
	version=version,
	description="""""",
	author=['Ricardo Ribeiro'],
	author_email='ricardojvr@gmail.com',
	url='https://bitbucket.org/fchampalimaud/pythonvideoannotator-module-virtualobjectgenerator',
	long_description = long_description,
    long_description_content_type = 'text/markdown',
	packages=find_packages(),	
)

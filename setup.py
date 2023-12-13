#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import io
import re
from glob import glob
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import splitext

from setuptools import find_packages
from setuptools import setup


def read(*names, **kwargs):
    return io.open(
        join(dirname(__file__), *names),
        encoding=kwargs.get('encoding', 'utf8')
    ).read()


setup(
    name='phocus',
    version='0.1.0',
    description='Phocus Routing Model',
    long_description='%s\n%s' % (
        re.compile('^.. start-badges.*^.. end-badges', re.M | re.S).sub('', read('README.rst')),
        re.sub(':[a-z]+:`~?(.*?)`', r'``\1``', read('CHANGELOG.rst'))
    ),
    author='Michael Shuffett',
    author_email='michael@quantcollective.com',
    url='https://github.com/QuantCollective/phocus',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    py_modules=[splitext(basename(path))[0] for path in glob('src/*.py')],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        # complete classifier list: http://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: Unix',
        'Operating System :: POSIX',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Topic :: Utilities',
    ],
    keywords=[
        # eg: 'keyword1', 'keyword2', 'keyword3',
    ],
    install_requires=[
        'click==6.7',
        # 'tensorflow==1.4.0',
        'pandas==0.21.1',
        'boto3==1.5.9',
        'numpy==1.13.3',
        'ortools',
        # 'dash==0.19.0',
        # 'dash-auth',
        # 'dash-renderer==0.11.1',
        # 'dash-html-components==0.8.0',
        # 'dash-core-components==0.21.0rc1',
        # 'dash-table-experiments',
        # 'plotly',
        'googlemaps',
        'colorlover',
        'pendulum',
        'jsonpickle',
        'joblib',
        'tenacity',
        'progressbar2',
        'connexion'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'pytest-cov'],
    extras_require={
        # eg:
        #   'rst': ['docutils>=0.11'],
        #   ':python_version=="2.6"': ['argparse'],
    },
    entry_points={
        'console_scripts': [
            'phocus = phocus.cli:main',
        ]
    },
)

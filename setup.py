# Copyright (C) 2018 Sebastiaan Mannem
#
# This file is part of pg_replication_activity.
#
# pg_replication_activity is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pg_replication_activity is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pg_replication_activity.  If not, see <http://www.gnu.org/licenses/>.

'''
This module installs pg_replication_activity as a binary.
'''

import codecs
import os
import re
from setuptools import setup, find_packages

INSTALL_REQUIREMENTS = [
    'psycopg2<=2.7.5'
]


def find_version():
    '''
    This function reads the pg_replication_activity version from pg_replication_activity/__init__.py
    '''
    here = os.path.abspath(os.path.dirname(__file__))
    init_path = os.path.join(here, 'pgreplicationactivity', '__init__.py')
    with codecs.open(init_path, 'r') as file_pointer:
        version_file = file_pointer.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='pg_replication_activity',
    version=find_version(),
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),
    install_requires=INSTALL_REQUIREMENTS,
    entry_points={
        'console_scripts': [
            'pg_replication_activity=pgreplicationactivity.pg_replication_activity:main',
        ]
    }
)

# Copyright (C) 2018
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

all: clean test build tag push
all-latest: clean test build tag-latest push-latest
test: test-flake8 test-pylint test-coverage

clean:
	rm -rf pg_replication_activity.egg-info/

setup:
	pip install --no-cache-dir .

test-flake8:
	flake8 .

test-pylint:
	pylint *.py pgreplicationactivity tests

test-coverage:
	coverage run --source pgreplicationactivity setup.py test
	coverage report -m

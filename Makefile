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
	docker kill pgra_builder || echo 'pgra_builder was not running'
	docker rmi pgra_builder:f28 || echo 'Image was not there'
	docker rmi pgra_builder:c7 || echo 'Image was not there'

setup:
	pip install --no-cache-dir .

test-flake8:
	flake8 .

test-pylint:
	pylint *.py pgreplicationactivity tests

test-coverage:
	coverage run --source pgreplicationactivity setup.py test
	coverage report -m

docker-images: docker-image-f28 docker-image-c7

docker-image-f28:
	docker build -t pgra_builder:f28 -f docker/Docker.f28 docker

docker-image-c7:
	docker build -t pgra_builder:c7 -f docker/Docker.c7 docker

rpms: rpm-f28 rpm-c7

rpm-f28:
	docker kill pgra_builder || echo 'pgra_builder was not running'
	docker run -d --rm --name pgra_builder -v $$PWD:/pgreplicationactivity pgra_builder:f28 sleep 86400
	docker exec pgra_builder /pgreplicationactivity/rpmspec/build.sh
	mkdir -p rpms
	docker exec pgra_builder find /home/rpmbuild/rpmbuild/ -name '*.rpm' | while read rpm; do docker cp "pgra_builder:$$rpm" ./rpms; done
	docker kill pgra_builder

rpm-c7:
	docker kill pgra_builder || echo 'pgra_builder was not running'
	docker run -d --rm --name pgra_builder -v $$PWD:/pgreplicationactivity pgra_builder:c7 sleep 86400
	docker exec pgra_builder /pgreplicationactivity/rpmspec/build.sh
	mkdir -p rpms
	docker exec pgra_builder find /home/rpmbuild/rpmbuild/ -name '*.rpm' | while read rpm; do docker cp "pgra_builder:$$rpm" ./rpms; done
	docker kill pgra_builder

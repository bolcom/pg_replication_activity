# Copyright (C) 2018
#
# This file is part of switchovertest.
#
# switchovertest is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# switchovertest is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with switchovertest.  If not, see <http://www.gnu.org/licenses/>.

COMPOSENAME := $(shell basename ${PWD})

all: clean run

clean:
	docker-compose kill || echo "Error"
	docker-compose rm -f || echo "Error"
	docker rmi ${COMPOSENAME}_master:latest ${COMPOSENAME}_standby:latest ${COMPOSENAME}_tester:latest || echo "Error"
	docker network rm ${COMPOSENAME}_postgres || echo "Error"

run:
	docker-compose up -d

switchover:
	./switchover.sh ${COMPOSENAME}_standby_1 ${COMPOSENAME}_master_1

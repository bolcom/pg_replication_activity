# pg_replication_activity

## What does it do
`pg_replication_activity` operates like pgtop, pg_view or pg_activity, but instead of monitoring Postgres processes it displays Postgres Replication info of a replicated cluster.

## Quick start
This program requires python3, so make sure you have that installed.

If you want to install the python modules, you can simply install them with `make setup`. The modules will be installed in the current python sitelib and an `EASY-INSTALL-ENTRY-SCRIPT` will be created.

If you rather build RPMs, you can build them using `make images rpms`. The new RPMs will be placed in the `rpms` subfolder. Example for Fedora28:

* `python3-pg_replication_activity-0.0.1-1.fc28.noarch.rpm`: the module

* `python3-pg_replication_activity-0.0.1-1.fc28.src.rpm`: the source rpm

* `python3-pg_replication_activity-bin-0.0.1-1.fc28.noarch.rpm`: the
`EASY-INSTALL-ENTRY-SCRIPT` and man page

## How is it developed
This projected started out as a fork of https://github.com/julmon/pg_activity/commit/ec96aa7f8e0b85a21956a3bd75a8ad26c7d6f5be. Since then a lot of changes have been done to

* upgrade code quality,
* update to newer standards and
* change from process details to replication details.

# What does it contain
In the basis this is a python project and you can simply build it using the setup.py in the root folder. But next to the python code, also docker files, RPM spec files, man doc files and build scripts are added, so you can build RPMs for Fedora 28 and/or Centos 7.

## Caveats
### RPM for Red Hat 7
It is quite easy to build for Red Hat 7 using a docker image for Red Hat 7, and using the docker file / build script as used for Centos 7 (only replace `FROM` in the `Dockerfile`). Note, however, that Red Hat 7 images require a valid Red Hat subscription.

### RPM for other versions
You probably can use the same docker files and build scripts to build for other versions. For Centos 8, replace `yum` with `dnf`. For other versions of Fedora, just use the same as for Fedora 28 (only change `FROM` in the `Dockerfile`).

### Other
See the man page for all other caveats.

## `Makefile`
All development logic is in the make file.
* Setup python module and build RPMs: `make all`
* Test all code: `make test`
* Test for pylint issues: `make test-pylint`
* Test for flake8 issues: `make test-flake8`
* Unittest: `make coverage`
* Clean: `make clean`
* Clean python clutter: `make clean-python`
* Clean docker images: `make clean-images`
* Build rpmbuilder images: `make images`
* Build rpmbuilder image Fedora 28: `make image-f28`
* Build rpmbuilder image Centos 7: `make image-c7`
* Build RPMs: `make rpms`
* Build RPMs Fedora 28: `make rpm-f28`
* Build RPMs Centos 7: `make rpm-c7`

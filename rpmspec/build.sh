#!/bin/bash
set -ex
SW_NAME=pg_replication_activity
PKG_VERSION=0.0.1
PKG_NAME="${SW_NAME}-${PKG_VERSION}"
PYTHONVER=$(rpm -E %{python3_pkgversion})
TAR_NAME="python${PYTHONVER}-${PKG_NAME}.tar.gz"
TEMPDIR=$(mktemp -d)

mkdir -p ~/rpmbuild/SOURCES
mkdir "${TEMPDIR}/${PKG_NAME}"
cp -av /pgreplicationactivity/{docs,pgreplicationactivity,setup.py} "${TEMPDIR}/${PKG_NAME}/"
cd "${TEMPDIR}"
tar -cvf ~/rpmbuild/SOURCES/"${TAR_NAME}" .
rpmbuild -ba /pgreplicationactivity/rpmspec/pg_replication_activity.spec

#!/bin/sh
#
# Set up unipycation
#
# You need: hg, git.
# To translate you probably want pypy.

DIR=$(cd $(dirname $0); pwd -P)
DEPSDIR=${DIR}/deps
PYROBASE=${DEPSDIR}/pyrolog-unipycation
SHAREDBASE=${DEPSDIR}/unipycation-shared
ENV_SCRIPT=${DIR}/env.sh

echo "\nRemoving existing deps (if any)..."
rm -Rf ${DEPSDIR} && mkdir ${DEPSDIR}

echo "Installing deps..."
cd ${DEPSDIR} && \
	hg clone ssh://hg@bitbucket.org/cfbolz/pyrolog-unipycation \
	${PYROBASE} && \
	cd ${PYROBASE} && hg up unipycation

cd ${DEPSDIR} && \
	git clone git@bitbucket.org:vext01/unipycation-shared.git \
	${SHAREDBASE} && \
	ln -sf ${SHAREDBASE}/unipycation_shared/uni.py ${DIR}/lib_pypy/

echo "#!/bin/sh" > ${ENV_SCRIPT}
echo "export PYTHONPATH=${PYTHONPATH}:${PYROBASE}:${SHAREDBASE}" >> ${ENV_SCRIPT}

echo "\nDone!\n\nNow source ${ENV_SCRIPT} to setup your environment"
echo "E.g. '. ./env.sh' or 'source ./env.sh'"

echo "\nTo translate, run:"
echo "  cd ${DIR} && \\ \n\t./rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py"

echo "\nOr on OpenBSD, install the newest GCC package and do:"
echo "  cd ${DIR} && \\ \n\tCC=egcc ./rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py"

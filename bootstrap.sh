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
PYRO_REPO=ssh://hg@bitbucket.org/cfbolz/pyrolog-unipycation
SHARED_REPO=git@bitbucket.org:vext01/unipycation-shared.git

envsh() {
	echo "#!/bin/sh" > ${ENV_SCRIPT} && \
		echo "export PYTHONPATH=\${PYTHONPATH}:${PYROBASE}:${SHAREDBASE}" >> ${ENV_SCRIPT} || return 1
}

symlink() {
	ln -sf ${SHAREDBASE}/unipycation_shared/uni.py ${DIR}/lib_pypy/ || \
		return 1
}

update_deps() {
	echo "Updating deps..." && \
		cd ${PYROBASE} && hg pull -u && \
		cd ${SHAREDBASE} && git pull -u || return 1
}

#cd ${PYROBASE} && hg up unipycation && \
init() {
	echo "\nRemoving existing deps (if any)..." && \
		rm -Rf ${DEPSDIR} && mkdir ${DEPSDIR} && \

		echo "Installing deps..." && \
		cd ${DEPSDIR} && \
		hg clone -u unipycation ${PYRO_REPO} ${PYROBASE} && \
		git clone ${SHARED_REPO} ${SHAREDBASE} && \

		symlink && envsh

		echo "\nDone!\n\nNow source ${ENV_SCRIPT} to setup your environment"
		echo "E.g. '. ./env.sh' or 'source ./env.sh'"

		echo "\nTo translate, run:"
		echo "  cd ${DIR} && \\ \n\t./rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py"

		echo "\nOr on OpenBSD, install the newest GCC package and do:"
		echo "  cd ${DIR} && \\ \n\tCC=egcc ./rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py"
}

usage() {
	echo "\nusage: bootstrap.sh (init|envsh|update-deps|symlink)\n"

	echo "    init:         initial setup"
	echo "    envsh:        regenerate env.sh"
	echo "    update-deps:  update dependencies from repos"
	echo "    symlink:      relink uni.py into the project"
	echo ""
}

case $1 in
	init) init;;
	envsh) envsh;;
	update-deps) update_deps;;
	symlink) symlink;;
	*) usage;;
esac


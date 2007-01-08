#!/sbin/runscript

CMD=/opt/pypy-dist/pypy/tool/build/bin/server

depend() {
	use net
}

start() {
	ebegin "Starting PyPy meta server"
	start-stop-daemon --start --quiet --exec $CMD
	eend $?
}

stop() {
	ebegin "Stopping PyPy meta server"
	start-stop-daemon --stop --quiet --exec $CMD
	eend $?
}

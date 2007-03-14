#!/sbin/runscript

CMD=/opt/pypy-dist/pypy/tool/build/bin/metaserver
PIDFILE=/var/run/build_metaserver.pid
LOGFILE=/var/log/build_metaserver.log

depend() {
	use net
}

start() {
	ebegin "Starting PyPy meta server"
	start-stop-daemon --start --quiet --exec $CMD \
        --make-pidfile --pidfile $PIDFILE --background >> $LOGFILE
	eend $?
}

stop() {
	ebegin "Stopping PyPy meta server"
	start-stop-daemon --stop --quiet --exec $CMD
	eend $?
}

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("js2")
py.log.setconsumer("js2", ansi_log)

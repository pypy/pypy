import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("js")
log.setconsumer("js", ansi_log)

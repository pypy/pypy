# logging

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("backendopt")
py.log.setconsumer("backendopt", ansi_log)

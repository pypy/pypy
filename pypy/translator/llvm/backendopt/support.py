# logging

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("llvmbackendopt")
py.log.setconsumer("llvmbackendopt", ansi_log)

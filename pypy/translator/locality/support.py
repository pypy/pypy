# logging

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("locality")
py.log.setconsumer("locality", ansi_log)

import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer("gctransform")
py.log.setconsumer("gctransform", ansi_log)

"""
Log for the JVM backend
Do the following:
  from pypy.translator.jvm.log import log
"""

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("jvm") 
py.log.setconsumer("jvm", ansi_log) 


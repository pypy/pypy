import py
from pypy.tool.ansi_print import ansi_log
log = py.log.Producer('llvm') 
py.log.setconsumer('llvm', ansi_log) 

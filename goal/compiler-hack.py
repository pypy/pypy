# Hacks to import compiler package
# As of revision 3865

import os
os.error = OSError
import __builtin__
__builtin__.reload = lambda x: x
import ihooks
ihooks.install()
import compiler
c = compiler.compile('a=1', '', 'exec')
import dis
dis.dis(c)

#from pypy.module.thread import ll_thread
from pypy.translator.stm import rstm





# __________  Entry point  __________

def entry_point(argv):
    print "hello world"
    rstm.transaction_boundary()
    i = 100
    while i > 1:
        i *= 0.821
    rstm.transaction_boundary()
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None

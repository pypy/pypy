import os, sys
from pypy.translator.test.snippet import sieve_of_eratosthenes as soe

def debug(msg): 
    os.write(2, "debug: " + msg + '\n')
   

# __________  Entry point  __________

def entry_point(argv):
    count = soe()
    return count

# _____ Define and setup target ___

def target(*args):
    return entry_point, None


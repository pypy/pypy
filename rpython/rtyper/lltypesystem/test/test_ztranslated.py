import time, os, sys
import py
import gc
from rpython.tool.udir import udir
from rpython.rlib import rvmprof, rthread
from rpython.translator.c.test.test_genc import compile
from rpython.rlib.nonconst import NonConstant
from rpython.rtyper.lltypesystem import rffi

def setup_module(mod):
    pass

def use_str():
    mystr = b"abc"
    ptr = rffi.get_raw_address_of_string(mystr)
    assert ptr[0] == 79
    gc.collect()
    assert ptr[0] == 79
    mystr = None



def main(argv=[]):
    use_str()
    return 0

# ____________________________________________________________

def target(driver, args):
    return main

def test_compiled():
    fn = compile(main, [], gcpolicy="minimark")
    fn()

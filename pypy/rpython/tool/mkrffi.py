#!/usr/bin/env python

import ctypes

import py
from py.code import Source


def proc_func(func):
    name = func.__name__
    src = Source("""
    c_%s = rffi.llexternal('%s', [rffi.INT], 
    lltype.Ptr(lltype.FixedSizeArray(lltype.Void, 1)))
    """%(name, name))
    return src

def proc_module(module):

    ns = module.__dict__

    for key, value in ns.items():
        print "found:", key
        if isinstance(value, ctypes._CFuncPtr):
            proc_func(value)

if __name__ == "__main__":
    test_1()












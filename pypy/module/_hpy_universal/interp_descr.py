"""
Implements HPy attribute descriptors, i.e members and getsets.
"""
from pypy.interpreter.error import oefmt

def add_member(space, w_type, hpymember):
    raise oefmt(space.w_NotImplementedError, "members")

def add_getset(space, w_type, hpygetset):
    raise oefmt(space.w_NotImplementedError, "getsets")

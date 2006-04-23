from pypy.rpython.objectmodel import r_dict
import os, sys
import operator

# __________  Entry point  __________

def eq(arg1, arg2):
    return arg1 == arg2

def myhash(arg):
    return arg.__hash__()

class number(object):
    def __init__(self,arg):
        self.num = arg
    def __hash__(self):
        return self.num

    def __eq__(self,other):
        return self.num == other.num

def entry_point(argv):
    dict_one = r_dict(eq,myhash)
    dict_two = r_dict(eq,myhash)
    os.write(1,'test for rdict.update\n')
    one = number(1)
    two = number(2)
    three = number(3)
    four = number(4)

    dict_one[one] = None
    dict_one[four] = None

    dict_two[two] = None
    dict_two[three] = None

    dict_one.update(dict_two)
    for key in dict_one.iterkeys():
        os.write(1,'found %s\n' % key.num)

    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None


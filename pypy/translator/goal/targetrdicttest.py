from pypy.rpython.objectmodel import r_dict
import os, sys
import operator

# __________  Entry point  __________

def eq(arg1, arg2):
    return arg1 == arg2

def myhash(arg):
    return arg.__hash__()

class hashable(object):
    def __hash__(self):
        return 1

class unhashable(hashable):
    def __hash__(self):
        raise TypeError
        return 1

def entry_point(argv):
    mydict = r_dict(eq,myhash)
    os.write(1,'test for exceptions raised by r_dict on unhashable objects\n')
    hobj = hashable()
    uhobj = unhashable()
    mydict[hobj] = 'a' 
    os.write(1,'test 1: hashing an unhashable object\n')
    try:
        myhash(uhobj) 
    except KeyError,e:
        os.write(1,'\tKeyError\t')
        os.write(1,str(e) + '\n')
    except TypeError,e:
        os.write(1,'\tTypeError\t')
        os.write(1,str(e) + '\n')
    else:
        os.write(1,'\tno exception\n')

    os.write(1,'test 2: getitem with unhashable key:\n')
    try:
        mydict[uhobj] 
    except KeyError,e:
        os.write(1,'\tKeyError\t')
        os.write(1,str(e) + '\n')
    except TypeError,e:
        os.write(1,'\tTypeError\t')
        os.write(1,str(e) + '\n')
    else:
        os.write(1,'\tno exception\n')

#   The Following can't be translated (for reasons I don't understand:
#   it has to do with the assignment.
#
#    os.write(1,'test 1: setitem with unhashable key:\n')
#    try:
#        mydict[uhobj] = 'b'
#    except KeyError:
#        os.write(1,'\tKeyError\n')
#    except TypeError:
#        os.write(1,'\tTypeError\n')
#    else:
#        os.write(1,'\tno exception\n')
#
    return 0

# _____ Define and setup target ___

def target(*args):
    return entry_point, None


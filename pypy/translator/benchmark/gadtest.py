"""
This file contains some monkeypatching for Gadfly, depending on
the options for pypy-c things are patched or not.

There is some bug related to files and marshal that prevented me
to finish this stuff.

TODO:
    Make paths independent from an actual install of Gadfly
    integrate benchmark into benchmarks.py
    maybe extract a few parts from Gadfly's test to make it take
    less time
    
    If instead anybody likes to continue from here, please feel free.
    I was too much occupated by everything else.
    cheers - chris
"""

import site

"""
Monkey-patching
gadfly asks for InstanceType. We need to cheat for new style classes.
Also time.gmtime does not always exist in PyPy. We simply patch it in.
"""

# depending on the buils, we may or may not have gmtime. Just make it work.
import time
try:
    time.gmtime
except AttributeError:
    time.gmtime = time.time

# do we have oldstyle classes? If not, just cheat.
import types
class _X: pass
if type(_X) is not types.ClassType:
    print 'emulating old-style classes by monkeypatching'
    _isinstance = isinstance
    def isinstance(ob, klass):
        if klass is types.InstanceType:
            return ob.__class__.__module__ != '__builtin__'
        return _isinstance(ob, klass)
    import __builtin__
    __builtin__.isinstance = isinstance
    _type = type
    def type(ob):
        tp = _type(ob)
        if ob.__class__.__module__ != '__builtin__':
            return types.InstanceType
else:
    print 'using real old-style classes (slow ATM)'
execfile('Desktop/gadflyZip/test/test_gadfly.py')
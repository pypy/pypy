"""
    This module analyzes the delta between the attributes of a module
    as seen by the PyPy interpreter, and the same module as seen by the
    CPython interpreter.  It can be used to help insure that pure-python
    functionality as provided by PyPy matches the original functionality
    provided by CPython.

    This module may be used as a standalone script, with modules to be
    analyzed listed on the command line (default if none given is to
    analyze __builtin__) or the moduledelta() function may be called
    from other modules.  When used standalone, it always analyzes
    using the standard object space.

    The current implementation does not examine function signatures --
    it only shows the attributes which are exclusively in one module
    or the other.

    The current implementation also may not work for non-builtin extension
    modules, depending on whether there is a different path variable
    inside PyPy, or whether the presence of the PyPy pure python module
    will shadow the original C module, making it unavailable for comparison.
"""

import autopath
from pypy.interpreter.gateway import app2interp
from sets import Set

def app_getmodattributes(modname):
    """ Return the attributes of the named module """
    pypy_module = __import__(modname,globals(),None,[])
    return pypy_module.__dict__.keys()

def moduledelta(space,modname):
    """
        moduledelta(space,modname) imports the module from inside
        the given space, and also from CPython, and returns a tuple
        (missing,extra) which describes attributes in CPython but
        not in PyPy, and the opposite.
    """

    wrapped_func = app2interp(app_getmodattributes).get_function(space)

    pypy_module = wrapped_func(space.wrap(modname))
    pypy_module = space.unpackiterable(pypy_module)
    pypy_module = [space.unwrap(x) for x in pypy_module]
    pypy_module = Set(pypy_module)

    c_module = __import__(modname,globals(),None,[])
    c_module = Set(c_module.__dict__.keys()) | Set(['__dict__','__new__'])
    diff = c_module ^ pypy_module
    missing = list(diff & c_module)
    extra = list(diff & pypy_module)
    missing.sort()
    extra.sort()
    return missing,extra

if __name__ == '__main__':
    from sys import argv
    from pypy.objspace.std import StdObjSpace

    def showdiff(name,stuff):
        if stuff:
            print
            print name
            for i in stuff: print "         ",i
            print

    modlist = argv[1:]
    if not modlist:
        print "modanalyze <module> [<module> ...]"
        print
        print "Analyzing __builtin__ by default"
        print
        modlist = ['__builtin__']

    print "Initializing std object space"
    std = StdObjSpace()

    for modname in modlist:
        print
        print 'Comparing %s module' % modname
        missing,extra = moduledelta(std,modname)
        showdiff("    Missing from PyPy",missing)
        showdiff("    Extra in PyPy",extra)

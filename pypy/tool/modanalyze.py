
from pypy.interpreter.gateway import app2interp
from sets import Set

def showdiff(name,stuff):
    if stuff:
        print
        print name
        for i in stuff: print "         ",i
        print

def app_getmodattributes(modname):
    moduleundertest = __import__(modname,globals(),None,[])
    return moduleundertest.__dict__.keys()

def module_delta(space,modname):
    wrapped_func = app2interp(app_getmodattributes).get_function(space)

    pypy_b = wrapped_func(space.wrap(modname))
    pypy_b = space.unpackiterable(pypy_b)
    pypy_b = [space.unwrap(x) for x in pypy_b]
    pypy_b = Set(pypy_b)

    import __builtin__ as c_b
    c_b = Set(c_b.__dict__.keys()) | Set(['__dict__','__new__'])
    diff = c_b ^ pypy_b
    missing = diff & c_b
    extra = diff & pypy_b
    return missing,extra

if __name__ == '__main__':
    from pypy.objspace.std import StdObjSpace
    print "Initializing std object space"
    std = StdObjSpace()

    for modname in ['__builtin__']:
        print
        print 'Comparing %s module' % modname
        missing,extra = module_delta(std,modname)
        showdiff("    Missing from PyPy",missing)
        showdiff("    Extra in PyPy",extra)

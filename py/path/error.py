"""
module with some shared utils 
"""

class Error(Exception):
    def __init__(self, *args):
        self.args = args

class Invalid(Error): 
    pass 

class FileNotFound(Invalid): 
    pass 
class FileExists(Invalid): 
    pass
class NoSpace(Invalid): 
    pass
class IsDirectory(Invalid): 
    pass
class NoDirectory(Invalid):
    pass
class PermissionDenied(Invalid): 
    pass
class NestedLink(Invalid):
    pass


#__________________________________________________________
# XXX use module errno
_errnoclass = {}
for errno, name in {
    2 : 'FileNotFound',
    3 : 'FileExists',
    13 : 'PermissionDenied',
    17 : 'FileExists',
    20 : 'NoDirectory',
    21 : 'IsDirectory',
    28 : 'NoSpace',
    40 : 'NestedLink',
    }.items():

    exec """
class %(name)s(%(name)s):
    pass 
""" % locals()
    _errnoclass[errno] = eval(name)

def error_enhance((cls, error, tb)):
    assert cls is not None
    if isinstance(error, (Error, KeyboardInterrupt, SystemExit, 
                  MemoryError)) or not hasattr(error, 'errno'):
        raise cls, error, tb
    #assert isinstance(error, IOError)
    ncls = _errnoclass.get(error.errno)
    if not ncls:
        raise cls, error, tb
    ncls = enhanceclass(error.__class__, ncls)
    newerror = ncls()
    newerror.__dict__.update(error.__dict__)
    raise ncls, newerror, tb  # XXX traceback shows wrong data? 

def enhanceclass(baseclass, newclass, cache={}):
    if issubclass(newclass, baseclass):
        return newclass
    else:
        try:
            return cache[baseclass, newclass]
        except KeyError:
            import new
            Mixed = new.classobj(
                         newclass.__name__, 
                         (newclass, baseclass),
                         {})

            cache[baseclass, newclass] = Mixed
            return Mixed


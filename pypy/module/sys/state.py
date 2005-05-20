"""
Implementation of interpreter-level 'sys' routines.
"""
import pypy
#from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError

import sys, os 

def hack_cpython_module(modname):
    "NOT_RPYTHON. Steal a module from CPython."
    cpy_module = __import__(modname, globals(), locals(), None)
    return cpy_module

# ____________________________________________________________
#

builtin_module_names = ['__builtin__', 'sys', 'exceptions']

# Create the builtin_modules dictionary, mapping names to Module instances
builtin_modules = {}
for fn in builtin_module_names:
    builtin_modules[fn] = None

# The following built-in modules are not written in PyPy, so we
# steal them from Python.
for fn in ['posix', 'nt', 'os2', 'mac', 'ce', 'riscos',
           'math', 'array', 'select',
           '_random', '_sre', 'time', '_socket', 'errno',
           'unicodedata',
           'parser', 'fcntl', '_codecs', 'binascii'
           ]: 
    if fn not in builtin_modules and not os.path.exists(
            os.path.join(os.path.dirname(pypy.__file__),
                         'lib', fn+'.py')):
        try:
            builtin_modules[fn] = hack_cpython_module(fn)
        except ImportError:
            pass
        else:
            builtin_module_names.append(fn)

builtin_module_names.sort() 

class State: 
    def __init__(self, space): 
        self.space = space 
        self.w_builtin_module_names = space.newtuple(
            [space.wrap(fn) for fn in builtin_module_names])
        self.w_modules = space.newdict([])
        for fn, module in builtin_modules.items(): 
            space.setitem(self.w_modules, space.wrap(fn), space.wrap(module))
        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])
        self.setinitialpath(space) 

    def setinitialpath(self, space): 
        # Initialize the default path
        from pypy.interpreter import autopath
        srcdir = os.path.dirname(autopath.pypydir)
        python_std_lib = os.path.normpath(
                os.path.join(autopath.pypydir, os.pardir,'lib-python', '2.3.4'))
        python_std_lib_modified = os.path.normpath(
                os.path.join(autopath.pypydir, os.pardir,'lib-python', 'modified-2.3.4'))

        pypy_lib = os.path.join(autopath.pypydir, 'lib') 
        assert os.path.exists(python_std_lib) 
        assert os.path.exists(python_std_lib_modified)
        importlist = ['']
        for p in os.environ.get('PYTHONPATH', '').split(':'): 
            if p: 
                importlist.append(p) 
        importlist.extend([pypy_lib, python_std_lib_modified, python_std_lib])
        self.w_path = space.newlist([space.wrap(x) for x in importlist])

def get(space): 
    return space.fromcache(State)

def pypy_getudir(space):
    """NOT_RPYTHON"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))

def getdefaultencoding(space): 
    return space.wrap(sys.getdefaultencoding())

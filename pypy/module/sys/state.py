"""
Implementation of interpreter-level 'sys' routines.
"""
import pypy
#from pypy.interpreter.module import Module
from pypy.interpreter.error import OperationError

import sys, os 

def load_cpython_module(modname):
    "NOT_RPYTHON. Steal a module from CPython."
    cpy_module = __import__(modname, globals(), locals(), None)
    return cpy_module

# ____________________________________________________________
#

ALL_BUILTIN_MODULES = [
    'posix', 'nt', 'os2', 'mac', 'ce', 'riscos',
    'math', 'array', 'select',
    '_random', '_sre', 'time', '_socket', 'errno',
    'unicodedata',
     'parser', 'fcntl', '_codecs', 'binascii'
]

class State: 
    def __init__(self, space): 
        self.space = space 

        self.w_modules = space.newdict([])
        self.complete_builtinmodules()

        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])
        self.setinitialpath(space) 

    def install_faked_module(self, modname):
        space = self.space
        try:
            module = load_cpython_module(modname)
        except ImportError:
            return False
        else:
            space.setitem(self.w_modules, space.wrap(modname),
                          space.wrap(module))
            return True

    def complete_builtinmodules(self):
        space = self.space
        builtinmodule_list = self.space.get_builtinmodule_list()
        builtinmodule_names = [name for name, mixedname in builtinmodule_list]

        if not space.options.nofakedmodules:
            for modname in ALL_BUILTIN_MODULES:
                if modname not in builtinmodule_names:
                    if not (os.path.exists(
                            os.path.join(os.path.dirname(pypy.__file__),
                            'lib', modname+'.py'))):
                        if self.install_faked_module(modname):
                             builtinmodule_names.append(modname)
        builtinmodule_names.sort()
        self.w_builtin_module_names = space.newtuple(
            [space.wrap(fn) for fn in builtinmodule_names])

    def setinitialpath(self, space): 
        # Initialize the default path
        from pypy.interpreter import autopath
        srcdir = os.path.dirname(autopath.pypydir)
        python_std_lib = os.path.normpath(
                os.path.join(autopath.pypydir, os.pardir,'lib-python', '2.4.1'))
        python_std_lib_modified = os.path.normpath(
                os.path.join(autopath.pypydir, os.pardir,'lib-python', 'modified-2.4.1'))

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

class IOState: 
    def __init__(self, space): 
        self.space = space
        if space.options.uselibfile: 
            self.w_stdout = space.call_function(space.builtin.get('file'))
            self.w_stderr = space.call_function(space.builtin.get('file'))
            self.w_stdin = space.call_function(space.builtin.get('file'))
        else: 
            self.w_stdout = space.wrap(sys.__stdout__) 
            self.w_stderr = space.wrap(sys.__stderr__) 
            self.w_stdin = space.wrap(sys.__stdin__) 

def getio(space): 
    return space.fromcache(IOState) 

def _pypy_getudir(space):
    """NOT_RPYTHON"""
    from pypy.tool.udir import udir
    return space.wrap(str(udir))
_pypy_getudir._annspecialcase_ = "override:ignore"

# we need the inderaction because this function will live in a dictionary with other 
# RPYTHON functions and share call sites with them. Better it not be a special-case
# directly. 
def pypy_getudir(space):
    return _pypy_getudir(space)

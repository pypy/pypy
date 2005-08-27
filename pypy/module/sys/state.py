"""
Implementation of interpreter-level 'sys' routines.
"""
import pypy
from pypy.interpreter.error import OperationError

import sys, os 

# ____________________________________________________________
#

class State: 
    def __init__(self, space): 
        self.space = space 

        self.w_modules = space.newdict([])

        self.w_warnoptions = space.newlist([])
        self.w_argv = space.newlist([])
        self.setinitialpath(space) 

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

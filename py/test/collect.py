from __future__ import generators

import sys, inspect, types, imp
from py import path, test 
import py
        
class Error(object):
    """ represents a non-fatal exception while collecting. """
    def __init__(self, excinfo):
        self.excinfo = excinfo

    def __repr__(self):
        tb = self.excinfo[2]
        while tb.tb_next:
            tb = tb.tb_next
        
        return '<collect.Error in %r, line %d>' % (
            tb.tb_frame.f_code.co_filename,
            tb.tb_lineno)

class Collector(object):
    """ instances are *restartable iterators*. They will yield Units or
        Collector instances during iteration.  
    """
    Item = test.run.Item 

    def iterunits(self):
        """ yield all units of the Collector instance. """
        for x in self:
            if isinstance(x, Collector):
                for y in x.iterunits():
                    yield y
            else:
                yield x

    def _except(self):
        excinfo = sys.exc_info()
        if isinstance(excinfo[1], (KeyboardInterrupt, SystemExit)):
            raise excinfo # KeyboardInterrupt
        return Error(excinfo)

# ----------------------------------------------
# Collectors starting from a file system path 
# ----------------------------------------------

class FSCollector(Collector):
    def __init__(self, fspath):
        self.fspath = py.path.local(fspath)
    def __repr__(self):
        return '%s(%r)' %(self.__class__.__name__, 
                          self.fspath.relto(py.path.local()))

class Directory(FSCollector):
    def fil(self, fspath):
        return (fspath.check(file=1, fnmatch='test_*.py') or 
                fspath.check(file=1, fnmatch='*_test.py'))
    rec = py.path.checker(dir=1, dotfile=0, link=0)
    def __iter__(self):
        try:
            for fspath in self.fspath.listdir(sort=True): 
                if self.rec(fspath):
                    yield self.__class__(fspath)
                elif self.fil(fspath):
                    yield Module(py.path.extpy(fspath))
        except:
            yield self._except()

# ----------------------------------------------
# Collectors starting from Python Paths/Objects
# ----------------------------------------------

class PyCollector(Collector):
    def __init__(self, extpy):
        self.extpy = py.path.extpy(extpy) 
        self.yielders = [getattr(self, x) 
                            for x in dir(self.__class__) 
                                if x.startswith('collect_')]

    def __repr__(self):
        return '%s(%r)' %(self.__class__.__name__, str(self.extpy))

    def __iter__(self):
        try:
            # we want to sort according to lineno, so here goes 
            # the generator lazyness 
            l = []
            for pypath in self.extpy.listdir():
                for meth in self.yielders:
                    for x in meth(pypath):
                        x.fspath = self.extpy.fspath 
                        sortvalue = self.getsortvalue(x) 
                        l.append((sortvalue, x)) 
            l.sort() 
            for x,y in l:
                yield y
        except:
            yield self._except()

    def getsortvalue(self, obj): 
        """ sorting function to bring test methods in 
            the same order as int he file. 
        """ 
        if isinstance(obj, self.Item): 
            obj = obj.pypath.resolve() 
        elif isinstance(obj, PyCollector):
            for x in obj:
                return self.getsortvalue(x) 
        if hasattr(obj, 'im_func'):
            obj = obj.im_func 
        if hasattr(obj, 'func_code'):
            obj = obj.func_code 
        # enough is enough 
        return (getattr(obj, 'co_filename', None), 
                getattr(obj, 'co_firstlineno', sys.maxint))
            
class Module(PyCollector):
    def __iter__(self):
        try:
            iter = self.extpy.join('Collector')
            if iter.check(exists=True):
                iter = iter.resolve()(self.extpy)
            else:
                iter = super(Module, self).__iter__() 
            for x in iter: 
                yield x 
        except:
            yield self._except()

    def collect_function(self, pypath):
        if pypath.check(func=1, basestarts='test_'):
            if self.extpy.samefile(pypath):
                yield self.Item(pypath)

    def collect_class(self, pypath):
        #print "checking %r (pypath: %r)" % (pypath.resolve(), pypath)
        if pypath.check(basestarts='Test') and self.extpy.samefile(pypath):
            obj = pypath.resolve()
            if inspect.isclass(obj) and not getattr(obj, 'disabled', 0):
                yield Class(pypath)

class Class(PyCollector):
    def collect_method(self, pypath):
        # note that we want to allow inheritance and thus
        # we don't check for "samemodule"-ness of test 
        # methods like in the Module Collector
        if pypath.check(basestarts='test_', func=1):
            func = pypath.resolve()
            yield getattr(func.im_class, 'Item', self.Item)(pypath)


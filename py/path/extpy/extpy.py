"""
A path to python objects located in filesystems. 

Note: this is still experimental and may be removed
      for the first stable release!
"""
from __future__ import generators
import py
from py.__impl__.path import common 
import sys
import inspect, imp

class Extpy(common.PathBase):
    """ a path abstraction addressing python objects in a file system. """
    sep = '.'
    def __new__(cls, fspath='', modpath=''): 
        if isinstance(fspath, cls) and not modpath:
            return fspath
            
        assert isinstance(modpath, str)
        self = object.__new__(cls)
        self.modpath = modpath
        if isinstance(fspath, str):
            fspath = py.path.local(fspath)
        self.fspath = fspath
        return self

    def __hash__(self):
        return hash((self.fspath, self.modpath)) 

    def __repr__(self):
        #if self.ns is rootns:
        #    return 'py(%r)' % (self.modpath, )
        return 'extpy(%r, %r)' % (self.fspath, self.modpath) 

    def __str__(self):
        return str(self.fspath.new(ext=self.modpath)) 

    def join(self, *args):
        for arg in args:
            if not isinstance(arg, str):
                raise TypeError, "non-strings not allowed in %r" % args
        modpath = [x.strip('.') for x in ((self.modpath,)+args) if x]
        modpath = self.sep.join(modpath)
        return self.__class__(self.fspath, modpath) 

    def dirpath(self, *args):
        modpath = self.modpath.split(self.sep) [:-1]
        modpath = self.sep.join(modpath+list(args))
        return self.__class__(self.fspath, modpath) 
        
    def new(self, **kw):
        """ create a modified version of this path.
            the following keyword arguments modify various path parts:
            modpath    substitute module path 
        """
        cls = self.__class__ 
        if 'modpath' in kw:
            return cls(self.fspath, kw['modpath']) 
        if 'basename' in kw:
            i = self.modpath.rfind('.')
            if i != -1: 
                return cls(self.fspath, self.modpath[i+1:] + kw['basename'])
            else:
                return cls(self.fspath, kw['basename'])
        return cls(self.fspath, self.modpath) 

    def get(self, spec):
        l = []
        modparts = self.modpath.split(self.sep)
        for name in spec.split(','):
            if name == 'basename':
                l.append(modparts[-1])

        if len(l) == 1:
            return l[0]
        elif len(l) == 0:
            return None
        else:
            return l

    def getmodule(self):
        #modname = str(self.fspath) 
        modname = str(self.fspath.new(ext='')).replace(self.fspath.sep, '_')
        try:
            return sys.modules[modname] 
        except KeyError: 
            #print "trying importing", modname
            if not self.fspath.check(file=1):
                raise py.path.NotFound(self.fspath)
            mod = imp.load_source(modname, str(self.fspath))
            mod.__name__ = modname 
            sys.modules[modname] = mod
            return mod 

    def resolve(self):
        """return the python object belonging to path. """
        module = self.getmodule()
        rest = filter(None, self.modpath.split('.')) 
        target = module 
        for name in rest:
            try:
                target = getattr(target, name)
            except AttributeError:
                raise py.path.NotFound(str(self))
        return target 

    def relto(self, otherpath):
        if self.fspath == otherpath.fspath: 
            if self.modpath.startswith(otherpath.modpath):
                s = self.modpath[len(otherpath.modpath):]
                return s.lstrip(self.sep)
        return ''

    def listobj(self, fil=None, **kw):
        l = []
        for x in self.listdir(fil, **kw):
            l.append(x.resolve())
        return l

    def listdir(self, fil=None, sort=True, **kw):
        if kw:
            if fil is None:
                fil = py.path.checker(**kw)
            else:
                raise TypeError, "cannot take filter and keyword arguments"
        elif isinstance(fil, str):
            fil = common.fnmatch(fil)
        obj = self.resolve()
        #if obj is rootns:
        #    d = {}
        #    for x in sys.modules:
        #        name = x.split('.')[0]
        #        d[name] = 1
        #    l = [self.join(x) for x in d if not fil or fil(x)]
        #else:
        l = []
        for name in dir(obj):
            sub = self.join(name)
            if not fil or fil(sub):
                l.append(sub)

        #print "listdir(%r) -> %r" %(self, l)
        #print "listdir on", repr(self)
        return l

    def setfile(self, filepath):
        self._filepath = filepath 

    def getfilelineno(self, scrapinit=0):
        x = obj = self.resolve()
        if inspect.ismodule(obj): 
            return obj.__file__, 0
        if inspect.ismethod(obj):
            obj = obj.im_func 
        if inspect.isfunction(obj):
            obj = obj.func_code 
        if inspect.iscode(obj):
            return py.path.local(obj.co_filename), obj.co_firstlineno
        else:
            source, lineno = inspect.findsource(obj) 
            return x.getfile(), lineno 

    def visit(self, fil=None, rec=None, ignore=None, seen=None):
        def myrec(p, seen={id(self): True}):
            if id(p) in seen:
                return False
            seen[id(p)] = True 
            if self.samefile(p):
                return True 
            
        for x in super(Extpy, self).visit(fil=fil, rec=rec, ignore=ignore):
            yield x
        return
  
        if seen is None:
            seen = {id(self): True}

        if isinstance(fil, str):
            fil = common.fnmatch(fil)
        if isinstance(rec, str):
            rec = common.fnmatch(fil)

        if ignore:
            try:
                l = self.listdir()
            except ignore:
                return 
        else:
            l = self.listdir()
        reclist = []
        for p in l: 
            if fil is None or fil(p):
                yield p
            if id(p) not in seen:
                try:
                    obj = p.resolve()
                    if inspect.isclass(obj) or inspect.ismodule(obj): 
                        reclist.append(p)
                finally:
                    seen[id(p)] = p 
        for p in reclist:
            for i in p.visit(fil, rec, seen):
                yield i

    def samefile(self, other):
        otherobj = other.resolve()
        try:
            x = inspect.getfile(otherobj) 
        except TypeError: 
            return False 
        if x.endswith('pyc'):
            x = x[:-1]
        if str(self.fspath) == x:
            return True

    class Checkers(common.Checkers):
        _depend_on_existence = (common.Checkers._depend_on_existence + 
                                ('func', 'class_', 'exists', 'dir'))

        def _obj(self):
            self._obj = self.path.resolve()
            return self._obj

        def exists(self):
            obj = self._obj()
            return True 

        def func(self):
            ob = self._obj()
            return inspect.isfunction(ob) or inspect.ismethod(ob)

        def class_(self):
            ob = self._obj()
            return inspect.isclass(ob) 
           
        def isinstance(self, args):
            return isinstance(self._obj(), args)

        def dir(self):
            obj = self._obj()
            return inspect.isclass(obj) or inspect.ismodule(obj) 

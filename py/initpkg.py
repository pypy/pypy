"""
std package initialization

"""
from __future__ import generators 
import sys

ModuleType = type(sys.modules[__name__])

# ---------------------------------------------------
# Package Object 
# ---------------------------------------------------

class Package(object):
    def __init__(self, name, exportdefs):
        pkgmodule = sys.modules[name]
        assert pkgmodule.__name__ == name 
        self.exportdefs = exportdefs
        self.module = pkgmodule 
        assert not hasattr(pkgmodule, '__package__'), \
                   "unsupported reinitialization of %r" % pkgmodule
        pkgmodule.__package__ = self

        # make available pkgname.__impl__  
        implname = name + '.' + '__impl__'
        self.implmodule = ModuleType(implname) 
        self.implmodule.__name__ = implname 
        self.implmodule.__file__ = pkgmodule.__file__
        self.implmodule.__path__ = pkgmodule.__path__ 
        pkgmodule.__impl__ = self.implmodule
        setmodule(implname, self.implmodule) 
        # inhibit further direct filesystem imports through the package module
        del pkgmodule.__path__
       
    def _resolve(self, extpy):
        """ resolve a combined filesystem/python "fspy" path. """
        assert extpy.startswith('./'), \
               "%r is not an implementation path (XXX)" % extpy 

        slash = extpy.rfind('/') 
        dot = extpy.find('.', slash) 
        if dot == -1:
            return self._loadimpl(extpy) 
           
        implmodule = self._loadimpl(extpy[:dot]) 
        attrname = extpy[dot+1:]
        return getattr(implmodule, attrname) 

    def _loadimpl(self, relfile):
        """ load implementation for the given relfile. """
        parts = [x.strip() for x in relfile.split('/') if x and x!= '.']
        modpath = ".".join([self.implmodule.__name__] + parts) 
        return __import__(modpath, None, None, ['name'])

    def exportitems(self):
        return self.exportdefs.items()

    def getpath(self):
        from py.path import local 
        base = local(self.implmodule.__file__).dirpath()
        assert base.check()
        return base

    def _iterfiles(self): 
        from py.path import checker 
        base = self.getpath() 
        for x in base.visit(checker(file=1, notext='.pyc'), 
                            rec=checker(dotfile=0)):
            yield x 

    def shahexdigest(self, cache=[]):
        """ return sha hexdigest for files contained in package. """
        if cache: 
            return cache[0]
        from sha import sha 
        sum = sha() 
        for x in self._iterfiles(): 
            sum.update(x.read()) 
        cache.append(sum.hexdigest())
        return cache[0]

    def getzipdata(self): 
        """ return string representing a zipfile containing the package. """ 
        import zipfile 
        import py
        try: from cStringIO import StringIO
        except ImportError: from StringIO import StringIO
        base = py.__package__.getpath().dirpath()
        outf = StringIO()
        f = zipfile.ZipFile(outf, 'w', compression=zipfile.ZIP_DEFLATED)
        try:
            for x in self._iterfiles(): 
                f.write(str(x), x.relto(base))
        finally: 
            f.close()
        return outf.getvalue() 

def setmodule(modpath, module):
    #print "sys.modules[%r] = %r" % (modpath, module)
    sys.modules[modpath] = module 

# ---------------------------------------------------
# Virtual Module Object 
# ---------------------------------------------------

class Module(ModuleType): 
    def __init__(self, pkg, name): 
        self.__package__ = pkg 
        self.__name__ = name
        self.__map__ = {}

    def __getattr__(self, name):
        try:
            extpy = self.__map__[name]
        except KeyError:
            raise AttributeError(name) 
        #print "getattr(%r, %r)" %(self, name) 
        result = self.__package__._resolve(extpy)
        setattr(self, name, result) 
        del self.__map__[name]
        # XXX modify some attrs to make a class appear at virtual module level 
        if hasattr(result, '__module__'): 
            setattr(result, '__module__', self.__name__) 
        if hasattr(result, '__bases__'):
            try:
                setattr(result, '__name__', name)
            except TypeError:   # doesn't work on Python 2.2
                pass
        #    print "setting virtual module on %r" % result 
        return result

    def __repr__(self):
        return '<Module %r>' % (self.__name__, )

    def getdict(self):
        # force all the content of the module to be loaded when __dict__ is read
        for name in self.__map__.keys():
            hasattr(self, name)   # force attribute to be loaded, ignore errors
        assert not self.__map__, "%r not empty" % self.__map__
        dictdescr = ModuleType.__dict__['__dict__']
        return dictdescr.__get__(self)

    __dict__ = property(getdict)
    del getdict

# ---------------------------------------------------
# Bootstrap Virtual Module Hierarchy 
# ---------------------------------------------------

def initpkg(pkgname, exportdefs):
    #print "initializing package", pkgname
    # bootstrap Package object 
    pkg = Package(pkgname, exportdefs)
    seen = { pkgname : pkg.module }

    for pypath, extpy in pkg.exportitems():
        pyparts = pypath.split('.')
        modparts = pyparts[:-1]
        current = pkgname 

        # ensure modules 
        for name in modparts:
            previous = current
            current += '.' + name 
            if current not in seen:
                seen[current] = mod = Module(pkg, current) 
                setattr(seen[previous], name, mod) 
                setmodule(current, mod) 
        mod = seen[current]
        if not hasattr(mod, '__map__'):
            assert mod is pkg.module, \
                   "only root modules are allowed to be non-lazy. "
            setattr(mod, pyparts[-1], pkg._resolve(extpy))
        else:
            mod.__map__[pyparts[-1]] = extpy 

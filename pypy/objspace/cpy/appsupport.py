from pypy.rpython.extregistry import ExtRegistryEntry, lookup_type
from pypy.interpreter.baseobjspace import W_Root, SpaceCache
from pypy.objspace.cpy.ctypes_base import W_Object

# ____________________________________________________________
# Hacks to support the app-level parts of MixedModules

class W_AppLevel(W_Root):
    def __init__(self, space, app, name):
        self.space = space
        self.w_moddict = space.fromcache(AppSupportModuleCache).getorbuild(app)
        self.name = name
    def force(self):
        dict = self.w_moddict.force()
        return W_Object(dict[self.name])

class W_AppLevelModDict(W_Root):
    def __init__(self, space, app):
        self.space = space
        self.app = app
        self._dict = None
    def force(self):
        if self._dict is None:
            import __builtin__
            self._dict = {'__builtins__': __builtin__}
            exec self.app.code in self._dict
        return self._dict

class AppSupportModuleCache(SpaceCache):
    def build(self, app):
        return W_AppLevelModDict(self.space, app)

# ____________________________________________________________

class Entry(ExtRegistryEntry):
    _type_ = W_AppLevel

    def compute_annotation(self):
        from pypy.annotation.bookkeeper import getbookkeeper
        bk = getbookkeeper()
        return lookup_type(W_Object).compute_annotation()

    def genc_pyobj(self, pyobjmaker):
        dictname = pyobjmaker.nameof(self.instance.w_moddict)
        name = pyobjmaker.uniquename('gapp')
        pyobjmaker.initcode_python(name, '%s[%r]' % (dictname,
                                                     self.instance.name))
        return name

class Entry(ExtRegistryEntry):
    _type_ = W_AppLevelModDict

    def compute_annotation(self):
        from pypy.annotation.bookkeeper import getbookkeeper
        bk = getbookkeeper()
        return lookup_type(W_Object).compute_annotation()

    def genc_pyobj(self, pyobjmaker):
        import marshal
        app = self.instance.app
        name = pyobjmaker.uniquename('gappmoddict_' + app.modname)
        bytecodedump = marshal.dumps(app.code)
        pyobjmaker.initcode.append("import marshal, __builtin__")
        pyobjmaker.initcode.append("%s = {'__builtins__': __builtin__}" % (
            name,))
        pyobjmaker.initcode.append("co = marshal.loads(%s)" % (
            pyobjmaker.nameof(bytecodedump),))
        pyobjmaker.initcode.append("exec co in %s" % (
            name))
        return name

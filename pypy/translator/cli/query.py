import sys
import cPickle as pickle
import os.path
import py
from py.compat import subprocess
from pypy.tool.udir import udir
from pypy.rpython.ootypesystem import ootype
from pypy.translator.cli.rte import Query
from pypy.translator.cli.sdk import SDK
from pypy.translator.cli.support import log

Assemblies = set()
Types = {} # TypeName -> ClassDesc
Namespaces = set()
mscorlib = 'mscorlib, Version=2.0.0.0, Culture=neutral, PublicKeyToken=b77a5c561934e089'
pypylib = 'pypylib, Version=0.0.0.0, Culture=neutral'
pypylib2 = 'pypylib, Version=0.0.0.0, Culture=neutral, PublicKeyToken=null' # this is for mono 1.9


#_______________________________________________________________________________
# This is the public interface of query.py

def get_cli_class(name):
    desc = get_class_desc(name)
    return desc.get_cliclass()

#_______________________________________________________________________________

def load_pypylib():
    from pypy.translator.cli.rte import get_pypy_dll
    dll = get_pypy_dll()
    try:
        import clr
        from System.Reflection import Assembly
    except ImportError:
        pass
    else:
        ass = Assembly.LoadFrom(dll)
        assert ass is not None
        clr.AddReference(pypylib)
    load_assembly(pypylib)

def load_assembly(name):
    if name in Assemblies:
        return
    Query.get() # clear the cache if we need to recompile
    _cache = get_cachedir()
    outfile = _cache.join(name + '.pickle')
    if outfile.check():
        f = outfile.open('rb')
        types = pickle.load(f)
        f.close()
    else:
        types = load_and_cache_assembly(name, outfile)

    for ttype in types:
        parts = ttype.split('.')
        ns = parts[0]
        Namespaces.add(ns)
        for part in parts[1:-1]:
            ns = '%s.%s' % (ns, part)
            Namespaces.add(ns)
    Assemblies.add(name)
    Types.update(types)


def get_cachedir():
    import pypy
    _cache = py.path.local(pypy.__file__).new(basename='_cache').ensure(dir=1)
    return _cache

def load_and_cache_assembly(name, outfile):
    tmpfile = udir.join(name)
    arglist = SDK.runtime() + [Query.get(), name, str(tmpfile)]
    retcode = subprocess.call(arglist)
    assert retcode == 0
    mydict = {}
    execfile(str(tmpfile), mydict)
    types = mydict['types']
    f = outfile.open('wb')
    pickle.dump(types, f, pickle.HIGHEST_PROTOCOL)
    f.close()
    return types

def get_ootype(name):
    # a bit messy, but works
    if name.startswith('ootype.'):
        _, name = name.split('.')
        return getattr(ootype, name)
    else:
        cliclass = get_cli_class(name)
        return cliclass._INSTANCE

def get_class_desc(name):
    if name in Types:
        return Types[name]

    if name == 'System.Array':
        desc = ClassDesc()
        desc.Assembly = mscorlib
        desc.FullName = name
        desc.AssemblyQualifiedName = name # XXX
        desc.BaseType = 'System.Object'
        desc.IsArray = True
        desc.ElementType = 'System.Object' # not really true, but we need something
    elif name.endswith('[]'): # it's an array
        itemname = name[:-2]
        itemdesc = get_class_desc(itemname)
        desc = ClassDesc()
        desc.Assembly = mscorlib
        desc.FullName = name
        desc.AssemblyQualifiedName = name # XXX
        desc.BaseType = 'System.Array'
        desc.ElementType = itemdesc.FullName
        desc.IsValueType = itemdesc.IsValueType
        desc.IsArray = True
        desc.Methods = [
            ('Get', ['ootype.Signed', ], itemdesc.FullName),
            ('Set', ['ootype.Signed', itemdesc.FullName], 'ootype.Void')
            ]
    else:
        assert False, 'Unknown desc'

    Types[name] = desc
    return desc


class ClassDesc(object):

    # default values
    StaticFields = []
    StaticMethods = []
    Methods = []
    IsValueType = False

    _cliclass = None

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        raise TypeError

    def get_cliclass(self):
        from pypy.translator.cli.dotnet import CliClass, NativeInstance
        from pypy.translator.cli.dotnet import _overloaded_static_meth, _static_meth

        if self._cliclass is not None:
            return self._cliclass

        if self.Assembly == mscorlib:
            assembly = '[mscorlib]'
        elif self.Assembly in (pypylib, pypylib2):
            assembly = '[pypylib]'
        else:
            assert False, 'TODO: support external assemblies'
        namespace, name = self.FullName.rsplit('.', 1)

        # construct OOTYPE and CliClass
        # no superclass for now, will add it later
        TYPE = NativeInstance(assembly, namespace, name, None, {}, {})
        TYPE._is_value_type = self.IsValueType
        TYPE._assembly_qualified_name = self.AssemblyQualifiedName
        Class = CliClass(TYPE, {}, {})
        self._cliclass = Class
        if self.FullName == 'System.Object':
            TYPE._set_superclass(ootype.ROOT)
        else:
            BASETYPE = get_ootype(self.BaseType)
            TYPE._set_superclass(BASETYPE)

        TYPE._isArray = self.IsArray
        if self.IsArray:
            TYPE._ELEMENT = get_ootype(self.ElementType)

        # add both static and instance methods, and static fields
        static_meths = self.group_methods(self.StaticMethods, _overloaded_static_meth,
                                          _static_meth, ootype.StaticMethod)
        meths = self.group_methods(self.Methods, ootype.overload, ootype.meth, ootype.Meth)
        fields = dict([(name, get_ootype(t)) for name, t in self.StaticFields])
        Class._add_methods(static_meths)
        Class._add_static_fields(fields)
        TYPE._add_methods(meths)
        return Class

    def group_methods(self, methods, overload, meth, Meth):
        from pypy.translator.cli.dotnet import OverloadingResolver
        groups = {}
        for name, args, result in methods:
            groups.setdefault(name, []).append((args, result))

        res = {}
        attrs = dict(resolver=OverloadingResolver)
        for name, methlist in groups.iteritems():
            TYPES = [self.get_method_type(Meth, args, result) for (args, result) in methlist]
            meths = [meth(TYPE) for TYPE in TYPES]
            res[name] = overload(*meths, **attrs)
        return res

    def get_method_type(self, Meth, args, result):
        ARGS = [get_ootype(arg) for arg in args]
        RESULT = get_ootype(result)
        return Meth(ARGS, RESULT)

placeholder = object()
class CliNamespace(object):
    def __init__(self, name):
        self._name = name
        self.__treebuilt = False

    def __fullname(self, name):
        if self._name is None:
            return name
        else:
            return '%s.%s' % (self._name, name)

    def _buildtree(self):
        assert self._name is None, '_buildtree can be called only on top-level CLR, not on namespaces'
        from pypy.translator.cli.support import getattr_ex
        load_assembly(mscorlib)
        load_pypylib()
        for fullname in sorted(list(Namespaces)):
            if '.' in fullname:
                parent, name = fullname.rsplit('.', 1)
                parent = getattr_ex(self, parent)
                setattr(parent, name, CliNamespace(fullname))
            else:
                setattr(self, fullname, CliNamespace(fullname))

        for fullname in Types.keys():
            parent, name = fullname.rsplit('.', 1)
            parent = getattr_ex(self, parent)
            setattr(parent, name, placeholder)
        self.System.Object # XXX hack

    def __getattribute__(self, attr):
        value = object.__getattribute__(self, attr)
        if value is placeholder:
            fullname = self.__fullname(attr)
            value = get_cli_class(fullname)
            setattr(self, attr, value)
        return value

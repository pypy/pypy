import types

from pypy.tool.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInstance, SomeOOInstance, SomeInteger, s_None,\
     s_ImpossibleValue, lltype_to_annotation, annotation_to_lltype, SomeChar, SomeString, SomePBC
from pypy.annotation.binaryop import _make_none_union
from pypy.annotation import model as annmodel
from pypy.rlib.rarithmetic import r_uint, r_longlong, r_ulonglong
from pypy.rpython.error import TyperError
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rpython.rmodel import Repr
from pypy.rpython.rint import IntegerRepr
from pypy.rpython.ootypesystem.rootype import OOInstanceRepr
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.ootypesystem.ootype import meth, overload, Meth, StaticMethod
from pypy.translator.cli.support import PythonNet

## Annotation model

class SomeCliClass(SomeObject):
    def getattr(self, s_attr):
        assert self.is_constant()
        assert s_attr.is_constant()
        return SomeCliStaticMethod(self.const, s_attr.const)

    def simple_call(self, *s_args):
        assert self.is_constant()
        return SomeOOInstance(self.const._INSTANCE)

    def rtyper_makerepr(self, rtyper):
        return CliClassRepr(self.const)

    def rtyper_makekey(self):
        return self.__class__, self.const


class SomeCliStaticMethod(SomeObject):
    def __init__(self, cli_class, meth_name):
        self.cli_class = cli_class
        self.meth_name = meth_name

    def simple_call(self, *args_s):
        return self.cli_class._ann_static_method(self.meth_name, args_s)

    def rtyper_makerepr(self, rtyper):
        return CliStaticMethodRepr(self.cli_class, self.meth_name)

    def rtyper_makekey(self):
        return self.__class__, self.cli_class, self.meth_name


class __extend__(pairtype(SomeOOInstance, SomeInteger)):
    def getitem((ooinst, index)):
        if ooinst.ootype._isArray:
            return SomeOOInstance(ooinst.ootype._ELEMENT)
        return s_ImpossibleValue

    def setitem((ooinst, index), s_value):
        if ooinst.ootype._isArray:
            if s_value is annmodel.s_None:
                return s_None
            ELEMENT = ooinst.ootype._ELEMENT
            VALUE = s_value.ootype
            assert ootype.isSubclass(VALUE, ELEMENT)
            return s_None
        return s_ImpossibleValue


## Rtyper model

class CliClassRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, cli_class):
        self.cli_class = cli_class

    def rtype_getattr(self, hop):
        return hop.inputconst(ootype.Void, self.cli_class)

    def rtype_simple_call(self, hop):
        # TODO: resolve constructor overloading
        INSTANCE = hop.args_r[0].cli_class._INSTANCE
        cINST = hop.inputconst(ootype.Void, INSTANCE)
        vlist = hop.inputargs(*hop.args_r)[1:] # discard the first argument
        hop.exception_is_here()
        return hop.genop("new", [cINST]+vlist, resulttype=hop.r_result.lowleveltype)

class CliStaticMethodRepr(Repr):
    lowleveltype = ootype.Void

    def __init__(self, cli_class, meth_name):
        self.cli_class = cli_class
        self.meth_name = meth_name

    def _build_desc(self, args_v):
        ARGS = tuple([v.concretetype for v in args_v])
        return self.cli_class._lookup(self.meth_name, ARGS)

    def rtype_simple_call(self, hop):
        vlist = []
        for i, repr in enumerate(hop.args_r[1:]):
            vlist.append(hop.inputarg(repr, i+1))
        resulttype = hop.r_result.lowleveltype
        desc = self._build_desc(vlist)
        cDesc = hop.inputconst(ootype.Void, desc)
        return hop.genop("direct_call", [cDesc] + vlist, resulttype=resulttype)


class __extend__(pairtype(OOInstanceRepr, IntegerRepr)):

    def rtype_getitem((r_inst, r_int), hop):
        if not r_inst.lowleveltype._isArray:
            raise TyperError("getitem() on a non-array instance")
        v_array, v_index = hop.inputargs(r_inst, ootype.Signed)
        hop.exception_is_here()
        return hop.genop('cli_getelem', [v_array, v_index], hop.r_result.lowleveltype)

    def rtype_setitem((r_inst, r_int), hop):
        if not r_inst.lowleveltype._isArray:
            raise TyperError("setitem() on a non-array instance")
        vlist = hop.inputargs(*hop.args_r)
        hop.exception_is_here()
        return hop.genop('cli_setelem', vlist, hop.r_result.lowleveltype)


class __extend__(OOInstanceRepr):

    def rtype_len(self, hop):
        if not self.lowleveltype._isArray:
            raise TypeError("len() on a non-array instance")
        vlist = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('cli_arraylength', vlist, hop.r_result.lowleveltype)

## OOType model

class OverloadingResolver(ootype.OverloadingResolver):

    def _can_convert_from_to(self, ARG1, ARG2):
        if ARG1 is ootype.Void and isinstance(ARG2, NativeInstance):
            return True # ARG1 could be None, that is always convertible to a NativeInstance
        else:
            return ootype.OverloadingResolver._can_convert_from_to(self, ARG1, ARG2)

    def annotation_to_lltype(cls, ann):
        if isinstance(ann, SomeChar):
            return ootype.Char
        elif isinstance(ann, SomeString):
            return ootype.String
        else:
            return annotation_to_lltype(ann)
    annotation_to_lltype = classmethod(annotation_to_lltype)

    def lltype_to_annotation(cls, TYPE):
        if isinstance(TYPE, NativeInstance):
            return SomeOOInstance(TYPE)
        elif TYPE is ootype.Char:
            return SomeChar()
        elif TYPE is ootype.String:
            return SomeString(can_be_None=True)
        else:
            return lltype_to_annotation(TYPE)
    lltype_to_annotation = classmethod(lltype_to_annotation)


class _static_meth(object):

    def __init__(self, TYPE):
        self._TYPE = TYPE

    def _set_attrs(self, cls, name):
        self._cls = cls
        self._name = name

    def _get_desc(self, ARGS):
        #assert ARGS == self._TYPE.ARGS
        return self


class _overloaded_static_meth(object):
    def __init__(self, *overloadings, **attrs):
        resolver = attrs.pop('resolver', OverloadingResolver)
        assert not attrs
        self._resolver = resolver(overloadings)

    def _set_attrs(self, cls, name):
        for meth in self._resolver.overloadings:
            meth._set_attrs(cls, name)

    def _get_desc(self, ARGS):
        meth = self._resolver.resolve(ARGS)
        assert isinstance(meth, _static_meth)
        return meth._get_desc(ARGS)


class NativeInstance(ootype.Instance):
    def __init__(self, assembly, namespace, name, superclass,
                 fields={}, methods={}, _is_root=False, _hints = {}):
        fullname = '%s%s.%s' % (assembly, namespace, name)
        self._namespace = namespace
        self._classname = name
        ootype.Instance.__init__(self, fullname, superclass, fields, methods, _is_root, _hints)


## RPython interface definition

class CliClass(object):
    def __init__(self, INSTANCE, static_methods):
        self._name = INSTANCE._name
        self._INSTANCE = INSTANCE
        self._static_methods = {}
        self._add_methods(static_methods)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE._name)

    def _add_methods(self, methods):
        self._static_methods.update(methods)
        for name, meth in methods.iteritems():
            meth._set_attrs(self, name)

    def _lookup(self, meth_name, ARGS):
        meth = self._static_methods[meth_name]
        return meth._get_desc(ARGS)

    def _ann_static_method(self, meth_name, args_s):
        meth = self._static_methods[meth_name]
        return meth._resolver.annotate(args_s)

    def _load_class(self):
        names = self._INSTANCE._namespace.split('.')
        names.append(self._INSTANCE._classname)
        obj = PythonNet
        for name in names:
            obj = getattr(obj, name)
        self._PythonNet_class = obj

    def __getattr__(self, attr):
        if attr in self._static_methods:
            self._load_class()
            return getattr(self._PythonNet_class, attr)
        else:
            raise AttributeError

    def __call__(self, *args):
        self._load_class()
        return self._PythonNet_class(*args)


class Entry(ExtRegistryEntry):
    _type_ = CliClass

    def compute_annotation(self):
        return SomeCliClass()

    def compute_result_annotation(self):
        return SomeOOInstance(self.instance._INSTANCE)

class CliNamespace(object):
    def __init__(self, name):
        self._name = name

    def __fullname(self, name):
        if self._name is None:
            return name
        else:
            return '%s.%s' % (self._name, name)

    def __getattr__(self, attr):
        from pypy.translator.cli.query import load_class_or_namespace
        # .NET namespace are not self-entities but just parts of the
        # FullName of a class. This imply that there is no way ask
        # .NET if a particular name is a namespace; there are many
        # names that are clearly not namespaces such as im_self and
        # _freeze_, but there is no general rule and we have to guess.
        # For now, the heuristic simply check is the first char of the
        # name is a UPPERCASE letter.
        
        if attr[0].isalpha() and attr[0] == attr[0].upper():
            # we assume it's a class or namespace
            name = self.__fullname(attr)
            load_class_or_namespace(name)
            assert attr in self.__dict__
            return getattr(self, attr)
        else:
            raise AttributeError

CLR = CliNamespace(None)

BOXABLE_TYPES = [ootype.Signed, ootype.Unsigned, ootype.SignedLongLong,
                 ootype.UnsignedLongLong, ootype.Bool, ootype.Float,
                 ootype.Char, ootype.String]

class BoxedSpace:
    objects = {}
    index = 0
    def put(cls, obj):
        index = cls.index
        cls.objects[index] = obj
        cls.index += 1
        return index
    put = classmethod(put)

    def get(cls, index):
        return cls.objects[index]
    get = classmethod(get)

def box(x):
    t = type(x)
    if t is int:
        return CLR.System.Int32(x)
    elif t is r_uint:
        return CLR.System.UInt32(x)
    elif t is r_longlong:
        return CLR.System.Int64(x)
    elif t is r_ulonglong:
        return CLR.System.UInt64(x)
    elif t is bool:
        return CLR.System.Boolean(x)
    elif t is float:
        return CLR.System.Double(x)
    elif t is str or t is unicode:
        if len(x) == 1:
            return CLR.System.Char(x)
        else:
            return CLR.System.String(x)
    elif isinstance(x, PythonNet.System.Object):
        return x
    elif x is None:
        return None
    else:
        # cast RPython instances to System.Object is trivial when
        # translated but not when interpreting, because Python for
        # .NET doesn't support passing aribrary Python objects to
        # .NET. To solve, we store them in the BoxedSpace, then we
        # return an opaque objects, which will be used by unbox to
        # retrieve the original RPython instance.
        index = BoxedSpace.put(x)
        res = PythonNet.pypy.test.ObjectWrapper(index)
        return res

def unbox(x, TYPE):
    if isinstance(x, PythonNet.pypy.test.ObjectWrapper):
        x = BoxedSpace.get(x.index)

    if isinstance(TYPE, (type, types.ClassType)):
        # we need to check the TYPE and return None if it fails
        if isinstance(x, TYPE):
            return x
        else:
            return None

    # TODO: do the typechecking also in the other cases

    # this is a workaround against a pythonnet limitation: you can't
    # directly get the, e.g., python int from the System.Int32 object:
    # a simple way to do this is to put it into an ArrayList and
    # retrieve the value.
    tmp = PythonNet.System.Collections.ArrayList()
    tmp.Add(x)
    return tmp[0]


class Entry(ExtRegistryEntry):
    _about_ = box

    def compute_result_annotation(self, x_s):
        can_be_None = getattr(x_s, 'can_be_None', False)
        return SomeOOInstance(CLR.System.Object._INSTANCE, can_be_None=can_be_None)

    def specialize_call(self, hop):
        v_obj, = hop.inputargs(*hop.args_r)

        hop.exception_cannot_occur()
        TYPE = v_obj.concretetype
        if (TYPE is ootype.String or isinstance(TYPE, (ootype.Instance, ootype.BuiltinType, NativeInstance))):
            return hop.genop('ooupcast', [v_obj], hop.r_result.lowleveltype)
        else:
            if TYPE not in BOXABLE_TYPES:
                raise TyperError, "Can't box values of type %s" % v_obj.concretetype
            return hop.genop('clibox', [v_obj], hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = unbox

    def compute_result_annotation(self, x_s, type_s):
        assert isinstance(x_s, SomeOOInstance)
        assert x_s.ootype == CLR.System.Object._INSTANCE
        assert type_s.is_constant()
        TYPE = type_s.const
        if isinstance(TYPE, (type, types.ClassType)):
            # it's a user-defined class, so we return SomeInstance
            # can_be_None == True because it can always return None, if it fails
            classdef = self.bookkeeper.getuniqueclassdef(TYPE)
            return SomeInstance(classdef, can_be_None=True)
        else:
            assert TYPE in BOXABLE_TYPES
            return OverloadingResolver.lltype_to_annotation(TYPE)

    def specialize_call(self, hop):
        TYPE = hop.args_v[1].value
        v_obj = hop.inputarg(hop.args_r[0], arg=0)
        if TYPE is ootype.String or isinstance(TYPE, (type, types.ClassType)):
            return hop.genop('oodowncast', [v_obj], hop.r_result.lowleveltype)
        else:
            c_type = hop.inputconst(ootype.Void, TYPE)
            return hop.genop('cliunbox', [v_obj, c_type], hop.r_result.lowleveltype)


native_exc_cache = {}
def NativeException(cliClass):
    try:
        return native_exc_cache[cliClass._name]
    except KeyError:
        res = _create_NativeException(cliClass)
        native_exc_cache[cliClass._name] = res
        return res

def _create_NativeException(cliClass):
    from pypy.translator.cli.query import getattr_ex
    TYPE = cliClass._INSTANCE
    if PythonNet.__name__ in ('CLR', 'clr'):
        # we are using pythonnet -- use the .NET class
        name = '%s.%s' % (TYPE._namespace, TYPE._classname)
        res = getattr_ex(PythonNet, name)
    else:
        # we are not using pythonnet -- create a fake class
        res = types.ClassType(TYPE._classname, (Exception,), {})
    res._rpython_hints = {'NATIVE_INSTANCE': TYPE}
    return res

def native_exc(exc):
    return exc

class Entry(ExtRegistryEntry):
    _about_ = native_exc

    def compute_result_annotation(self, exc_s):
        assert isinstance(exc_s, SomeInstance)
        cls = exc_s.classdef.classdesc.pyobj
        assert issubclass(cls, Exception)
        NATIVE_INSTANCE = cls._rpython_hints['NATIVE_INSTANCE']
        return SomeOOInstance(NATIVE_INSTANCE)

    def specialize_call(self, hop):
        v_obj, = hop.inputargs(*hop.args_r)
        return hop.genop('same_as', [v_obj], hop.r_result.lowleveltype)

def new_array(type, length):
    return [None] * length

def init_array(type, *args):
    # PythonNet doesn't provide a straightforward way to create arrays... fake it with a list
    return list(args)

class Entry(ExtRegistryEntry):
    _about_ = new_array

    def compute_result_annotation(self, type_s, length_s):
        from pypy.translator.cli.query import load_class_maybe
        assert type_s.is_constant()
        assert isinstance(length_s, SomeInteger)
        TYPE = type_s.const._INSTANCE
        fullname = '%s.%s[]' % (TYPE._namespace, TYPE._classname)
        cliArray = load_class_maybe(fullname)
        return SomeOOInstance(cliArray._INSTANCE)

    def specialize_call(self, hop):
        c_type, v_length = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('cli_newarray', [c_type, v_length], hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = init_array

    def compute_result_annotation(self, type_s, *args_s):
        from pypy.translator.cli.query import load_class_maybe
        assert type_s.is_constant()
        TYPE = type_s.const._INSTANCE
        for i, arg_s in enumerate(args_s):
            if TYPE is not arg_s.ootype:
                raise TypeError, 'Wrong type of arg #%d: %s expected, %s found' % \
                      (i, TYPE, arg_s.ootype)
        fullname = '%s.%s[]' % (TYPE._namespace, TYPE._classname)
        cliArray = load_class_maybe(fullname)
        return SomeOOInstance(cliArray._INSTANCE)

    def specialize_call(self, hop):
        vlist = hop.inputargs(*hop.args_r)
        c_type, v_elems = vlist[0], vlist[1:]
        c_length = hop.inputconst(ootype.Signed, len(v_elems))
        hop.exception_cannot_occur()
        v_array = hop.genop('cli_newarray', [c_type, c_length], hop.r_result.lowleveltype)
        for i, v_elem in enumerate(v_elems):
            c_index = hop.inputconst(ootype.Signed, i)
            hop.genop('cli_setelem', [v_array, c_index, v_elem], ootype.Void)
        return v_array


def typeof(cliClass):
    TYPE = cliClass._INSTANCE
    name = '%s.%s' % (TYPE._namespace, TYPE._classname)
    return PythonNet.System.Type.GetType(name)

class Entry(ExtRegistryEntry):
    _about_ = typeof

    def compute_result_annotation(self, cliClass_s):
        from query import load_class_maybe
        assert cliClass_s.is_constant()
        cliType = load_class_maybe('System.Type')
        return SomeOOInstance(cliType._INSTANCE)

    def specialize_call(self, hop):
        v_type, = hop.inputargs(*hop.args_r)
        return hop.genop('cli_typeof', [v_type], hop.r_result.lowleveltype)

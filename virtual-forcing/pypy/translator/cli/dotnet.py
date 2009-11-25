import types

from pypy.tool.pairtype import pair, pairtype
from pypy.annotation.model import SomeObject, SomeInstance, SomeOOInstance, SomeInteger, s_None,\
     s_ImpossibleValue, lltype_to_annotation, annotation_to_lltype, SomeChar, SomeString, SomeOOStaticMeth
from pypy.annotation.unaryop import immutablevalue
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
        cliclass = self.const
        attrname = s_attr.const
        if attrname in cliclass._static_fields:
            TYPE = cliclass._static_fields[attrname]
            return OverloadingResolver.lltype_to_annotation(TYPE)
        elif attrname in cliclass._static_methods:
            return SomeCliStaticMethod(cliclass, attrname)
        else:
            return s_ImpossibleValue

    def setattr(self, s_attr, s_value):
        assert self.is_constant()
        assert s_attr.is_constant
        cliclass = self.const
        attrname = s_attr.const
        if attrname not in cliclass._static_fields:
            return s_ImpossibleValue
        # XXX: check types?

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

class __extend__(SomeOOInstance):

    def simple_call(self, *s_args):
        from pypy.translator.cli.query import get_cli_class
        DELEGATE = get_cli_class('System.Delegate')._INSTANCE
        if ootype.isSubclass(self.ootype, DELEGATE):
            s_invoke = self.getattr(immutablevalue('Invoke'))
            return s_invoke.simple_call(*s_args)
        else:
            # cannot call a non-delegate
            return SomeObject.simple_call(self, *s_args)

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
        attrname = hop.args_v[1].value
        if attrname in self.cli_class._static_methods:
            return hop.inputconst(ootype.Void, self.cli_class)
        else:
            assert attrname in self.cli_class._static_fields
            TYPE = self.cli_class._static_fields[attrname]
            c_class = hop.inputarg(hop.args_r[0], arg=0)
            c_name = hop.inputconst(ootype.Void, attrname)
            return hop.genop("cli_getstaticfield", [c_class, c_name], resulttype=hop.r_result.lowleveltype)

    def rtype_setattr(self, hop):
        attrname = hop.args_v[1].value
        assert attrname in self.cli_class._static_fields
        c_class = hop.inputarg(hop.args_r[0], arg=0)
        c_name = hop.inputconst(ootype.Void, attrname)
        v_value = hop.inputarg(hop.args_r[2], arg=2)
        return hop.genop("cli_setstaticfield", [c_class, c_name, v_value], resulttype=hop.r_result.lowleveltype)

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

    def rtype_simple_call(self, hop):
        TYPE = self.lowleveltype
        _, meth = TYPE._lookup('Invoke')
        assert isinstance(meth, ootype._overloaded_meth)
        ARGS = tuple([repr.lowleveltype for repr in hop.args_r[1:]])
        desc = meth._get_desc('Invoke', ARGS)
        cname = hop.inputconst(ootype.Void, desc)
        vlist = hop.inputargs(self, *hop.args_r[1:])
        hop.exception_is_here()
        return hop.genop("oosend", [cname]+vlist,
                         resulttype = hop.r_result.lowleveltype)


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
        self._is_value_type = False
        ootype.Instance.__init__(self, fullname, superclass, fields, methods, _is_root, _hints)


## RPython interface definition

class CliClass(object):
    def __init__(self, INSTANCE, static_methods, static_fields):
        self._name = INSTANCE._name
        self._INSTANCE = INSTANCE
        self._static_methods = {}
        self._static_fields = {}
        self._add_methods(static_methods)

    def __repr__(self):
        return '<%s>' % (self,)

    def __str__(self):
        return '%s(%s)' % (self.__class__.__name__, self._INSTANCE._name)

    def _add_methods(self, methods):
        self._static_methods.update(methods)
        for name, meth in methods.iteritems():
            meth._set_attrs(self, name)

    def _add_static_fields(self, fields):
        self._static_fields.update(fields)

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
        if attr in self._static_methods or attr in self._static_fields:
            self._load_class()
            return getattr(self._PythonNet_class, attr)
        else:
            raise AttributeError, attr

    def __call__(self, *args):
        self._load_class()
        return self._PythonNet_class(*args)


class Entry(ExtRegistryEntry):
    _type_ = CliClass

    def compute_annotation(self):
        return SomeCliClass()

    def compute_result_annotation(self):
        return SomeOOInstance(self.instance._INSTANCE)


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
    elif isinstance(x, ootype._class):
        if hasattr(x, '_FUNC'):
            TYPE = x._FUNC
            assert isinstance(TYPE, ootype.StaticMethod)
            return typeof(TYPE)
        elif x is ootype.nullruntimeclass:
            return None
        else:
            name = x._INSTANCE._assembly_qualified_name
            t = CLR.System.Type.GetType(name)
            assert t is not None
            return t
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

    if isinstance(TYPE, ootype.OOType) and TYPE is not ootype.String and not isinstance(TYPE, ootype.StaticMethod):
        try:
            return ootype.enforce(TYPE, x)
        except TypeError:
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
        if (TYPE is ootype.String or isinstance(TYPE, (ootype.OOType, NativeInstance))):
            return hop.genop('ooupcast', [v_obj], hop.r_result.lowleveltype)
        else:
            if TYPE not in BOXABLE_TYPES:
                raise TyperError, "Can't box values of type %s" % v_obj.concretetype
            return hop.genop('clibox', [v_obj], hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = unbox

    def compute_result_annotation(self, x_s, type_s):
        assert isinstance(x_s, SomeOOInstance)
        assert isinstance(x_s.ootype, NativeInstance)
        assert type_s.is_constant()
        TYPE = type_s.const
        if isinstance(TYPE, (type, types.ClassType)):
            # it's a user-defined class, so we return SomeInstance
            # can_be_None == True because it can always return None, if it fails
            classdef = self.bookkeeper.getuniqueclassdef(TYPE)
            return SomeInstance(classdef, can_be_None=True)
        elif TYPE in BOXABLE_TYPES:
            return OverloadingResolver.lltype_to_annotation(TYPE)
        elif isinstance(TYPE, ootype.StaticMethod):
            return SomeOOStaticMeth(TYPE)
        elif isinstance(TYPE, ootype.OOType):
            return SomeOOInstance(TYPE)
        else:
            assert False
            

    def specialize_call(self, hop):
        assert hop.args_s[1].is_constant()
        TYPE = hop.args_s[1].const
        v_obj = hop.inputarg(hop.args_r[0], arg=0)
        if TYPE is ootype.String or isinstance(TYPE, (type, types.ClassType)) or isinstance(TYPE, ootype.OOType):
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
    from pypy.translator.cli.support import getattr_ex
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
    # PythonNet doesn't provide a straightforward way to create arrays,
    # let's use reflection instead

    # hack to produce the array type name from the member type name
    typename = type._INSTANCE._assembly_qualified_name
    parts = typename.split(',')
    parts[0] = parts[0] + '[]'
    typename = ','.join(parts)
    t = PythonNet.System.Type.GetType(typename)
    ctor = t.GetConstructors()[0]
    return ctor.Invoke([length])

def init_array(type, *args):
    array = new_array(type, len(args))
    for i, arg in enumerate(args):
        array[i] = arg
    return array

class Entry(ExtRegistryEntry):
    _about_ = new_array

    def compute_result_annotation(self, type_s, length_s):
        from pypy.translator.cli.query import get_cli_class
        assert type_s.is_constant()
        assert isinstance(length_s, SomeInteger)
        TYPE = type_s.const._INSTANCE
        fullname = '%s.%s[]' % (TYPE._namespace, TYPE._classname)
        cliArray = get_cli_class(fullname)
        return SomeOOInstance(cliArray._INSTANCE)

    def specialize_call(self, hop):
        c_type, v_length = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('cli_newarray', [c_type, v_length], hop.r_result.lowleveltype)


class Entry(ExtRegistryEntry):
    _about_ = init_array

    def compute_result_annotation(self, type_s, *args_s):
        from pypy.translator.cli.query import get_cli_class
        assert type_s.is_constant()
        TYPE = type_s.const._INSTANCE
        for i, arg_s in enumerate(args_s):
            if TYPE is not arg_s.ootype:
                raise TypeError, 'Wrong type of arg #%d: %s expected, %s found' % \
                      (i, TYPE, arg_s.ootype)
        fullname = '%s.%s[]' % (TYPE._namespace, TYPE._classname)
        cliArray = get_cli_class(fullname)
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

def typeof(cliClass_or_type):
    if isinstance(cliClass_or_type, ootype.StaticMethod):
        FUNCTYPE = cliClass_or_type
        cliClass = known_delegates[FUNCTYPE]
    else:
        assert isinstance(cliClass_or_type, CliClass)
        cliClass = cliClass_or_type
    TYPE = cliClass._INSTANCE
    return PythonNet.System.Type.GetType(TYPE._assembly_qualified_name)

def classof(cliClass_or_type):
    if isinstance(cliClass_or_type, ootype.StaticMethod):
        try:
            FUNC = cliClass_or_type
            return known_delegates_class[FUNC]
        except KeyError:
            cls = ootype._class(ootype.ROOT)
            cls._FUNC = FUNC
            known_delegates_class[FUNC] = cls
            return cls
    else:
        assert isinstance(cliClass_or_type, CliClass)
        TYPE = cliClass_or_type._INSTANCE
        return ootype.runtimeClass(TYPE)

class Entry(ExtRegistryEntry):
    _about_ = typeof

    def compute_result_annotation(self, cliClass_s):
        from pypy.translator.cli.query import get_cli_class
        assert cliClass_s.is_constant()
        cliType = get_cli_class('System.Type')
        return SomeOOInstance(cliType._INSTANCE)

    def specialize_call(self, hop):
        v_type, = hop.inputargs(*hop.args_r)
        return hop.genop('cli_typeof', [v_type], hop.r_result.lowleveltype)


def eventhandler(obj):
    return CLR.System.EventHandler(obj)

class Entry(ExtRegistryEntry):
    _about_ = eventhandler

    def compute_result_annotation(self, s_value):
        from pypy.translator.cli.query import get_cli_class
        cliType = get_cli_class('System.EventHandler')
        return SomeOOInstance(cliType._INSTANCE)

    def specialize_call(self, hop):
        v_obj, = hop.inputargs(*hop.args_r)
        methodname = hop.args_r[0].methodname
        c_methodname = hop.inputconst(ootype.Void, methodname)
        return hop.genop('cli_eventhandler', [v_obj, c_methodname], hop.r_result.lowleveltype)


def clidowncast(obj, TYPE):
    return obj

class Entry(ExtRegistryEntry):
    _about_ = clidowncast

    def compute_result_annotation(self, s_value, s_type):
        if isinstance(s_type.const, ootype.OOType):
            TYPE = s_type.const
        else:
            cliClass = s_type.const
            TYPE = cliClass._INSTANCE
        assert ootype.isSubclass(TYPE, s_value.ootype)
        return SomeOOInstance(TYPE)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
        v_inst = hop.inputarg(hop.args_r[0], arg=0)
        return hop.genop('oodowncast', [v_inst], resulttype = hop.r_result.lowleveltype)


def cliupcast(obj, TYPE):
    return obj

class Entry(ExtRegistryEntry):
    _about_ = cliupcast

    def compute_result_annotation(self, s_value, s_type):
        if isinstance(s_type.const, ootype.OOType):
            TYPE = s_type.const
        else:
            cliClass = s_type.const
            TYPE = cliClass._INSTANCE
        assert ootype.isSubclass(s_value.ootype, TYPE)
        return SomeOOInstance(TYPE)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], annmodel.SomeOOInstance)
        v_inst = hop.inputarg(hop.args_r[0], arg=0)
        return hop.genop('ooupcast', [v_inst], resulttype = hop.r_result.lowleveltype)


def cast_to_native_object(obj):
    raise TypeError, "cast_to_native_object is meant to be rtyped and not called direclty"

def cast_from_native_object(obj):
    raise TypeError, "cast_from_native_object is meant to be rtyped and not called direclty"

class Entry(ExtRegistryEntry):
    _about_ = cast_to_native_object

    def compute_result_annotation(self, s_value):
        assert isinstance(s_value, annmodel.SomeOOObject)
        assert s_value.ootype is ootype.Object
        return SomeOOInstance(CLR.System.Object._INSTANCE)

    def specialize_call(self, hop):
        assert isinstance(hop.args_s[0], annmodel.SomeOOObject)
        v_obj, = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        return hop.genop('ooupcast', [v_obj], hop.r_result.lowleveltype)

class Entry(ExtRegistryEntry):
    _about_ = cast_from_native_object

    def compute_result_annotation(self, s_value):
        assert isinstance(s_value, annmodel.SomeOOInstance)
        assert s_value.ootype is CLR.System.Object._INSTANCE
        return annmodel.SomeOOObject()

    def specialize_call(self, hop):
        v_obj = hop.inputarg(hop.args_r[0], arg=0)
        return hop.genop('oodowncast', [v_obj], hop.r_result.lowleveltype)



from pypy.translator.cli.query import CliNamespace
CLR = CliNamespace(None)
CLR._buildtree()

known_delegates = {
    ootype.StaticMethod([], ootype.Signed): CLR.pypy.test.DelegateType_int__0,
    ootype.StaticMethod([ootype.Signed, ootype.Float], ootype.Float): CLR.pypy.test.DelegateType_double_int_double,
    ootype.StaticMethod([ootype.Float], ootype.Float):         CLR.pypy.test.DelegateType_double__double_1,
    ootype.StaticMethod([ootype.Bool], ootype.Bool):           CLR.pypy.test.DelegateType_bool_bool_1,
    ootype.StaticMethod([ootype.Char], ootype.Char):           CLR.pypy.test.DelegateType_char_char_1,
    ootype.StaticMethod([ootype.Signed], ootype.Void):         CLR.pypy.test.DelegateType_void_int_1,
    ootype.StaticMethod([ootype.Signed], ootype.Signed):       CLR.pypy.test.DelegateType_int__int_1,
    ootype.StaticMethod([ootype.Signed] * 2, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_2,
    ootype.StaticMethod([ootype.Signed] * 3, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_3,
    ootype.StaticMethod([ootype.Signed] * 5, ootype.Signed):   CLR.pypy.test.DelegateType_int__int_5,
    ootype.StaticMethod([ootype.Signed] * 27, ootype.Signed):  CLR.pypy.test.DelegateType_int__int_27,
    ootype.StaticMethod([ootype.Signed] * 100, ootype.Signed): CLR.pypy.test.DelegateType_int__int_100
    }

known_delegates_class = {}

cVoid = classof(CLR.System.Void)
def class2type(cls):
    'Cast a PBC of type ootype.Class into a System.Type instance'
    if cls is cVoid:
        return None
    return clidowncast(box(cls), CLR.System.Type)

def type2class(clitype):
    'Cast a System.Type instance to a PBC of type ootype.Class'
##     if clitype is None:
##         return cVoid
    return unbox(clitype, ootype.Class)

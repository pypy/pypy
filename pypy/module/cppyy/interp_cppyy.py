import pypy.module.cppyy.capi as capi

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, interp_attrproperty
from pypy.interpreter.baseobjspace import Wrappable, W_Root

from pypy.rpython.lltypesystem import rffi, lltype

from pypy.rlib import libffi, rdynload, rweakref
from pypy.rlib import jit, debug, objectmodel

from pypy.module.cppyy import converter, executor, helper


class FastCallNotPossible(Exception):
    pass


@unwrap_spec(name=str)
def load_dictionary(space, name):
    try:
        cdll = capi.c_load_dictionary(name)
    except rdynload.DLOpenError, e:
        raise OperationError(space.w_RuntimeError, space.wrap(str(e)))
    return W_CPPLibrary(space, cdll)

class State(object):
    def __init__(self, space):
        self.r_cppscope_cache = {
            "void" : W_CPPType(space, "void", capi.C_NULL_TYPE) }
        self.r_cpptemplate_cache = {}
        self.type_registry = {}
        self.w_clgen_callback = None

@unwrap_spec(name=str)
def resolve_name(space, name):
    return space.wrap(capi.c_resolve_name(name))

@unwrap_spec(name=str)
def type_byname(space, name):
    true_name = capi.c_resolve_name(name)

    state = space.fromcache(State)
    try:
        return state.r_cppscope_cache[true_name]
    except KeyError:
        pass

    cppscope = capi.c_get_scope(true_name)
    assert lltype.typeOf(cppscope) == capi.C_SCOPE
    if cppscope:
        final_name = capi.c_final_name(cppscope)
        if capi.c_is_namespace(cppscope):
            r_cppscope = W_CPPNamespace(space, final_name, cppscope)
        elif capi.c_has_complex_hierarchy(cppscope):
            r_cppscope = W_ComplexCPPType(space, final_name, cppscope)
        else:
            r_cppscope = W_CPPType(space, final_name, cppscope)
        state.r_cppscope_cache[name] = r_cppscope

        r_cppscope._find_methods()
        r_cppscope._find_data_members()
        return r_cppscope

    return None

@unwrap_spec(name=str)
def template_byname(space, name):
    state = space.fromcache(State)
    try:
        return state.r_cpptemplate_cache[name]
    except KeyError:
        pass

    cpptemplate = capi.c_get_template(name)
    assert lltype.typeOf(cpptemplate) == capi.C_TYPE
    if cpptemplate:
        r_cpptemplate = W_CPPTemplateType(space, name, cpptemplate)
        state.r_cpptemplate_cache[name] = r_cpptemplate
        return r_cpptemplate

    return None

@unwrap_spec(w_callback=W_Root)
def set_class_generator(space, w_callback):
    state = space.fromcache(State)
    state.w_clgen_callback = w_callback

@unwrap_spec(w_type=W_Root)
def register_class(space, w_type):
    w_cpptype = space.findattr(w_type, space.wrap("_cpp_proxy"))
    cpptype = space.interp_w(W_CPPType, w_cpptype, can_be_None=False)
    state = space.fromcache(State)
    state.type_registry[cpptype.handle] = w_type


class W_CPPLibrary(Wrappable):
    _immutable_ = True

    def __init__(self, space, cdll):
        self.cdll = cdll
        self.space = space

W_CPPLibrary.typedef = TypeDef(
    'CPPLibrary',
)
W_CPPLibrary.typedef.acceptable_as_base_class = True


class CPPMethod(object):
    """ A concrete function after overloading has been resolved """
    _immutable_ = True
    
    def __init__(self, cpptype, method_index, result_type, arg_defs, args_required):
        self.space = cpptype.space
        self.cpptype = cpptype
        self.method_index = method_index
        self.cppmethod = capi.c_get_method(self.cpptype.handle, method_index)
        self.arg_defs = arg_defs
        self.args_required = args_required
        self.executor = executor.get_executor(self.space, result_type)

        # Setup of the method dispatch's innards is done lazily, i.e. only when
        # the method is actually used. TODO: executor should be lazy as well.
        self.arg_converters = None
        self._libffifunc = None

    @jit.unroll_safe
    def call(self, cppthis, args_w):
        jit.promote(self)
        assert lltype.typeOf(cppthis) == capi.C_OBJECT
        args_expected = len(self.arg_defs)
        args_given = len(args_w)
        if args_expected < args_given or args_given < self.args_required:
            raise TypeError("wrong number of arguments")

        if self.arg_converters is None:
            self._setup(cppthis)

        if self._libffifunc:
            try:
                return self.do_fast_call(cppthis, args_w)
            except FastCallNotPossible:
                pass          # can happen if converters or executor does not implement ffi

        args = self.prepare_arguments(args_w)
        try:
            return self.executor.execute(self.space, self.cppmethod, cppthis, len(args_w), args)
        finally:
            self.free_arguments(args, len(args_w))

    @jit.unroll_safe
    def do_fast_call(self, cppthis, args_w):
        jit.promote(self)
        argchain = libffi.ArgChain()
        argchain.arg(cppthis)
        i = len(self.arg_defs)
        for i in range(len(args_w)):
            conv = self.arg_converters[i]
            w_arg = args_w[i]
            conv.convert_argument_libffi(self.space, w_arg, argchain)
        for j in range(i+1, len(self.arg_defs)):
            conv = self.arg_converters[j]
            conv.default_argument_libffi(self.space, argchain)
        return self.executor.execute_libffi(self.space, self._libffifunc, argchain)

    def _setup(self, cppthis):
        self.arg_converters = [converter.get_converter(self.space, arg_type, arg_dflt)
                                   for arg_type, arg_dflt in self.arg_defs]

        # Each CPPMethod corresponds one-to-one to a C++ equivalent and cppthis
        # has been offset to the matching class. Hence, the libffi pointer is
        # uniquely defined and needs to be setup only once.
        methgetter = capi.c_get_methptr_getter(self.cpptype.handle, self.method_index)
        if methgetter and cppthis:      # methods only for now
            funcptr = methgetter(rffi.cast(capi.C_OBJECT, cppthis))
            argtypes_libffi = [conv.libffitype for conv in self.arg_converters
                               if conv.libffitype]
            if (len(argtypes_libffi) == len(self.arg_converters) and
                    self.executor.libffitype):
                # add c++ this to the arguments
                libffifunc = libffi.Func("XXX",
                                         [libffi.types.pointer] + argtypes_libffi,
                                         self.executor.libffitype, funcptr)
                self._libffifunc = libffifunc

    @jit.unroll_safe
    def prepare_arguments(self, args_w):
        jit.promote(self)
        args = capi.c_allocate_function_args(len(args_w))
        stride = capi.c_function_arg_sizeof()
        for i in range(len(args_w)):
            conv = self.arg_converters[i]
            w_arg = args_w[i]
            try:
                arg_i = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), i*stride)
                conv.convert_argument(self.space, w_arg, rffi.cast(capi.C_OBJECT, arg_i))
            except:
                # fun :-(
                for j in range(i):
                    conv = self.arg_converters[j]
                    arg_j = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), j*stride)
                    conv.free_argument(rffi.cast(capi.C_OBJECT, arg_j))
                capi.c_deallocate_function_args(args)
                raise
        return args

    @jit.unroll_safe
    def free_arguments(self, args, nargs):
        stride = capi.c_function_arg_sizeof()
        for i in range(nargs):
            conv = self.arg_converters[i]
            arg_i = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), i*stride)
            conv.free_argument(rffi.cast(capi.C_OBJECT, arg_i))
        capi.c_deallocate_function_args(args)

    def __repr__(self):
        return "CPPFunction(%s, %s, %r, %s)" % (
            self.cpptype, self.method_index, self.executor, self.arg_defs)

    def _freeze_(self):
        assert 0, "you should never have a pre-built instance of this!"


class CPPFunction(CPPMethod):
    _immutable_ = True


class CPPConstructor(CPPMethod):
    _immutable_ = True

    def call(self, cppthis, args_w):
        newthis = capi.c_allocate(self.cpptype.handle)
        assert lltype.typeOf(newthis) == capi.C_OBJECT
        try:
            CPPMethod.call(self, newthis, args_w)
        except Exception:
            capi.c_deallocate(self.cpptype.handle, newthis)
            raise
        return wrap_new_cppobject_nocast(self.space, None, self.cpptype, newthis, False, True)


class W_CPPOverload(Wrappable):
    _immutable_ = True

    def __init__(self, space, scope_handle, func_name, functions):
        self.space = space
        assert lltype.typeOf(scope_handle) == capi.C_SCOPE
        self.scope_handle = scope_handle
        self.func_name = func_name
        self.functions = debug.make_sure_not_resized(functions)

    def is_static(self):
        return self.space.wrap(isinstance(self.functions[0], CPPFunction))

    @jit.unroll_safe
    def call(self, w_cppinstance, args_w):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        if cppinstance is not None:
            cppinstance._nullcheck()
            assert isinstance(cppinstance.cppclass, W_CPPType)
            cppthis = cppinstance.cppclass.get_cppthis(cppinstance, self.scope_handle)
        else:
            cppthis = capi.C_NULL_OBJECT
        assert lltype.typeOf(cppthis) == capi.C_OBJECT

        # The following code tries out each of the functions in order. If
        # argument conversion fails (or simply if the number of arguments do
        # not match, that will lead to an exception, The JIT will snip out
        # those (always) failing paths, but only if they have no side-effects.
        # A second loop gathers all exceptions in the case all methods fail
        # (the exception gathering would otherwise be a side-effect as far as
        # the JIT is concerned).
        #
        # TODO: figure out what happens if a callback into from the C++ call
        # raises a Python exception.
        jit.promote(self)
        for i in range(len(self.functions)):
            cppyyfunc = self.functions[i]
            try:
                return cppyyfunc.call(cppthis, args_w)
            except Exception:
                pass

        # only get here if all overloads failed ...
        errmsg = 'None of the overloads matched:'
        for i in range(len(self.functions)):
            cppyyfunc = self.functions[i]
            try:
                return cppyyfunc.call(cppthis, args_w)
            except Exception, e:
                errmsg += '\n\t'+str(e)

        raise OperationError(self.space.w_TypeError, self.space.wrap(errmsg))

    def __repr__(self):
        return "W_CPPOverload(%s, %s)" % (self.func_name, self.functions)

W_CPPOverload.typedef = TypeDef(
    'CPPOverload',
    is_static = interp2app(W_CPPOverload.is_static, unwrap_spec=['self']),
    call = interp2app(W_CPPOverload.call, unwrap_spec=['self', W_Root, 'args_w']),
)


class W_CPPDataMember(Wrappable):
    _immutable_ = True

    def __init__(self, space, scope_handle, type_name, offset, is_static):
        self.space = space
        assert lltype.typeOf(scope_handle) == capi.C_SCOPE
        self.scope_handle = scope_handle
        self.converter = converter.get_converter(self.space, type_name, '')
        self.offset = offset
        self._is_static = is_static

    def get_returntype(self):
        return self.space.wrap(self.converter.name)

    def is_static(self):
        return self.space.newbool(self._is_static)

    @jit.elidable_promote()
    def _get_offset(self, cppinstance):
        if cppinstance:
            assert lltype.typeOf(cppinstance.cppclass.handle) == lltype.typeOf(self.scope_handle)
            offset = self.offset + capi.c_base_offset(
                cppinstance.cppclass.handle, self.scope_handle, cppinstance.get_rawobject())
        else:
            offset = self.offset
        return offset

    def get(self, w_cppinstance, w_type):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        offset = self._get_offset(cppinstance)
        try:
            return self.converter.from_memory(self.space, w_cppinstance, w_type, offset)
        except TypeError, e:
            raise OperationError(self.space.w_TypeError, self.space.wrap(str(e)))
        except ValueError, e:
            raise OperationError(self.space.w_ValueError, self.space.wrap(str(e)))

    def set(self, w_cppinstance, w_value):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        offset = self._get_offset(cppinstance)
        try:
            self.converter.to_memory(self.space, w_cppinstance, w_value, offset)
            return self.space.w_None
        except TypeError, e:
            raise OperationError(self.space.w_TypeError, self.space.wrap(str(e)))
        except ValueError, e:
            raise OperationError(self.space.w_ValueError, self.space.wrap(str(e)))

W_CPPDataMember.typedef = TypeDef(
    'CPPDataMember',
    is_static = interp2app(W_CPPDataMember.is_static, unwrap_spec=['self']),
    get_returntype = interp2app(W_CPPDataMember.get_returntype, unwrap_spec=['self']),
    get = interp2app(W_CPPDataMember.get, unwrap_spec=['self', W_Root, W_Root]),
    set = interp2app(W_CPPDataMember.set, unwrap_spec=['self', W_Root, W_Root]),
)
W_CPPDataMember.typedef.acceptable_as_base_class = False


class W_CPPScope(Wrappable):
    _immutable_ = True
    _immutable_fields_ = ["methods[*]", "data_members[*]"]

    kind = "scope"

    def __init__(self, space, name, handle):
        self.space = space
        self.name = name
        assert lltype.typeOf(handle) == capi.C_SCOPE
        self.handle = handle
        self.methods = {}
        # Do not call "self._find_methods()" here, so that a distinction can
        #  be made between testing for existence (i.e. existence in the cache
        #  of classes) and actual use. Point being that a class can use itself,
        #  e.g. as a return type or an argument to one of its methods.

        self.data_members = {}
        # Idem self.methods: a type could hold itself by pointer.

    def _find_methods(self):
        num_methods = capi.c_num_methods(self.handle)
        args_temp = {}
        for i in range(num_methods):
            method_name = capi.c_method_name(self.handle, i)
            pymethod_name = helper.map_operator_name(
                    method_name, capi.c_method_num_args(self.handle, i),
                    capi.c_method_result_type(self.handle, i))
            if not pymethod_name in self.methods:
                cppfunction = self._make_cppfunction(i)
                overload = args_temp.setdefault(pymethod_name, [])
                overload.append(cppfunction)
        for name, functions in args_temp.iteritems():
            overload = W_CPPOverload(self.space, self.handle, name, functions[:])
            self.methods[name] = overload

    def get_method_names(self):
        return self.space.newlist([self.space.wrap(name) for name in self.methods])

    @jit.elidable_promote('0')
    def get_overload(self, name):
        try:
            return self.methods[name]
        except KeyError:
            raise self.missing_attribute_error(name)

    def get_data_member_names(self):
        return self.space.newlist([self.space.wrap(name) for name in self.data_members])

    @jit.elidable_promote('0')
    def get_data_member(self, name):
        try:
            return self.data_members[name]
        except KeyError:
            raise self.missing_attribute_error(name)

    def missing_attribute_error(self, name):
        return OperationError(
            self.space.w_AttributeError,
            self.space.wrap("%s '%s' has no attribute %s" % (self.kind, self.name, name)))


# For now, keep namespaces and classes separate as namespaces are extensible
# with info from multiple dictionaries and do not need to bother with meta
# classes for inheritance. Both are python classes, though, and refactoring
# may be in order at some point.
class W_CPPNamespace(W_CPPScope):
    _immutable_ = True

    kind = "namespace"

    def _make_cppfunction(self, method_index):
        result_type = capi.c_method_result_type(self.handle, method_index)
        num_args = capi.c_method_num_args(self.handle, method_index)
        args_required = capi.c_method_req_args(self.handle, method_index)
        arg_defs = []
        for i in range(num_args):
            arg_type = capi.c_method_arg_type(self.handle, method_index, i)
            arg_dflt = capi.c_method_arg_default(self.handle, method_index, i)
            arg_defs.append((arg_type, arg_dflt))
        return CPPFunction(self, method_index, result_type, arg_defs, args_required)

    def _find_data_members(self):
        num_data_members = capi.c_num_data_members(self.handle)
        for i in range(num_data_members):
            if not capi.c_is_publicdata(self.handle, i):
                continue
            data_member_name = capi.c_data_member_name(self.handle, i)
            if not data_member_name in self.data_members:
                type_name = capi.c_data_member_type(self.handle, i)
                offset = capi.c_data_member_offset(self.handle, i)
                data_member = W_CPPDataMember(self.space, self.handle, type_name, offset, True)
                self.data_members[data_member_name] = data_member

    def update(self):
        self._find_methods()
        self._find_data_members()

    def is_namespace(self):
        return self.space.w_True

W_CPPNamespace.typedef = TypeDef(
    'CPPNamespace',
    update = interp2app(W_CPPNamespace.update, unwrap_spec=['self']),
    get_method_names = interp2app(W_CPPNamespace.get_method_names, unwrap_spec=['self']),
    get_overload = interp2app(W_CPPNamespace.get_overload, unwrap_spec=['self', str]),
    get_data_member_names = interp2app(W_CPPNamespace.get_data_member_names, unwrap_spec=['self']),
    get_data_member = interp2app(W_CPPNamespace.get_data_member, unwrap_spec=['self', str]),
    is_namespace = interp2app(W_CPPNamespace.is_namespace, unwrap_spec=['self']),
)
W_CPPNamespace.typedef.acceptable_as_base_class = False


class W_CPPType(W_CPPScope):
    _immutable_ = True

    kind = "class"

    def _make_cppfunction(self, method_index):
        result_type = capi.c_method_result_type(self.handle, method_index)
        num_args = capi.c_method_num_args(self.handle, method_index)
        args_required = capi.c_method_req_args(self.handle, method_index)
        arg_defs = []
        for i in range(num_args):
            arg_type = capi.c_method_arg_type(self.handle, method_index, i)
            arg_dflt = capi.c_method_arg_default(self.handle, method_index, i)
            arg_defs.append((arg_type, arg_dflt))
        if capi.c_is_constructor(self.handle, method_index):
            result_type = "void"       # b/c otherwise CINT v.s. Reflex difference
            cls = CPPConstructor
        elif capi.c_is_staticmethod(self.handle, method_index):
            cls = CPPFunction
        else:
            cls = CPPMethod
        return cls(self, method_index, result_type, arg_defs, args_required)

    def _find_data_members(self):
        num_data_members = capi.c_num_data_members(self.handle)
        for i in range(num_data_members):
            if not capi.c_is_publicdata(self.handle, i):
                continue
            data_member_name = capi.c_data_member_name(self.handle, i)
            type_name = capi.c_data_member_type(self.handle, i)
            offset = capi.c_data_member_offset(self.handle, i)
            is_static = bool(capi.c_is_staticdata(self.handle, i))
            data_member = W_CPPDataMember(self.space, self.handle, type_name, offset, is_static)
            self.data_members[data_member_name] = data_member

    def get_cppthis(self, cppinstance, scope_handle):
        assert self.handle == cppinstance.cppclass.handle
        return cppinstance.get_rawobject()

    def is_namespace(self):
        return self.space.w_False

    def get_base_names(self):
        bases = []
        num_bases = capi.c_num_bases(self.handle)
        for i in range(num_bases):
            base_name = capi.c_base_name(self.handle, i)
            bases.append(self.space.wrap(base_name))
        return self.space.newlist(bases)

W_CPPType.typedef = TypeDef(
    'CPPType',
    type_name = interp_attrproperty('name', W_CPPType),
    get_base_names = interp2app(W_CPPType.get_base_names, unwrap_spec=['self']),
    get_method_names = interp2app(W_CPPType.get_method_names, unwrap_spec=['self']),
    get_overload = interp2app(W_CPPType.get_overload, unwrap_spec=['self', str]),
    get_data_member_names = interp2app(W_CPPType.get_data_member_names, unwrap_spec=['self']),
    get_data_member = interp2app(W_CPPType.get_data_member, unwrap_spec=['self', str]),
    is_namespace = interp2app(W_CPPType.is_namespace, unwrap_spec=['self']),
)
W_CPPType.typedef.acceptable_as_base_class = False


class W_ComplexCPPType(W_CPPType):
    _immutable_ = True

    def get_cppthis(self, cppinstance, scope_handle):
        assert self.handle == cppinstance.cppclass.handle
        offset = capi.c_base_offset(self.handle, scope_handle, cppinstance.get_rawobject())
        return capi.direct_ptradd(cppinstance.get_rawobject(), offset)

W_ComplexCPPType.typedef = TypeDef(
    'ComplexCPPType',
    type_name = interp_attrproperty('name', W_CPPType),
    get_base_names = interp2app(W_ComplexCPPType.get_base_names, unwrap_spec=['self']),
    get_method_names = interp2app(W_ComplexCPPType.get_method_names, unwrap_spec=['self']),
    get_overload = interp2app(W_ComplexCPPType.get_overload, unwrap_spec=['self', str]),
    get_data_member_names = interp2app(W_ComplexCPPType.get_data_member_names, unwrap_spec=['self']),
    get_data_member = interp2app(W_ComplexCPPType.get_data_member, unwrap_spec=['self', str]),
    is_namespace = interp2app(W_ComplexCPPType.is_namespace, unwrap_spec=['self']),
)
W_ComplexCPPType.typedef.acceptable_as_base_class = False


class W_CPPTemplateType(Wrappable):
    _immutable_ = True

    def __init__(self, space, name, handle):
        self.space = space
        self.name = name
        assert lltype.typeOf(handle) == capi.C_TYPE
        self.handle = handle

    def __call__(self, args_w):
        # TODO: this is broken but unused (see pythonify.py)
        fullname = "".join([self.name, '<', self.space.str_w(args_w[0]), '>'])
        return type_byname(self.space, fullname)

W_CPPTemplateType.typedef = TypeDef(
    'CPPTemplateType',
    __call__ = interp2app(W_CPPTemplateType.__call__, unwrap_spec=['self', 'args_w']),
)
W_CPPTemplateType.typedef.acceptable_as_base_class = False


class W_CPPInstance(Wrappable):
    _immutable_fields_ = ["cppclass", "isref"]

    def __init__(self, space, cppclass, rawobject, isref, python_owns):
        self.space = space
        assert isinstance(cppclass, W_CPPType)
        self.cppclass = cppclass
        assert lltype.typeOf(rawobject) == capi.C_OBJECT
        assert not isref or rawobject
        self._rawobject = rawobject
        assert not isref or not python_owns
        self.isref = isref
        self.python_owns = python_owns

    def _nullcheck(self):
        if not self._rawobject or (self.isref and not self.get_rawobject()):
            raise OperationError(self.space.w_ReferenceError,
                                 self.space.wrap("trying to access a NULL pointer"))

    def get_rawobject(self):
        if not self.isref:
            return self._rawobject
        else:
            ptrptr = rffi.cast(rffi.VOIDPP, self._rawobject)
            return rffi.cast(capi.C_OBJECT, ptrptr[0])

    def instance__eq__(self, w_other):
        other = self.space.interp_w(W_CPPInstance, w_other, can_be_None=False)
        iseq = self._rawobject == other._rawobject
        return self.space.wrap(iseq)

    def instance__ne__(self, w_other):
        return self.space.not_(self.instance__eq__(w_other))

    def instance__nonzero__(self):
        if not self._rawobject or (self.isref and not self.get_rawobject()):
            return self.space.w_False
        return self.space.w_True

    def destruct(self):
        assert isinstance(self, W_CPPInstance)
        if self._rawobject and not self.isref:
            memory_regulator.unregister(self)
            capi.c_destruct(self.cppclass.handle, self._rawobject)
            self._rawobject = capi.C_NULL_OBJECT

    def __del__(self):
        if self.python_owns:
            self.enqueue_for_destruction(self.space, W_CPPInstance.destruct,
                                         '__del__() method of ')

W_CPPInstance.typedef = TypeDef(
    'CPPInstance',
    cppclass = interp_attrproperty('cppclass', cls=W_CPPInstance),
    __eq__ = interp2app(W_CPPInstance.instance__eq__, unwrap_spec=['self', W_Root]),
    __ne__ = interp2app(W_CPPInstance.instance__ne__, unwrap_spec=['self', W_Root]),
    __nonzero__ = interp2app(W_CPPInstance.instance__nonzero__, unwrap_spec=['self']),
    destruct = interp2app(W_CPPInstance.destruct, unwrap_spec=['self']),
)
W_CPPInstance.typedef.acceptable_as_base_class = True


class MemoryRegulator:
    # TODO: (?) An object address is not unique if e.g. the class has a
    # public data member of class type at the start of its definition and
    # has no virtual functions. A _key class that hashes on address and
    # type would be better, but my attempt failed in the rtyper, claiming
    # a call on None ("None()") and needed a default ctor. (??)
    # Note that for now, the associated test carries an m_padding to make
    # a difference in the addresses.
    def __init__(self):
        self.objects = rweakref.RWeakValueDictionary(int, W_CPPInstance)

    def register(self, obj):
        int_address = int(rffi.cast(rffi.LONG, obj._rawobject))
        self.objects.set(int_address, obj)

    def unregister(self, obj):
        int_address = int(rffi.cast(rffi.LONG, obj._rawobject))
        self.objects.set(int_address, None)

    def retrieve(self, address):
        int_address = int(rffi.cast(rffi.LONG, address))
        return self.objects.get(int_address)

memory_regulator = MemoryRegulator()


def get_wrapped_type(space, handle):
    state = space.fromcache(State)
    try:
        w_type = state.type_registry[handle]
    except KeyError:
        final_name = capi.c_scoped_final_name(handle)
        w_type = space.call_function(state.w_clgen_callback, space.wrap(final_name))
    return w_type

def wrap_new_cppobject_nocast(space, w_type, cpptype, rawobject, isref, python_owns):
    if w_type is None:
        w_type = get_wrapped_type(space, cpptype.handle)
    w_cppinstance = space.allocate_instance(W_CPPInstance, w_type)
    cppinstance = space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=False)
    W_CPPInstance.__init__(cppinstance, space, cpptype, rawobject, isref, python_owns)
    memory_regulator.register(cppinstance)
    return w_cppinstance

def wrap_cppobject_nocast(space, w_type, cpptype, rawobject, isref, python_owns):
    obj = memory_regulator.retrieve(rawobject)
    if obj and obj.cppclass == cpptype:
         return obj
    return wrap_new_cppobject_nocast(space, w_type, cpptype, rawobject, isref, python_owns)

def wrap_cppobject(space, w_type, cpptype, rawobject, isref, python_owns):
    if rawobject:
        actual = capi.c_get_object_type(cpptype.handle, rawobject)
        if actual != cpptype.handle:
            offset = capi.c_base_offset(actual, cpptype.handle, rawobject)
            rawobject = capi.direct_ptradd(rawobject, offset)
            w_type = get_wrapped_type(space, actual)
            w_cpptype = space.findattr(w_type, space.wrap("_cpp_proxy"))
            cpptype = space.interp_w(W_CPPType, w_cpptype, can_be_None=False)
    return wrap_cppobject_nocast(space, w_type, cpptype, rawobject, isref, python_owns)

@unwrap_spec(cppinstance=W_CPPInstance)
def addressof(space, cppinstance):
     address = rffi.cast(rffi.LONG, cppinstance.get_rawobject())
     return space.wrap(address)

@unwrap_spec(address=int, owns=bool)
def bind_object(space, address, w_type, owns=False):
    rawobject = rffi.cast(capi.C_OBJECT, address)
    w_cpptype = space.findattr(w_type, space.wrap("_cpp_proxy"))
    cpptype = space.interp_w(W_CPPType, w_cpptype, can_be_None=False)
    return wrap_cppobject_nocast(space, w_type, cpptype, rawobject, False, owns)

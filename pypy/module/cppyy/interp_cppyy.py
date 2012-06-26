import pypy.module.cppyy.capi as capi

from pypy.interpreter.error import OperationError
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty
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
        self.cppscope_cache = {
            "void" : W_CPPClass(space, "void", capi.C_NULL_TYPE) }
        self.cpptemplate_cache = {}
        self.cppclass_registry = {}
        self.w_clgen_callback = None

@unwrap_spec(name=str)
def resolve_name(space, name):
    return space.wrap(capi.c_resolve_name(name))

@unwrap_spec(name=str)
def scope_byname(space, name):
    true_name = capi.c_resolve_name(name)

    state = space.fromcache(State)
    try:
        return state.cppscope_cache[true_name]
    except KeyError:
        pass

    opaque_handle = capi.c_get_scope_opaque(true_name)
    assert lltype.typeOf(opaque_handle) == capi.C_SCOPE
    if opaque_handle:
        final_name = capi.c_final_name(opaque_handle)
        if capi.c_is_namespace(opaque_handle):
            cppscope = W_CPPNamespace(space, final_name, opaque_handle)
        elif capi.c_has_complex_hierarchy(opaque_handle):
            cppscope = W_ComplexCPPClass(space, final_name, opaque_handle)
        else:
            cppscope = W_CPPClass(space, final_name, opaque_handle)
        state.cppscope_cache[name] = cppscope

        cppscope._build_methods()
        cppscope._find_datamembers()
        return cppscope

    return None

@unwrap_spec(name=str)
def template_byname(space, name):
    state = space.fromcache(State)
    try:
        return state.cpptemplate_cache[name]
    except KeyError:
        pass

    opaque_handle = capi.c_get_template(name)
    assert lltype.typeOf(opaque_handle) == capi.C_TYPE
    if opaque_handle:
        cpptemplate = W_CPPTemplateType(space, name, opaque_handle)
        state.cpptemplate_cache[name] = cpptemplate
        return cpptemplate

    return None

@unwrap_spec(w_callback=W_Root)
def set_class_generator(space, w_callback):
    state = space.fromcache(State)
    state.w_clgen_callback = w_callback

@unwrap_spec(w_pycppclass=W_Root)
def register_class(space, w_pycppclass):
    w_cppclass = space.findattr(w_pycppclass, space.wrap("_cpp_proxy"))
    cppclass = space.interp_w(W_CPPClass, w_cppclass, can_be_None=False)
    state = space.fromcache(State)
    state.cppclass_registry[cppclass.handle] = w_pycppclass


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
    
    def __init__(self, space, containing_scope, method_index, arg_defs, args_required):
        self.space = space
        self.scope = containing_scope
        self.index = method_index
        self.cppmethod = capi.c_get_method(self.scope, method_index)
        self.arg_defs = arg_defs
        self.args_required = args_required
        self.args_expected = len(arg_defs)

        # Setup of the method dispatch's innards is done lazily, i.e. only when
        # the method is actually used.
        self.converters = None
        self.executor = None
        self._libffifunc = None

    def _address_from_local_buffer(self, call_local, idx):
        if not call_local:
            return call_local
        stride = 2*rffi.sizeof(rffi.VOIDP)
        loc_idx = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, call_local), idx*stride)
        return rffi.cast(rffi.VOIDP, loc_idx)

    @jit.unroll_safe
    def call(self, cppthis, args_w):
        jit.promote(self)
        assert lltype.typeOf(cppthis) == capi.C_OBJECT

        # check number of given arguments against required (== total - defaults)
        args_expected = len(self.arg_defs)
        args_given = len(args_w)
        if args_expected < args_given or args_given < self.args_required:
            raise OperationError(self.space.w_TypeError,
                                 self.space.wrap("wrong number of arguments"))

        # initial setup of converters, executors, and libffi (if available)
        if self.converters is None:
            self._setup(cppthis)

        # some calls, e.g. for ptr-ptr or reference need a local array to store data for
        # the duration of the call
        if [conv for conv in self.converters if conv.uses_local]:
            call_local = lltype.malloc(rffi.VOIDP.TO, 2*len(args_w), flavor='raw')
        else:
            call_local = lltype.nullptr(rffi.VOIDP.TO)

        try:
            # attempt to call directly through ffi chain
            if self._libffifunc:
                try:
                    return self.do_fast_call(cppthis, args_w, call_local)
                except FastCallNotPossible:
                    pass      # can happen if converters or executor does not implement ffi

            # ffi chain must have failed; using stub functions instead
            args = self.prepare_arguments(args_w, call_local)
            try:
                return self.executor.execute(self.space, self.cppmethod, cppthis, len(args_w), args)
            finally:
                self.finalize_call(args, args_w, call_local)
        finally:
            if call_local:
                lltype.free(call_local, flavor='raw')

    @jit.unroll_safe
    def do_fast_call(self, cppthis, args_w, call_local):
        jit.promote(self)
        argchain = libffi.ArgChain()
        argchain.arg(cppthis)
        i = len(self.arg_defs)
        for i in range(len(args_w)):
            conv = self.converters[i]
            w_arg = args_w[i]
            conv.convert_argument_libffi(self.space, w_arg, argchain, call_local)
        for j in range(i+1, len(self.arg_defs)):
            conv = self.converters[j]
            conv.default_argument_libffi(self.space, argchain)
        return self.executor.execute_libffi(self.space, self._libffifunc, argchain)

    def _setup(self, cppthis):
        self.converters = [converter.get_converter(self.space, arg_type, arg_dflt)
                               for arg_type, arg_dflt in self.arg_defs]
        self.executor = executor.get_executor(self.space, capi.c_method_result_type(self.scope, self.index))

        # Each CPPMethod corresponds one-to-one to a C++ equivalent and cppthis
        # has been offset to the matching class. Hence, the libffi pointer is
        # uniquely defined and needs to be setup only once.
        methgetter = capi.c_get_methptr_getter(self.scope, self.index)
        if methgetter and cppthis:      # methods only for now
            funcptr = methgetter(rffi.cast(capi.C_OBJECT, cppthis))
            argtypes_libffi = [conv.libffitype for conv in self.converters if conv.libffitype]
            if (len(argtypes_libffi) == len(self.converters) and
                    self.executor.libffitype):
                # add c++ this to the arguments
                libffifunc = libffi.Func("XXX",
                                         [libffi.types.pointer] + argtypes_libffi,
                                         self.executor.libffitype, funcptr)
                self._libffifunc = libffifunc

    @jit.unroll_safe
    def prepare_arguments(self, args_w, call_local):
        jit.promote(self)
        args = capi.c_allocate_function_args(len(args_w))
        stride = capi.c_function_arg_sizeof()
        for i in range(len(args_w)):
            conv = self.converters[i]
            w_arg = args_w[i]
            try:
                arg_i = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), i*stride)
                loc_i = self._address_from_local_buffer(call_local, i)
                conv.convert_argument(self.space, w_arg, rffi.cast(capi.C_OBJECT, arg_i), loc_i)
            except:
                # fun :-(
                for j in range(i):
                    conv = self.converters[j]
                    arg_j = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), j*stride)
                    loc_j = self._address_from_local_buffer(call_local, j)
                    conv.free_argument(self.space, rffi.cast(capi.C_OBJECT, arg_j), loc_j)
                capi.c_deallocate_function_args(args)
                raise
        return args

    @jit.unroll_safe
    def finalize_call(self, args, args_w, call_local):
        stride = capi.c_function_arg_sizeof()
        for i in range(len(args_w)):
            conv = self.converters[i]
            arg_i = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), i*stride)
            loc_i = self._address_from_local_buffer(call_local, i)
            conv.finalize_call(self.space, args_w[i], loc_i)
            conv.free_argument(self.space, rffi.cast(capi.C_OBJECT, arg_i), loc_i)
        capi.c_deallocate_function_args(args)

    def signature(self):
        return capi.c_method_signature(self.scope, self.index)

    def __repr__(self):
        return "CPPMethod: %s" % self.signature()

    def _freeze_(self):
        assert 0, "you should never have a pre-built instance of this!"


class CPPFunction(CPPMethod):
    _immutable_ = True

    def __repr__(self):
        return "CPPFunction: %s" % self.signature()


class CPPConstructor(CPPMethod):
    _immutable_ = True

    def call(self, cppthis, args_w):
        newthis = capi.c_allocate(self.scope)
        assert lltype.typeOf(newthis) == capi.C_OBJECT
        try:
            CPPMethod.call(self, newthis, args_w)
        except:
            capi.c_deallocate(self.scope, newthis)
            raise
        return wrap_new_cppobject_nocast(
            self.space, self.space.w_None, self.scope, newthis, isref=False, python_owns=True)

    def __repr__(self):
        return "CPPConstructor: %s" % self.signature()


class W_CPPOverload(Wrappable):
    _immutable_ = True

    def __init__(self, space, containing_scope, functions):
        self.space = space
        self.scope = containing_scope
        self.functions = debug.make_sure_not_resized(functions)

    def is_static(self):
        return self.space.wrap(isinstance(self.functions[0], CPPFunction))

    @jit.unroll_safe
    @unwrap_spec(args_w='args_w')
    def call(self, w_cppinstance, args_w):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        if cppinstance is not None:
            cppinstance._nullcheck()
            cppthis = cppinstance.get_cppthis(self.scope)
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
        errmsg = 'none of the %d overloaded methods succeeded. Full details:' % len(self.functions)
        if hasattr(self.space, "fake"):     # FakeSpace fails errorstr (see below)
            raise OperationError(self.space.w_TypeError, self.space.wrap(errmsg))
        for i in range(len(self.functions)):
            cppyyfunc = self.functions[i]
            try:
                return cppyyfunc.call(cppthis, args_w)
            except OperationError, e:
                errmsg += '\n  '+cppyyfunc.signature()+' =>\n'
                errmsg += '    '+e.errorstr(self.space)
            except Exception, e:
                errmsg += '\n  '+cppyyfunc.signature()+' =>\n'
                errmsg += '    Exception: '+str(e)

        raise OperationError(self.space.w_TypeError, self.space.wrap(errmsg))

    def signature(self):
        sig = self.functions[0].signature()
        for i in range(1, len(self.functions)):
            sig += '\n'+self.functions[i].signature()
        return self.space.wrap(sig)

    def __repr__(self):
        return "W_CPPOverload(%s)" % [f.signature() for f in self.functions]

W_CPPOverload.typedef = TypeDef(
    'CPPOverload',
    is_static = interp2app(W_CPPOverload.is_static),
    call = interp2app(W_CPPOverload.call),
    signature = interp2app(W_CPPOverload.signature),
)


class W_CPPDataMember(Wrappable):
    _immutable_ = True

    def __init__(self, space, containing_scope, type_name, offset, is_static):
        self.space = space
        self.scope = containing_scope
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
            assert lltype.typeOf(cppinstance.cppclass.handle) == lltype.typeOf(self.scope.handle)
            offset = self.offset + capi.c_base_offset(
                cppinstance.cppclass, self.scope, cppinstance.get_rawobject(), 1)
        else:
            offset = self.offset
        return offset

    def get(self, w_cppinstance, w_pycppclass):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        offset = self._get_offset(cppinstance)
        return self.converter.from_memory(self.space, w_cppinstance, w_pycppclass, offset)

    def set(self, w_cppinstance, w_value):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        offset = self._get_offset(cppinstance)
        self.converter.to_memory(self.space, w_cppinstance, w_value, offset)
        return self.space.w_None

W_CPPDataMember.typedef = TypeDef(
    'CPPDataMember',
    is_static = interp2app(W_CPPDataMember.is_static),
    get_returntype = interp2app(W_CPPDataMember.get_returntype),
    get = interp2app(W_CPPDataMember.get),
    set = interp2app(W_CPPDataMember.set),
)
W_CPPDataMember.typedef.acceptable_as_base_class = False


class W_CPPScope(Wrappable):
    _immutable_ = True
    _immutable_fields_ = ["methods[*]", "datamembers[*]"]

    kind = "scope"

    def __init__(self, space, name, opaque_handle):
        self.space = space
        self.name = name
        assert lltype.typeOf(opaque_handle) == capi.C_SCOPE
        self.handle = opaque_handle
        self.methods = {}
        # Do not call "self._build_methods()" here, so that a distinction can
        #  be made between testing for existence (i.e. existence in the cache
        #  of classes) and actual use. Point being that a class can use itself,
        #  e.g. as a return type or an argument to one of its methods.

        self.datamembers = {}
        # Idem as for self.methods: a type could hold itself by pointer.

    def _build_methods(self):
        assert len(self.methods) == 0
        methods_temp = {}
        N = capi.c_num_methods(self)
        for i in range(N):
            idx = capi.c_method_index_at(self, i)
            pyname = helper.map_operator_name(
                capi.c_method_name(self, idx),
                capi.c_method_num_args(self, idx),
                capi.c_method_result_type(self, idx))
            cppmethod = self._make_cppfunction(idx)
            methods_temp.setdefault(pyname, []).append(cppmethod)
        for pyname, methods in methods_temp.iteritems():
            overload = W_CPPOverload(self.space, self, methods[:])
            self.methods[pyname] = overload

    def get_method_names(self):
        return self.space.newlist([self.space.wrap(name) for name in self.methods])

    @jit.elidable_promote('0')
    def get_overload(self, name):
        try:
            return self.methods[name]
        except KeyError:
            pass
        new_method = self.find_overload(name)
        self.methods[name] = new_method
        return new_method

    def get_datamember_names(self):
        return self.space.newlist([self.space.wrap(name) for name in self.datamembers])

    @jit.elidable_promote('0')
    def get_datamember(self, name):
        try:
            return self.datamembers[name]
        except KeyError:
            pass
        new_dm = self.find_datamember(name)
        self.datamembers[name] = new_dm
        return new_dm

    @jit.elidable_promote('0')
    def dispatch(self, name, signature):
        overload = self.get_overload(name)
        sig = '(%s)' % signature
        for f in overload.functions:
            if 0 < f.signature().find(sig):
                return W_CPPOverload(self.space, self, [f])
        raise OperationError(self.space.w_TypeError, self.space.wrap("no overload matches signature"))

    def missing_attribute_error(self, name):
        return OperationError(
            self.space.w_AttributeError,
            self.space.wrap("%s '%s' has no attribute %s" % (self.kind, self.name, name)))

    def __eq__(self, other):
        return self.handle == other.handle


# For now, keep namespaces and classes separate as namespaces are extensible
# with info from multiple dictionaries and do not need to bother with meta
# classes for inheritance. Both are python classes, though, and refactoring
# may be in order at some point.
class W_CPPNamespace(W_CPPScope):
    _immutable_ = True
    kind = "namespace"

    def _make_cppfunction(self, index):
        num_args = capi.c_method_num_args(self, index)
        args_required = capi.c_method_req_args(self, index)
        arg_defs = []
        for i in range(num_args):
            arg_type = capi.c_method_arg_type(self, index, i)
            arg_dflt = capi.c_method_arg_default(self, index, i)
            arg_defs.append((arg_type, arg_dflt))
        return CPPFunction(self.space, self, index, arg_defs, args_required)

    def _make_datamember(self, dm_name, dm_idx):
        type_name = capi.c_datamember_type(self, dm_idx)
        offset = capi.c_datamember_offset(self, dm_idx)
        datamember = W_CPPDataMember(self.space, self, type_name, offset, True)
        self.datamembers[dm_name] = datamember
        return datamember

    def _find_datamembers(self):
        num_datamembers = capi.c_num_datamembers(self)
        for i in range(num_datamembers):
            if not capi.c_is_publicdata(self, i):
                continue
            datamember_name = capi.c_datamember_name(self, i)
            if not datamember_name in self.datamembers:
                self._make_datamember(datamember_name, i)

    def find_overload(self, meth_name):
        # TODO: collect all overloads, not just the non-overloaded version
        meth_idx = capi.c_method_index_from_name(self, meth_name)
        if meth_idx == -1:
            raise self.missing_attribute_error(meth_name)
        cppfunction = self._make_cppfunction(meth_idx)
        overload = W_CPPOverload(self.space, self, [cppfunction])
        return overload

    def find_datamember(self, dm_name):
        dm_idx = capi.c_datamember_index(self, dm_name)
        if dm_idx < 0:
            raise self.missing_attribute_error(dm_name)
        datamember = self._make_datamember(dm_name, dm_idx)
        return datamember

    def is_namespace(self):
        return self.space.w_True

W_CPPNamespace.typedef = TypeDef(
    'CPPNamespace',
    get_method_names = interp2app(W_CPPNamespace.get_method_names),
    get_overload = interp2app(W_CPPNamespace.get_overload, unwrap_spec=['self', str]),
    get_datamember_names = interp2app(W_CPPNamespace.get_datamember_names),
    get_datamember = interp2app(W_CPPNamespace.get_datamember, unwrap_spec=['self', str]),
    is_namespace = interp2app(W_CPPNamespace.is_namespace),
)
W_CPPNamespace.typedef.acceptable_as_base_class = False


class W_CPPClass(W_CPPScope):
    _immutable_ = True
    kind = "class"

    def _make_cppfunction(self, index):
        num_args = capi.c_method_num_args(self, index)
        args_required = capi.c_method_req_args(self, index)
        arg_defs = []
        for i in range(num_args):
            arg_type = capi.c_method_arg_type(self, index, i)
            arg_dflt = capi.c_method_arg_default(self, index, i)
            arg_defs.append((arg_type, arg_dflt))
        if capi.c_is_constructor(self, index):
            cls = CPPConstructor
        elif capi.c_is_staticmethod(self, index):
            cls = CPPFunction
        else:
            cls = CPPMethod
        return cls(self.space, self, index, arg_defs, args_required)

    def _find_datamembers(self):
        num_datamembers = capi.c_num_datamembers(self)
        for i in range(num_datamembers):
            if not capi.c_is_publicdata(self, i):
                continue
            datamember_name = capi.c_datamember_name(self, i)
            type_name = capi.c_datamember_type(self, i)
            offset = capi.c_datamember_offset(self, i)
            is_static = bool(capi.c_is_staticdata(self, i))
            datamember = W_CPPDataMember(self.space, self, type_name, offset, is_static)
            self.datamembers[datamember_name] = datamember

    def find_overload(self, name):
        raise self.missing_attribute_error(name)

    def find_datamember(self, name):
        raise self.missing_attribute_error(name)

    def get_cppthis(self, cppinstance, calling_scope):
        assert self == cppinstance.cppclass
        return cppinstance.get_rawobject()

    def is_namespace(self):
        return self.space.w_False

    def get_base_names(self):
        bases = []
        num_bases = capi.c_num_bases(self)
        for i in range(num_bases):
            base_name = capi.c_base_name(self, i)
            bases.append(self.space.wrap(base_name))
        return self.space.newlist(bases)

W_CPPClass.typedef = TypeDef(
    'CPPClass',
    type_name = interp_attrproperty('name', W_CPPClass),
    get_base_names = interp2app(W_CPPClass.get_base_names),
    get_method_names = interp2app(W_CPPClass.get_method_names),
    get_overload = interp2app(W_CPPClass.get_overload, unwrap_spec=['self', str]),
    get_datamember_names = interp2app(W_CPPClass.get_datamember_names),
    get_datamember = interp2app(W_CPPClass.get_datamember, unwrap_spec=['self', str]),
    is_namespace = interp2app(W_CPPClass.is_namespace),
    dispatch = interp2app(W_CPPClass.dispatch, unwrap_spec=['self', str, str])
)
W_CPPClass.typedef.acceptable_as_base_class = False


class W_ComplexCPPClass(W_CPPClass):
    _immutable_ = True

    def get_cppthis(self, cppinstance, calling_scope):
        assert self == cppinstance.cppclass
        offset = capi.c_base_offset(self, calling_scope, cppinstance.get_rawobject(), 1)
        return capi.direct_ptradd(cppinstance.get_rawobject(), offset)

W_ComplexCPPClass.typedef = TypeDef(
    'ComplexCPPClass',
    type_name = interp_attrproperty('name', W_CPPClass),
    get_base_names = interp2app(W_ComplexCPPClass.get_base_names),
    get_method_names = interp2app(W_ComplexCPPClass.get_method_names),
    get_overload = interp2app(W_ComplexCPPClass.get_overload, unwrap_spec=['self', str]),
    get_datamember_names = interp2app(W_ComplexCPPClass.get_datamember_names),
    get_datamember = interp2app(W_ComplexCPPClass.get_datamember, unwrap_spec=['self', str]),
    is_namespace = interp2app(W_ComplexCPPClass.is_namespace),
    dispatch = interp2app(W_CPPClass.dispatch, unwrap_spec=['self', str, str])
)
W_ComplexCPPClass.typedef.acceptable_as_base_class = False


class W_CPPTemplateType(Wrappable):
    _immutable_ = True

    def __init__(self, space, name, opaque_handle):
        self.space = space
        self.name = name
        assert lltype.typeOf(opaque_handle) == capi.C_TYPE
        self.handle = opaque_handle

    @unwrap_spec(args_w='args_w')
    def __call__(self, args_w):
        # TODO: this is broken but unused (see pythonify.py)
        fullname = "".join([self.name, '<', self.space.str_w(args_w[0]), '>'])
        return scope_byname(self.space, fullname)

W_CPPTemplateType.typedef = TypeDef(
    'CPPTemplateType',
    __call__ = interp2app(W_CPPTemplateType.__call__),
)
W_CPPTemplateType.typedef.acceptable_as_base_class = False


class W_CPPInstance(Wrappable):
    _immutable_fields_ = ["cppclass", "isref"]

    def __init__(self, space, cppclass, rawobject, isref, python_owns):
        self.space = space
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

    # allow user to determine ownership rules on a per object level
    def fget_python_owns(self, space):
        return space.wrap(self.python_owns)

    @unwrap_spec(value=bool)
    def fset_python_owns(self, space, value):
        self.python_owns = space.is_true(value)

    def get_cppthis(self, calling_scope):
        return self.cppclass.get_cppthis(self, calling_scope)

    def get_rawobject(self):
        if not self.isref:
            return self._rawobject
        else:
            ptrptr = rffi.cast(rffi.VOIDPP, self._rawobject)
            return rffi.cast(capi.C_OBJECT, ptrptr[0])

    def instance__eq__(self, w_other):
        other = self.space.interp_w(W_CPPInstance, w_other, can_be_None=False)
        # get here if no class-specific overloaded operator is available
        meth_idx = capi.c_get_global_operator(self.cppclass, other.cppclass, "==")
        if meth_idx != -1:
            gbl = scope_byname(self.space, "")
            f = gbl._make_cppfunction(meth_idx)
            ol = W_CPPOverload(self.space, scope_byname(self.space, ""), [f])
            # TODO: cache this operator (currently cached by JIT in capi/__init__.py)
            return ol.call(self, (self, w_other))
        
        # fallback: direct pointer comparison (the class comparison is needed since the
        # first data member in a struct and the struct have the same address)
        iseq = (self._rawobject == other._rawobject) and (self.cppclass == other.cppclass)
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
            capi.c_destruct(self.cppclass, self._rawobject)
            self._rawobject = capi.C_NULL_OBJECT

    def __del__(self):
        if self.python_owns:
            self.enqueue_for_destruction(self.space, W_CPPInstance.destruct,
                                         '__del__() method of ')

W_CPPInstance.typedef = TypeDef(
    'CPPInstance',
    cppclass = interp_attrproperty('cppclass', cls=W_CPPInstance),
    _python_owns = GetSetProperty(W_CPPInstance.fget_python_owns, W_CPPInstance.fset_python_owns),
    __eq__ = interp2app(W_CPPInstance.instance__eq__),
    __ne__ = interp2app(W_CPPInstance.instance__ne__),
    __nonzero__ = interp2app(W_CPPInstance.instance__nonzero__),
    destruct = interp2app(W_CPPInstance.destruct),
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


def get_pythonized_cppclass(space, handle):
    state = space.fromcache(State)
    try:
        w_pycppclass = state.cppclass_registry[handle]
    except KeyError:
        final_name = capi.c_scoped_final_name(handle)
        w_pycppclass = space.call_function(state.w_clgen_callback, space.wrap(final_name))
    return w_pycppclass

def wrap_new_cppobject_nocast(space, w_pycppclass, cppclass, rawobject, isref, python_owns):
    if space.is_w(w_pycppclass, space.w_None):
        w_pycppclass = get_pythonized_cppclass(space, cppclass.handle)
    w_cppinstance = space.allocate_instance(W_CPPInstance, w_pycppclass)
    cppinstance = space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=False)
    W_CPPInstance.__init__(cppinstance, space, cppclass, rawobject, isref, python_owns)
    memory_regulator.register(cppinstance)
    return w_cppinstance

def wrap_cppobject_nocast(space, w_pycppclass, cppclass, rawobject, isref, python_owns):
    obj = memory_regulator.retrieve(rawobject)
    if not (obj is None) and obj.cppclass is cppclass:
        return obj
    return wrap_new_cppobject_nocast(space, w_pycppclass, cppclass, rawobject, isref, python_owns)

def wrap_cppobject(space, w_pycppclass, cppclass, rawobject, isref, python_owns):
    if rawobject:
        actual = capi.c_actual_class(cppclass, rawobject)
        if actual != cppclass.handle:
            offset = capi._c_base_offset(actual, cppclass.handle, rawobject, -1)
            rawobject = capi.direct_ptradd(rawobject, offset)
            w_pycppclass = get_pythonized_cppclass(space, actual)
            w_cppclass = space.findattr(w_pycppclass, space.wrap("_cpp_proxy"))
            cppclass = space.interp_w(W_CPPClass, w_cppclass, can_be_None=False)
    return wrap_cppobject_nocast(space, w_pycppclass, cppclass, rawobject, isref, python_owns)

@unwrap_spec(cppinstance=W_CPPInstance)
def addressof(space, cppinstance):
    address = rffi.cast(rffi.LONG, cppinstance.get_rawobject())
    return space.wrap(address)

@unwrap_spec(address=int, owns=bool)
def bind_object(space, address, w_pycppclass, owns=False):
    rawobject = rffi.cast(capi.C_OBJECT, address)
    w_cppclass = space.findattr(w_pycppclass, space.wrap("_cpp_proxy"))
    cppclass = space.interp_w(W_CPPClass, w_cppclass, can_be_None=False)
    return wrap_cppobject_nocast(space, w_pycppclass, cppclass, rawobject, False, owns)

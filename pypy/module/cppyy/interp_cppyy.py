import pypy.module.cppyy.capi as capi

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef, GetSetProperty, interp_attrproperty, interp_attrproperty_w
from pypy.interpreter.baseobjspace import W_Root

from rpython.rtyper.lltypesystem import rffi, lltype, llmemory

from rpython.rlib import jit, rdynload, rweakref, rgc
from rpython.rlib import jit_libffi, clibffi
from rpython.rlib.objectmodel import we_are_translated, keepalive_until_here

from pypy.module._cffi_backend import ctypefunc
from pypy.module.cppyy import converter, executor, ffitypes, helper


class FastCallNotPossible(Exception):
    pass

# overload priorities: lower is preferred
priority = { 'void*'         : 100,
             'void**'        : 100,
             'float'         :  30,
             'double'        :  10,
             'const string&' :   1, } # solves a specific string ctor overload

from rpython.rlib.listsort import make_timsort_class
CPPMethodBaseTimSort = make_timsort_class()
class CPPMethodSort(CPPMethodBaseTimSort):
    def lt(self, a, b):
        return a.priority() < b.priority()

@unwrap_spec(name='text')
def load_dictionary(space, name):
    try:
        cdll = capi.c_load_dictionary(name)
        if not cdll:
           raise OperationError(space.w_RuntimeError, space.wrap(str("could not load dictionary " + name)))

    except rdynload.DLOpenError as e:
        if hasattr(space, "fake"):      # FakeSpace fails e.msg (?!)
            errmsg = "failed to load cdll"
        else:
            errmsg = e.msg
        raise OperationError(space.w_RuntimeError, space.newtext(str(errmsg)))
    return W_CPPLibrary(space, cdll)

class State(object):
    def __init__(self, space):
        self.cppscope_cache = {
            "void" : W_CPPClass(space, "void", capi.C_NULL_TYPE) }
        self.w_nullptr = None
        self.cpptemplate_cache = {}
        self.cppclass_registry = {}
        self.w_clgen_callback = None
        self.w_fngen_callback = None

def get_nullptr(space):
    if hasattr(space, "fake"):
        raise NotImplementedError
    state = space.fromcache(State)
    if state.w_nullptr is None:
        from pypy.module._rawffi.interp_rawffi import unpack_simple_shape
        from pypy.module._rawffi.array import W_Array, W_ArrayInstance
        arr = space.interp_w(W_Array, unpack_simple_shape(space, space.newtext('P')))
        # TODO: fix this hack; fromaddress() will allocate memory if address
        # is null and there seems to be no way around it (ll_buffer can not
        # be touched directly)
        nullarr = arr.fromaddress(space, rffi.cast(rffi.ULONG, 0), 0)
        assert isinstance(nullarr, W_ArrayInstance)
        nullarr.free(space)
        state.w_nullptr = nullarr
    return state.w_nullptr

@unwrap_spec(name='text')
def resolve_name(space, name):
    return space.newtext(capi.c_resolve_name(space, name))

@unwrap_spec(name='text')
def scope_byname(space, name):
    true_name = capi.c_resolve_name(space, name)

    state = space.fromcache(State)
    try:
        return state.cppscope_cache[true_name]
    except KeyError:
        pass

    opaque_handle = capi.c_get_scope_opaque(space, true_name)
    assert lltype.typeOf(opaque_handle) == capi.C_SCOPE
    if opaque_handle:
        final_name = capi.c_final_name(space, opaque_handle)
        if capi.c_is_namespace(space, opaque_handle):
            cppscope = W_CPPNamespace(space, final_name, opaque_handle)
        elif capi.c_has_complex_hierarchy(space, opaque_handle):
            cppscope = W_ComplexCPPClass(space, final_name, opaque_handle)
        else:
            cppscope = W_CPPClass(space, final_name, opaque_handle)
        state.cppscope_cache[name] = cppscope

        cppscope._build_methods()
        cppscope._find_datamembers()
        return cppscope

    return None

@unwrap_spec(name='text')
def template_byname(space, name):
    state = space.fromcache(State)
    try:
        return state.cpptemplate_cache[name]
    except KeyError:
        pass

    if capi.c_is_template(space, name):
        cpptemplate = W_CPPTemplateType(space, name)
        state.cpptemplate_cache[name] = cpptemplate
        return cpptemplate

    return None

def std_string_name(space):
    return space.newtext(capi.std_string_name)

@unwrap_spec(w_callback=W_Root)
def set_class_generator(space, w_callback):
    state = space.fromcache(State)
    state.w_clgen_callback = w_callback

@unwrap_spec(w_callback=W_Root)
def set_function_generator(space, w_callback):
    state = space.fromcache(State)
    state.w_fngen_callback = w_callback

def register_class(space, w_pycppclass):
    w_cppclass = space.findattr(w_pycppclass, space.newtext("_cpp_proxy"))
    cppclass = space.interp_w(W_CPPClass, w_cppclass, can_be_None=False)
    # add back-end specific method pythonizations (doing this on the wrapped
    # class allows simple aliasing of methods)
    capi.pythonize(space, cppclass.name, w_pycppclass)
    state = space.fromcache(State)
    state.cppclass_registry[rffi.cast(rffi.LONG, cppclass.handle)] = w_pycppclass


class W_CPPLibrary(W_Root):
    _immutable_ = True

    def __init__(self, space, cdll):
        self.cdll = cdll
        self.space = space

W_CPPLibrary.typedef = TypeDef(
    'CPPLibrary',
)
W_CPPLibrary.typedef.acceptable_as_base_class = True


class CPPMethod(object):
    """Dispatcher of methods. Checks the arguments, find the corresponding FFI
    function if available, makes the call, and returns the wrapped result. It
    also takes care of offset casting and recycling of known objects through
    the memory_regulator."""

    _attrs_ = ['space', 'scope', 'index', 'cppmethod', 'arg_defs', 'args_required',
               'converters', 'executor', '_funcaddr', 'cif_descr', 'uses_local']
    _immutable_ = True

    def __init__(self, space, declaring_scope, method_index, arg_defs, args_required):
        self.space = space
        self.scope = declaring_scope
        self.index = method_index
        self.cppmethod = capi.c_get_method(self.space, self.scope, method_index)
        self.arg_defs = arg_defs
        self.args_required = args_required

        # Setup of the method dispatch's innards is done lazily, i.e. only when
        # the method is actually used.
        self.converters = None
        self.executor = None
        self.cif_descr = lltype.nullptr(jit_libffi.CIF_DESCRIPTION)
        self._funcaddr = lltype.nullptr(capi.C_FUNC_PTR.TO)
        self.uses_local = False

    @staticmethod
    def unpack_cppthis(space, w_cppinstance, declaring_scope):
        cppinstance = space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=False)
        cppinstance._nullcheck()
        return cppinstance.get_cppthis(declaring_scope)

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
            raise oefmt(self.space.w_TypeError, "wrong number of arguments")

        # initial setup of converters, executors, and libffi (if available)
        if self.converters is None:
            try:
                self._setup(cppthis)
            except Exception:
                pass

        # some calls, e.g. for ptr-ptr or reference need a local array to store data for
        # the duration of the call
        if self.uses_local:
            call_local = lltype.malloc(rffi.VOIDP.TO, 2*len(args_w), flavor='raw')
        else:
            call_local = lltype.nullptr(rffi.VOIDP.TO)

        try:
            # attempt to call directly through ffi chain
            if self._funcaddr:
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
        if self.cif_descr == lltype.nullptr(jit_libffi.CIF_DESCRIPTION):
            raise FastCallNotPossible
        cif_descr = self.cif_descr
        buffer = lltype.malloc(rffi.CCHARP.TO, cif_descr.exchange_size, flavor='raw')
        try:
            # this pointer
            data = capi.exchange_address(buffer, cif_descr, 0)
            x = rffi.cast(rffi.LONGP, data)       # LONGP needed for test_zjit.py
            x[0] = rffi.cast(rffi.LONG, cppthis)

            # other arguments and defaults
            i = len(self.arg_defs) + 1
            for i in range(len(args_w)):
                conv = self.converters[i]
                w_arg = args_w[i]
                data = capi.exchange_address(buffer, cif_descr, i+1)
                conv.convert_argument_libffi(self.space, w_arg, data, call_local)
            for j in range(i+1, len(self.arg_defs)):
                conv = self.converters[j]
                data = capi.exchange_address(buffer, cif_descr, j+1)
                conv.default_argument_libffi(self.space, data)

            assert self._funcaddr
            w_res = self.executor.execute_libffi(
                self.space, cif_descr, self._funcaddr, buffer)
        finally:
            lltype.free(buffer, flavor='raw')
            keepalive_until_here(args_w)
        return w_res

    # from ctypefunc; have my own version for annotater purposes and to disable
    # memory tracking (method live time is longer than the tests)
    @jit.dont_look_inside
    def _rawallocate(self, builder):
        builder.space = self.space

        # compute the total size needed in the CIF_DESCRIPTION buffer
        builder.nb_bytes = 0
        builder.bufferp = lltype.nullptr(rffi.CCHARP.TO)
        builder.fb_build()

        # allocate the buffer
        if we_are_translated():
            rawmem = lltype.malloc(rffi.CCHARP.TO, builder.nb_bytes,
                                   flavor='raw', track_allocation=False)
            rawmem = rffi.cast(jit_libffi.CIF_DESCRIPTION_P, rawmem)
        else:
            # gross overestimation of the length below, but too bad
            rawmem = lltype.malloc(jit_libffi.CIF_DESCRIPTION_P.TO, builder.nb_bytes,
                                   flavor='raw', track_allocation=False)

        # the buffer is automatically managed from the W_CTypeFunc instance
        self.cif_descr = rawmem

        # call again fb_build() to really build the libffi data structures
        builder.bufferp = rffi.cast(rffi.CCHARP, rawmem)
        builder.fb_build()
        assert builder.bufferp == rffi.ptradd(rffi.cast(rffi.CCHARP, rawmem),
                                              builder.nb_bytes)

        # fill in the 'exchange_*' fields
        builder.fb_build_exchange(rawmem)

        # fill in the extra fields
        builder.fb_extra_fields(rawmem)

        # call libffi's ffi_prep_cif() function
        res = jit_libffi.jit_ffi_prep_cif(rawmem)
        if res != clibffi.FFI_OK:
            raise oefmt(self.space.w_SystemError,
                        "libffi failed to build this function type")

    def _setup(self, cppthis):
        self.converters = [converter.get_converter(self.space, arg_type, arg_dflt)
                               for arg_type, arg_dflt in self.arg_defs]
        self.executor = executor.get_executor(
            self.space, capi.c_method_result_type(self.space, self.scope, self.index))

        for conv in self.converters:
            if conv.uses_local:
                self.uses_local = True
                break

        # Each CPPMethod corresponds one-to-one to a C++ equivalent and cppthis
        # has been offset to the matching class. Hence, the libffi pointer is
        # uniquely defined and needs to be setup only once.
        funcaddr = capi.c_get_function_address(self.space, self.scope, self.index)
        if funcaddr and cppthis:      # methods only for now
            state = self.space.fromcache(ffitypes.State)

            # argument type specification (incl. cppthis)
            fargs = []
            try:
                fargs.append(state.c_voidp)
                for i, conv in enumerate(self.converters):
                    fargs.append(conv.cffi_type(self.space))
                fresult = self.executor.cffi_type(self.space)
            except:
                raise FastCallNotPossible

            # the following is derived from _cffi_backend.ctypefunc
            builder = ctypefunc.CifDescrBuilder(fargs[:], fresult, clibffi.FFI_DEFAULT_ABI)
            try:
                self._rawallocate(builder)
            except OperationError as e:
                if not e.match(self.space, self.space.w_NotImplementedError):
                    raise
                # else, eat the NotImplementedError.  We will get the
                # exception if we see an actual call
                if self.cif_descr:   # should not be True, but you never know
                    lltype.free(self.cif_descr, flavor='raw')
                    self.cif_descr = lltype.nullptr(jit_libffi.CIF_DESCRIPTION)
                raise FastCallNotPossible

            # success ...
            self._funcaddr = funcaddr

    @jit.unroll_safe
    def prepare_arguments(self, args_w, call_local):
        args = capi.c_allocate_function_args(self.space, len(args_w))
        stride = capi.c_function_arg_sizeof(self.space)
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
                capi.c_deallocate_function_args(self.space, args)
                raise
        return args

    @jit.unroll_safe
    def finalize_call(self, args, args_w, call_local):
        stride = capi.c_function_arg_sizeof(self.space)
        for i in range(len(args_w)):
            conv = self.converters[i]
            arg_i = lltype.direct_ptradd(rffi.cast(rffi.CCHARP, args), i*stride)
            loc_i = self._address_from_local_buffer(call_local, i)
            conv.finalize_call(self.space, args_w[i], loc_i)
            conv.free_argument(self.space, rffi.cast(capi.C_OBJECT, arg_i), loc_i)
        capi.c_deallocate_function_args(self.space, args)

    def signature(self):
        return capi.c_method_signature(self.space, self.scope, self.index)

    def priority(self):
        total_arg_priority = 0
        for p in [priority.get(arg_type, 0) for arg_type, arg_dflt in self.arg_defs]:
            total_arg_priority += p
        return total_arg_priority

    @rgc.must_be_light_finalizer
    def __del__(self):
        if self.cif_descr:
            lltype.free(self.cif_descr, flavor='raw')

    def __repr__(self):
        return "CPPMethod: %s" % self.signature()

    def _freeze_(self):
        assert 0, "you should never have a pre-built instance of this!"


class CPPFunction(CPPMethod):
    """Global (namespaced) function dispatcher."""

    _immutable_ = True

    @staticmethod
    def unpack_cppthis(space, w_cppinstance, declaring_scope):
        return capi.C_NULL_OBJECT

    def __repr__(self):
        return "CPPFunction: %s" % self.signature()


class CPPTemplatedCall(CPPMethod):
    """Method dispatcher that first resolves the template instance."""

    _attrs_ = ['space', 'templ_args']
    _immutable_ = True

    def __init__(self, space, templ_args, declaring_scope, method_index, arg_defs, args_required):
        self.space = space
        self.templ_args = templ_args
        # TODO: might have to specialize for CPPTemplatedCall on CPPMethod/CPPFunction here
        CPPMethod.__init__(self, space, declaring_scope, method_index, arg_defs, args_required)

    def call(self, cppthis, args_w):
        assert lltype.typeOf(cppthis) == capi.C_OBJECT
        for i in range(len(args_w)):
            try:
                s = self.space.text_w(args_w[i])
            except OperationError:
                s = self.space.text_w(self.space.getattr(args_w[i], self.space.newtext('__name__')))
            s = capi.c_resolve_name(self.space, s)
            if s != self.templ_args[i]:
                raise oefmt(self.space.w_TypeError,
                            "non-matching template (got %s where %s expected)",
                            s, self.templ_args[i])
        return W_CPPBoundMethod(cppthis, self)

    def bound_call(self, cppthis, args_w):
        return CPPMethod.call(self, cppthis, args_w)

    def __repr__(self):
        return "CPPTemplatedCall: %s" % self.signature()


class CPPConstructor(CPPMethod):
    """Method dispatcher that constructs new objects. This method can not have
    a fast path, as the allocation of the object is currently left to the
    reflection layer only, since the C++ class may have an overloaded operator
    new, disallowing malloc here."""

    _immutable_ = True

    @staticmethod
    def unpack_cppthis(space, w_cppinstance, declaring_scope):
        return rffi.cast(capi.C_OBJECT, declaring_scope.handle)

    def call(self, cppthis, args_w):
        # Note: this does not return a wrapped instance, just a pointer to the
        # new instance; the overload must still wrap it before returning. Also,
        # cppthis is declaring_scope.handle (as per unpack_cppthis(), above).
        return CPPMethod.call(self, cppthis, args_w)

    def __repr__(self):
        return "CPPConstructor: %s" % self.signature()


class CPPSetItem(CPPMethod):
    """Method dispatcher specific to Python's __setitem__ mapped onto C++'s
    operator[](int). The former function takes an extra argument to assign to
    the return type of the latter."""

    _immutable_ = True

    def call(self, cppthis, args_w):
        end = len(args_w)-1
        if 0 <= end:
            w_item = args_w[end]
            args_w = args_w[:end]
            if self.converters is None:
                self._setup(cppthis)
            self.executor.set_item(self.space, w_item) # TODO: what about threads?
        CPPMethod.call(self, cppthis, args_w)


class W_CPPOverload(W_Root):
    """Dispatcher that is actually available at the app-level: it is a
    collection of (possibly) overloaded methods or functions. It calls these
    in order and deals with error handling and reporting."""

    _attrs_ = ['space', 'scope', 'functions']
    _immutable_fields_ = ['scope', 'functions[*]']

    def __init__(self, space, declaring_scope, functions):
        self.space = space
        self.scope = declaring_scope
        assert len(functions)
        from rpython.rlib import debug
        self.functions = debug.make_sure_not_resized(functions)

    @jit.elidable_promote()
    def is_static(self):
        if isinstance(self.functions[0], CPPFunction):
            return self.space.w_True
        return self.space.w_False

    @jit.unroll_safe
    @unwrap_spec(args_w='args_w')
    def call(self, w_cppinstance, args_w):
        # instance handling is specific to the function type only, so take it out
        # of the loop over function overloads
        cppthis = self.functions[0].unpack_cppthis(
            self.space, w_cppinstance, self.functions[0].scope)
        assert lltype.typeOf(cppthis) == capi.C_OBJECT

        # The following code tries out each of the functions in order. If
        # argument conversion fails (or simply if the number of arguments do
        # not match), that will lead to an exception, The JIT will snip out
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
            raise OperationError(self.space.w_TypeError, self.space.newtext(errmsg))
        w_exc_type = None
        all_same_type = True
        for i in range(len(self.functions)):
            cppyyfunc = self.functions[i]
            try:
                return cppyyfunc.call(cppthis, args_w)
            except OperationError as e:
                # special case if there's just one function, to prevent clogging the error message
                if len(self.functions) == 1:
                    raise
                if w_exc_type is None:
                    w_exc_type = e.w_type
                elif all_same_type and not e.match(self.space, w_exc_type):
                    all_same_type = False
                errmsg += '\n  '+cppyyfunc.signature()+' =>\n'
                errmsg += '    '+e.errorstr(self.space)
            except Exception as e:
                # can not special case this for non-overloaded functions as we anyway need an
                # OperationError error down from here
                errmsg += '\n  '+cppyyfunc.signature()+' =>\n'
                errmsg += '    Exception: '+str(e)

        if all_same_type and w_exc_type is not None:
            raise OperationError(w_exc_type, self.space.newtext(errmsg))
        else:
            raise OperationError(self.space.w_TypeError, self.space.newtext(errmsg))

    def signature(self):
        sig = self.functions[0].signature()
        for i in range(1, len(self.functions)):
            sig += '\n'+self.functions[i].signature()
        return self.space.newtext(sig)

    def __repr__(self):
        return "W_CPPOverload(%s)" % [f.signature() for f in self.functions]

W_CPPOverload.typedef = TypeDef(
    'CPPOverload',
    is_static = interp2app(W_CPPOverload.is_static),
    call = interp2app(W_CPPOverload.call),
    signature = interp2app(W_CPPOverload.signature),
)


class W_CPPConstructorOverload(W_CPPOverload):
    @jit.elidable_promote()
    def is_static(self):
        return self.space.w_False

    @jit.elidable_promote()
    def unpack_cppthis(self, w_cppinstance):
        return rffi.cast(capi.C_OBJECT, self.scope.handle)

    @jit.unroll_safe
    @unwrap_spec(args_w='args_w')
    def call(self, w_cppinstance, args_w):
        w_result = W_CPPOverload.call(self, w_cppinstance, args_w)
        newthis = rffi.cast(capi.C_OBJECT, self.space.uint_w(w_result))
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        if cppinstance is not None:
            cppinstance._rawobject = newthis
            memory_regulator.register(cppinstance)
            return w_cppinstance
        return wrap_cppobject(self.space, newthis, self.functions[0].scope,
                              do_cast=False, python_owns=True, fresh=True)

    def __repr__(self):
        return "W_CPPConstructorOverload(%s)" % [f.signature() for f in self.functions]

W_CPPConstructorOverload.typedef = TypeDef(
    'CPPConstructorOverload',
    is_static = interp2app(W_CPPConstructorOverload.is_static),
    call = interp2app(W_CPPConstructorOverload.call),
    signature = interp2app(W_CPPOverload.signature),
)


class W_CPPBoundMethod(W_Root):
    _attrs_ = ['cppthis', 'method']

    def __init__(self, cppthis, method):
        self.cppthis = cppthis
        self.method = method

    def __call__(self, args_w):
        return self.method.bound_call(self.cppthis, args_w)

W_CPPBoundMethod.typedef = TypeDef(
    'CPPBoundMethod',
    __call__ = interp2app(W_CPPBoundMethod.__call__),
)


class W_CPPDataMember(W_Root):
    _attrs_ = ['space', 'scope', 'converter', 'offset']
    _immutable_fields = ['scope', 'converter', 'offset']

    def __init__(self, space, declaring_scope, type_name, offset):
        self.space = space
        self.scope = declaring_scope
        self.converter = converter.get_converter(self.space, type_name, '')
        self.offset = offset

    def is_static(self):
        return self.space.w_False

    def _get_offset(self, cppinstance):
        if cppinstance:
            assert lltype.typeOf(cppinstance.cppclass.handle) == lltype.typeOf(self.scope.handle)
            offset = self.offset + cppinstance.cppclass.get_base_offset(cppinstance, self.scope)
        else:
            offset = self.offset
        return offset

    def get(self, w_cppinstance, w_pycppclass):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        if not cppinstance:
            raise oefmt(self.space.w_ReferenceError,
                        "attribute access requires an instance")
        offset = self._get_offset(cppinstance)
        return self.converter.from_memory(self.space, w_cppinstance, w_pycppclass, offset)

    def set(self, w_cppinstance, w_value):
        cppinstance = self.space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=True)
        if not cppinstance:
            raise oefmt(self.space.w_ReferenceError,
                        "attribute access requires an instance")
        offset = self._get_offset(cppinstance)
        self.converter.to_memory(self.space, w_cppinstance, w_value, offset)
        return self.space.w_None

W_CPPDataMember.typedef = TypeDef(
    'CPPDataMember',
    is_static = interp2app(W_CPPDataMember.is_static),
    __get__ = interp2app(W_CPPDataMember.get),
    __set__ = interp2app(W_CPPDataMember.set),
)
W_CPPDataMember.typedef.acceptable_as_base_class = False

class W_CPPStaticData(W_CPPDataMember):
    def is_static(self):
        return self.space.w_True

    @jit.elidable_promote()
    def _get_offset(self, cppinstance):
        return self.offset

    def get(self, w_cppinstance, w_pycppclass):
        return self.converter.from_memory(self.space, self.space.w_None, w_pycppclass, self.offset)

    def set(self, w_cppinstance, w_value):
        self.converter.to_memory(self.space, self.space.w_None, w_value, self.offset)
        return self.space.w_None

W_CPPStaticData.typedef = TypeDef(
    'CPPStaticData',
    is_static = interp2app(W_CPPStaticData.is_static),
    __get__ = interp2app(W_CPPStaticData.get),
    __set__ = interp2app(W_CPPStaticData.set),
)
W_CPPStaticData.typedef.acceptable_as_base_class = False

def is_static(space, w_obj):
    try:
        space.interp_w(W_CPPStaticData, w_obj, can_be_None=False)
        return space.w_True
    except Exception:
        return space.w_False

class W_CPPScope(W_Root):
    _attrs_ = ['space', 'name', 'handle', 'methods', 'datamembers']
    _immutable_fields_ = ['kind', 'name']

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
        for i in range(capi.c_num_methods(self.space, self)):
            idx = capi.c_method_index_at(self.space, self, i)
            pyname = helper.map_operator_name(self.space,
                capi.c_method_name(self.space, self, idx),
                capi.c_method_num_args(self.space, self, idx),
                capi.c_method_result_type(self.space, self, idx))
            cppmethod = self._make_cppfunction(pyname, idx)
            methods_temp.setdefault(pyname, []).append(cppmethod)
        # the following covers the case where the only kind of operator[](idx)
        # returns are the ones that produce non-const references; these can be
        # used for __getitem__ just as much as for __setitem__, though
        if not "__getitem__" in methods_temp:
            try:
                for m in methods_temp["__setitem__"]:
                    cppmethod = self._make_cppfunction("__getitem__", m.index)
                    methods_temp.setdefault("__getitem__", []).append(cppmethod)
            except KeyError:
                pass          # just means there's no __setitem__ either

        # create the overload methods from the method sets
        for pyname, methods in methods_temp.iteritems():
            CPPMethodSort(methods).sort()
            if pyname == self.name:
                overload = W_CPPConstructorOverload(self.space, self, methods[:])
            else:
                overload = W_CPPOverload(self.space, self, methods[:])
            self.methods[pyname] = overload

    def full_name(self):
        return capi.c_scoped_final_name(self.space, self.handle)

    def get_method_names(self):
        return self.space.newlist([self.space.newtext(name) for name in self.methods])

    def get_overload(self, name):
        try:
            return self.methods[name]
        except KeyError:
            pass
        new_method = self.find_overload(name)
        self.methods[name] = new_method
        return new_method

    def get_datamember_names(self):
        return self.space.newlist([self.space.newtext(name) for name in self.datamembers])

    def get_datamember(self, name):
        try:
            return self.datamembers[name]
        except KeyError:
            pass
        new_dm = self.find_datamember(name)
        self.datamembers[name] = new_dm
        return new_dm

    def dispatch(self, name, signature):
        overload = self.get_overload(name)
        sig = '(%s)' % signature
        for f in overload.functions:
            if 0 < f.signature().find(sig):
                return W_CPPOverload(self.space, self, [f])
        raise oefmt(self.space.w_TypeError, "no overload matches signature")

    def missing_attribute_error(self, name):
        return oefmt(self.space.w_AttributeError,
                     "%s '%s' has no attribute %s",
                     self.kind, self.name, name)

    def __eq__(self, other):
        return self.handle == other.handle

    def __ne__(self, other):
        return self.handle != other.handle


# For now, keep namespaces and classes separate as namespaces are extensible
# with info from multiple dictionaries and do not need to bother with meta
# classes for inheritance. Both are python classes, though, and refactoring
# may be in order at some point.
class W_CPPNamespace(W_CPPScope):
    _immutable_fields_ = ['kind']

    kind = "namespace"

    def _make_cppfunction(self, pyname, index):
        num_args = capi.c_method_num_args(self.space, self, index)
        args_required = capi.c_method_req_args(self.space, self, index)
        arg_defs = []
        for i in range(num_args):
            arg_type = capi.c_method_arg_type(self.space, self, index, i)
            arg_dflt = capi.c_method_arg_default(self.space, self, index, i)
            arg_defs.append((arg_type, arg_dflt))
        return CPPFunction(self.space, self, index, arg_defs, args_required)

    def _build_methods(self):
        pass       # force lazy lookups in namespaces

    def _make_datamember(self, dm_name, dm_idx):
        type_name = capi.c_datamember_type(self.space, self, dm_idx)
        offset = capi.c_datamember_offset(self.space, self, dm_idx)
        if offset == -1:
            raise self.missing_attribute_error(dm_name)
        datamember = W_CPPStaticData(self.space, self, type_name, offset)
        self.datamembers[dm_name] = datamember
        return datamember

    def _find_datamembers(self):
        pass       # force lazy lookups in namespaces

    def find_overload(self, meth_name):
        indices = capi.c_method_indices_from_name(self.space, self, meth_name)
        if not indices:
            raise self.missing_attribute_error(meth_name)
        cppfunctions = []
        for meth_idx in indices:
            f = self._make_cppfunction(meth_name, meth_idx)
            cppfunctions.append(f)
        overload = W_CPPOverload(self.space, self, cppfunctions)
        return overload

    def find_datamember(self, dm_name):
        dm_idx = capi.c_datamember_index(self.space, self, dm_name)
        if dm_idx < 0:
            raise self.missing_attribute_error(dm_name)
        datamember = self._make_datamember(dm_name, dm_idx)
        return datamember

    def is_namespace(self):
        return self.space.w_True

    def ns__dir__(self):
        # Collect a list of everything (currently) available in the namespace.
        # The backend can filter by returning empty strings. Special care is
        # taken for functions, which need not be unique (overloading).
        alldir = []
        for i in range(capi.c_num_scopes(self.space, self)):
            sname = capi.c_scope_name(self.space, self, i)
            if sname: alldir.append(self.space.newtext(sname))
        allmeth = {}
        for i in range(capi.c_num_methods(self.space, self)):
            idx = capi.c_method_index_at(self.space, self, i)
            mname = capi.c_method_name(self.space, self, idx)
            if mname: allmeth.setdefault(mname, 0)
        for m in allmeth.keys():
            alldir.append(self.space.newtext(m))
        for i in range(capi.c_num_datamembers(self.space, self)):
            dname = capi.c_datamember_name(self.space, self, i)
            if dname: alldir.append(self.space.newtext(dname))
        return self.space.newlist(alldir)
        

W_CPPNamespace.typedef = TypeDef(
    'CPPNamespace',
    get_method_names = interp2app(W_CPPNamespace.get_method_names),
    get_overload = interp2app(W_CPPNamespace.get_overload, unwrap_spec=['self', 'text']),
    get_datamember_names = interp2app(W_CPPNamespace.get_datamember_names),
    get_datamember = interp2app(W_CPPNamespace.get_datamember, unwrap_spec=['self', 'text']),
    is_namespace = interp2app(W_CPPNamespace.is_namespace),
    __dir__ = interp2app(W_CPPNamespace.ns__dir__),
)
W_CPPNamespace.typedef.acceptable_as_base_class = False


class W_CPPClass(W_CPPScope):
    _attrs_ = ['space', 'name', 'handle', 'methods', 'datamembers']
    _immutable_fields_ = ['kind', 'constructor', 'methods[*]', 'datamembers[*]']

    kind = "class"

    def __init__(self, space, name, opaque_handle):
        W_CPPScope.__init__(self, space, name, opaque_handle)

    def _make_cppfunction(self, pyname, index):
        num_args = capi.c_method_num_args(self.space, self, index)
        args_required = capi.c_method_req_args(self.space, self, index)
        arg_defs = []
        for i in range(num_args):
            arg_type = capi.c_method_arg_type(self.space, self, index, i)
            arg_dflt = capi.c_method_arg_default(self.space, self, index, i)
            arg_defs.append((arg_type, arg_dflt))
        if capi.c_is_constructor(self.space, self, index):
            cppfunction = CPPConstructor(self.space, self, index, arg_defs, args_required)
        elif capi.c_method_is_template(self.space, self, index):
            templ_args = capi.c_template_args(self.space, self, index)
            cppfunction = CPPTemplatedCall(self.space, templ_args, self, index, arg_defs, args_required)
        elif capi.c_is_staticmethod(self.space, self, index):
            cppfunction = CPPFunction(self.space, self, index, arg_defs, args_required)
        elif pyname == "__setitem__":
            cppfunction = CPPSetItem(self.space, self, index, arg_defs, args_required)
        else:
            cppfunction = CPPMethod(self.space, self, index, arg_defs, args_required)
        return cppfunction

    def _find_datamembers(self):
        num_datamembers = capi.c_num_datamembers(self.space, self)
        for i in range(num_datamembers):
            if not capi.c_is_publicdata(self.space, self, i):
                continue
            datamember_name = capi.c_datamember_name(self.space, self, i)
            type_name = capi.c_datamember_type(self.space, self, i)
            offset = capi.c_datamember_offset(self.space, self, i)
            if offset == -1:
                continue      # dictionary problem; raises AttributeError on use
            is_static = bool(capi.c_is_staticdata(self.space, self, i))
            if is_static:
                datamember = W_CPPStaticData(self.space, self, type_name, offset)
            else:
                datamember = W_CPPDataMember(self.space, self, type_name, offset)
            self.datamembers[datamember_name] = datamember

    def construct(self):
        return self.get_overload(self.name).call(None, [])

    def find_overload(self, name):
        raise self.missing_attribute_error(name)

    def find_datamember(self, name):
        raise self.missing_attribute_error(name)

    def get_base_offset(self, cppinstance, calling_scope):
        assert self == cppinstance.cppclass
        return 0

    def get_cppthis(self, cppinstance, calling_scope):
        assert self == cppinstance.cppclass
        return cppinstance.get_rawobject()

    def is_namespace(self):
        return self.space.w_False

    def get_base_names(self):
        bases = []
        num_bases = capi.c_num_bases(self.space, self)
        for i in range(num_bases):
            base_name = capi.c_base_name(self.space, self, i)
            bases.append(self.space.newtext(base_name))
        return self.space.newlist(bases)

W_CPPClass.typedef = TypeDef(
    'CPPClass',
    type_name = interp_attrproperty('name', W_CPPClass, wrapfn="newtext"),
    get_base_names = interp2app(W_CPPClass.get_base_names),
    get_method_names = interp2app(W_CPPClass.get_method_names),
    get_overload = interp2app(W_CPPClass.get_overload, unwrap_spec=['self', 'text']),
    get_datamember_names = interp2app(W_CPPClass.get_datamember_names),
    get_datamember = interp2app(W_CPPClass.get_datamember, unwrap_spec=['self', 'text']),
    is_namespace = interp2app(W_CPPClass.is_namespace),
    dispatch = interp2app(W_CPPClass.dispatch, unwrap_spec=['self', 'text', 'text'])
)
W_CPPClass.typedef.acceptable_as_base_class = False


class W_ComplexCPPClass(W_CPPClass):

    def get_base_offset(self, cppinstance, calling_scope):
        assert self == cppinstance.cppclass
        offset = capi.c_base_offset(self.space,
                                    self, calling_scope, cppinstance.get_rawobject(), 1)
        return offset

    def get_cppthis(self, cppinstance, calling_scope):
        assert self == cppinstance.cppclass
        offset = self.get_base_offset(cppinstance, calling_scope)
        return capi.direct_ptradd(cppinstance.get_rawobject(), offset)

W_ComplexCPPClass.typedef = TypeDef(
    'ComplexCPPClass',
    type_name = interp_attrproperty('name', W_CPPClass, wrapfn="newtext"),
    get_base_names = interp2app(W_ComplexCPPClass.get_base_names),
    get_method_names = interp2app(W_ComplexCPPClass.get_method_names),
    get_overload = interp2app(W_ComplexCPPClass.get_overload, unwrap_spec=['self', 'text']),
    get_datamember_names = interp2app(W_ComplexCPPClass.get_datamember_names),
    get_datamember = interp2app(W_ComplexCPPClass.get_datamember, unwrap_spec=['self', 'text']),
    is_namespace = interp2app(W_ComplexCPPClass.is_namespace),
    dispatch = interp2app(W_CPPClass.dispatch, unwrap_spec=['self', 'text', 'text'])
)
W_ComplexCPPClass.typedef.acceptable_as_base_class = False


class W_CPPTemplateType(W_Root):
    _attrs_ = ['space', 'name']
    _immutable_fields = ['name']

    def __init__(self, space, name):
        self.space = space
        self.name = name

    @unwrap_spec(args_w='args_w')
    def __call__(self, args_w):
        # TODO: this is broken but unused (see pythonify.py)
        fullname = "".join([self.name, '<', self.space.text_w(args_w[0]), '>'])
        return scope_byname(self.space, fullname)

W_CPPTemplateType.typedef = TypeDef(
    'CPPTemplateType',
    __call__ = interp2app(W_CPPTemplateType.__call__),
)
W_CPPTemplateType.typedef.acceptable_as_base_class = False


class W_CPPInstance(W_Root):
    _attrs_ = ['space', 'cppclass', '_rawobject', 'isref', 'python_owns',
               'finalizer_registered']
    _immutable_fields_ = ["cppclass", "isref"]

    finalizer_registered = False

    def __init__(self, space, cppclass, rawobject, isref, python_owns):
        self.space = space
        self.cppclass = cppclass
        assert lltype.typeOf(rawobject) == capi.C_OBJECT
        assert not isref or rawobject
        self._rawobject = rawobject
        assert not isref or not python_owns
        self.isref = isref
        self.python_owns = python_owns
        self._opt_register_finalizer()

    def _opt_register_finalizer(self):
        if self.python_owns and not self.finalizer_registered \
               and not hasattr(self.space, "fake"):
            self.register_finalizer(self.space)
            self.finalizer_registered = True

    def _nullcheck(self):
        if not self._rawobject or (self.isref and not self.get_rawobject()):
            raise oefmt(self.space.w_ReferenceError,
                        "trying to access a NULL pointer")

    # allow user to determine ownership rules on a per object level
    def fget_python_owns(self, space):
        return space.newbool(self.python_owns)

    @unwrap_spec(value=bool)
    def fset_python_owns(self, space, value):
        self.python_owns = space.is_true(value)
        self._opt_register_finalizer()

    def get_cppthis(self, calling_scope):
        return self.cppclass.get_cppthis(self, calling_scope)

    def get_rawobject(self):
        if not self.isref:
            return self._rawobject
        else:
            ptrptr = rffi.cast(rffi.VOIDPP, self._rawobject)
            return rffi.cast(capi.C_OBJECT, ptrptr[0])

    def _get_as_builtin(self):
        try:
            return self.space.call_method(self, "_cppyy_as_builtin")
        except OperationError as e:
            if not (e.match(self.space, self.space.w_TypeError) or
                    e.match(self.space, self.space.w_AttributeError)):
                # TODO: TypeError is raised by call_method if the method is not found;
                # it'd be a lot nicer if only AttributeError were raise
                raise
        return None

    def instance__init__(self, args_w):
        if capi.c_is_abstract(self.space, self.cppclass.handle):
            raise oefmt(self.space.w_TypeError,
                        "cannot instantiate abstract class '%s'",
                        self.cppclass.name)
        constructor_overload = self.cppclass.get_overload(self.cppclass.name)
        constructor_overload.call(self, args_w)
 
    def instance__eq__(self, w_other):
        # special case: if other is None, compare pointer-style
        if self.space.is_w(w_other, self.space.w_None):
            return self.space.newbool(not self._rawobject)

        # get here if no class-specific overloaded operator is available, try to
        # find a global overload in gbl, in __gnu_cxx (for iterators), or in the
        # scopes of the argument classes (TODO: implement that last option)
        try:
            # TODO: expecting w_other to be an W_CPPInstance is too limiting
            other = self.space.interp_w(W_CPPInstance, w_other, can_be_None=False)
            for name in ["", "__gnu_cxx", "__1"]:
                nss = scope_byname(self.space, name)
                meth_idx = capi.c_get_global_operator(
                    self.space, nss, self.cppclass, other.cppclass, "operator==")
                if meth_idx != -1:
                    f = nss._make_cppfunction("operator==", meth_idx)
                    ol = W_CPPOverload(self.space, nss, [f])
                    # TODO: cache this operator (not done yet, as the above does not
                    # select all overloads)
                    return ol.call(self, [self, w_other])
        except OperationError as e:
            if not e.match(self.space, self.space.w_TypeError):
                raise

        # fallback 1: convert the object to a builtin equivalent
        w_as_builtin = self._get_as_builtin()
        if w_as_builtin is not None:
            return self.space.eq(w_as_builtin, w_other)

        # fallback 2: direct pointer comparison (the class comparison is needed since
        # the first data member in a struct and the struct have the same address)
        other = self.space.interp_w(W_CPPInstance, w_other, can_be_None=False)  # TODO: factor out
        iseq = (self._rawobject == other._rawobject) and (self.cppclass == other.cppclass)
        return self.space.newbool(iseq)

    def instance__ne__(self, w_other):
        return self.space.not_(self.instance__eq__(w_other))

    def instance__nonzero__(self):
        if not self._rawobject or (self.isref and not self.get_rawobject()):
            return self.space.w_False
        return self.space.w_True

    def instance__len__(self):
        w_as_builtin = self._get_as_builtin()
        if w_as_builtin is not None:
            return self.space.len(w_as_builtin)
        raise oefmt(self.space.w_TypeError,
                    "'%s' has no length", self.cppclass.name)

    def instance__cmp__(self, w_other):
        w_as_builtin = self._get_as_builtin()
        if w_as_builtin is not None:
            return self.space.cmp(w_as_builtin, w_other)
        raise oefmt(self.space.w_AttributeError,
                    "'%s' has no attribute __cmp__", self.cppclass.name)

    def instance__repr__(self):
        w_as_builtin = self._get_as_builtin()
        if w_as_builtin is not None:
            return self.space.repr(w_as_builtin)
        return self.space.newtext("<%s object at 0x%x>" %
                               (self.cppclass.name, rffi.cast(rffi.ULONG, self.get_rawobject())))

    def destruct(self):
        if self._rawobject and not self.isref:
            memory_regulator.unregister(self)
            capi.c_destruct(self.space, self.cppclass, self._rawobject)
            self._rawobject = capi.C_NULL_OBJECT

    def _finalize_(self):
        if self.python_owns:
            self.destruct()

W_CPPInstance.typedef = TypeDef(
    'CPPInstance',
    cppclass = interp_attrproperty_w('cppclass', cls=W_CPPInstance),
    _python_owns = GetSetProperty(W_CPPInstance.fget_python_owns, W_CPPInstance.fset_python_owns),
    __init__ = interp2app(W_CPPInstance.instance__init__),
    __eq__ = interp2app(W_CPPInstance.instance__eq__),
    __ne__ = interp2app(W_CPPInstance.instance__ne__),
    __nonzero__ = interp2app(W_CPPInstance.instance__nonzero__),
    __len__ = interp2app(W_CPPInstance.instance__len__),
    __cmp__ = interp2app(W_CPPInstance.instance__cmp__),
    __repr__ = interp2app(W_CPPInstance.instance__repr__),
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
        if not obj._rawobject:
            return
        int_address = int(rffi.cast(rffi.LONG, obj._rawobject))
        self.objects.set(int_address, obj)

    def unregister(self, obj):
        if not obj._rawobject:
            return
        int_address = int(rffi.cast(rffi.LONG, obj._rawobject))
        self.objects.set(int_address, None)

    def retrieve(self, address):
        int_address = int(rffi.cast(rffi.LONG, address))
        return self.objects.get(int_address)

memory_regulator = MemoryRegulator()


def get_pythonized_cppclass(space, handle):
    state = space.fromcache(State)
    try:
        w_pycppclass = state.cppclass_registry[rffi.cast(rffi.LONG, handle)]
    except KeyError:
        final_name = capi.c_scoped_final_name(space, handle)
        # the callback will cache the class by calling register_class
        w_pycppclass = space.call_function(state.w_clgen_callback, space.newtext(final_name))
    return w_pycppclass

def get_interface_func(space, w_callable, npar):
    state = space.fromcache(State)
    return space.call_function(state.w_fngen_callback, w_callable, space.newint(npar))

def wrap_cppobject(space, rawobject, cppclass,
                   do_cast=True, python_owns=False, is_ref=False, fresh=False):
    rawobject = rffi.cast(capi.C_OBJECT, rawobject)

    # cast to actual if requested and possible
    w_pycppclass = None
    if do_cast and rawobject:
        actual = capi.c_actual_class(space, cppclass, rawobject)
        if actual != cppclass.handle:
            try:
                w_pycppclass = get_pythonized_cppclass(space, actual)
                offset = capi.c_base_offset1(space, actual, cppclass, rawobject, -1)
                rawobject = capi.direct_ptradd(rawobject, offset)
                w_cppclass = space.findattr(w_pycppclass, space.newtext("_cpp_proxy"))
                cppclass = space.interp_w(W_CPPClass, w_cppclass, can_be_None=False)
            except Exception:
                # failed to locate/build the derived class, so stick to the base (note
                # that only get_pythonized_cppclass is expected to raise, so none of
                # the variables are re-assigned yet)
                pass

    if w_pycppclass is None:
        w_pycppclass = get_pythonized_cppclass(space, cppclass.handle)

    # try to recycle existing object if this one is not newly created
    if not fresh and rawobject:
        obj = memory_regulator.retrieve(rawobject)
        if obj is not None and obj.cppclass is cppclass:
            return obj

    # fresh creation
    w_cppinstance = space.allocate_instance(W_CPPInstance, w_pycppclass)
    cppinstance = space.interp_w(W_CPPInstance, w_cppinstance, can_be_None=False)
    cppinstance.__init__(space, cppclass, rawobject, is_ref, python_owns)
    memory_regulator.register(cppinstance)
    return w_cppinstance

def _addressof(space, w_obj):
    try:
        # attempt to extract address from array
        return rffi.cast(rffi.INTPTR_T, converter.get_rawbuffer(space, w_obj))
    except TypeError:
        pass
    # attempt to get address of C++ instance
    return rffi.cast(rffi.INTPTR_T, converter.get_rawobject(space, w_obj))

@unwrap_spec(w_obj=W_Root)
def addressof(space, w_obj):
    """Takes a bound C++ instance or array, returns the raw address."""
    address = _addressof(space, w_obj)
    return space.newlong(address)

@unwrap_spec(owns=bool, cast=bool)
def bind_object(space, w_obj, w_pycppclass, owns=False, cast=False):
    """Takes an address and a bound C++ class proxy, returns a bound instance."""
    try:
        # attempt address from array or C++ instance
        rawobject = rffi.cast(capi.C_OBJECT, _addressof(space, w_obj))
    except Exception:
        # accept integer value as address
        rawobject = rffi.cast(capi.C_OBJECT, space.uint_w(w_obj))
    w_cppclass = space.findattr(w_pycppclass, space.newtext("_cpp_proxy"))
    if not w_cppclass:
        w_cppclass = scope_byname(space, space.text_w(w_pycppclass))
        if not w_cppclass:
            raise oefmt(space.w_TypeError,
                        "no such class: %s", space.text_w(w_pycppclass))
    cppclass = space.interp_w(W_CPPClass, w_cppclass, can_be_None=False)
    return wrap_cppobject(space, rawobject, cppclass, do_cast=cast, python_owns=owns)

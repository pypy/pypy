import sys

import py

from pypy.rlib.nonconst import NonConstant
from pypy.rlib.objectmodel import CDefinedIntSymbolic, keepalive_until_here, specialize
from pypy.rlib.unroll import unrolling_iterable
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.tool.sourcetools import func_with_new_name

DEBUG_ELIDABLE_FUNCTIONS = False


def elidable(func):
    """ Decorate a function as "trace-elidable". This means precisely that:

    (1) the result of the call should not change if the arguments are
        the same (same numbers or same pointers)
    (2) it's fine to remove the call completely if we can guess the result
    according to rule 1
    (3) the function call can be moved around by optimizer,
        but only so it'll be called earlier and not later.

    Most importantly it doesn't mean that an elidable function has no observable
    side effect, but those side effects are idempotent (ie caching).
    If a particular call to this function ends up raising an exception, then it
    is handled like a normal function call (this decorator is ignored).
    """
    if DEBUG_ELIDABLE_FUNCTIONS:
        cache = {}
        oldfunc = func
        def func(*args):
            result = oldfunc(*args)    # if it raises, no caching
            try:
                oldresult = cache.setdefault(args, result)
            except TypeError:
                pass           # unhashable args
            else:
                assert oldresult == result
            return result
    func._elidable_function_ = True
    return func

def purefunction(*args, **kwargs):
    import warnings
    warnings.warn("purefunction is deprecated, use elidable instead", DeprecationWarning)
    return elidable(*args, **kwargs)

def hint(x, **kwds):
    """ Hint for the JIT

    possible arguments are:

    * promote - promote the argument from a variable into a constant
    * promote_string - same, but promote string by *value*
    * access_directly - directly access a virtualizable, as a structure
                        and don't treat it as a virtualizable
    * fresh_virtualizable - means that virtualizable was just allocated.
                            Useful in say Frame.__init__ when we do want
                            to store things directly on it. Has to come with
                            access_directly=True
    """
    return x

@specialize.argtype(0)
def promote(x):
    return hint(x, promote=True)

def promote_string(x):
    return hint(x, promote_string=True)

def dont_look_inside(func):
    """ Make sure the JIT does not trace inside decorated function
    (it becomes a call instead)
    """
    func._jit_look_inside_ = False
    return func

def unroll_safe(func):
    """ JIT can safely unroll loops in this function and this will
    not lead to code explosion
    """
    func._jit_unroll_safe_ = True
    return func

def loop_invariant(func):
    """ Describes a function with no argument that returns an object that
    is always the same in a loop.

    Use it only if you know what you're doing.
    """
    dont_look_inside(func)
    func._jit_loop_invariant_ = True
    return func

def _get_args(func):
    import inspect

    args, varargs, varkw, defaults = inspect.getargspec(func)
    args = ["v%s" % (i, ) for i in range(len(args))]
    assert varargs is None and varkw is None
    assert not defaults
    return args

def elidable_promote(promote_args='all'):
    """ A decorator that promotes all arguments and then calls the supplied
    function
    """
    def decorator(func):
        elidable(func)
        args = _get_args(func)
        argstring = ", ".join(args)
        code = ["def f(%s):\n" % (argstring, )]
        if promote_args != 'all':
            args = [('v%d' % int(i)) for i in promote_args.split(",")]
        for arg in args:
            code.append("    %s = hint(%s, promote=True)\n" % (arg, arg))
        code.append("    return func(%s)\n" % (argstring, ))
        d = {"func": func, "hint": hint}
        exec py.code.Source("\n".join(code)).compile() in d
        result = d["f"]
        result.func_name = func.func_name + "_promote"
        return result
    return decorator

def purefunction_promote(*args, **kwargs):
    import warnings
    warnings.warn("purefunction_promote is deprecated, use elidable_promote instead", DeprecationWarning)
    return elidable_promote(*args, **kwargs)

def look_inside_iff(predicate):
    """
    look inside (including unrolling loops) the target function, if and only if
    predicate(*args) returns True
    """
    def inner(func):
        func = unroll_safe(func)
        # When we return the new function, it might be specialized in some
        # way. We "propogate" this specialization by using
        # specialize:call_location on relevant functions.
        for thing in [func, predicate]:
            thing._annspecialcase_ = "specialize:call_location"

        args = _get_args(func)
        d = {
            "dont_look_inside": dont_look_inside,
            "predicate": predicate,
            "func": func,
            "we_are_jitted": we_are_jitted,
        }
        exec py.code.Source("""
            @dont_look_inside
            def trampoline(%(arguments)s):
                return func(%(arguments)s)
            if hasattr(func, "oopspec"):
                # XXX: This seems like it should be here, but it causes errors.
                # trampoline.oopspec = func.oopspec
                del func.oopspec
            trampoline.__name__ = func.__name__ + "_trampoline"
            trampoline._annspecialcase_ = "specialize:call_location"

            def f(%(arguments)s):
                if not we_are_jitted() or predicate(%(arguments)s):
                    return func(%(arguments)s)
                else:
                    return trampoline(%(arguments)s)
            f.__name__ = func.__name__ + "_look_inside_iff"
        """ % {"arguments": ", ".join(args)}).compile() in d
        return d["f"]
    return inner

def oopspec(spec):
    def decorator(func):
        func.oopspec = spec
        return func
    return decorator

@oopspec("jit.isconstant(value)")
@specialize.ll()
def isconstant(value):
    """
    While tracing, returns whether or not the value is currently known to be
    constant. This is not perfect, values can become constant later. Mostly for
    use with @look_inside_iff.

    This is for advanced usage only.
    """
    return NonConstant(False)

@oopspec("jit.isvirtual(value)")
@specialize.ll()
def isvirtual(value):
    """
    Returns if this value is virtual, while tracing, it's relatively
    conservative and will miss some cases.

    This is for advanced usage only.
    """
    return NonConstant(False)

class Entry(ExtRegistryEntry):
    _about_ = hint

    def compute_result_annotation(self, s_x, **kwds_s):
        from pypy.annotation import model as annmodel
        s_x = annmodel.not_const(s_x)
        access_directly = 's_access_directly' in kwds_s
        fresh_virtualizable = 's_fresh_virtualizable' in kwds_s
        if access_directly or fresh_virtualizable:
            assert access_directly, "lone fresh_virtualizable hint"
            if isinstance(s_x, annmodel.SomeInstance):
                from pypy.objspace.flow.model import Constant
                classdesc = s_x.classdef.classdesc
                virtualizable = classdesc.read_attribute('_virtualizable2_',
                                                         Constant(None)).value
                if virtualizable is not None:
                    flags = s_x.flags.copy()
                    flags['access_directly'] = True
                    if fresh_virtualizable:
                        flags['fresh_virtualizable'] = True
                    s_x = annmodel.SomeInstance(s_x.classdef,
                                                s_x.can_be_None,
                                                flags)
        return s_x

    def specialize_call(self, hop, **kwds_i):
        from pypy.rpython.lltypesystem import lltype
        hints = {}
        for key, index in kwds_i.items():
            s_value = hop.args_s[index]
            if not s_value.is_constant():
                from pypy.rpython.error import TyperError
                raise TyperError("hint %r is not constant" % (key,))
            assert key.startswith('i_')
            hints[key[2:]] = s_value.const
        v = hop.inputarg(hop.args_r[0], arg=0)
        c_hint = hop.inputconst(lltype.Void, hints)
        hop.exception_cannot_occur()
        return hop.genop('hint', [v, c_hint], resulttype=v.concretetype)


def we_are_jitted():
    """ Considered as true during tracing and blackholing,
    so its consquences are reflected into jitted code """
    return False

_we_are_jitted = CDefinedIntSymbolic('0 /* we are not jitted here */',
                                     default=0)

class Entry(ExtRegistryEntry):
    _about_ = we_are_jitted

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        hop.exception_cannot_occur()
        return hop.inputconst(lltype.Signed, _we_are_jitted)


def current_trace_length():
    """During JIT tracing, returns the current trace length (as a constant).
    If not tracing, returns -1."""
    if NonConstant(False):
        return 73
    return -1
current_trace_length.oopspec = 'jit.current_trace_length()'

def jit_debug(string, arg1=-sys.maxint-1, arg2=-sys.maxint-1,
                      arg3=-sys.maxint-1, arg4=-sys.maxint-1):
    """When JITted, cause an extra operation JIT_DEBUG to appear in
    the graphs.  Should not be left after debugging."""
    keepalive_until_here(string) # otherwise the whole function call is removed
jit_debug.oopspec = 'jit.debug(string, arg1, arg2, arg3, arg4)'

def assert_green(value):
    """Very strong assert: checks that 'value' is a green
    (a JIT compile-time constant)."""
    keepalive_until_here(value)
assert_green._annspecialcase_ = 'specialize:argtype(0)'
assert_green.oopspec = 'jit.assert_green(value)'

class AssertGreenFailed(Exception):
    pass


# ____________________________________________________________
# VRefs

def virtual_ref(x):
    """Creates a 'vref' object that contains a reference to 'x'.  Calls
    to virtual_ref/virtual_ref_finish must be properly nested.  The idea
    is that the object 'x' is supposed to be JITted as a virtual between
    the calls to virtual_ref and virtual_ref_finish, but the 'vref'
    object can escape at any point in time.  If at runtime it is
    dereferenced (by the call syntax 'vref()'), it returns 'x', which is
    then forced."""
    return DirectJitVRef(x)
virtual_ref.oopspec = 'virtual_ref(x)'

def virtual_ref_finish(vref, x):
    """See docstring in virtual_ref(x)"""
    keepalive_until_here(x)   # otherwise the whole function call is removed
    _virtual_ref_finish(vref, x)
virtual_ref_finish.oopspec = 'virtual_ref_finish(x)'

def non_virtual_ref(x):
    """Creates a 'vref' that just returns x when called; nothing more special.
    Used for None or for frames outside JIT scope."""
    return DirectVRef(x)

class InvalidVirtualRef(Exception):
    """
    Raised if we try to call a non-forced virtualref after the call to
    virtual_ref_finish
    """

# ---------- implementation-specific ----------

class DirectVRef(object):
    def __init__(self, x):
        self._x = x
        self._state = 'non-forced'

    def __call__(self):
        if self._state == 'non-forced':
            self._state = 'forced'
        elif self._state == 'invalid':
            raise InvalidVirtualRef
        return self._x

    @property
    def virtual(self):
        """A property that is True if the vref contains a virtual that would
        be forced by the '()' operator."""
        return self._state == 'non-forced'

    def _finish(self):
        if self._state == 'non-forced':
            self._state = 'invalid'

class DirectJitVRef(DirectVRef):
    def __init__(self, x):
        assert x is not None, "virtual_ref(None) is not allowed"
        DirectVRef.__init__(self, x)

def _virtual_ref_finish(vref, x):
    assert vref._x is x, "Invalid call to virtual_ref_finish"
    vref._finish()

class Entry(ExtRegistryEntry):
    _about_ = (non_virtual_ref, DirectJitVRef)

    def compute_result_annotation(self, s_obj):
        from pypy.rlib import _jit_vref
        return _jit_vref.SomeVRef(s_obj)

    def specialize_call(self, hop):
        return hop.r_result.specialize_call(hop)

class Entry(ExtRegistryEntry):
    _type_ = DirectVRef

    def compute_annotation(self):
        from pypy.rlib import _jit_vref
        assert isinstance(self.instance, DirectVRef)
        s_obj = self.bookkeeper.immutablevalue(self.instance())
        return _jit_vref.SomeVRef(s_obj)

class Entry(ExtRegistryEntry):
    _about_ = _virtual_ref_finish

    def compute_result_annotation(self, s_vref, s_obj):
        pass

    def specialize_call(self, hop):
        pass

vref_None = non_virtual_ref(None)

# ____________________________________________________________
# User interface for the warmspot JIT policy

class JitHintError(Exception):
    """Inconsistency in the JIT hints."""

PARAMETERS = {'threshold': 1039, # just above 1024, prime
              'function_threshold': 1619, # slightly more than one above, also prime
              'trace_eagerness': 200,
              'trace_limit': 6000,
              'inlining': 1,
              'loop_longevity': 1000,
              'retrace_limit': 5,
              'max_retrace_guards': 15,
              'enable_opts': 'all',
              }
unroll_parameters = unrolling_iterable(PARAMETERS.items())
DEFAULT = object()

# ____________________________________________________________

class JitDriver(object):
    """Base class to declare fine-grained user control on the JIT.  So
    far, there must be a singleton instance of JitDriver.  This style
    will allow us (later) to support a single RPython program with
    several independent JITting interpreters in it.
    """

    active = True          # if set to False, this JitDriver is ignored
    virtualizables = []

    def __init__(self, greens=None, reds=None, virtualizables=None,
                 get_jitcell_at=None, set_jitcell_at=None,
                 get_printable_location=None, confirm_enter_jit=None,
                 can_never_inline=None, should_unroll_one_iteration=None):
        if greens is not None:
            self.greens = greens
        if reds is not None:
            self.reds = reds
        if not hasattr(self, 'greens') or not hasattr(self, 'reds'):
            raise AttributeError("no 'greens' or 'reds' supplied")
        if virtualizables is not None:
            self.virtualizables = virtualizables
        for v in self.virtualizables:
            assert v in self.reds
        self._alllivevars = dict.fromkeys(
            [name for name in self.greens + self.reds if '.' not in name])
        self._make_extregistryentries()
        self.get_jitcell_at = get_jitcell_at
        self.set_jitcell_at = set_jitcell_at
        self.get_printable_location = get_printable_location
        self.confirm_enter_jit = confirm_enter_jit
        self.can_never_inline = can_never_inline
        self.should_unroll_one_iteration = should_unroll_one_iteration

    def _freeze_(self):
        return True

    def jit_merge_point(_self, **livevars):
        # special-cased by ExtRegistryEntry
        assert dict.fromkeys(livevars) == _self._alllivevars

    def can_enter_jit(_self, **livevars):
        # special-cased by ExtRegistryEntry
        assert dict.fromkeys(livevars) == _self._alllivevars

    def loop_header(self):
        # special-cased by ExtRegistryEntry
        pass

    def on_compile(self, logger, looptoken, operations, type, *greenargs):
        """ A hook called when loop is compiled. Overwrite
        for your own jitdriver if you want to do something special, like
        call applevel code
        """

    def on_compile_bridge(self, logger, orig_looptoken, operations, n):
        """ A hook called when a bridge is compiled. Overwrite
        for your own jitdriver if you want to do something special
        """

    # note: if you overwrite this functions with the above signature it'll
    #       work, but the *greenargs is different for each jitdriver, so we
    #       can't share the same methods
    del on_compile
    del on_compile_bridge

    def _make_extregistryentries(self):
        # workaround: we cannot declare ExtRegistryEntries for functions
        # used as methods of a frozen object, but we can attach the
        # bound methods back to 'self' and make ExtRegistryEntries
        # specifically for them.
        self.jit_merge_point = self.jit_merge_point
        self.can_enter_jit = self.can_enter_jit
        self.loop_header = self.loop_header
        class Entry(ExtEnterLeaveMarker):
            _about_ = (self.jit_merge_point, self.can_enter_jit)

        class Entry(ExtLoopHeader):
            _about_ = self.loop_header

def _set_param(driver, name, value):
    # special-cased by ExtRegistryEntry
    # (internal, must receive a constant 'name')
    # if value is DEFAULT, sets the default value.
    assert name in PARAMETERS

@specialize.arg(0, 1)
def set_param(driver, name, value):
    """Set one of the tunable JIT parameter. Driver can be None, then all
    drivers have this set """
    _set_param(driver, name, value)

@specialize.arg(0, 1)
def set_param_to_default(driver, name):
    """Reset one of the tunable JIT parameters to its default value."""
    _set_param(driver, name, DEFAULT)

def set_user_param(driver, text):
    """Set the tunable JIT parameters from a user-supplied string
    following the format 'param=value,param=value', or 'off' to
    disable the JIT.  For programmatic setting of parameters, use
    directly JitDriver.set_param().
    """
    if text == 'off':
        set_param(driver, 'threshold', -1)
        set_param(driver, 'function_threshold', -1)
        return
    if text == 'default':
        for name1, _ in unroll_parameters:
            set_param_to_default(driver, name1)
        return
    for s in text.split(','):
        s = s.strip(' ')
        parts = s.split('=')
        if len(parts) != 2:
            raise ValueError
        name = parts[0]
        value = parts[1]
        if name == 'enable_opts':
            set_param(driver, 'enable_opts', value)
        else:
            for name1, _ in unroll_parameters:
                if name1 == name and name1 != 'enable_opts':
                    try:
                        set_param(driver, name1, int(value))
                    except ValueError:
                        raise
set_user_param._annspecialcase_ = 'specialize:arg(0)'


# ____________________________________________________________
#
# Annotation and rtyping of some of the JitDriver methods

class BaseJitCell(object):
    __slots__ = ()


class ExtEnterLeaveMarker(ExtRegistryEntry):
    # Replace a call to myjitdriver.jit_merge_point(**livevars)
    # with an operation jit_marker('jit_merge_point', myjitdriver, livevars...)
    # Also works with can_enter_jit.

    def compute_result_annotation(self, **kwds_s):
        from pypy.annotation import model as annmodel

        if self.instance.__name__ == 'jit_merge_point':
            self.annotate_hooks(**kwds_s)

        driver = self.instance.im_self
        keys = kwds_s.keys()
        keys.sort()
        expected = ['s_' + name for name in driver.greens + driver.reds
                                if '.' not in name]
        expected.sort()
        if keys != expected:
            raise JitHintError("%s expects the following keyword "
                               "arguments: %s" % (self.instance,
                                                  expected))

        try:
            cache = self.bookkeeper._jit_annotation_cache[driver]
        except AttributeError:
            cache = {}
            self.bookkeeper._jit_annotation_cache = {driver: cache}
        except KeyError:
            cache = {}
            self.bookkeeper._jit_annotation_cache[driver] = cache
        for key, s_value in kwds_s.items():
            s_previous = cache.get(key, annmodel.s_ImpossibleValue)
            s_value = annmodel.unionof(s_previous, s_value)
            if annmodel.isdegenerated(s_value):
                raise JitHintError("mixing incompatible types in argument %s"
                                   " of jit_merge_point/can_enter_jit" %
                                   key[2:])
            cache[key] = s_value

        # add the attribute _dont_reach_me_in_del_ (see pypy.rpython.rclass)
        try:
            graph = self.bookkeeper.position_key[0]
            graph.func._dont_reach_me_in_del_ = True
        except (TypeError, AttributeError):
            pass

        return annmodel.s_None

    def annotate_hooks(self, **kwds_s):
        driver = self.instance.im_self
        s_jitcell = self.bookkeeper.valueoftype(BaseJitCell)
        h = self.annotate_hook
        h(driver.get_jitcell_at, driver.greens, **kwds_s)
        h(driver.set_jitcell_at, driver.greens, [s_jitcell], **kwds_s)
        h(driver.get_printable_location, driver.greens, **kwds_s)

    def annotate_hook(self, func, variables, args_s=[], **kwds_s):
        if func is None:
            return
        bk = self.bookkeeper
        s_func = bk.immutablevalue(func)
        uniquekey = 'jitdriver.%s' % func.func_name
        args_s = args_s[:]
        for name in variables:
            if '.' not in name:
                s_arg = kwds_s['s_' + name]
            else:
                objname, fieldname = name.split('.')
                s_instance = kwds_s['s_' + objname]
                attrdef = s_instance.classdef.find_attribute(fieldname)
                position = self.bookkeeper.position_key
                attrdef.read_locations[position] = True
                s_arg = attrdef.getvalue()
                assert s_arg is not None
            args_s.append(s_arg)
        bk.emulate_pbc_call(uniquekey, s_func, args_s)

    def get_getfield_op(self, rtyper):
        if rtyper.type_system.name == 'ootypesystem':
            return 'oogetfield'
        else:
            return 'getfield'

    def specialize_call(self, hop, **kwds_i):
        # XXX to be complete, this could also check that the concretetype
        # of the variables are the same for each of the calls.
        from pypy.rpython.error import TyperError
        from pypy.rpython.lltypesystem import lltype
        driver = self.instance.im_self
        greens_v = []
        reds_v = []
        for name in driver.greens:
            if '.' not in name:
                i = kwds_i['i_' + name]
                r_green = hop.args_r[i]
                v_green = hop.inputarg(r_green, arg=i)
            else:
                objname, fieldname = name.split('.')   # see test_green_field
                assert objname in driver.reds
                i = kwds_i['i_' + objname]
                s_red = hop.args_s[i]
                r_red = hop.args_r[i]
                while True:
                    try:
                        mangled_name, r_field = r_red._get_field(fieldname)
                        break
                    except KeyError:
                        pass
                    assert r_red.rbase is not None, (
                        "field %r not found in %r" % (name,
                                                      r_red.lowleveltype.TO))
                    r_red = r_red.rbase
                if hop.rtyper.type_system.name == 'ootypesystem':
                    GTYPE = r_red.lowleveltype
                else:
                    GTYPE = r_red.lowleveltype.TO
                assert GTYPE._immutable_field(mangled_name), (
                    "field %r must be declared as immutable" % name)
                if not hasattr(driver, 'll_greenfields'):
                    driver.ll_greenfields = {}
                driver.ll_greenfields[name] = GTYPE, mangled_name
                #
                v_red = hop.inputarg(r_red, arg=i)
                c_llname = hop.inputconst(lltype.Void, mangled_name)
                getfield_op = self.get_getfield_op(hop.rtyper)
                v_green = hop.genop(getfield_op, [v_red, c_llname],
                                    resulttype=r_field)
                s_green = s_red.classdef.about_attribute(fieldname)
                assert s_green is not None
                hop.rtyper.annotator.setbinding(v_green, s_green)
            greens_v.append(v_green)
        for name in driver.reds:
            i = kwds_i['i_' + name]
            r_red = hop.args_r[i]
            v_red = hop.inputarg(r_red, arg=i)
            reds_v.append(v_red)
        hop.exception_cannot_occur()
        vlist = [hop.inputconst(lltype.Void, self.instance.__name__),
                 hop.inputconst(lltype.Void, driver)]
        vlist.extend(greens_v)
        vlist.extend(reds_v)
        return hop.genop('jit_marker', vlist,
                         resulttype=lltype.Void)

class ExtLoopHeader(ExtRegistryEntry):
    # Replace a call to myjitdriver.loop_header()
    # with an operation jit_marker('loop_header', myjitdriver).

    def compute_result_annotation(self, **kwds_s):
        from pypy.annotation import model as annmodel
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        driver = self.instance.im_self
        hop.exception_cannot_occur()
        vlist = [hop.inputconst(lltype.Void, 'loop_header'),
                 hop.inputconst(lltype.Void, driver)]
        return hop.genop('jit_marker', vlist,
                         resulttype=lltype.Void)

class ExtSetParam(ExtRegistryEntry):
    _about_ = _set_param

    def compute_result_annotation(self, s_driver, s_name, s_value):
        from pypy.annotation import model as annmodel
        assert s_name.is_constant()
        if not self.bookkeeper.immutablevalue(DEFAULT).contains(s_value):
            if s_name.const == 'enable_opts':
                assert annmodel.SomeString(can_be_None=True).contains(s_value)
            else:
                assert annmodel.SomeInteger().contains(s_value)
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.lltypesystem.rstr import string_repr
        from pypy.objspace.flow.model import Constant

        hop.exception_cannot_occur()
        driver = hop.inputarg(lltype.Void, arg=0)
        name = hop.args_s[1].const
        if name == 'enable_opts':
            repr = string_repr
        else:
            repr = lltype.Signed
        if (isinstance(hop.args_v[2], Constant) and
            hop.args_v[2].value is DEFAULT):
            value = PARAMETERS[name]
            v_value = hop.inputconst(repr, value)
        else:
            v_value = hop.inputarg(repr, arg=2)
        vlist = [hop.inputconst(lltype.Void, "set_param"),
                 driver,
                 hop.inputconst(lltype.Void, name),
                 v_value]
        return hop.genop('jit_marker', vlist,
                         resulttype=lltype.Void)


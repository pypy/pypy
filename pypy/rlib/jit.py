from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib.unroll import unrolling_iterable

def purefunction(func):
    func._pure_function_ = True
    return func

def hint(x, **kwds):
    return x

class Entry(ExtRegistryEntry):
    _about_ = hint

    def compute_result_annotation(self, s_x, **kwds_s):
        from pypy.annotation import model as annmodel
        s_x = annmodel.not_const(s_x)
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
    return False
# timeshifts to True

_we_are_jitted = CDefinedIntSymbolic('0 /* we are not jitted here */',
                                     default=0)

class Entry(ExtRegistryEntry):
    _about_ = we_are_jitted

    def compute_result_annotation(self):
        from pypy.annotation import model as annmodel
        return annmodel.SomeInteger(nonneg=True)

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        return hop.inputconst(lltype.Signed, _we_are_jitted)

def _is_early_constant(x):
    return False

class Entry(ExtRegistryEntry):
    _about_ = _is_early_constant

    def compute_result_annotation(self, s_value):
        from pypy.annotation import model as annmodel
        s = annmodel.SomeBool()
        if s_value.is_constant():
            s.const = True
        return s

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        if hop.s_result.is_constant():
            assert hop.s_result.const
            return hop.inputconst(lltype.Bool, True)
        v, = hop.inputargs(hop.args_r[0])
        return hop.genop('is_early_constant', [v], resulttype=lltype.Bool)

# ____________________________________________________________
# User interface for the hotpath JIT policy

class JitHintError(Exception):
    """Inconsistency in the JIT hints."""

PARAMETERS = {'threshold': 1000,
              'trace_eagerness': 200,
              'hash_bits': 14,
              }
unroll_parameters = unrolling_iterable(PARAMETERS.keys())

class JitDriver:    
    """Base class to declare fine-grained user control on the JIT.  So
    far, there must be a singleton instance of JitDriver.  This style
    will allow us (later) to support a single RPython program with
    several independent JITting interpreters in it.
    """

    virtualizables = []
    
    def __init__(self, greens=None, reds=None, virtualizables=None):
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
        self._alllivevars = dict.fromkeys(self.greens + self.reds)
        self._params = PARAMETERS.copy()
        if hasattr(self, 'on_enter_jit'):
            self._make_on_enter_jit_wrappers()
        self._make_extregistryentries()

    def _freeze_(self):
        return True

    def jit_merge_point(self, **livevars):
        # special-cased by ExtRegistryEntry
        assert dict.fromkeys(livevars) == self._alllivevars

    def can_enter_jit(self, **livevars):
        # special-cased by ExtRegistryEntry
        assert dict.fromkeys(livevars) == self._alllivevars

    def _set_param(self, name, value):
        # special-cased by ExtRegistryEntry
        # (internal, must receive a constant 'name')
        assert name in PARAMETERS
        self._params[name] = value

    def set_param(self, name, value):
        """Set one of the tunable JIT parameter."""
        for name1 in unroll_parameters:
            if name1 == name:
                self._set_param(name1, value)
                return
        raise ValueError("no such parameter")
    set_param._annspecialcase_ = 'specialize:arg(0)'

    def set_user_param(self, text):
        """Set the tunable JIT parameters from a user-supplied string
        following the format 'param=value,param=value'.  For programmatic
        setting of parameters, use directly JitDriver.set_param().
        """
        for s in text.split(','):
            s = s.strip(' ')
            parts = s.split('=')
            if len(parts) != 2:
                raise ValueError
            try:
                value = int(parts[1])
            except ValueError:
                raise    # re-raise the ValueError (annotator hint)
            name = parts[0]
            self.set_param(name, value)
    set_user_param._annspecialcase_ = 'specialize:arg(0)'

    def compute_invariants(self, reds, *greens):
        """This can compute a value or tuple that is passed as a green
        argument 'invariants' to on_enter_jit().  It should in theory
        only depend on the 'greens', but in practice it can peek at the
        reds currently stored in 'self'.  This allows the extraction in
        an interpreter-specific way of whatever red information that
        ultimately depends on the greens only.
        """
    compute_invariants._annspecialcase_ = 'specialize:arg(0)'

    def _emulate_method_calls(self, bk, livevars_s):
        # annotate "self.on_enter_jit()" if it is defined.
        # self.on_enter_jit(invariants, reds, *greenvars) is called with a
        # copy of the value of the red variables in 'reds'.  The red variables
        # can be modified in order to give hints to the JIT about the
        # redboxes.
        from pypy.annotation import model as annmodel
        if hasattr(self, 'on_enter_jit'):
            args_s = []
            for name in self.greens + self.reds:
                args_s.append(livevars_s['s_' + name])

            key = "rlib.jit.JitDriver._on_enter_jit"
            s_func = bk.immutablevalue(self._on_enter_jit_wrapper)
            s_result = bk.emulate_pbc_call(key, s_func, args_s)
            assert annmodel.s_None.contains(s_result)

            key = "rlib.jit.JitDriver._compute_invariants"
            s_func = bk.immutablevalue(self._compute_invariants_wrapper)
            bk.emulate_pbc_call(key, s_func, args_s)

    def _make_on_enter_jit_wrappers(self):
        # build some unrolling wrappers around on_enter_jit() and
        # compute_invariants() which takes all green and red arguments
        # and puts the red ones in a fresh instance of the
        # RedVarsHolder.  This logic is here in jit.py because it needs
        # to be annotated and rtyped as a high-level function.

        num_green_args = len(self.greens)
        unroll_reds = unrolling_iterable(self.reds)

        class RedVarsHolder:
            def __init__(self, *redargs):
                i = 0
                for name in unroll_reds:
                    setattr(self, name, redargs[i])
                    i += 1

        self._RedVarsHolder = RedVarsHolder

        def _on_enter_jit_wrapper(*allargs):
            # This is what theoretically occurs when we are entering the
            # JIT.  In truth, compute_invariants() is called only once
            # per set of greens and its result is cached.  On the other
            # hand, on_enter_jit() is compiled into machine code and so
            # it runs every time the execution jumps from the regular
            # interpreter to the machine code.  Also note that changes
            # to the attribute of RedVarsHolder are reflected back in
            # the caller.
            reds = RedVarsHolder(*allargs[num_green_args:])
            greens = allargs[:num_green_args]
            invariants = self.compute_invariants(reds, *greens)
            return self.on_enter_jit(invariants, reds, *greens)
        self._on_enter_jit_wrapper = _on_enter_jit_wrapper

        def _compute_invariants_wrapper(*allargs):
            reds = RedVarsHolder(*allargs[num_green_args:])
            greens = allargs[:num_green_args]
            return self.compute_invariants(reds, *greens)
        self._compute_invariants_wrapper = _compute_invariants_wrapper

    def _make_extregistryentries(self):
        # workaround: we cannot declare ExtRegistryEntries for functions
        # used as methods of a frozen object, but we can attach the
        # bound methods back to 'self' and make ExtRegistryEntries
        # specifically for them.
        self.jit_merge_point = self.jit_merge_point
        self.can_enter_jit = self.can_enter_jit
        self._set_param = self._set_param

        class Entry(ExtEnterLeaveMarker):
            _about_ = (self.jit_merge_point, self.can_enter_jit)

        class Entry(ExtSetParam):
            _about_ = self._set_param

# ____________________________________________________________
#
# Annotation and rtyping of some of the JitDriver methods

class ExtEnterLeaveMarker(ExtRegistryEntry):
    # Replace a call to myjitdriver.jit_merge_point(**livevars)
    # with an operation jit_marker('jit_merge_point', myjitdriver, livevars...)
    # Also works with can_enter_jit.

    def compute_result_annotation(self, **kwds_s):
        from pypy.annotation import model as annmodel
        driver = self.instance.im_self
        keys = kwds_s.keys()
        keys.sort()
        expected = ['s_' + name for name in driver.greens + driver.reds]
        expected.sort()
        if keys != expected:
            raise JitHintError("%s expects the following keyword "
                               "arguments: %s" % (self.instance,
                                                  expected))
        driver._emulate_method_calls(self.bookkeeper, kwds_s)
        for name in driver.greens:
            s_green_key = kwds_s['s_' + name]
            s_green_key.hash()      # force the hash cache to appear
        return annmodel.s_None

    def specialize_call(self, hop, **kwds_i):
        # XXX to be complete, this could also check that the concretetype
        # of the variables are the same for each of the calls.
        from pypy.rpython.error import TyperError
        from pypy.rpython.lltypesystem import lltype
        driver = self.instance.im_self
        greens_v = []
        reds_v = []
        for name in driver.greens:
            i = kwds_i['i_' + name]
            r_green = hop.args_r[i]
            v_green = hop.inputarg(r_green, arg=i)
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

class ExtSetParam(ExtRegistryEntry):

    def compute_result_annotation(self, s_name, s_value):
        from pypy.annotation import model as annmodel
        assert s_name.is_constant()
        assert annmodel.SomeInteger().contains(s_value)
        return annmodel.s_None

    def specialize_call(self, hop):
        from pypy.rpython.lltypesystem import lltype
        hop.exception_cannot_occur()
        driver = self.instance.im_self
        name = hop.args_s[0].const
        v_value = hop.inputarg(lltype.Signed, arg=1)
        vlist = [hop.inputconst(lltype.Void, "set_param"),
                 hop.inputconst(lltype.Void, driver),
                 hop.inputconst(lltype.Void, name),
                 v_value]
        return hop.genop('jit_marker', vlist,
                         resulttype=lltype.Void)

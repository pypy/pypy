from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib.unroll import unrolling_iterable

def purefunction(func):
    func._pure_function_ = True
    return func

def hint(x, **kwds):
    return x

def dont_look_inside(func):
    func._look_inside_me_ = False
    return func

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

def _no_printable_location(*greenargs):
    return '(no jitdriver.get_printable_location!)'

# ____________________________________________________________

class JitDriver:    
    """Base class to declare fine-grained user control on the JIT.  So
    far, there must be a singleton instance of JitDriver.  This style
    will allow us (later) to support a single RPython program with
    several independent JITting interpreters in it.
    """

    virtualizables = []
    
    def __init__(self, greens=None, reds=None, virtualizables=None,
                 get_printable_location=_no_printable_location,
                 can_inline=None):
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
        self._make_extregistryentries()
        self.get_printable_location = get_printable_location
        self.can_inline = can_inline

    def _freeze_(self):
        return True

    def jit_merge_point(_self, **livevars):
        # special-cased by ExtRegistryEntry
        assert dict.fromkeys(livevars) == _self._alllivevars

    def can_enter_jit(_self, **livevars):
        # special-cased by ExtRegistryEntry
        assert dict.fromkeys(livevars) == _self._alllivevars

    def _set_param(self, name, value):
        # special-cased by ExtRegistryEntry
        # (internal, must receive a constant 'name')
        assert name in PARAMETERS

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

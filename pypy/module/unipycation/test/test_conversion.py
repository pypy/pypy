import pypy.module.unipycation.conversion as conv
import pypy.module.unipycation.util as util
import pypy.module.unipycation.objects as objects
from pypy.interpreter.error import OperationError
import prolog.interpreter.signature as psig

import prolog.interpreter.term as pterm
import pytest

class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('unipycation',))

    # -------------------------------------
    # Test conversion from Python to Prolog
    # -------------------------------------

    def test_p_number_of_w_int(self):
        w_int = self.space.newint(666)
        p_number = conv.p_number_of_w_int(self.space, w_int)

        unwrap1 = self.space.int_w(w_int)
        unwrap2 = p_number.num

        assert unwrap1 == unwrap2

    def test_p_float_of_w_float(self):
        w_float = self.space.newfloat(678.666)
        p_float = conv.p_float_of_w_float(self.space, w_float)

        unwrap1 = self.space.float_w(w_float)
        unwrap2 = p_float.floatval

        assert unwrap1 == unwrap2

    # corner case: test -0.0 converts properly
    def test_p_float_of_w_float_2(self):
        w_float = self.space.newfloat(-0.0)
        p_float = conv.p_float_of_w_float(self.space, w_float)

        unwrap1 = self.space.float_w(w_float)
        unwrap2 = p_float.floatval

        assert unwrap1 == unwrap2

    def test_p_bigint_of_w_long(self):
        w_long = self.space.newlong_from_rbigint(2**65 + 42)
        p_bigint = conv.p_bigint_of_w_long(self.space, w_long)

        unwrap1 = self.space.bigint_w(w_long)
        unwrap2 = p_bigint.value

        assert unwrap1 == unwrap2

    def test_p_atom_of_w_str(self):
        w_str = self.space.wrap("humppa")
        p_atom = conv.p_atom_of_w_str(self.space, w_str)

        unwrap1 = self.space.str_w(w_str)
        unwrap2 = p_atom._signature.name

        assert unwrap1 == unwrap2

    # -------------------------------------
    # Test conversion from Prolog to Python
    # -------------------------------------

    def test_w_int_of_p_number(self):
        p_number = pterm.Number(666)
        w_int = conv.w_int_of_p_number(self.space, p_number)

        unwrap1 = p_number.num
        unwrap2 = self.space.int_w(w_int)

        assert unwrap1 == unwrap2

    def test_w_float_of_p_float(self):
        p_float = pterm.Float(666.1234)
        w_float = conv.w_float_of_p_float(self.space, p_float)

        unwrap1 = p_float.floatval
        unwrap2 = self.space.float_w(w_float)

        assert unwrap1 == unwrap2

    def test_w_long_of_p_bigint(self):
        p_bigint = pterm.BigInt(2**64 * 4 + 3)
        w_long = conv.w_long_of_p_bigint(self.space, p_bigint)

        unwrap1 = p_bigint.value
        unwrap2 = self.space.bigint_w(w_long)

        assert unwrap1 == unwrap2

    def test_w_str_of_p_atom(self):
        p_atom = pterm.Atom("Smeg")
        w_str = conv.w_str_of_p_atom(self.space, p_atom)

        unwrap1 = p_atom._signature.name
        unwrap2 = self.space.str_w(w_str)

        assert unwrap1 == unwrap2

    def test_w_term_of_p_callable(self):
        space = self.space

        p_sig = psig.Signature.getsignature("someterm", 3)
        p_atoms = [ pterm.Atom(x) for x in ["x", "y", "z"] ]
        p_callable = pterm.Term("someterm",  p_atoms, p_sig)

        w_term = conv.w_term_of_p_callable(space, p_callable)

        term_len = space.int_w(w_term.descr_len(space))
        unwrap = space.listview_str(w_term.prop_getargs(space))
        unwrap2 = [ space.str_w(w_term.descr_getitem(space, space.newint(x))) \
                for x in range(term_len) ]

        assert isinstance(w_term, objects.W_Term) and \
                space.is_true(space.eq(w_term.descr_len(space), space.wrap(3))) and \
                space.is_true(space.eq(w_term.prop_getname(space), space.wrap("someterm"))) and \
                unwrap == ["x", "y", "z"] == unwrap2

    # --------------------------
    # Test high level converions
    # --------------------------

    def test_w_of_p_atom(self):
        p_atom = pterm.Atom("Wibble")
        w_str = conv.w_of_p(self.space, p_atom)

        assert self.space.str_w(w_str) == "Wibble"

    def test_w_of_p_int(self):
        p_num = pterm.Number(666)
        w_int = conv.w_of_p(self.space, p_num)

        assert self.space.int_w(w_int) == 666

    def test_w_of_p_long(self):
        p_bigint = pterm.BigInt(2**64 * 7 + 3)
        w_long = conv.w_of_p(self.space, p_bigint)

        assert self.space.bigint_w(w_long) == 2 ** 64 * 7 + 3

    def test_w_of_p_float(self):
        p_float = pterm.Float(3.1415)
        w_float = conv.w_of_p(self.space, p_float)

        assert self.space.float_w(w_float) == 3.1415

    def test_w_of_p_fails(self):
        p_val = 666            # clearly not a prolog type

        # XXX
        #info = py.test.raises(OperationError, conv.w_of_p, self.space, p_val)
        #info.exc should exist now
        try:
            w_boom = conv.w_of_p(self.space, p_val)
        except OperationError as e:
            w_ConversionError = util.get_from_module(self.space, "unipycation", "ConversionError")
            assert e.w_type == w_ConversionError
            return

        assert False

    def test_p_of_w(self):
        w_str = self.space.wrap("Flibble")
        p_atom = conv.p_of_w(self.space, w_str)

        assert p_atom._signature.name == "Flibble"

    # XXX reincarnate this, but pass down a pypy type that we can't convert.
    #def test_p_of_w_fails(self):
    #    w_str = pterm.Atom("Ohno!") # not a pypy type, should fail
    #
    #    try:
    #        p_boom = conv.p_of_w(self.space, w_str)
    #    except OperationError as e:
    #        w_ConversionError = util.get_from_module(self.space, "unipycation", "ConversionError")
    #        assert e.w_type == w_ConversionError
    #        return
    #
    #    assert False

# Check that aggregate structures are nested properly.
# Easier to test at the app-level
class AppTestConversion(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_list(self):
        import unipycation

        e = unipycation.Engine("f([w, x]).")
        x = e.query_single("f(X).")["X"]

        assert x.name == "."
        assert x.args[0] == "w"
        assert x.args[1].name == "."
        assert x.args[1].args[0] == "x"
        assert x.args[1].args[1] == "[]"

    def test_aggregate_struct(self):
        import unipycation

        e = unipycation.Engine("f(g(a, b, c, d)).")
        x = e.query_single("f(X).")["X"]

        assert len(x) == 4 and \
                x[0] == "a" and \
                x[1] == "b" and \
                x[2] == "c" and \
                x[3] == "d"

    def test_term_builder(self):
        import unipycation

        t = unipycation.Term("myterm", ["e1", "e2", "e3"])
        elems = [ t[x] for x in range(len(t)) ]

        assert elems == ["e1", "e2", "e3" ]


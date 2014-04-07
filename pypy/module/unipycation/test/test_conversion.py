import pypy.module.unipycation.conversion as conv
import pypy.module.unipycation.util as util
import pypy.module.unipycation.objects as objects
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError
import prolog.interpreter.signature as psig

import prolog.interpreter.term as pterm
import pypy.module.unipycation.app_error as err
import pytest

class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('unipycation',))

    # -------------------------------------
    # Test conversion from Python to Prolog
    # -------------------------------------

    def test_p_var_of_w_var(self):
        w_var = objects.var_new__(self.space, W_Root, [])
        var = conv.p_var_of_w_var(self.space, w_var)

        assert type(var) == pterm.BindingVar

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

    def test_p_term_of_w_term(self):
        # f(1,2,3).
        p_sig = psig.Signature.getsignature("f", 3)
        p_atoms = [ pterm.Number(x) for x in [1, 2, 3] ]
        p_callable = pterm.Callable.build("f",  p_atoms, p_sig)

        w_term = objects.W_CoreTerm(self.space, p_callable)
        p_term = conv.p_term_of_w_term(self.space, w_term)
        assert p_term is p_callable

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
        unwrap = space.listview_bytes(w_term.prop_getargs(space))
        unwrap2 = [ space.str_w(w_term.descr_getitem(space, space.newint(x))) \
                for x in range(term_len) ]

        assert isinstance(w_term, objects.W_CoreTerm) and \
                space.is_true(space.eq(w_term.descr_len(space), space.wrap(3))) and \
                space.is_true(space.eq(w_term.prop_getname(space), space.wrap("someterm"))) and \
                unwrap == ["x", "y", "z"] == unwrap2

    # ---------------------------
    # Test high level conversions
    # ---------------------------

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

    def test_w_of_p_var_bound_to_number(self):
        p_number = pterm.BindingVar()
        p_number.binding = pterm.Number(666)
        w_int = conv.w_of_p(self.space, p_number)

        unwrap = self.space.int_w(w_int)

        assert unwrap == 666

    def test_w_of_p_fails(self):
        p_val = 666            # clearly not a prolog type

        info = pytest.raises(OperationError, conv.w_of_p, self.space, p_val)
        exn_str = info.exconly()
        assert "ConversionError" in exn_str

    def test_p_of_w(self):
        w_str = self.space.wrap("Flibble")
        p_atom = conv.p_of_w(self.space, w_str)

        assert p_atom._signature.name == "Flibble"

    # XXX some cases missing for p_of_w

    def test_p_of_w_var(self):
        w_var = objects.var_new__(self.space, W_Root, [])
        var = conv.p_of_w(self.space, w_var)
        assert type(var) == pterm.BindingVar

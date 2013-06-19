import pypy.module.unipycation.conversion as conv
import pypy.module.unipycation.util as util
from pypy.interpreter.error import OperationError

import prolog.interpreter.term as pterm
import pytest

class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('unipycation',))

    # -------------------------------------
    # Test conversion from Python to Prolog
    # -------------------------------------

    def test_p_int_of_w_int(self):
        w_int = self.space.newint(666)
        p_int = conv.p_int_of_w_int(self.space, w_int)

        unwrap1 = self.space.int_w(w_int)
        unwrap2 = p_int.num

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

    def test_w_int_of_p_int(self):
        p_int = pterm.Number(666)
        w_int = conv.w_int_of_p_int(self.space, p_int)

        unwrap1 = p_int.num
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

    # --------------------------
    # Test high level converions
    # --------------------------

    def test_w_of_p(self):
        p_atom = pterm.Atom("Wibble")
        w_str = conv.w_of_p(self.space, p_atom)

        assert self.space.str_w(w_str) == "Wibble"

    def test_w_of_p_fails(self):
        p_val = 666            # clearly not a prolog type

        try:
            w_boom = conv.w_of_p(self.space, p_val)
        except OperationError as e:
            w_ConversionError = util.get_from_module(self.space, "unipycation", "ConversionError")
            assert e.w_type == w_ConversionError
            return

        assert False

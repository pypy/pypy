from pypy.interpreter import gateway
import random

class AppTestContext:
    spaceconfig = dict(usemodules=('_decimal',))

    def setup_class(cls):
        space = cls.space
        cls.w_decimal = space.call_function(space.builtin.get('__import__'),
                                            space.wrap("_decimal"))
        cls.w_Decimal = space.getattr(cls.w_decimal, space.wrap("Decimal"))
        def random_float(space):
            f = random.expovariate(0.01) * (random.random() * 2.0 - 1.0)
            return space.wrap(f)
        cls.w_random_float = space.wrap(gateway.interp2app(random_float))

        # a few functions from unittest library
        def assertTrue(space, w_x):
            assert space.is_true(w_x)
        cls.w_assertTrue = space.wrap(gateway.interp2app(assertTrue))
        def assertEqual(space, w_x, w_y):
            assert space.eq_w(w_x, w_y)
        cls.w_assertEqual = space.wrap(gateway.interp2app(assertEqual))

        cls.w_assertRaises = space.appexec([], """(): return raises""")

    def test_context_repr(self):
        c = self.decimal.DefaultContext.copy()

        c.prec = 425000000
        c.Emax = 425000000
        c.Emin = -425000000
        c.rounding = self.decimal.ROUND_HALF_DOWN
        c.capitals = 0
        c.clamp = 1

        d = self.decimal
        OrderedSignals = [d.Clamped, d.Rounded, d.Inexact, d.Subnormal,
                          d.Underflow, d.Overflow, d.DivisionByZero,
                          d.InvalidOperation, d.FloatOperation]
        for sig in OrderedSignals:
            c.flags[sig] = False
            c.traps[sig] = False

        s = c.__repr__()
        t = "Context(prec=425000000, rounding=ROUND_HALF_DOWN, " \
            "Emin=-425000000, Emax=425000000, capitals=0, clamp=1, " \
            "flags=[], traps=[])"
        self.assertEqual(s, t)

    def test_explicit_context_create_from_float(self):
        Decimal = self.decimal.Decimal

        nc = self.decimal.Context()
        r = nc.create_decimal(0.1)
        self.assertEqual(type(r), Decimal)
        self.assertEqual(str(r), '0.1000000000000000055511151231')
        self.assertTrue(nc.create_decimal(float('nan')).is_qnan())
        self.assertTrue(nc.create_decimal(float('inf')).is_infinite())
        self.assertTrue(nc.create_decimal(float('-inf')).is_infinite())
        self.assertEqual(str(nc.create_decimal(float('nan'))),
                         str(nc.create_decimal('NaN')))
        self.assertEqual(str(nc.create_decimal(float('inf'))),
                         str(nc.create_decimal('Infinity')))
        self.assertEqual(str(nc.create_decimal(float('-inf'))),
                         str(nc.create_decimal('-Infinity')))
        self.assertEqual(str(nc.create_decimal(float('-0.0'))),
                         str(nc.create_decimal('-0')))
        nc.prec = 100
        for i in range(200):
            x = self.random_float()
            self.assertEqual(x, float(nc.create_decimal(x))) # roundtrip

    def test_add(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.add(Decimal(1), Decimal(1))
        self.assertEqual(c.add(1, 1), d)
        self.assertEqual(c.add(Decimal(1), 1), d)
        self.assertEqual(c.add(1, Decimal(1)), d)
        self.assertRaises(TypeError, c.add, '1', 1)
        self.assertRaises(TypeError, c.add, 1, '1')

    def test_subtract(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.subtract(Decimal(1), Decimal(2))
        self.assertEqual(c.subtract(1, 2), d)
        self.assertEqual(c.subtract(Decimal(1), 2), d)
        self.assertEqual(c.subtract(1, Decimal(2)), d)
        self.assertRaises(TypeError, c.subtract, '1', 2)
        self.assertRaises(TypeError, c.subtract, 1, '2')

    def test_multiply(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.multiply(Decimal(1), Decimal(2))
        self.assertEqual(c.multiply(1, 2), d)
        self.assertEqual(c.multiply(Decimal(1), 2), d)
        self.assertEqual(c.multiply(1, Decimal(2)), d)
        self.assertRaises(TypeError, c.multiply, '1', 2)
        self.assertRaises(TypeError, c.multiply, 1, '2')

    def test_divide(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.divide(Decimal(1), Decimal(2))
        self.assertEqual(c.divide(1, 2), d)
        self.assertEqual(c.divide(Decimal(1), 2), d)
        self.assertEqual(c.divide(1, Decimal(2)), d)
        self.assertRaises(TypeError, c.divide, '1', 2)
        self.assertRaises(TypeError, c.divide, 1, '2')

    def test_logical_and(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.logical_and(Decimal(1), Decimal(1))
        self.assertEqual(c.logical_and(1, 1), d)
        self.assertEqual(c.logical_and(Decimal(1), 1), d)
        self.assertEqual(c.logical_and(1, Decimal(1)), d)
        self.assertRaises(TypeError, c.logical_and, '1', 1)
        self.assertRaises(TypeError, c.logical_and, 1, '1')

    def test_logical_invert(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.logical_invert(Decimal(1000))
        self.assertEqual(c.logical_invert(1000), d)
        self.assertRaises(TypeError, c.logical_invert, '1000')

    def test_logical_or(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.logical_or(Decimal(1), Decimal(1))
        self.assertEqual(c.logical_or(1, 1), d)
        self.assertEqual(c.logical_or(Decimal(1), 1), d)
        self.assertEqual(c.logical_or(1, Decimal(1)), d)
        self.assertRaises(TypeError, c.logical_or, '1', 1)
        self.assertRaises(TypeError, c.logical_or, 1, '1')

    def test_logical_xor(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.logical_xor(Decimal(1), Decimal(1))
        self.assertEqual(c.logical_xor(1, 1), d)
        self.assertEqual(c.logical_xor(Decimal(1), 1), d)
        self.assertEqual(c.logical_xor(1, Decimal(1)), d)
        self.assertRaises(TypeError, c.logical_xor, '1', 1)
        self.assertRaises(TypeError, c.logical_xor, 1, '1')

    def test_is_finite(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_finite(Decimal(10))
        self.assertEqual(c.is_finite(10), d)
        self.assertRaises(TypeError, c.is_finite, '10')

    def test_is_infinite(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_infinite(Decimal(10))
        self.assertEqual(c.is_infinite(10), d)
        self.assertRaises(TypeError, c.is_infinite, '10')

    def test_is_nan(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_nan(Decimal(10))
        self.assertEqual(c.is_nan(10), d)
        self.assertRaises(TypeError, c.is_nan, '10')

    def test_is_normal(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_normal(Decimal(10))
        self.assertEqual(c.is_normal(10), d)
        self.assertRaises(TypeError, c.is_normal, '10')

    def test_is_qnan(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_qnan(Decimal(10))
        self.assertEqual(c.is_qnan(10), d)
        self.assertRaises(TypeError, c.is_qnan, '10')

    def test_is_signed(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_signed(Decimal(10))
        self.assertEqual(c.is_signed(10), d)
        self.assertRaises(TypeError, c.is_signed, '10')

    def test_is_snan(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_snan(Decimal(10))
        self.assertEqual(c.is_snan(10), d)
        self.assertRaises(TypeError, c.is_snan, '10')

    def test_is_subnormal(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_subnormal(Decimal(10))
        self.assertEqual(c.is_subnormal(10), d)
        self.assertRaises(TypeError, c.is_subnormal, '10')

    def test_is_zero(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.is_zero(Decimal(10))
        self.assertEqual(c.is_zero(10), d)
        self.assertRaises(TypeError, c.is_zero, '10')


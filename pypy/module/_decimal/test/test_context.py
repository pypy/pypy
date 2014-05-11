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
        assert s == t

    def test_explicit_context_create_from_float(self):
        Decimal = self.decimal.Decimal

        nc = self.decimal.Context()
        r = nc.create_decimal(0.1)
        assert type(r) is Decimal
        assert str(r) == '0.1000000000000000055511151231'
        assert nc.create_decimal(float('nan')).is_qnan()
        assert nc.create_decimal(float('inf')).is_infinite()
        assert nc.create_decimal(float('-inf')).is_infinite()
        assert (str(nc.create_decimal(float('nan'))) ==
                str(nc.create_decimal('NaN')))
        assert (str(nc.create_decimal(float('inf'))) ==
                str(nc.create_decimal('Infinity')))
        assert (str(nc.create_decimal(float('-inf'))) ==
                str(nc.create_decimal('-Infinity')))
        assert (str(nc.create_decimal(float('-0.0'))) ==
                str(nc.create_decimal('-0')))
        nc.prec = 100
        for i in range(200):
            x = self.random_float()
            assert x == float(nc.create_decimal(x))  # roundtrip

    def test_add(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.add(Decimal(1), Decimal(1))
        assert c.add(1, 1) == d
        assert c.add(Decimal(1), 1) == d
        assert c.add(1, Decimal(1)) == d
        raises(TypeError, c.add, '1', 1)
        raises(TypeError, c.add, 1, '1')

    def test_subtract(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.subtract(Decimal(1), Decimal(2))
        assert c.subtract(1, 2) == d
        assert c.subtract(Decimal(1), 2) == d
        assert c.subtract(1, Decimal(2)) == d
        raises(TypeError, c.subtract, '1', 2)
        raises(TypeError, c.subtract, 1, '2')

    def test_multiply(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.multiply(Decimal(1), Decimal(2))
        assert c.multiply(1, 2)== d
        assert c.multiply(Decimal(1), 2)== d
        assert c.multiply(1, Decimal(2))== d
        raises(TypeError, c.multiply, '1', 2)
        raises(TypeError, c.multiply, 1, '2')

    def test_divide(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context

        c = Context()
        d = c.divide(Decimal(1), Decimal(2))
        assert c.divide(1, 2)== d
        assert c.divide(Decimal(1), 2)== d
        assert c.divide(1, Decimal(2))== d
        raises(TypeError, c.divide, '1', 2)
        raises(TypeError, c.divide, 1, '2')

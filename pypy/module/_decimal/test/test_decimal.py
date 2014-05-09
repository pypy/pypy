from pypy.interpreter import gateway
import random

class AppTestExplicitConstruction:
    spaceconfig = dict(usemodules=('_decimal', '_random'))

    def setup_class(cls):
        space = cls.space
        cls.w_decimal = space.call_function(space.builtin.get('__import__'),
                                            space.wrap("_decimal"))
        cls.w_Decimal = space.getattr(cls.w_decimal, space.wrap("Decimal"))
        def random_float(space):
            f = random.expovariate(0.01) * (random.random() * 2.0 - 1.0)
            return space.wrap(f)
        cls.w_random_float = space.wrap(gateway.interp2app(random_float))

    def test_explicit_empty(self):
        Decimal = self.Decimal
        assert Decimal() == Decimal("0")

    def test_explicit_from_None(self):
        Decimal = self.Decimal
        raises(TypeError, Decimal, None)

    def test_explicit_from_int(self):
        Decimal = self.decimal.Decimal

        #positive
        d = Decimal(45)
        assert str(d) == '45'

        #very large positive
        d = Decimal(500000123)
        assert str(d) == '500000123'

        #negative
        d = Decimal(-45)
        assert str(d) == '-45'

        #zero
        d = Decimal(0)
        assert str(d) == '0'

        # single word longs
        for n in range(0, 32):
            for sign in (-1, 1):
                for x in range(-5, 5):
                    i = sign * (2**n + x)
                    d = Decimal(i)
                    assert str(d) == str(i)

    def test_explicit_from_string(self):
        Decimal = self.decimal.Decimal
        InvalidOperation = self.decimal.InvalidOperation
        localcontext = self.decimal.localcontext

        #empty
        assert str(Decimal('')) == 'NaN'

        #int
        assert str(Decimal('45')) == '45'

        #float
        assert str(Decimal('45.34')) == '45.34'

        #engineer notation
        assert str(Decimal('45e2')) == '4.5E+3'

        #just not a number
        assert str(Decimal('ugly')) == 'NaN'

        #leading and trailing whitespace permitted
        assert str(Decimal('1.3E4 \n')) == '1.3E+4'
        assert str(Decimal('  -7.89')) == '-7.89'
        assert str(Decimal("  3.45679  ")) == '3.45679'

        # unicode whitespace
        for lead in ["", ' ', '\u00a0', '\u205f']:
            for trail in ["", ' ', '\u00a0', '\u205f']:
                assert str(Decimal(lead + '9.311E+28' + trail)) == '9.311E+28'

        with localcontext() as c:
            c.traps[InvalidOperation] = True
            # Invalid string
            raises(InvalidOperation, Decimal, "xyz")
            # Two arguments max
            raises(TypeError, Decimal, "1234", "x", "y")

            # space within the numeric part
            raises(InvalidOperation, Decimal, "1\u00a02\u00a03")
            raises(InvalidOperation, Decimal, "\u00a01\u00a02\u00a0")

            # unicode whitespace
            raises(InvalidOperation, Decimal, "\u00a0")
            raises(InvalidOperation, Decimal, "\u00a0\u00a0")

            # embedded NUL
            raises(InvalidOperation, Decimal, "12\u00003")

    def test_explicit_from_tuples(self):
        Decimal = self.decimal.Decimal

        #zero
        d = Decimal( (0, (0,), 0) )
        assert str(d) == '0'

        #int
        d = Decimal( (1, (4, 5), 0) )
        assert str(d) == '-45'

        #float
        d = Decimal( (0, (4, 5, 3, 4), -2) )
        assert str(d) == '45.34'

        #weird
        d = Decimal( (1, (4, 3, 4, 9, 1, 3, 5, 3, 4), -25) )
        assert str(d) == '-4.34913534E-17'

        #inf
        d = Decimal( (0, (), "F") )
        assert str(d) == 'Infinity'

        #wrong number of items
        raises(ValueError, Decimal, (1, (4, 3, 4, 9, 1)) )

        #bad sign
        raises(ValueError, Decimal, (8, (4, 3, 4, 9, 1), 2) )
        raises(ValueError, Decimal, (0., (4, 3, 4, 9, 1), 2) )
        raises(ValueError, Decimal, (Decimal(1), (4, 3, 4, 9, 1), 2))

        #bad exp
        raises(ValueError, Decimal, (1, (4, 3, 4, 9, 1), 'wrong!') )
        raises(ValueError, Decimal, (1, (4, 3, 4, 9, 1), 0.) )
        raises(ValueError, Decimal, (1, (4, 3, 4, 9, 1), '1') )

        #bad coefficients
        raises(ValueError, Decimal, (1, "xyz", 2) )
        raises(ValueError, Decimal, (1, (4, 3, 4, None, 1), 2) )
        raises(ValueError, Decimal, (1, (4, -3, 4, 9, 1), 2) )
        raises(ValueError, Decimal, (1, (4, 10, 4, 9, 1), 2) )
        raises(ValueError, Decimal, (1, (4, 3, 4, 'a', 1), 2) )

    def test_explicit_from_list(self):
        Decimal = self.decimal.Decimal

        d = Decimal([0, [0], 0])
        assert str(d) == '0'

        d = Decimal([1, [4, 3, 4, 9, 1, 3, 5, 3, 4], -25])
        assert str(d) == '-4.34913534E-17'

        d = Decimal([1, (4, 3, 4, 9, 1, 3, 5, 3, 4), -25])
        assert str(d) == '-4.34913534E-17'

        d = Decimal((1, [4, 3, 4, 9, 1, 3, 5, 3, 4], -25))
        assert str(d) == '-4.34913534E-17'

    def test_explicit_from_bool(self):
        Decimal = self.decimal.Decimal

        assert bool(Decimal(0)) is False
        assert bool(Decimal(1)) is True
        assert Decimal(False) == Decimal(0)
        assert Decimal(True) == Decimal(1)

    def test_explicit_from_Decimal(self):
        Decimal = self.decimal.Decimal

        #positive
        d = Decimal(45)
        e = Decimal(d)
        assert str(e) == '45'

        #very large positive
        d = Decimal(500000123)
        e = Decimal(d)
        assert str(e) == '500000123'

        #negative
        d = Decimal(-45)
        e = Decimal(d)
        assert str(e) == '-45'

        #zero
        d = Decimal(0)
        e = Decimal(d)
        assert str(e) == '0'

    def test_explicit_from_float(self):
        Decimal = self.decimal.Decimal

        r = Decimal(0.1)
        assert type(r) is Decimal
        assert str(r) == (
                '0.1000000000000000055511151231257827021181583404541015625')
        assert Decimal(float('nan')).is_qnan()
        assert Decimal(float('inf')).is_infinite()
        assert Decimal(float('-inf')).is_infinite()
        assert str(Decimal(float('nan'))) == str(Decimal('NaN'))
        assert str(Decimal(float('inf'))) == str(Decimal('Infinity'))
        assert str(Decimal(float('-inf'))) == str(Decimal('-Infinity'))
        assert str(Decimal(float('-0.0'))) == str(Decimal('-0'))
        for i in range(200):
            x = self.random_float()
            assert x == float(Decimal(x)) # roundtrip

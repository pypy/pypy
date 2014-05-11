from pypy.interpreter import gateway
import random

class AppTestExplicitConstruction:
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

        self.decimal.getcontext().traps[InvalidOperation] = False

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

    def test_explicit_context_create_decimal(self):
        Decimal = self.decimal.Decimal
        InvalidOperation = self.decimal.InvalidOperation
        Rounded = self.decimal.Rounded

        nc = self.decimal.getcontext().copy()
        nc.prec = 3
        nc.traps[InvalidOperation] = False
        nc.traps[self.decimal.Overflow] = False
        nc.traps[self.decimal.DivisionByZero] = False

        # empty
        d = Decimal()
        assert str(d) == '0'
        d = nc.create_decimal()
        assert str(d) == '0'

        # from None
        raises(TypeError, nc.create_decimal, None)

        # from int
        d = nc.create_decimal(456)
        assert isinstance(d, Decimal)
        assert nc.create_decimal(45678) == nc.create_decimal('457E+2')

        # from string
        d = Decimal('456789')
        assert str(d) == '456789'
        d = nc.create_decimal('456789')
        assert str(d) == '4.57E+5'
        # leading and trailing whitespace should result in a NaN;
        # spaces are already checked in Cowlishaw's test-suite, so
        # here we just check that a trailing newline results in a NaN
        assert str(nc.create_decimal('3.14\n')) == 'NaN'

        # from tuples
        d = Decimal( (1, (4, 3, 4, 9, 1, 3, 5, 3, 4), -25) )
        assert str(d) == '-4.34913534E-17'
        d = nc.create_decimal( (1, (4, 3, 4, 9, 1, 3, 5, 3, 4), -25) )
        assert str(d) == '-4.35E-17'

        # from Decimal
        prevdec = Decimal(500000123)
        d = Decimal(prevdec)
        assert str(d) == '500000123'
        d = nc.create_decimal(prevdec)
        assert str(d) == '5.00E+8'

        # more integers
        nc.prec = 28
        nc.traps[InvalidOperation] = True

        for v in [-2**63-1, -2**63, -2**31-1, -2**31, 0,
                   2**31-1, 2**31, 2**63-1, 2**63]:
            d = nc.create_decimal(v)
            assert isinstance(d, Decimal)
            assert str(d) == str(v)

        nc.prec = 3
        nc.traps[Rounded] = True
        raises(Rounded, nc.create_decimal, 1234)

        # from string
        nc.prec = 28
        assert str(nc.create_decimal('0E-017')) == '0E-17'
        assert str(nc.create_decimal('45')) == '45'
        assert str(nc.create_decimal('-Inf')) == '-Infinity'
        assert str(nc.create_decimal('NaN123')) == 'NaN123'

        # invalid arguments
        raises(InvalidOperation, nc.create_decimal, "xyz")
        raises(ValueError, nc.create_decimal, (1, "xyz", -25))
        raises(TypeError, nc.create_decimal, "1234", "5678")

        # too many NaN payload digits
        nc.prec = 3
        raises(InvalidOperation, nc.create_decimal, 'NaN12345')
        raises(InvalidOperation, nc.create_decimal, Decimal('NaN12345'))

        nc.traps[InvalidOperation] = False
        assert str(nc.create_decimal('NaN12345')) == 'NaN'
        assert nc.flags[InvalidOperation]

        nc.flags[InvalidOperation] = False
        assert str(nc.create_decimal(Decimal('NaN12345'))) == 'NaN'
        assert nc.flags[InvalidOperation]

    def test_operations(self):
        Decimal = self.decimal.Decimal

        assert Decimal(4) + Decimal(3) == Decimal(7)
        assert Decimal(4) - Decimal(3) == Decimal(1)
        assert Decimal(4) * Decimal(3) == Decimal(12)
        assert Decimal(6) / Decimal(3) == Decimal(2)

    def test_tostring_methods(self):
        Decimal = self.decimal.Decimal
        d = Decimal('15.32')
        assert str(d) == '15.32'
        assert repr(d) == "Decimal('15.32')"

    def test_tonum_methods(self):
        #Test float and int methods.
        Decimal = self.decimal.Decimal
        InvalidOperation = self.decimal.InvalidOperation
        self.decimal.getcontext().traps[InvalidOperation] = False

        import math

        d1 = Decimal('66')
        d2 = Decimal('15.32')

        #int
        assert int(d1) == 66
        assert int(d2) == 15

        #float
        assert float(d1) == 66
        assert float(d2) == 15.32

        #floor
        test_pairs = [
            ('123.00', 123),
            ('3.2', 3),
            ('3.54', 3),
            ('3.899', 3),
            ('-2.3', -3),
            ('-11.0', -11),
            ('0.0', 0),
            ('-0E3', 0),
            ('89891211712379812736.1', 89891211712379812736),
            ]
        for d, i in test_pairs:
            assert math.floor(Decimal(d)) == i
        raises(ValueError, math.floor, Decimal('-NaN'))
        raises(ValueError, math.floor, Decimal('sNaN'))
        raises(ValueError, math.floor, Decimal('NaN123'))
        raises(OverflowError, math.floor, Decimal('Inf'))
        raises(OverflowError, math.floor, Decimal('-Inf'))

        #ceiling
        test_pairs = [
            ('123.00', 123),
            ('3.2', 4),
            ('3.54', 4),
            ('3.899', 4),
            ('-2.3', -2),
            ('-11.0', -11),
            ('0.0', 0),
            ('-0E3', 0),
            ('89891211712379812736.1', 89891211712379812737),
            ]
        for d, i in test_pairs:
            assert math.ceil(Decimal(d)) == i
        raises(ValueError, math.ceil, Decimal('-NaN'))
        raises(ValueError, math.ceil, Decimal('sNaN'))
        raises(ValueError, math.ceil, Decimal('NaN123'))
        raises(OverflowError, math.ceil, Decimal('Inf'))
        raises(OverflowError, math.ceil, Decimal('-Inf'))

        #round, single argument
        test_pairs = [
            ('123.00', 123),
            ('3.2', 3),
            ('3.54', 4),
            ('3.899', 4),
            ('-2.3', -2),
            ('-11.0', -11),
            ('0.0', 0),
            ('-0E3', 0),
            ('-3.5', -4),
            ('-2.5', -2),
            ('-1.5', -2),
            ('-0.5', 0),
            ('0.5', 0),
            ('1.5', 2),
            ('2.5', 2),
            ('3.5', 4),
            ]
        for d, i in test_pairs:
            assert round(Decimal(d)) == i
        raises(ValueError, round, Decimal('-NaN'))
        raises(ValueError, round, Decimal('sNaN'))
        raises(ValueError, round, Decimal('NaN123'))
        raises(OverflowError, round, Decimal('Inf'))
        raises(OverflowError, round, Decimal('-Inf'))

        #round, two arguments;  this is essentially equivalent
        #to quantize, which is already extensively tested
        test_triples = [
            ('123.456', -4, '0E+4'),
            ('123.456', -3, '0E+3'),
            ('123.456', -2, '1E+2'),
            ('123.456', -1, '1.2E+2'),
            ('123.456', 0, '123'),
            ('123.456', 1, '123.5'),
            ('123.456', 2, '123.46'),
            ('123.456', 3, '123.456'),
            ('123.456', 4, '123.4560'),
            ('123.455', 2, '123.46'),
            ('123.445', 2, '123.44'),
            ('Inf', 4, 'NaN'),
            ('-Inf', -23, 'NaN'),
            ('sNaN314', 3, 'NaN314'),
            ]
        for d, n, r in test_triples:
            assert str(round(Decimal(d), n)) == r

    def test_addition(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('-11.1')
        d2 = Decimal('22.2')

        #two Decimals
        assert d1+d2 == Decimal('11.1')
        assert d2+d1 == Decimal('11.1')

        #with other type, left
        c = d1 + 5
        assert c == Decimal('-6.1')
        assert type(c) == type(d1)

        #with other type, right
        c = 5 + d1
        assert c == Decimal('-6.1')
        assert type(c) == type(d1)

        #inline with decimal
        d1 += d2
        assert d1 == Decimal('11.1')

        #inline with other type
        d1 += 5
        assert d1 == Decimal('16.1')

    def test_subtraction(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('-11.1')
        d2 = Decimal('22.2')

        #two Decimals
        assert d1-d2 == Decimal('-33.3')
        assert d2-d1 == Decimal('33.3')

        #with other type, left
        c = d1 - 5
        assert c == Decimal('-16.1')
        assert type(c) == type(d1)

        #with other type, right
        c = 5 - d1
        assert c == Decimal('16.1')
        assert type(c) == type(d1)

        #inline with decimal
        d1 -= d2
        assert d1 == Decimal('-33.3')

        #inline with other type
        d1 -= 5
        assert d1 == Decimal('-38.3')

    def test_multiplication(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('-5')
        d2 = Decimal('3')

        #two Decimals
        assert d1*d2 == Decimal('-15')
        assert d2*d1 == Decimal('-15')

        #with other type, left
        c = d1 * 5
        assert c == Decimal('-25')
        assert type(c) == type(d1)

        #with other type, right
        c = 5 * d1
        assert c == Decimal('-25')
        assert type(c) == type(d1)

        #inline with decimal
        d1 *= d2
        assert d1 == Decimal('-15')

        #inline with other type
        d1 *= 5
        assert d1 == Decimal('-75')

    def test_division(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('-5')
        d2 = Decimal('2')

        #two Decimals
        assert d1/d2 == Decimal('-2.5')
        assert d2/d1 == Decimal('-0.4')

        #with other type, left
        c = d1 / 4
        assert c == Decimal('-1.25')
        assert type(c) == type(d1)

        #with other type, right
        c = 4 / d1
        assert c == Decimal('-0.8')
        assert type(c) == type(d1)

        #inline with decimal
        d1 /= d2
        assert d1 == Decimal('-2.5')

        #inline with other type
        d1 /= 4
        assert d1 == Decimal('-0.625')

    def test_floor_division(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('5')
        d2 = Decimal('2')

        #two Decimals
        assert d1//d2 == Decimal('2')
        assert d2//d1 == Decimal('0')

        #with other type, left
        c = d1 // 4
        assert c == Decimal('1')
        assert type(c) == type(d1)

        #with other type, right
        c = 7 // d1
        assert c == Decimal('1')
        assert type(c) == type(d1)

        #inline with decimal
        d1 //= d2
        assert d1 == Decimal('2')

        #inline with other type
        d1 //= 2
        assert d1 == Decimal('1')

    def test_powering(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('5')
        d2 = Decimal('2')

        #two Decimals
        assert d1**d2 == Decimal('25')
        assert d2**d1 == Decimal('32')

        #with other type, left
        c = d1 ** 4
        assert c == Decimal('625')
        assert type(c) == type(d1)

        #with other type, right
        c = 7 ** d1
        assert c == Decimal('16807')
        assert type(c) == type(d1)

        #inline with decimal
        d1 **= d2
        assert d1 == Decimal('25')

        #inline with other type
        d1 **= 4
        assert d1 == Decimal('390625')

    def test_module(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('5')
        d2 = Decimal('2')

        #two Decimals
        assert d1%d2 == Decimal('1')
        assert d2%d1 == Decimal('2')

        #with other type, left
        c = d1 % 4
        assert c == Decimal('1')
        assert type(c) == type(d1)

        #with other type, right
        c = 7 % d1
        assert c == Decimal('2')
        assert type(c) == type(d1)

        #inline with decimal
        d1 %= d2
        assert d1 == Decimal('1')

        #inline with other type
        d1 %= 4
        assert d1 == Decimal('1')

    def test_floor_div_module(self):
        Decimal = self.decimal.Decimal

        d1 = Decimal('5')
        d2 = Decimal('2')

        #two Decimals
        (p, q) = divmod(d1, d2)
        assert p == Decimal('2')
        assert q == Decimal('1')
        assert type(p) == type(d1)
        assert type(q) == type(d1)

        #with other type, left
        (p, q) = divmod(d1, 4)
        assert p == Decimal('1')
        assert q == Decimal('1')
        assert type(p) == type(d1)
        assert type(q) == type(d1)

        #with other type, right
        (p, q) = divmod(7, d1)
        assert p == Decimal('1')
        assert q == Decimal('2')
        assert type(p) == type(d1)
        assert type(q) == type(d1)

    def test_unary_operators(self):
        Decimal = self.decimal.Decimal

        assert +Decimal(45) == Decimal(+45)
        assert -Decimal(45) == Decimal(-45)
        assert abs(Decimal(45)) == abs(Decimal(-45))

    def test_nan_comparisons(self):
        import operator
        # comparisons involving signaling nans signal InvalidOperation

        # order comparisons (<, <=, >, >=) involving only quiet nans
        # also signal InvalidOperation

        # equality comparisons (==, !=) involving only quiet nans
        # don't signal, but return False or True respectively.
        Decimal = self.decimal.Decimal
        InvalidOperation = self.decimal.InvalidOperation
        Overflow = self.decimal.Overflow
        DivisionByZero = self.decimal.DivisionByZero
        localcontext = self.decimal.localcontext

        self.decimal.getcontext().traps[InvalidOperation] = False
        self.decimal.getcontext().traps[Overflow] = False
        self.decimal.getcontext().traps[DivisionByZero] = False

        n = Decimal('NaN')
        s = Decimal('sNaN')
        i = Decimal('Inf')
        f = Decimal('2')

        qnan_pairs = (n, n), (n, i), (i, n), (n, f), (f, n)
        snan_pairs = (s, n), (n, s), (s, i), (i, s), (s, f), (f, s), (s, s)
        order_ops = operator.lt, operator.le, operator.gt, operator.ge
        equality_ops = operator.eq, operator.ne

        # results when InvalidOperation is not trapped
        for x, y in qnan_pairs + snan_pairs:
            for op in order_ops + equality_ops:
                got = op(x, y)
                expected = True if op is operator.ne else False
                assert expected is got, (
                    "expected {0!r} for operator.{1}({2!r}, {3!r}); "
                    "got {4!r}".format(
                        expected, op.__name__, x, y, got))

        # repeat the above, but this time trap the InvalidOperation
        with localcontext() as ctx:
            ctx.traps[InvalidOperation] = 1

            for x, y in qnan_pairs:
                for op in equality_ops:
                    got = op(x, y)
                    expected = True if op is operator.ne else False
                    assert expected is got, (
                        "expected {0!r} for "
                        "operator.{1}({2!r}, {3!r}); "
                        "got {4!r}".format(
                            expected, op.__name__, x, y, got))

            for x, y in snan_pairs:
                for op in equality_ops:
                    raises(InvalidOperation, operator.eq, x, y)
                    raises(InvalidOperation, operator.ne, x, y)

            for x, y in qnan_pairs + snan_pairs:
                for op in order_ops:
                    raises(InvalidOperation, op, x, y)

    def test_copy_sign(self):
        Decimal = self.decimal.Decimal

        d = Decimal(1).copy_sign(Decimal(-2))
        assert Decimal(1).copy_sign(-2) == d
        raises(TypeError, Decimal(1).copy_sign, '-2')

    def test_as_tuple(self):
        Decimal = self.decimal.Decimal

        #with zero
        d = Decimal(0)
        assert d.as_tuple() == (0, (0,), 0) 

        #int
        d = Decimal(-45)
        assert d.as_tuple() == (1, (4, 5), 0) 

        #complicated string
        d = Decimal("-4.34913534E-17")
        assert d.as_tuple() == (1, (4, 3, 4, 9, 1, 3, 5, 3, 4), -25) 

        # The '0' coefficient is implementation specific to decimal.py.
        # It has no meaning in the C-version and is ignored there.
        d = Decimal("Infinity")
        assert d.as_tuple() == (0, (0,), 'F') 

        #leading zeros in coefficient should be stripped
        d = Decimal( (0, (0, 0, 4, 0, 5, 3, 4), -2) )
        assert d.as_tuple() == (0, (4, 0, 5, 3, 4), -2) 
        d = Decimal( (1, (0, 0, 0), 37) )
        assert d.as_tuple() == (1, (0,), 37)
        d = Decimal( (1, (), 37) )
        assert d.as_tuple() == (1, (0,), 37)

        #leading zeros in NaN diagnostic info should be stripped
        d = Decimal( (0, (0, 0, 4, 0, 5, 3, 4), 'n') )
        assert d.as_tuple() == (0, (4, 0, 5, 3, 4), 'n') 
        d = Decimal( (1, (0, 0, 0), 'N') )
        assert d.as_tuple() == (1, (), 'N') 
        d = Decimal( (1, (), 'n') )
        assert d.as_tuple() == (1, (), 'n') 

        # For infinities, decimal.py has always silently accepted any
        # coefficient tuple.
        d = Decimal( (0, (0,), 'F') )
        assert d.as_tuple() == (0, (0,), 'F')
        d = Decimal( (0, (4, 5, 3, 4), 'F') )
        assert d.as_tuple() == (0, (0,), 'F')
        d = Decimal( (1, (0, 2, 7, 1), 'F') )
        assert d.as_tuple() == (1, (0,), 'F')


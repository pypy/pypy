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

        # a few functions from unittest library
        cls.w_assertTrue = space.appexec([], """():
            def assertTrue(x): assert x
            return assertTrue""")
        cls.w_assertEqual = space.appexec([], """():
            def assertEqual(x, y): assert x == y
            return assertEqual""")
        cls.w_assertRaises = space.appexec([], """(): return raises""")

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

    def test_from_float(self):
        Decimal = self.decimal.Decimal

        class MyDecimal(Decimal):
            pass

        self.assertTrue(issubclass(MyDecimal, Decimal))

        r = MyDecimal.from_float(0.1)
        self.assertEqual(type(r), MyDecimal)
        self.assertEqual(str(r),
                '0.1000000000000000055511151231257827021181583404541015625')
        bigint = 12345678901234567890123456789
        self.assertEqual(MyDecimal.from_float(bigint), MyDecimal(bigint))
        self.assertTrue(MyDecimal.from_float(float('nan')).is_qnan())
        self.assertTrue(MyDecimal.from_float(float('inf')).is_infinite())
        self.assertTrue(MyDecimal.from_float(float('-inf')).is_infinite())
        self.assertEqual(str(MyDecimal.from_float(float('nan'))),
                         str(Decimal('NaN')))
        self.assertEqual(str(MyDecimal.from_float(float('inf'))),
                         str(Decimal('Infinity')))
        self.assertEqual(str(MyDecimal.from_float(float('-inf'))),
                         str(Decimal('-Infinity')))
        self.assertRaises(TypeError, MyDecimal.from_float, 'abc')
        for i in range(200):
            x = self.random_float()
            self.assertEqual(x, float(MyDecimal.from_float(x))) # roundtrip

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

    def test_complex(self):
        Decimal = self.decimal.Decimal
        d = Decimal("2.34")
        assert d.real == d
        assert d.imag == 0
        assert d.conjugate() == d

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

    def test_hash_method(self):

        Decimal = self.decimal.Decimal
        localcontext = self.decimal.localcontext

        def hashit(d):
            a = hash(d)
            b = d.__hash__()
            assert a == b
            return a

        #just that it's hashable
        hashit(Decimal(23))
        hashit(Decimal('Infinity'))
        hashit(Decimal('-Infinity'))
        hashit(Decimal('nan123'))
        hashit(Decimal('-NaN'))

        test_values = [Decimal(sign*(2**m + n))
                       for m in [0, 14, 15, 16, 17, 30, 31,
                                 32, 33, 61, 62, 63, 64, 65, 66]
                       for n in range(-10, 10)
                       for sign in [-1, 1]]
        test_values.extend([
                Decimal("-1"), # ==> -2
                Decimal("-0"), # zeros
                Decimal("0.00"),
                Decimal("-0.000"),
                Decimal("0E10"),
                Decimal("-0E12"),
                Decimal("10.0"), # negative exponent
                Decimal("-23.00000"),
                Decimal("1230E100"), # positive exponent
                Decimal("-4.5678E50"),
                # a value for which hash(n) != hash(n % (2**64-1))
                # in Python pre-2.6
                Decimal(2**64 + 2**32 - 1),
                # selection of values which fail with the old (before
                # version 2.6) long.__hash__
                Decimal("1.634E100"),
                Decimal("90.697E100"),
                Decimal("188.83E100"),
                Decimal("1652.9E100"),
                Decimal("56531E100"),
                ])

        # check that hash(d) == hash(int(d)) for integral values
        for value in test_values:
            assert hashit(value) == hashit(int(value))

        #the same hash that to an int
        assert hashit(Decimal(23)) == hashit(23)
        raises(TypeError, hash, Decimal('sNaN'))
        assert hashit(Decimal('Inf'))
        assert hashit(Decimal('-Inf'))

        # check that the hashes of a Decimal float match when they
        # represent exactly the same values
        test_strings = ['inf', '-Inf', '0.0', '-.0e1',
                        '34.0', '2.5', '112390.625', '-0.515625']
        for s in test_strings:
            f = float(s)
            d = Decimal(s)
            assert hashit(f) == hashit(d)

        with localcontext() as c:
            # check that the value of the hash doesn't depend on the
            # current context (issue #1757)
            x = Decimal("123456789.1")

            c.prec = 6
            h1 = hashit(x)
            c.prec = 10
            h2 = hashit(x)
            c.prec = 16
            h3 = hashit(x)

            assert h1 == h2 == h3

            c.prec = 10000
            x = 1100 ** 1248
            assert hashit(Decimal(x)) == hashit(x)

    def test_float_comparison(self):
        Decimal = self.decimal.Decimal
        Context = self.decimal.Context
        FloatOperation = self.decimal.FloatOperation
        localcontext = self.decimal.localcontext

        def assert_attr(a, b, attr, context, signal=None):
            context.clear_flags()
            f = getattr(a, attr)
            if signal == FloatOperation:
                raises(signal, f, b)
            else:
                assert f(b) is True
            assert context.flags[FloatOperation]

        small_d = Decimal('0.25')
        big_d = Decimal('3.0')
        small_f = 0.25
        big_f = 3.0

        zero_d = Decimal('0.0')
        neg_zero_d = Decimal('-0.0')
        zero_f = 0.0
        neg_zero_f = -0.0

        inf_d = Decimal('Infinity')
        neg_inf_d = Decimal('-Infinity')
        inf_f = float('inf')
        neg_inf_f = float('-inf')

        def doit(c, signal=None):
            # Order
            for attr in '__lt__', '__le__':
                assert_attr(small_d, big_f, attr, c, signal)

            for attr in '__gt__', '__ge__':
                assert_attr(big_d, small_f, attr, c, signal)

            # Equality
            assert_attr(small_d, small_f, '__eq__', c, None)

            assert_attr(neg_zero_d, neg_zero_f, '__eq__', c, None)
            assert_attr(neg_zero_d, zero_f, '__eq__', c, None)

            assert_attr(zero_d, neg_zero_f, '__eq__', c, None)
            assert_attr(zero_d, zero_f, '__eq__', c, None)

            assert_attr(neg_inf_d, neg_inf_f, '__eq__', c, None)
            assert_attr(inf_d, inf_f, '__eq__', c, None)

            # Inequality
            assert_attr(small_d, big_f, '__ne__', c, None)

            assert_attr(Decimal('0.1'), 0.1, '__ne__', c, None)

            assert_attr(neg_inf_d, inf_f, '__ne__', c, None)
            assert_attr(inf_d, neg_inf_f, '__ne__', c, None)

            assert_attr(Decimal('NaN'), float('nan'), '__ne__', c, None)

        def test_containers(c, signal=None):
            c.clear_flags()
            s = set([100.0, Decimal('100.0')])
            assert len(s) == 1
            assert c.flags[FloatOperation]

            c.clear_flags()
            if signal:
                raises(signal, sorted, [1.0, Decimal('10.0')])
            else:
                s = sorted([10.0, Decimal('10.0')])
            assert c.flags[FloatOperation]

            c.clear_flags()
            b = 10.0 in [Decimal('10.0'), 1.0]
            assert c.flags[FloatOperation]

            c.clear_flags()
            b = 10.0 in {Decimal('10.0'):'a', 1.0:'b'}
            assert c.flags[FloatOperation]

        nc = Context()
        with localcontext(nc) as c:
            assert not c.traps[FloatOperation]
            doit(c, signal=None)
            test_containers(c, signal=None)

            c.traps[FloatOperation] = True
            doit(c, signal=FloatOperation)
            test_containers(c, signal=FloatOperation)

    def test_decimal_fraction_comparison(self):
        C = self.decimal
        D = self.decimal.Decimal
        from fractions import Fraction as F
        Context = self.decimal.Context
        localcontext = self.decimal.localcontext
        InvalidOperation = self.decimal.InvalidOperation


        emax = C.MAX_EMAX
        emin = C.MIN_EMIN
        etiny = C.MIN_ETINY
        c = Context(Emax=emax, Emin=emin)

        with localcontext(c):
            c.prec = emax
            assert D(0) < F(1,9999999999999999999999999999999999999)
            assert F(-1,9999999999999999999999999999999999999) < D(0)
            assert F(0,1) < D("1e" + str(etiny))
            assert D("-1e" + str(etiny)) < F(0,1)
            assert F(0,9999999999999999999999999) < D("1e" + str(etiny))
            assert D("-1e" + str(etiny)) < F(0,9999999999999999999999999)

            assert D("0.1") == F(1,10)
            assert F(1,10) == D("0.1")

            c.prec = 300
            assert D(1)/3 != F(1,3)
            assert F(1,3) != D(1)/3

            assert F(120984237, 9999999999) <= D("9e" + str(emax))
            assert D("9e" + str(emax)) >= F(120984237, 9999999999)

            assert D('inf') > F(99999999999,123)
            assert D('inf') > F(-99999999999,123)
            assert D('-inf') < F(99999999999,123)
            assert D('-inf') < F(-99999999999,123)

            raises(InvalidOperation, D('nan').__gt__, F(-9,123))
            assert F(-9,123).__lt__(D('nan')) is NotImplemented
            assert D('nan') != F(-9,123)
            assert F(-9,123) != D('nan')

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

    def test_c_integral(self):
        Decimal = self.decimal.Decimal
        Inexact = self.decimal.Inexact
        localcontext = self.decimal.localcontext
        ROUND_UP = self.decimal.ROUND_UP

        x = Decimal(10)
        assert x.to_integral() == 10
        raises(TypeError, x.to_integral, '10')
        raises(TypeError, x.to_integral, 10, 'x')
        raises(TypeError, x.to_integral, 10)

        assert x.to_integral_value() == 10
        raises(TypeError, x.to_integral_value, '10')
        raises(TypeError, x.to_integral_value, 10, 'x')
        raises(TypeError, x.to_integral_value, 10)

        assert x.to_integral_exact() == 10
        raises(TypeError, x.to_integral_exact, '10')
        raises(TypeError, x.to_integral_exact, 10, 'x')
        raises(TypeError, x.to_integral_exact, 10)

        with localcontext() as c:
            x = Decimal("99999999999999999999999999.9").to_integral_value(ROUND_UP)
            assert x == Decimal('100000000000000000000000000')

            x = Decimal("99999999999999999999999999.9").to_integral_exact(ROUND_UP)
            assert x == Decimal('100000000000000000000000000')

            c.traps[Inexact] = True
            raises(Inexact, Decimal("999.9").to_integral_exact, ROUND_UP)

    def test_formatting(self):
        Decimal = self.decimal.Decimal

        # triples giving a format, a Decimal, and the expected result
        test_values = [
            ('e', '0E-15', '0e-15'),
            ('e', '2.3E-15', '2.3e-15'),
            ('e', '2.30E+2', '2.30e+2'), # preserve significant zeros
            ('e', '2.30000E-15', '2.30000e-15'),
            ('e', '1.23456789123456789e40', '1.23456789123456789e+40'),
            ('e', '1.5', '1.5e+0'),
            ('e', '0.15', '1.5e-1'),
            ('e', '0.015', '1.5e-2'),
            ('e', '0.0000000000015', '1.5e-12'),
            ('e', '15.0', '1.50e+1'),
            ('e', '-15', '-1.5e+1'),
            ('e', '0', '0e+0'),
            ('e', '0E1', '0e+1'),
            ('e', '0.0', '0e-1'),
            ('e', '0.00', '0e-2'),
            ('.6e', '0E-15', '0.000000e-9'),
            ('.6e', '0', '0.000000e+6'),
            ('.6e', '9.999999', '9.999999e+0'),
            ('.6e', '9.9999999', '1.000000e+1'),
            ('.6e', '-1.23e5', '-1.230000e+5'),
            ('.6e', '1.23456789e-3', '1.234568e-3'),
            ('f', '0', '0'),
            ('f', '0.0', '0.0'),
            ('f', '0E-2', '0.00'),
            ('f', '0.00E-8', '0.0000000000'),
            ('f', '0E1', '0'), # loses exponent information
            ('f', '3.2E1', '32'),
            ('f', '3.2E2', '320'),
            ('f', '3.20E2', '320'),
            ('f', '3.200E2', '320.0'),
            ('f', '3.2E-6', '0.0000032'),
            ('.6f', '0E-15', '0.000000'), # all zeros treated equally
            ('.6f', '0E1', '0.000000'),
            ('.6f', '0', '0.000000'),
            ('.0f', '0', '0'), # no decimal point
            ('.0f', '0e-2', '0'),
            ('.0f', '3.14159265', '3'),
            ('.1f', '3.14159265', '3.1'),
            ('.4f', '3.14159265', '3.1416'),
            ('.6f', '3.14159265', '3.141593'),
            ('.7f', '3.14159265', '3.1415926'), # round-half-even!
            ('.8f', '3.14159265', '3.14159265'),
            ('.9f', '3.14159265', '3.141592650'),

            ('g', '0', '0'),
            ('g', '0.0', '0.0'),
            ('g', '0E1', '0e+1'),
            ('G', '0E1', '0E+1'),
            ('g', '0E-5', '0.00000'),
            ('g', '0E-6', '0.000000'),
            ('g', '0E-7', '0e-7'),
            ('g', '-0E2', '-0e+2'),
            ('.0g', '3.14159265', '3'),  # 0 sig fig -> 1 sig fig
            ('.0n', '3.14159265', '3'),  # same for 'n'
            ('.1g', '3.14159265', '3'),
            ('.2g', '3.14159265', '3.1'),
            ('.5g', '3.14159265', '3.1416'),
            ('.7g', '3.14159265', '3.141593'),
            ('.8g', '3.14159265', '3.1415926'), # round-half-even!
            ('.9g', '3.14159265', '3.14159265'),
            ('.10g', '3.14159265', '3.14159265'), # don't pad

            ('%', '0E1', '0%'),
            ('%', '0E0', '0%'),
            ('%', '0E-1', '0%'),
            ('%', '0E-2', '0%'),
            ('%', '0E-3', '0.0%'),
            ('%', '0E-4', '0.00%'),

            ('.3%', '0', '0.000%'), # all zeros treated equally
            ('.3%', '0E10', '0.000%'),
            ('.3%', '0E-10', '0.000%'),
            ('.3%', '2.34', '234.000%'),
            ('.3%', '1.234567', '123.457%'),
            ('.0%', '1.23', '123%'),

            ('e', 'NaN', 'NaN'),
            ('f', '-NaN123', '-NaN123'),
            ('+g', 'NaN456', '+NaN456'),
            ('.3e', 'Inf', 'Infinity'),
            ('.16f', '-Inf', '-Infinity'),
            ('.0g', '-sNaN', '-sNaN'),

            ('', '1.00', '1.00'),

            # test alignment and padding
            ('6', '123', '   123'),
            ('<6', '123', '123   '),
            ('>6', '123', '   123'),
            ('^6', '123', ' 123  '),
            ('=+6', '123', '+  123'),
            ('#<10', 'NaN', 'NaN#######'),
            ('#<10', '-4.3', '-4.3######'),
            ('#<+10', '0.0130', '+0.0130###'),
            ('#< 10', '0.0130', ' 0.0130###'),
            ('@>10', '-Inf', '@-Infinity'),
            ('#>5', '-Inf', '-Infinity'),
            ('?^5', '123', '?123?'),
            ('%^6', '123', '%123%%'),
            (' ^6', '-45.6', '-45.6 '),
            ('/=10', '-45.6', '-/////45.6'),
            ('/=+10', '45.6', '+/////45.6'),
            ('/= 10', '45.6', ' /////45.6'),
            ('\x00=10', '-inf', '-\x00Infinity'),
            ('\x00^16', '-inf', '\x00\x00\x00-Infinity\x00\x00\x00\x00'),
            ('\x00>10', '1.2345', '\x00\x00\x00\x001.2345'),
            ('\x00<10', '1.2345', '1.2345\x00\x00\x00\x00'),

            # thousands separator
            (',', '1234567', '1,234,567'),
            (',', '123456', '123,456'),
            (',', '12345', '12,345'),
            (',', '1234', '1,234'),
            (',', '123', '123'),
            (',', '12', '12'),
            (',', '1', '1'),
            (',', '0', '0'),
            (',', '-1234567', '-1,234,567'),
            (',', '-123456', '-123,456'),
            ('7,', '123456', '123,456'),
            ('8,', '123456', ' 123,456'),
            ('08,', '123456', '0,123,456'), # special case: extra 0 needed
            ('+08,', '123456', '+123,456'), # but not if there's a sign
            (' 08,', '123456', ' 123,456'),
            ('08,', '-123456', '-123,456'),
            ('+09,', '123456', '+0,123,456'),
            # ... with fractional part...
            ('07,', '1234.56', '1,234.56'),
            ('08,', '1234.56', '1,234.56'),
            ('09,', '1234.56', '01,234.56'),
            ('010,', '1234.56', '001,234.56'),
            ('011,', '1234.56', '0,001,234.56'),
            ('012,', '1234.56', '0,001,234.56'),
            ('08,.1f', '1234.5', '01,234.5'),
            # no thousands separators in fraction part
            (',', '1.23456789', '1.23456789'),
            (',%', '123.456789', '12,345.6789%'),
            (',e', '123456', '1.23456e+5'),
            (',E', '123456', '1.23456E+5'),

            # issue 6850
            ('a=-7.0', '0.12345', 'aaaa0.1'),
            ]
        for fmt, d, result in test_values:
            self.assertEqual(format(Decimal(d), fmt), result)

        # bytes format argument
        self.assertRaises(TypeError, Decimal(1).__format__, b'-020')

    def test_n_format(self):
        Decimal = self.decimal.Decimal

        try:
            from locale import CHAR_MAX
        except ImportError:
            self.skipTest('locale.CHAR_MAX not available')

        def make_grouping(lst):
            return ''.join([chr(x) for x in lst])

        def get_fmt(x, override=None, fmt='n'):
            return Decimal(x).__format__(fmt, override)

        # Set up some localeconv-like dictionaries
        en_US = {
            'decimal_point' : '.',
            'grouping' : make_grouping([3, 3, 0]),
            'thousands_sep' : ','
            }

        fr_FR = {
            'decimal_point' : ',',
            'grouping' : make_grouping([CHAR_MAX]),
            'thousands_sep' : ''
            }

        ru_RU = {
            'decimal_point' : ',',
            'grouping': make_grouping([3, 3, 0]),
            'thousands_sep' : ' '
            }

        crazy = {
            'decimal_point' : '&',
            'grouping': make_grouping([1, 4, 2, CHAR_MAX]),
            'thousands_sep' : '-'
            }

        dotsep_wide = {
            'decimal_point' : b'\xc2\xbf'.decode('utf-8'),
            'grouping': make_grouping([3, 3, 0]),
            'thousands_sep' : b'\xc2\xb4'.decode('utf-8')
            }

        self.assertEqual(get_fmt(Decimal('12.7'), en_US), '12.7')
        self.assertEqual(get_fmt(Decimal('12.7'), fr_FR), '12,7')
        self.assertEqual(get_fmt(Decimal('12.7'), ru_RU), '12,7')
        self.assertEqual(get_fmt(Decimal('12.7'), crazy), '1-2&7')

        self.assertEqual(get_fmt(123456789, en_US), '123,456,789')
        self.assertEqual(get_fmt(123456789, fr_FR), '123456789')
        self.assertEqual(get_fmt(123456789, ru_RU), '123 456 789')
        self.assertEqual(get_fmt(1234567890123, crazy), '123456-78-9012-3')

        self.assertEqual(get_fmt(123456789, en_US, '.6n'), '1.23457e+8')
        self.assertEqual(get_fmt(123456789, fr_FR, '.6n'), '1,23457e+8')
        self.assertEqual(get_fmt(123456789, ru_RU, '.6n'), '1,23457e+8')
        self.assertEqual(get_fmt(123456789, crazy, '.6n'), '1&23457e+8')

        # zero padding
        self.assertEqual(get_fmt(1234, fr_FR, '03n'), '1234')
        self.assertEqual(get_fmt(1234, fr_FR, '04n'), '1234')
        self.assertEqual(get_fmt(1234, fr_FR, '05n'), '01234')
        self.assertEqual(get_fmt(1234, fr_FR, '06n'), '001234')

        self.assertEqual(get_fmt(12345, en_US, '05n'), '12,345')
        self.assertEqual(get_fmt(12345, en_US, '06n'), '12,345')
        self.assertEqual(get_fmt(12345, en_US, '07n'), '012,345')
        self.assertEqual(get_fmt(12345, en_US, '08n'), '0,012,345')
        self.assertEqual(get_fmt(12345, en_US, '09n'), '0,012,345')
        self.assertEqual(get_fmt(12345, en_US, '010n'), '00,012,345')

        self.assertEqual(get_fmt(123456, crazy, '06n'), '1-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '07n'), '1-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '08n'), '1-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '09n'), '01-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '010n'), '0-01-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '011n'), '0-01-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '012n'), '00-01-2345-6')
        self.assertEqual(get_fmt(123456, crazy, '013n'), '000-01-2345-6')

        # wide char separator and decimal point
        self.assertEqual(get_fmt(Decimal('-1.5'), dotsep_wide, '020n'),
                         '-0\u00b4000\u00b4000\u00b4000\u00b4001\u00bf5')


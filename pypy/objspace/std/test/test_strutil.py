import autopath
from pypy.tool import testit
from pypy.objspace.std.strutil import *

class TestStrUtil(testit.TestCase):

    def test_string_to_int(self):
        cases = [('0', 0),
                 ('1', 1),
                 ('9', 9),
                 ('10', 10),
                 ('09', 9),
                 ('0000101', 101),    # not octal unless base 0 or 8
                 ('5123', 5123),
                 ('1891234174197319', 1891234174197319),
                 (' 0', 0),
                 ('0  ', 0),
                 (' \t \n   32313  \f  \v   \r  \n\r    ', 32313),
                 ('+12', 12),
                 ('-5', -5),
                 ('  -123456789 ', -123456789),
                 ]
        for s, expected in cases:
            self.assertEquals(string_to_int(s), expected)
            self.assertEquals(string_to_long(s), expected)

    def test_string_to_int_base(self):
        cases = [('111', 2, 7),
                 ('010', 2, 2),
                 ('102', 3, 11),
                 ('103', 4, 19),
                 ('107', 8, 71),
                 ('109', 10, 109),
                 ('10A', 11, 131),
                 ('10a', 11, 131),
                 ('10f', 16, 271),
                 ('10F', 16, 271),
                 ('0x10f', 16, 271),
                 ('0x10F', 16, 271),
                 ('10z', 36, 1331),
                 ('10Z', 36, 1331),
                 ('12',   0, 12),
                 ('015',  0, 13),
                 ('0x10', 0, 16),
                 ('0XE',  0, 14),
                 ('0',    0, 0),
                 ('0x',   0, 0),    # according to CPython so far
                 ('0X',   0, 0),    #     "           "
                 ('0x',  16, 0),    #     "           "
                 ('0X',  16, 0),    #     "           "
                 ]
        for s, base, expected in cases:
            self.assertEquals(string_to_int(s, base), expected)
            self.assertEquals(string_to_int('+'+s, base), expected)
            self.assertEquals(string_to_int('-'+s, base), -expected)
            self.assertEquals(string_to_int(s+'\n', base), expected)
            self.assertEquals(string_to_int('  +'+s, base), expected)
            self.assertEquals(string_to_int('-'+s+'  ', base), -expected)

    def test_string_to_int_error(self):
        cases = ['0x123',    # must use base 0 or 16
                 ' 0X12 ',
                 '',
                 '++12',
                 '+-12',
                 '-+12',
                 '--12',
                 '- 5',
                 '+ 5',
                 '12a6',
                 '12A6',
                 'f',
                 'Z',
                 '.',
                 '@',
                 ]
        for s in cases:
            self.assertRaises(ValueError, string_to_int, s)
            self.assertRaises(ValueError, string_to_int, '  '+s)
            self.assertRaises(ValueError, string_to_int, s+'  ')
            self.assertRaises(ValueError, string_to_int, '+'+s)
            self.assertRaises(ValueError, string_to_int, '-'+s)

    def test_string_to_int_base_error(self):
        cases = [('1', 1),
                 ('1', 37),
                 ('a', 0),
                 ('9', 9),
                 ('0x123', 7),
                 ('145cdf', 15),
                 ('12', 37),
                 ('12', 98172),
                 ('12', -1),
                 ('12', -908),
                 ('12.3', 10),
                 ('12.3', 13),
                 ('12.3', 16),
                 ]
        for s, base in cases:
            self.assertRaises(ValueError, string_to_int, s, base)
            self.assertRaises(ValueError, string_to_int, '  '+s, base)
            self.assertRaises(ValueError, string_to_int, s+'  ', base)
            self.assertRaises(ValueError, string_to_int, '+'+s, base)
            self.assertRaises(ValueError, string_to_int, '-'+s, base)

    def test_string_to_long(self):
        self.assertEquals(string_to_long('123L'), 123)
        self.assertEquals(string_to_long('123L  '), 123)
        self.assertRaises(ValueError, string_to_long, 'L')
        self.assertRaises(ValueError, string_to_long, 'L  ')
        self.assertEquals(string_to_long('123L', 4), 27)
        self.assertEquals(string_to_long('123L', 30), 27000 + 1800 + 90 + 21)
        self.assertEquals(string_to_long('123L', 22), 10648 + 968 + 66 + 21)
        self.assertEquals(string_to_long('123L', 21), 441 + 42 + 3)

if __name__ == '__main__':
    testit.main()

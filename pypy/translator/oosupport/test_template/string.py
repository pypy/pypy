import py
from pypy.rpython.test.test_rstr import BaseTestRstr
from pypy.rlib.objectmodel import compute_hash

class BaseTestString(BaseTestRstr):

    def test_char_isxxx(self):
        def fn(s):
            return (s.isspace()      |
                    s.isdigit() << 1 |
                    s.isalpha() << 2 |
                    s.isalnum() << 3 |
                    s.isupper() << 4 |
                    s.islower() << 5)
        # need to start from 1, because we cannot pass '\x00' as a
        # command line parameter
        for i in range(1, 128):
            ch = chr(i)
            res = self.interpret(fn, [ch])
            assert res == fn(ch)

    def test_replace_TyperError(self):
        pass # it doesn't make sense here

    def test_hash_value(self):
        # make sure that hash are computed by value and not by reference
        def fn(x, y):
            s1 = ''.join([x, 'e', 'l', 'l', 'o'])
            s2 = ''.join([y, 'e', 'l', 'l', 'o'])
            return (compute_hash(s1) == compute_hash(s2)) and (s1 is not s2)
        assert self.interpret(fn, ['h', 'h']) == True

    def test_int_formatting(self):
        def fn(answer):
            return 'the answer is %s' % answer
        assert self.ll_to_string(self.interpret(fn, [42])) == 'the answer is 42'

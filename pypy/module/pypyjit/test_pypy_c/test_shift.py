import py
from pypy.module.pypyjit.test_pypy_c.test_00_model import BaseTestPyPyC

class TestShift(BaseTestPyPyC):

    def test_shift_intbound(self):
        def main(b):
            res = 0
            a = 0
            while a < 300:
                assert a >= 0
                assert 0 <= b <= 10
                val = a >> b
                if val >= 0:    # ID: rshift
                    res += 1
                val = a << b
                if val >= 0:    # ID: lshift
                    res += 2
                a += 1
            return res
        #
        log = self.run(main, [2])
        assert log.result == 300*3
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('rshift', "")  # guard optimized away
        assert loop.match_by_id('lshift', "")  # guard optimized away

    def test_lshift_and_then_rshift(self):
        py.test.skip('fixme, this optimization is disabled')
        def main(b):
            res = 0
            a = 0
            while res < 300:
                assert a >= 0
                assert 0 <= b <= 10
                res = (a << b) >> b     # ID: shift
                a += 1
            return res
        #
        log = self.run(main, [2])
        assert log.result == 300
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('shift', "")  # optimized away

    def test_division_to_rshift(self):
        def main(b):
            res = 0
            a = 0
            while a < 300:
                assert a >= 0
                assert 0 <= b <= 10
                res = a/b     # ID: div
                a += 1
            return res
        #
        log = self.run(main, [3])
        assert log.result == 99
        loop, = log.loops_by_filename(self.filepath)
        assert loop.match_by_id('div', """
            i10 = int_floordiv(i6, i7)
            i11 = int_mul(i10, i7)
            i12 = int_sub(i6, i11)
            i14 = int_rshift(i12, 63)
            i15 = int_add(i10, i14)
        """)

    def test_division_to_rshift_allcases(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        avalues = ('a', 'b', 7, -42, 8)
        bvalues = ['b'] + range(-10, 0) + range(1,10)
        code = ''
        for a in avalues:
            for b in bvalues:
                code += '                sa += %s / %s\n' % (a, b)
        src = """
        def main(a, b):
            i = sa = 0
            while i < 300:
%s
                i += 1
            return sa
        """ % code
        self.run_and_check(src, [ 10,  20])
        self.run_and_check(src, [ 10, -20])
        self.run_and_check(src, [-10, -20])

    def test_mod(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        avalues = ('a', 'b', 7, -42, 8)
        bvalues = ['b'] + range(-10, 0) + range(1,10)
        code = ''
        for a in avalues:
            for b in bvalues:
                code += '                sa += %s %% %s\n' % (a, b)
        src = """
        def main(a, b):
            i = sa = 0
            while i < 2000:
                if a > 0: pass
                if 1 < b < 2: pass
%s
                i += 1
            return sa
        """ % code
        self.run_and_check(src, [ 10,  20])
        self.run_and_check(src, [ 10, -20])
        self.run_and_check(src, [-10, -20])

    def test_shift_allcases(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        from sys import maxint
        def main(a, b):
            i = sa = 0
            while i < 300:
                if a > 0: # Specialises the loop
                    pass
                if b < 2 and b > 0:
                    pass
                if (a >> b) >= 0:
                    sa += 1
                if (a << b) > 2:
                    sa += 10000
                i += 1
            return sa
        #
        maxvals = (-maxint-1, -maxint, maxint-1, maxint)
        for a in (-4, -3, -2, -1, 0, 1, 2, 3, 4) + maxvals:
            for b in (0, 1, 2, 31, 32, 33, 61, 62, 63):
                yield self.run_and_check, main, [a, b]

    def test_revert_shift_allcases(self):
        """
        This test only checks that we get the expected result, not that any
        optimization has been applied.
        """
        from sys import maxint

        def main(a, b, c):
            from sys import maxint
            i = sa = 0
            while i < 300:
                if 0 < a < 10: pass
                if -100 < b < 100: pass
                if -maxint/2 < c < maxint/2: pass
                sa += (a<<a)>>a
                sa += (b<<a)>>a
                sa += (c<<a)>>a
                sa += (a<<100)>>100
                sa += (b<<100)>>100
                sa += (c<<100)>>100
                i += 1
            return long(sa)

        for a in (1, 4, 8, 100):
            for b in (-10, 10, -201, 201, -maxint/3, maxint/3):
                for c in (-10, 10, -maxint/3, maxint/3):
                    yield self.run_and_check, main, [a, b, c]

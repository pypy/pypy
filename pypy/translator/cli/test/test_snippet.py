import py
from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.oosupport.test_template.snippets import BaseTestSnippets

class TestSnippets(BaseTestSnippets, CliTest):
    def test_llshl(self):
        py.test.skip('llshl currently broken on CLI')

    def test_link_SSA(self):
        def fn():
            lst = [42, 43, 44]
            for i in range(len(lst)):
                item = lst[i]
                if i < 10:
                    lst[i] = item+10
            return lst
        res = self.ll_to_list(self.interpret(fn, []))
        assert res == [52, 53, 54]

    def test_mangle(self):
        class Foo:
            def le(self):
                return 42

        def fn():
            f = Foo()
            return f.le()
        res = self.interpret(fn, [], backendopt=False)
        
    def test_link_vars_overlapping(self):
        from pypy.rlib.rarithmetic import ovfcheck
        def fn(maxofs):
            lastofs = 0
            ofs = 1
            while ofs < maxofs:
                lastofs = ofs
                try:
                    ofs = ovfcheck(ofs << 1)
                except OverflowError:
                    ofs = maxofs
                else:
                    ofs = ofs + 1
            return lastofs
        res = self.interpret(fn, [64])
        expected = fn(64)
        assert res == expected
        

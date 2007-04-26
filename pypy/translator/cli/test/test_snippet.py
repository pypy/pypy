from pypy.translator.cli.test.runtest import CliTest
from pypy.translator.oosupport.test_template.snippets import BaseTestSnippets

class TestSnippets(BaseTestSnippets, CliTest):
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



from rpython.rtyper.test.tool import BaseRtypingTest
from rpython.tool.udir import udir
from rpython.rlib import rfile

class TestFile(BaseRtypingTest):
    def test_open(self):
        fname = str(udir.join('test_file', 'file_1'))

        def f():
            f = open(fname, "w")
            f.write("dupa")
            f.close()

        self.interpret(f, [])
        assert open(fname, "r").read() == "dupa"

import sys
from types import MethodType

from pypy.translator.cli import conftest
from pypy.translator.cli.ilgenerator import IlasmGenerator
from pypy.translator.cli.function import Function
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.option import getoption
from pypy.translator.cli.database import LowLevelDatabase


class Tee(object):
    def __init__(self, *args):
        self.outfiles = args

    def write(self, s):
        for outfile in self.outfiles:
            outfile.write(s)

    def close(self):
        for outfile in self.outfiles:
            if outfile is not sys.stdout:
                outfile.close()

class GenCli(object):
    def __init__(self, tmpdir, translator, entrypoint = None):
        self.tmpdir = tmpdir
        self.translator = translator
        self.entrypoint = entrypoint
        self.db = LowLevelDatabase()

        if entrypoint is None:
            self.assembly_name = self.translator.graphs[0].name
        else:
            self.assembly_name = entrypoint.get_name()

        self.tmpfile = tmpdir.join(self.assembly_name + '.il')

    def generate_source(self):
        out = self.tmpfile.open('w')
        if getoption('stdout'):
            out = Tee(sys.stdout, out)

        self.ilasm = IlasmGenerator(out, self.assembly_name)
        
        # TODO: instance methods that are also called as unbound
        # methods are rendered twice, once within the class and once
        # as an external function. Fix this.        
        self.gen_entrypoint()
        self.gen_pendings()
        self.db.gen_constants(self.ilasm)
        self.gen_pendings()
        out.close()
        return self.tmpfile.strpath

    def gen_entrypoint(self):
        if self.entrypoint:
            self.entrypoint.db = self.db
            self.db.pending_node(self.entrypoint)
        else:
            self.db.pending_function(self.translator.graphs[0])

    def gen_pendings(self):
        while self.db._pending_nodes:
            node = self.db._pending_nodes.pop()
            node.render(self.ilasm)



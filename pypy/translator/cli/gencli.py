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
        self.find_superclasses()
        self.gen_classes()
        self.gen_functions()        
        out.close()
        return self.tmpfile.strpath

    def gen_entrypoint(self):
        if self.entrypoint:
            self.db.pending_graphs += self.entrypoint.render(self.ilasm)
        else:
            self.db.pending_graphs.append(self.translator.graphs[0])

        self.gen_functions()

    def gen_functions(self):
        while self.db.pending_graphs:
            graph = self.db.pending_graphs.pop()
            if self.db.function_name(graph) is None:
                f = Function(self.db, graph)
                f.render(self.ilasm)

    def find_superclasses(self):
        classes = set()
        pendings = self.db.classes

        while pendings:
            classdef = pendings.pop()
            if classdef not in classes and classdef is not None:
                classes.add(classdef)
                pendings.add(classdef._superclass)

        self.db.classes = classes

    def gen_classes(self):
        for classdef in self.db.classes:
            c = Class(self.db, classdef)
            c.render(self.ilasm)

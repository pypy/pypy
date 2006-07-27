import sys
import subprocess
import shutil

from pypy.translator.cli import conftest
from pypy.translator.cli.ilgenerator import IlasmGenerator
from pypy.translator.cli.function import Function, log
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.option import getoption
from pypy.translator.cli.database import LowLevelDatabase
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.opcodes import opcodes
from pypy.translator.cli.sdk import SDK
from pypy.translator.cli.rte import get_pypy_dll
from pypy.translator.cli.support import Tee


class GenCli(object):
    def __init__(self, tmpdir, translator, entrypoint=None, type_system_class=CTS,
                 opcode_dict=opcodes, name_suffix='.il', function_class=Function,
                 database_class = LowLevelDatabase, pending_graphs=()):
        self.tmpdir = tmpdir
        self.translator = translator
        self.entrypoint = entrypoint
        self.db = database_class(type_system_class = type_system_class, opcode_dict = opcode_dict,
            function_class = function_class)

        for graph, functype in pending_graphs:
            self.db.pending_function(graph, functype)

        if entrypoint is None:
            self.assembly_name = self.translator.graphs[0].name
        else:
            entrypoint.set_db(self.db)
            self.assembly_name = entrypoint.get_name()

        self.tmpfile = tmpdir.join(self.assembly_name + name_suffix)

    def generate_source(self , asm_class = IlasmGenerator ):
        out = self.tmpfile.open('w')
        if getoption('stdout'):
            out = Tee(sys.stdout, out)

        self.ilasm = asm_class(out, self.assembly_name )
        
        # TODO: instance methods that are also called as unbound
        # methods are rendered twice, once within the class and once
        # as an external function. Fix this.
        self.fix_names()
        self.gen_entrypoint()
        self.gen_pendings()
        self.db.gen_constants(self.ilasm)

        out.close()
        return self.tmpfile.strpath

    def gen_entrypoint(self):
        if self.entrypoint:
            self.entrypoint.db = self.db
            self.db.pending_node(self.entrypoint)
        else:
            self.db.pending_function(self.translator.graphs[0])

    def gen_pendings(self):
        n = 0
        while self.db._pending_nodes:
            node = self.db._pending_nodes.pop()
            node.render(self.ilasm)
            self.db._rendered_nodes.add(node)

            n+=1
            total = len(self.db._pending_nodes) + n
            log.graphs('Rendered %d/%d (approx. %.2f%%)' %\
                     (n, total, n*100.0/total))


    def fix_names(self):
        # it could happen that two distinct graph have the same name;
        # here we assign an unique name to each graph.
        names = set()
        for graph in self.translator.graphs:
            base_name = graph.name
            i = 0
            while graph.name in names:
                graph.name = '%s_%d' % (base_name, i)
                i+=1
            names.add(graph.name)

    def build_exe(self):        
        if getoption('source'):
            return None

        pypy_dll = get_pypy_dll() # get or recompile pypy.dll
        shutil.copy(pypy_dll, self.tmpdir.strpath)

        ilasm = SDK.ilasm()
        tmpfile = self.tmpfile.strpath
        self._exec_helper(ilasm, tmpfile, 'ilasm failed to assemble (%s):\n%s\n%s')

        exefile = tmpfile.replace('.il', '.exe')
        if getoption('verify'):
            peverify = SDK.peverify()
            self._exec_helper(peverify, exefile, 'peverify failed to verify (%s):\n%s\n%s')
        return exefile

    def _exec_helper(self, helper, filename, msg):
        proc = subprocess.Popen([helper, filename], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        retval = proc.wait()
        assert retval == 0, msg % (filename, stdout, stderr)
        

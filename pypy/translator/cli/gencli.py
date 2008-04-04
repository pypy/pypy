import sys
import shutil

import py
from py.compat import subprocess
from pypy.config.config import Config
from pypy.translator.oosupport.genoo import GenOO
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
from pypy.translator.cli.prebuiltnodes import get_prebuilt_nodes
from pypy.translator.cli import constant

class GenCli(GenOO):
    TypeSystem = CTS
    Function = Function
    opcodes = opcodes
    Database = LowLevelDatabase
    log = log
    
    ConstantGenerator = constant.StaticFieldConstGenerator
    InstanceConst = constant.CLIInstanceConst
    RecordConst = constant.CLIRecordConst
    ClassConst = constant.CLIClassConst
    ListConst = constant.CLIListConst
    ArrayConst = constant.CLIArrayConst
    StaticMethodConst = constant.CLIStaticMethodConst
    CustomDictConst = constant.CLICustomDictConst
    DictConst = constant.CLIDictConst
    WeakRefConst = constant.CLIWeakRefConst

    def __init__(self, tmpdir, translator, entrypoint, config=None, exctrans=False):
        GenOO.__init__(self, tmpdir, translator, entrypoint, config, exctrans)
        self.assembly_name = entrypoint.get_name()
        self.tmpfile = tmpdir.join(self.assembly_name + '.il')
        self.const_stat = str(tmpdir.join('const_stat'))

    def append_prebuilt_nodes(self):
        for node in get_prebuilt_nodes(self.translator, self.db):
            self.db.pending_node(node)

    def generate_source(self):
        GenOO.generate_source(self)
        self.db.const_count.dump(self.const_stat)
        return self.tmpfile.strpath

    def create_assembler(self):
        out = self.tmpfile.open('w')
        if getoption('stdout'):
            out = Tee(sys.stdout, out)
        isnetmodule = self.entrypoint.isnetmodule
        return IlasmGenerator(out, self.assembly_name, self.config, isnetmodule)

    def build_exe(self):        
        if getoption('source'):
            return None

        pypy_dll = get_pypy_dll() # get or recompile pypy.dll
        shutil.copy(pypy_dll, self.tmpdir.strpath)

        ilasm = SDK.ilasm()
        tmpfile = self.tmpfile.strpath
        self.outfile = self.entrypoint.output_filename(tmpfile)
        argv = [tmpfile,'/output:' + self.outfile] + self.entrypoint.ilasm_flags()
        self._exec_helper(ilasm, argv,
                          'ilasm failed to assemble (%s):\n%s\n%s',
                          timeout = 900)
        # Mono's ilasm occasionally deadlocks.  We set a timer to avoid
        # blocking automated test runs forever.


        if getoption('verify'):
            peverify = SDK.peverify()
            self._exec_helper(peverify, [outfile], 'peverify failed to verify (%s):\n%s\n%s')
        return self.outfile

    def _exec_helper(self, helper, args, msg, timeout=None):
        args = [helper] + args
        if timeout and not sys.platform.startswith('win'):
            import os
            from pypy.tool import autopath
            watchdog = os.path.join(autopath.pypydir, 'tool', 'watchdog.py')
            args[:0] = [sys.executable, watchdog, str(float(timeout))]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        retval = proc.wait()
        assert retval == 0, msg % (args[0], stdout, stderr)
        

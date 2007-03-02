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
from pypy.translator.cli.stackopt import StackOptGenerator
from pypy.translator.cli import query
from pypy.translator.cli import constant

try:
    set
except NameError:
    from sets import Set as set

#USE_STACKOPT = True and not getoption('nostackopt')
USE_STACKOPT = False


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
    StaticMethodConst = constant.CLIStaticMethodConst
    CustomDictConst = constant.CLICustomDictConst
    DictConst = constant.CLIDictConst
    WeakRefConst = constant.CLIWeakRefConst

    def __init__(self, tmpdir, translator, entrypoint, config=None):
        GenOO.__init__(self, tmpdir, translator, entrypoint, config)
        for node in get_prebuilt_nodes(translator, self.db):
            self.db.pending_node(node)
        self.assembly_name = entrypoint.get_name()
        self.tmpfile = tmpdir.join(self.assembly_name + '.il')
        self.const_stat = str(tmpdir.join('const_stat'))

    def generate_source(self):
        GenOO.generate_source(self)
        self.db.const_count.dump(self.const_stat)
        query.savedesc()
        return self.tmpfile.strpath

    def create_assembler(self):
        out = self.tmpfile.open('w')
        if getoption('stdout'):
            out = Tee(sys.stdout, out)

        if USE_STACKOPT:
            return StackOptGenerator(out, self.assembly_name, self.config)
        else:
            return IlasmGenerator(out, self.assembly_name, self.config)

    def build_exe(self):        
        if getoption('source'):
            return None

        pypy_dll = get_pypy_dll() # get or recompile pypy.dll
        shutil.copy(pypy_dll, self.tmpdir.strpath)

        ilasm = SDK.ilasm()
        tmpfile = self.tmpfile.strpath
        self._exec_helper(ilasm, tmpfile,
                          'ilasm failed to assemble (%s):\n%s\n%s',
                          timeout = 900)
        # Mono's ilasm occasionally deadlocks.  We set a timer to avoid
        # blocking automated test runs forever.

        exefile = tmpfile.replace('.il', '.exe')
        if getoption('verify'):
            peverify = SDK.peverify()
            self._exec_helper(peverify, exefile, 'peverify failed to verify (%s):\n%s\n%s')
        return exefile

    def _exec_helper(self, helper, filename, msg, timeout=None):
        args = [helper, filename]
        if timeout and not sys.platform.startswith('win'):
            import os
            from pypy.tool import autopath
            watchdog = os.path.join(autopath.pypydir, 'tool', 'watchdog.py')
            args[:0] = [sys.executable, watchdog, str(float(timeout))]
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        retval = proc.wait()
        assert retval == 0, msg % (filename, stdout, stderr)
        

'''
reference material:
    http://webreference.com/javascript/reference/core_ref/
    http://webreference.com/programming/javascript/
    http://mochikit.com/
    http://www.mozilla.org/js/spidermonkey/
    svn co http://codespeak.net/svn/kupu/trunk/ecmaunit 
'''

import py
import os

from pypy.rpython.rmodel import inputconst
from pypy.rpython.typesystem import getfunctionptr
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.ootypesystem import ootype
from pypy.tool.udir import udir
from pypy.translator.js2.log import log

from pypy.translator.js2.asmgen import AsmGen
from pypy.translator.js2.jts import JTS
from pypy.translator.js2.opcodes import opcodes
from pypy.translator.js2.function import Function

from pypy.translator.cli.gencli import GenCli

def _path_join(root_path, *paths):
    path = root_path
    for p in paths:
        path = os.path.join(path, p)
    return path

class JS(object):
    def __init__(self, translator, functions=[], stackless=False, compress=False, logging=False):
        self.cli = GenCli(udir, translator, type_system_class = JTS, opcode_dict = opcodes,\
            name_suffix = '.js', function_class = Function)
        self.translator = translator
    
    def write_source(self):
        self.cli.generate_source(AsmGen)
        self.filename = self.cli.tmpfile
        return self.cli.tmpfile

import py
from hypothesis import given
from rpython.tool.udir import udir
from rpython.jit.metainterp.optimize import SpeculativeError
from rpython.annotator.listdef import s_list_of_strings
from rpython.translator.translator import TranslationContext
from rpython.translator.c import genc
from rpython.jit.backend.llsupport.tl import interp
from rpython.jit.backend.llsupport.tl.test import code_strategies as st

def persist(type, contents):
    dir = udir.ensure(type)
    print "written", type, "to", dir
    with open(dir.strpath, 'wb') as fd:
        fd.write(contents)
    return dir.strpath

def persist_constants(consts):
    contents = ""
    for string in consts:
        contents += string.replace("\n", "\\n") + "\n"
    return persist('constants', contents)

def persist_bytecode(bc):
    return persist('bytecode', bc)

class GCHypothesis(object):
    builder = None
    def setup_method(self, name):
        if self.builder:
            return

        t = TranslationContext()
        t.config.translation.gc = "incminimark"
        t.config.translation.gcremovetypeptr = True
        ann = t.buildannotator()
        ann.build_types(interp.entry_point, [s_list_of_strings], main_entry_point=True)
        rtyper = t.buildrtyper()
        rtyper.specialize()

        cbuilder = genc.CStandaloneBuilder(t, interp.entry_point, t.config)
        cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
        cbuilder.compile()
        # prevent from rebuilding the c object!
        self.builder = cbuilder

    def execute(self, bytecode, consts):
        exe = self.builder.executable_name
        bc_file = persist_bytecode(bytecode)
        consts_file = persist_constants(consts)
        args = [bc_file, consts_file]
        env = {}
        res = self.builder.translator.platform.execute(exe, args, env=env)
        return res.returncode, res.out, res.err

    @given(st.bytecode_block())
    def test_execute_single_bytecode(self, program):
        bytecode, consts = program
        result, out, err = self.execute(bytecode, consts)
        if result != 0:
            raise Exception(("could not run program. returned %d"
                            " stderr:\n%s\nstdout:\n%s\n") % (result, err, out))

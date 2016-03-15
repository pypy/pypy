import py
from hypothesis import given, settings
from hypothesis.strategies import lists
from rpython.tool.udir import udir
from rpython.jit.metainterp.optimize import SpeculativeError
from rpython.annotator.listdef import s_list_of_strings
from rpython.translator.translator import TranslationContext
from rpython.translator.c import genc
from rpython.jit.backend.llsupport.tl import interp, code
from rpython.jit.backend.llsupport.tl.test import code_strategies as st

def persist(type, contents):
    dir = udir.ensure(type)
    with open(dir.strpath, 'wb') as fd:
        fd.write(contents)
    return dir.strpath

def persist_constants(consts):
    contents = ""
    for key, string in sorted(consts.items()):
        contents += string.replace("\n", "\\n") + "\n"
    return persist('constants', contents.encode('utf-8'))

def persist_bytecode(bc):
    return persist('bytecode', bc)


class GCHypothesis(object):

    def setup_class(cls):
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
        cls.builder = cbuilder

    def execute(self, bytecode, consts):
        exe = self.builder.executable_name
        bc_file = persist_bytecode(bytecode)
        consts_file = persist_constants(consts)
        args = [bc_file, consts_file]
        env = {}
        res = self.builder.translator.platform.execute(exe, args, env=env)
        return res.returncode, res.out, res.err

    # cannot have a non empty stack, cannot pass stack to executable!
    @given(st.bytecode())
    def test_execute_single_bytecode(self, bc_obj):
        bytecode, consts = code.Context().transform([bc_obj])
        result, out, err = self.execute(bytecode, consts)
        if result != 0:
            raise Exception(("could not run program. returned %d"
                            " stderr:\n%s\nstdout:\n%s\n") % (result, err, out))

    # cannot have a non empty stack, cannot pass stack to executable!
    @given(st.basic_block(st.bytecode(), min_size=1, average_size=24))
    def test_execute_basic_block(self, bc_objs):
        bytecode, consts = code.Context().transform(bc_objs)
        result, out, err = self.execute(bytecode, consts)
        if result != 0:
            raise Exception(("could not run program. returned %d"
                            " stderr:\n%s\nstdout:\n%s\n") % (result, err, out))

    @given(st.control_flow_graph())
    @settings(perform_health_check=False, min_satisfying_examples=1000)
    def test_execute_cfg(self, cfg):
        print "execute_cfg: cfg with steps:", cfg.interp_steps()
        bytecode, consts = cfg.linearize()
        result, out, err = self.execute(bytecode, consts)
        if result != 0:
            raise Exception(("could not run program. returned %d"
                            " stderr:\n%s\nstdout:\n%s\n") % (result, err, out))

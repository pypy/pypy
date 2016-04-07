
from rpython.jit.backend.llsupport.test.zrpy_vmprof_test import CompiledVmprofTest
from rpython.translator.translator import TranslationContext

class TestZVMprofSTM(CompiledVmprofTest):
    gcrootfinder = "stm"
    gc = "stmgc"
    thread = True
    stm = True

    def _get_TranslationContext(self):
        t = TranslationContext()
        t.config.translation.thread = True
        t.config.translation.stm = True
        t.config.translation.gc = "stmgc"
        t.config.translation.list_comprehension_operations = True
        return t

class TestZVMprof(CompiledVmprofTest):
    
    gcrootfinder = "shadowstack"
    gc = "incminimark"

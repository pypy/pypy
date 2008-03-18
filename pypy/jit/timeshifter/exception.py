from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.jit.timeshifter import rvalue, rtimeshift


class ExceptionDesc:

    def __init__(self, hrtyper, lazy_exception_path):
        RGenOp = hrtyper.RGenOp
        self.etrafo = hrtyper.annotator.exceptiontransformer
        self.cexcdata = self.etrafo.cexcdata
        self.exc_data_ptr = self.cexcdata.value
        self.gv_excdata = RGenOp.constPrebuiltGlobal(self.exc_data_ptr)

        EXCDATA = self.etrafo.EXCDATA
        LL_EXC_TYPE = self.etrafo.lltype_of_exception_type
        LL_EXC_VALUE = self.etrafo.lltype_of_exception_value
        self.exc_type_token  = RGenOp.fieldToken(EXCDATA, 'exc_type')
        self.exc_value_token = RGenOp.fieldToken(EXCDATA, 'exc_value')
        self.exc_type_kind   = RGenOp.kindToken(LL_EXC_TYPE)
        self.exc_value_kind  = RGenOp.kindToken(LL_EXC_VALUE)

        null_exc_type = self.etrafo.c_null_etype.value
        null_exc_value = self.etrafo.c_null_evalue.value
        self.gv_null_exc_type = RGenOp.constPrebuiltGlobal(null_exc_type)
        self.gv_null_exc_value = RGenOp.constPrebuiltGlobal(null_exc_value)

        if hrtyper.rtyper.type_system.name == 'lltypesystem':
            self.null_exc_type_box = rvalue.PtrRedBox(self.exc_type_kind,
                                                      self.gv_null_exc_type)
            self.null_exc_value_box = rvalue.PtrRedBox(self.exc_value_kind,
                                                       self.gv_null_exc_value)
        else:
            # XXX: think more about exceptions
            self.null_exc_type_box = rvalue.PtrRedBox(self.exc_type_kind,
                                                      RGenOp.constPrebuiltGlobal(llmemory.NULL))
            self.null_exc_value_box = rvalue.PtrRedBox(self.exc_value_kind,
                                                       RGenOp.constPrebuiltGlobal(llmemory.NULL))
            
        self.lazy_exception_path = lazy_exception_path

    def _freeze_(self):
        return True

    def genop_get_exc_type(self, builder):
        return builder.genop_getfield(self.exc_type_token, self.gv_excdata)

    def genop_get_exc_value(self, builder):
        return builder.genop_getfield(self.exc_value_token, self.gv_excdata)

    def genop_set_exc_type(self, builder, gv_value):
        builder.genop_setfield(self.exc_type_token, self.gv_excdata, gv_value)

    def genop_set_exc_value(self, builder, gv_value):
        builder.genop_setfield(self.exc_value_token, self.gv_excdata, gv_value)

    def fetch_global_excdata(self, jitstate, known_occurred=False):
        builder = jitstate.curbuilder
        gv_etype  = self.genop_get_exc_type (builder)
        gv_evalue = self.genop_get_exc_value(builder)
        self.genop_set_exc_type (builder, self.gv_null_exc_type )
        self.genop_set_exc_value(builder, self.gv_null_exc_value)
        etypebox  = rvalue.PtrRedBox(self.exc_type_kind,  gv_etype )
        evaluebox = rvalue.PtrRedBox(self.exc_value_kind, gv_evalue)
        etypebox .known_nonzero = known_occurred
        evaluebox.known_nonzero = known_occurred
        rtimeshift.setexctypebox (jitstate, etypebox)
        rtimeshift.setexcvaluebox(jitstate, evaluebox)

    def store_global_excdata(self, jitstate):
        builder = jitstate.curbuilder
        etypebox = jitstate.exc_type_box
        if etypebox.is_constant():
            # we should really use LL_EXC_TYPE instead of Address, but at the moment it crashes with ootype
            #LL_EXC_TYPE = self.etrafo.lltype_of_exception_type
            #ll_etype = rvalue.ll_getvalue(etypebox, LL_EXC_TYPE)
            ll_etype = rvalue.ll_getvalue(etypebox, llmemory.Address)
            if not ll_etype:
                return       # we know there is no exception set
        evaluebox = jitstate.exc_value_box
        gv_etype  = etypebox .getgenvar(jitstate)
        gv_evalue = evaluebox.getgenvar(jitstate)
        self.genop_set_exc_type (builder, gv_etype )
        self.genop_set_exc_value(builder, gv_evalue)

    def gen_exc_occurred(self, builder):
        gv_etype = self.genop_get_exc_type(builder)
        return builder.genop_ptr_nonzero(self.exc_type_kind, gv_etype)

from pypy.translator.jvm.generator import \
     Field, Method
from pypy.translator.oosupport.constant import \
     BaseConstantGenerator, RecordConst, InstanceConst, ClassConst
from pypy.translator.jvm.typesystem import \
     jPyPyConst, jObject, jVoid

# ___________________________________________________________________________
# Constant Generator

class JVMConstantGenerator(BaseConstantGenerator):

    # _________________________________________________________________
    # Constant Operations
    #
    # We store constants in static fields of the jPyPyConst class.
    
    def _init_constant(self, const):
        fieldty = self.db.lltype_to_cts(const.OOTYPE())
        const.fieldobj = Field(jPyPyConst.name, const.name, fieldty, True)

    def push_constant(self, gen, const):
        const.fieldobj.load(gen)

    def _store_constant(self, gen, const):
        const.fieldobj.store(gen)

    # _________________________________________________________________
    # Constant Generation
    
    def _begin_gen_constants(self, gen, all_constants):
        gen.begin_class(jPyPyConst, jObject)
        return gen

    def _declare_const(self, gen, const):
        gen.add_field(const.fieldobj)

    def _declare_step(self, gen, stepnum):
        next_nm = "constant_init_%d" % stepnum
        gen.begin_function(next_nm, [], [], jVoid, True)

    def _close_step(self, gen, stepnum):
        gen.return_val(jVoid)
        gen.end_function()    # end constant_init_N where N == stepnum
    
    def _end_gen_constants(self, gen, numsteps):
        # The static init code just needs to call constant_init_1..N
        gen.begin_function('<clinit>', [], [], jVoid, True)
        for x in range(numsteps):
            m = Method.s(jPyPyConst, "constant_init_%d" % x, [], jVoid)
            gen.emit(m)
        gen.return_val(jVoid)
        gen.end_function()
        
        gen.end_class()
    

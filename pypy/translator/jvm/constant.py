from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.generator import \
     Field, Method, CUSTOMDICTMAKE
from pypy.translator.oosupport.constant import \
     BaseConstantGenerator, RecordConst, InstanceConst, ClassConst, \
     StaticMethodConst, CustomDictConst
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
    
class JVMStaticMethodConst(StaticMethodConst):

    def record_dependencies(self):
        if self.value is ootype.null(self.value._TYPE):
            self.delegate_impl = None
            return
        StaticMethodConst.record_dependencies(self)
        self.delegate_impl = self.db.record_delegate_standalone_func_impl(
            self.value.graph)

    def create_pointer(self, gen):
        if self.delegate_impl:
            gen.new_with_jtype(self.delegate_impl)
        else:
            gen.push_null(jObject)

    def initialize_data(self, ilasm):
        return
    
class JVMCustomDictConst(CustomDictConst):

    def record_dependencies(self):
        # Near as I can tell, self.value is an ootype._custom_dict,
        # key_eq is a Python function and graph is, well, a method
        # graph that seems to be added to the function pointer
        # somewhere.  Adapted from cli/constant.py
        self.eq_jcls = self.db.record_delegate_standalone_func_impl(
            self.value._dict.key_eq.graph)
        self.hash_jcls = self.db.record_delegate_standalone_func_impl(
            self.value._dict.key_hash.graph)
        
    def create_pointer(self, gen):
        gen.new_with_jtype(self.eq_jcls)
        gen.new_with_jtype(self.hash_jcls)
        gen.emit(CUSTOMDICTMAKE)
        

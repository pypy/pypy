from pypy.rpython.ootypesystem import ootype
from pypy.objspace.flow import model as flowmodel
import pypy.translator.jvm.typesystem as jvm
from pypy.translator.jvm.typesystem import \
     jVoid, Method, Field
from pypy.translator.oosupport.constant import \
     BaseConstantGenerator, RecordConst, InstanceConst, ClassConst, \
     StaticMethodConst, CustomDictConst, WeakRefConst, push_constant, \
     MAX_CONST_PER_STEP

jPyPyConstantInit = jvm.JvmClassType('pypy.ConstantInit')
jPyPyConstantInitMethod = Method.s(jPyPyConstantInit, 'init', [], jVoid)

# ___________________________________________________________________________
# Constant Generator

class JVMConstantGenerator(BaseConstantGenerator):

    MAX_INSTRUCTION_COUNT = 20000

    def __init__(self, db):
        BaseConstantGenerator.__init__(self, db)
        self.num_constants = 0
        self.ccs = []

    def runtime_init(self, gen):
        """
        Called from node.EntryPoint to generate code that initializes
        all of the constants.  Right now, this invokes a known static
        method, but this should probably be changed eventually.
        """
        gen.emit(jPyPyConstantInitMethod)

    # _________________________________________________________________
    # Constant Operations
    #
    # We store constants in static fields of a constant class; we
    # generate new constant classes every MAX_CONST_PER_STEP constants
    # to avoid any particular class getting too big.
    
    def _init_constant(self, const):
        # Determine the Java type of the constant: some constants
        # (weakrefs) do not have an OOTYPE, so if it returns None use
        # jtype()                
        JFIELDOOTY = const.OOTYPE()
        if not JFIELDOOTY: jfieldty = const.jtype()
        else: jfieldty = self.db.lltype_to_cts(JFIELDOOTY)

        # Every MAX_CONST_PER_STEP constants, we create a new class.
        # This prevents any one class from getting too big.
        if (self.num_constants % MAX_CONST_PER_STEP) == 0:
            cc_num = len(self.ccs)
            self.ccs.append(jvm.JvmClassType('pypy.Constant_%d' % cc_num))
        self.num_constants += 1

        const.fieldobj = Field(self.ccs[-1].name, const.name, jfieldty, True)

    def push_constant(self, gen, const):
        const.fieldobj.load(gen)

    def _store_constant(self, gen, const):
        const.fieldobj.store(gen)

    # _________________________________________________________________
    # Constant Generation
    #
    # The JVM constants are generated as follows:
    #
    #   First, a set of classes are used as simple structs with static
    #   fields that store each constant.  These class names have already
    #   been generated, and they are stored in the member array self.ccs.
    #   Therefore, the first thing we do is to generate these classes
    #   by iterating over all constants and declaring their fields.
    #
    #   We then generate initialization code the constants in a SEPARATE
    #   set of classes, named pypy.ConstantInit_NNN.  We generate one such
    #   class for each "step" of the underlying BaseConstantGenerator.
    #
    #   Note that, in this setup, we cannot rely on the JVM's class init
    #   to initialize our constants for us: instead, we generate a static
    #   method (jPyPyConstantInitMethod) in _end_gen_constants() that
    #   invokes each of the ConstantInit_NNN's methods.  
    #
    #   Normally, these static field classes and the initialization
    #   code are stored together.  The JVM stores them seperately,
    #   because otherwise it is quite hard to ensure that (a) the
    #   constants are initialized in the right order, and (b) all of
    #   the constant declarations are emitted when they are needed.

    def gen_constants(self, ilasm):
        self.step_classes = []
        
        # First, create the classes that store the static fields.
        constants_by_cls = {}
        for const in self.cache.values():
            try:
                constants_by_cls[const.fieldobj.class_name].append(const)
            except KeyError:
                constants_by_cls[const.fieldobj.class_name] = [const]
        for cc in self.ccs:
            ilasm.begin_class(cc, jvm.jObject)
            for const in constants_by_cls[cc.name]:
                ilasm.add_field(const.fieldobj)
            ilasm.end_class()

        # Now, delegate to the normal code for the rest
        super(JVMConstantGenerator, self).gen_constants(ilasm)
    
    def _begin_gen_constants(self, gen, all_constants):
        return gen

    def _declare_const(self, gen, const):
        # in JVM, this is done first, in gen_constants()
        return

    def _consider_split_current_function(self, gen):
        if gen.get_instruction_count() >= self.MAX_INSTRUCTION_COUNT:
            const = self.current_const
            gen.pop(const.value._TYPE)
            self._new_step(gen)
            self._push_constant_during_init(gen, const)

    def _declare_step(self, gen, stepnum):
        self.step_classes.append(jvm.JvmClassType(
            'pypy.ConstantInit_%d' % stepnum))
        gen.begin_class(self.step_classes[-1], jvm.jObject)
        gen.begin_function('constant_init', [], [], jVoid, True)

    def _close_step(self, gen, stepnum):
        gen.return_val(jVoid)
        gen.end_function()    # end constant_init()
        gen.end_class()       # end pypy.ConstantInit_NNN
    
    def _end_gen_constants(self, gen, numsteps):
        gen.begin_class(jPyPyConstantInit, jvm.jObject)
        gen.begin_j_function(jPyPyConstantInit, jPyPyConstantInitMethod)
        for cls in self.step_classes:
            m = Method.s(cls, "constant_init", [], jVoid)
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
            gen.push_null(jvm.jObject)

    def initialize_data(self, constgen, gen):
        return
    
class JVMCustomDictConst(CustomDictConst):

    def record_dependencies(self):
        # Near as I can tell, self.value is an ootype._custom_dict,
        # key_eq is a Python function and graph is, well, a method
        # graph that seems to be added to the function pointer
        # somewhere.  Adapted from cli/constant.py
        if self.value is ootype.null(self.value._TYPE):
            return
        self.eq_jcls = self.db.record_delegate_standalone_func_impl(
            self.value._dict.key_eq.graph)
        self.hash_jcls = self.db.record_delegate_standalone_func_impl(
            self.value._dict.key_hash.graph)
        
        CustomDictConst.record_dependencies(self)
        
    def create_pointer(self, gen):
        gen.new_with_jtype(self.eq_jcls)
        gen.new_with_jtype(self.hash_jcls)
        gen.emit(jvm.CUSTOMDICTMAKE)
        
class JVMWeakRefConst(WeakRefConst):

    # Ensure that weak refs are initialized last:
    PRIORITY = 200

    def jtype(self):
        return jvm.jPyPyWeakRef

    def create_pointer(self, gen):        
        if not self.value:
            TYPE = ootype.ROOT
            gen.push_null(TYPE)
        else:
            TYPE = self.value._TYPE
            push_constant(self.db, self.value._TYPE, self.value, gen)
        gen.create_weakref(TYPE)

    def initialize_data(self, constgen, gen):
        gen.pop(ootype.ROOT)
        return True
    
    
    

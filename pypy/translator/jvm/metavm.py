from pypy.translator.oosupport.metavm import MicroInstruction
from pypy.translator.jvm.typesystem import JvmScalarType, JvmClassType
import pypy.translator.jvm.generator as jvmgen
import pypy.translator.jvm.typesystem as jvmtype

class _IndirectCall(MicroInstruction):
    def render(self, gen, op):
        interface = gen.db.lltype_to_cts(op.args[0].concretetype)
        method = interface.lookup_method('invoke')
        gen.emit(method)
IndirectCall = _IndirectCall()

class _JvmCallMethod(MicroInstruction):

    def _invoke_method(self, gen, db, jmethod, jactargs, args, jactres, res):
        for arg, jmthdty in zip(args, jactargs):
            # Load the argument on the stack:
            gen.load(arg)
            
            # Perform any boxing required:
            jargty = db.lltype_to_cts(arg.concretetype)
            if jargty != jmthdty:
                gen.prepare_generic_argument(arg.concretetype)
                
        gen.emit(jmethod)

        # Perform any unboxing required:
        jresty = db.lltype_to_cts(res.concretetype)
        if jresty != jactres:
            gen.prepare_generic_result(res.concretetype)
    
    def render(self, gen, op):

        method = op.args[0] # a FlowConstant string...
        this = op.args[1]

        # Locate the java method we will be invoking:
        thisjtype = gen.db.lltype_to_cts(this.concretetype)
        jmethod = thisjtype.lookup_method(method.value)

        # Ugly: if jmethod ends up being a static method, then
        # peel off the first argument
        jactargs = jmethod.argument_types
        if jmethod.is_static():
            jactargs = jactargs[1:]

        # Iterate through the arguments, inserting casts etc as required
        gen.load(this)
        self._invoke_method(gen, gen.db, jmethod,
                            jactargs, op.args[2:],
                            jmethod.return_type, op.result)
JvmCallMethod = _JvmCallMethod()

class TranslateException(MicroInstruction):
    """ Translates an exception into a call of a method on the PyPy object """
    def __init__(self, jexc, pexcmthd, inst):
        """
        jexc: the JvmType of the exception
        pexcmthd: the name of the method on the PyPy object to call.
        The PyPy method must take no arguments, return void, and must
        always throw an exception in practice.
        """
        self.java_exc = jexc
        self.pypy_method = jvmgen.Method.s(
            jvmtype.jPyPy, pexcmthd, [], jvmtype.jVoid)
        self.instruction = inst
        
    def render(self, gen, op):
        trylbl = gen.unique_label('translate_exc_begin')
        catchlbl = gen.unique_label('translate_exc_catch')
        donelbl = gen.unique_label('translate_exc_done')

        # try {
        gen.mark(trylbl)
        self.instruction.render(gen, op)
        gen.goto(donelbl)
        # } catch (JavaExceptionType) {
        gen.mark(catchlbl)
        gen.emit(jvmgen.POP)
        gen.emit(self.pypy_method)
        # Note: these instructions will never execute, as we expect
        # the pypy_method to throw an exception and not to return.  We
        # need them here to satisfy the Java verifier, however, as it
        # does not know that the pypy_method will never return.
        gen.emit(jvmgen.ACONST_NULL)
        gen.emit(jvmgen.ATHROW)
        # }
        gen.mark(donelbl)

        gen.try_catch_region(self.java_exc, trylbl, catchlbl, catchlbl)
        
class _NewCustomDict(MicroInstruction):
    def _load_func(self, gen, fn, obj, method_name):
        db = gen.db
        if fn.value:
            # Standalone function: find the delegate class and
            # instantiate it.
            assert method_name.value is None
            smimpl = fn.value.concretize().value   # ootype._static_meth
            db.record_delegate(smimpl._TYPE)       # _TYPE is a StaticMethod
            ty = db.record_delegate_standalone_func_impl(smimpl.graph)
            gen.new_with_jtype(ty)
        else:
            # Bound method: create a wrapper bound to the given
            # object, using the "bind()" static method that bound
            # method wrapper classes have.
            INSTANCE = obj.concretetype
            method_name = method_name.value
            ty = db.record_delegate_bound_method_impl(INSTANCE, method_name)
            gen.load(obj)
            gen.emit(ty.bind_method)
    def render(self, generator, op):
        self._load_func(generator, *op.args[1:4])
        self._load_func(generator, *op.args[4:7])
        generator.emit(jvmgen.CUSTOMDICTMAKE)
NewCustomDict = _NewCustomDict()

class _CastPtrToWeakAddress(MicroInstruction):
    def render(self, generator, op):
        arg = op.args[0]
        generator.prepare_cast_ptr_to_weak_address()
        generator.load(arg)
        generator.finalize_cast_ptr_to_weak_address(arg.concretetype)
        generator.store(op.result)
CastPtrToWeakAddress = _CastPtrToWeakAddress()
        
class _CastWeakAddressToPtr(MicroInstruction):
    def render(self, generator, op):
        RESULTTYPE = op.result.concretetype
        generator.cast_weak_address_to_ptr(RESULTTYPE)
CastWeakAddressToPtr = _CastWeakAddressToPtr()


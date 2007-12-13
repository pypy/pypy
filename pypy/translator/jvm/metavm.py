from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.metavm import MicroInstruction
from pypy.translator.jvm.typesystem import JvmScalarType, JvmClassType
import pypy.translator.jvm.generator as jvmgen
import pypy.translator.jvm.typesystem as jvmtype
from pypy.translator.jvm.builtin import JvmBuiltInType

class _IndirectCall(MicroInstruction):
    def render(self, gen, op):
        interface = gen.db.lltype_to_cts(op.args[0].concretetype)
        method = interface.lookup_method('invoke')
        gen.emit(method)
IndirectCall = _IndirectCall()

class _JvmCallMethod(MicroInstruction):

    def _invoke_method(self, gen, db, jmethod, jactargs, args, jactres, res):
        assert len(args) == len(jactargs)
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

        # if this is a builtin-type, the signature is exact and we
        # need to keep Void values; else, the signature does not
        # include Void values, so we need to drop them.
        if isinstance(thisjtype, JvmBuiltInType):
            args = op.args[2:]
        else:
            args = [arg for arg in op.args[2:] if arg.concretetype is not ootype.Void]

        # Ugly: if jmethod ends up being a static method, then
        # peel off the first argument
        jactargs = jmethod.argument_types
        if jmethod.is_static():
            jactargs = jactargs[1:]

        # Iterate through the arguments, inserting casts etc as required
        gen.load(this)
        self._invoke_method(gen, gen.db, jmethod,
                            jactargs, args,
                            jmethod.return_type, op.result)
JvmCallMethod = _JvmCallMethod()

class TranslateException(MicroInstruction):
    """ Translates an exception into a call of a method on the PyPy object """
    def __init__(self, jexc, pexcmthd, inst):
        """
        jexc: the JvmType of the exception
        pexcmthd: the name of the method on the PyPy object to call.
        The PyPy method must take no arguments, return void, and must
        always throw an exception in practice.  It would be better to
        just find the class to throw normally, but I don't know how.
        """
        self.java_exc = jexc
        self.pypy_method = jvmgen.Method.v(
            jvmtype.jPyPyInterlink, pexcmthd, [], jvmtype.jVoid)
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
        gen.emit(jvmgen.POP)            # throw away the exception object
        gen.push_pypy()                 # load the PyPy object
        gen.emit(jvmgen.PYPYINTERLINK)  # load the interlink field from it
        gen.emit(self.pypy_method)      # invoke the method
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
            smimpl = fn.value                      # ootype._static_meth
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

#XXX These classes have been adapted to the new
#XXX WeakRef methods, but don't appear to be needed.
#class _CastPtrToWeakAddress(MicroInstruction):
#    def render(self, generator, op):
#        arg = op.args[0]
#        generator.load(arg)
#        generator.create_weakref(arg.concretetype)
#        generator.store(op.result)
#CastPtrToWeakAddress = _CastPtrToWeakAddress()
        
#class _CastWeakAddressToPtr(MicroInstruction):
#    def render(self, generator, op):
#        RESULTTYPE = op.result.concretetype
#        generator.deref_weakref(RESULTTYPE)
#CastWeakAddressToPtr = _CastWeakAddressToPtr()


CASTS = {
#   FROM                      TO
    (ootype.Signed,           ootype.UnsignedLongLong): jvmgen.I2L,
    (ootype.SignedLongLong,   ootype.Signed):           jvmgen.L2I,
    (ootype.UnsignedLongLong, ootype.SignedLongLong):   None,
    }

class _CastPrimitive(MicroInstruction):
    def render(self, generator, op):
        FROM = op.args[0].concretetype
        TO = op.result.concretetype
        opcode = CASTS[(FROM, TO)]
        if opcode:
            generator.emit(opcode)
CastPrimitive = _CastPrimitive()

class _PushPyPy(MicroInstruction):
    """ Pushes the PyPy instance where our helper functions are found
    from the static field on the generated PyPyMain class """
    def render(self, generator, op):
        generator.push_pypy()
PushPyPy = _PushPyPy()

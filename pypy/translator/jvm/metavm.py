from pypy.translator.oosupport.metavm import MicroInstruction
from pypy.translator.jvm.typesystem import JvmScalarType, JvmClassType

class _IndirectCall(MicroInstruction):
    def render(self, gen, op):
        interface = gen.db.lltype_to_cts(op.args[0].concretetype)
        method = interface.lookup_method('invoke')
        gen.emit(method)
IndirectCall = _IndirectCall()

class _JvmCallMethod(MicroInstruction):

    def _invoke_method(self, gen, db, jmethod, jactargs, args, jactres, res):
        for arg, jmthdty in zip(args, jactargs):
            jargty = db.lltype_to_cts(arg.concretetype)

            # Load the argument on the stack:
            gen.load(arg)
            
            # Perform any boxing required:
            if (isinstance(jargty, JvmScalarType) and
                not isinstance(jmthdty, JvmScalarType)):
                gen.box_value(jargty)
                
        gen.emit(jmethod)
        
        jresty = db.lltype_to_cts(res.concretetype)

        if (isinstance(jresty, JvmScalarType) and
            not isinstance(jactres, JvmScalarType)):
            # Perform any un-boxing required:
            gen.downcast_jtype(jresty.box_type)
            gen.unbox_value(jresty)
        elif jresty != jactres:
            # Perform any casting required:
            gen.downcast(res.concretetype)
    
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

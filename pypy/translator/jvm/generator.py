try:
    import pycrash
    mypycrash = pycrash.PyCrash({'AppName': 'genjvm'})
except ImportError:
    mypycrash = None

from pypy.objspace.flow import model as flowmodel
from pypy.translator.oosupport.metavm import Generator
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.function import render_sub_op
from pypy.rpython.ootypesystem import ootype
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rlib.rarithmetic import isnan, isinf
from pypy.translator.oosupport.constant import push_constant
import pypy.translator.jvm.typesystem as jvm

# Load a few commonly used names, but prefer to use 'jvm.Name'
from pypy.translator.jvm.typesystem import \
     jPyPy, jString, jInt, jVoid

# ___________________________________________________________________________
# Labels
#
# We use a class here just for sanity checks and debugging print-outs.

class Label(object):

    def __init__(self, number, desc):
        """ number is a unique integer
        desc is a short, descriptive string that is a valid java identifier """
        self.label = "%s_%s" % (desc, number)

    def __repr__(self):
        return "Label(%s)"%self.label

    def jasmin_syntax(self):
        return self.label
    
# ___________________________________________________________________________
# Generator State

class ClassState(object):
    """ When you invoked begin_class(), one of these objects is allocated
    and tracks the state as we go through the definition process. """
    def __init__(self, classty, superclassty):
        self.class_type = classty
        self.superclass_type = superclassty
        self.line_number = 1
    def out(self, arg):
        self.file.write(arg)
        self.line_number += arg.count("\n")

class FunctionState(object):
    """ When you invoked begin_function(), one of these objects is allocated
    and tracks the state as we go through the definition process. """
    def __init__(self):
        self.next_offset = 0
        self.local_vars = {}
        self.function_arguments = []
        self.instr_counter = 0
    def add_var(self, jvar, jtype, is_param):
        """ Adds new entry for variable 'jvar', of java type 'jtype' """
        idx = self.next_offset
        self.next_offset += jtype.descriptor.type_width()
        if jvar:
            assert jvar.name not in self.local_vars # never been added before
            self.local_vars[jvar.name] = (idx, jtype)
        if is_param:
            self.function_arguments.append((jtype, idx))
        return idx
    def var_offset(self, jvar, jtype):
        """ Returns offset for variable 'jvar', of java type 'jtype' """
        if jvar.name in self.local_vars:
            return self.local_vars[jvar.name][0]
        return self.add_var(jvar, jtype, False)
    def var_info_list(self):
        var_info_list = [None] * self.next_offset
        for name, (idx, jtype) in self.local_vars.items():
            var_info_list[idx] = (name, jtype)
        return var_info_list
        


# ___________________________________________________________________________
# Generator

class JVMGenerator(Generator):

    """ Base class for all JVM generators.  Invokes a small set of '_'
    methods which indicate which opcodes to emit; these can be
    translated by a subclass into Jasmin assembly, binary output, etc.
    Must be inherited from to specify a particular output format;
    search for the string 'unimplemented' to find the methods that
    must be overloaded. """

    def __init__(self, db):
        self.db = db
        self.label_counter = 0
        self.curclass = None
        self.curfunc = None

    # __________________________________________________________________
    # JVM specific methods to be overloaded by a subclass
    #
    # If the name does not begin with '_', it will be called from
    # outside the generator.

    def begin_class(self, classty, superclsty,
                    abstract=False, interface=False):
        """
        Begins a class declaration.  Overall flow of class declaration
        looks like:

        begin_class()
        {implements()}
        {add_field()}
        begin_constructor()...end_constructor()
        [begin_function()...end_function()]
        end_class()

        Where items in brackets may appear anywhere from 0 to inf times.
        
        classty --- JvmType for the class
        superclassty --- JvmType for the superclass
        """
        assert not self.curclass
        self.curclass = ClassState(classty, superclsty)
        self._begin_class(abstract, interface)

    def end_class(self):
        self._end_class()
        self.curclass = None
        self.curfunc = None

    def current_type(self):
        """ Returns the jvm type we are currently defining.  If
        begin_class() has not been called, returns None. """
        return self.curclass.class_type

    def _begin_class(self, abstract, interface):
        """ Main implementation of begin_class """
        raise NotImplementedError

    def _end_class(self):
        """ Main implementation of end_class """
        raise NotImplementedError    

    def implements(self, jinterface):
        """
        Indicates that the current class implements the interface
        jinterface, which should be a JvmType.
        """
        raise NotImplementedError

    def add_field(self, fobj):
        """
        fobj: a Field object
        """
        unimplemented

    def begin_constructor(self):
        """
        Emits the constructor for this class, which merely invokes the
        parent constructor.
        
        superclsnm --- same Java name of super class as from begin_class
        """
        self.begin_function("<init>", [], [self.current_type()], jVoid)
        self.load_jvm_var(self.current_type(), 0)
        jmethod = jvm.Method.c(self.curclass.superclass_type, ())
        jmethod.invoke(self)

    def end_constructor(self):
        self.return_val(jVoid)
        self.end_function()

    def begin_j_function(self, cls_obj, method_obj, abstract=False):
        """
        A convenience function that invokes begin_function() with the
        appropriate arguments to define a method on class 'cls_obj' that
        could be invoked with 'method_obj'.
        """
        if method_obj.is_static(): def_args = []
        else: def_args = [cls_obj]
        return self.begin_function(method_obj.method_name,
                                   [],
                                   def_args+method_obj.argument_types,
                                   method_obj.return_type,
                                   static=method_obj.is_static(),
                                   abstract=abstract)
    
    def begin_function(self, funcname, argvars, argtypes, rettype,
                       static=False, abstract=False, final=False):
        """
        funcname --- name of the function
        argvars --- list of objects passed to load() that represent arguments;
                    should be in order, or () if load() will not be used
        argtypes --- JvmType for each argument [INCLUDING this]
        rettype --- JvmType for the return value
        static --- keyword, if true then a static func is generated
        final --- keyword, if true then a final method is generated

        This function also defines the scope for variables passed to
        load()/store().
        """
        # Compute the indicates of each argument in the local variables
        # for the function.  Note that some arguments take up two slots
        # depending on their type [this is compute by type_width()]
        assert not self.curfunc
        self.curfunc = FunctionState()
        for idx, ty in enumerate(argtypes):
            if idx < len(argvars): var = argvars[idx]
            else: var = None
            self.curfunc.add_var(var, ty, True)
        # Prepare a map for the local variable indices we will add
        # Let the subclass do the rest of the work; note that it does
        # not need to know the argvars parameter, so don't pass it
        self._begin_function(funcname, argtypes, rettype, static, abstract, final)

    def _begin_function(self, funcname, argtypes, rettype, static, abstract, final):
        """
        Main implementation of begin_function.  The begin_function()
        does some generic handling of args.
        """
        unimplemented        

    def end_function(self):
        self._end_function()
        self.curfunc = None

    def _end_function(self):
        unimplemented

    def mark(self, lbl):
        """ Marks the point that a label indicates. """
        unimplemented

    def _instr(self, opcode, *args):
        """ Emits an instruction with the given opcode and arguments.
        The correct opcode and their types depends on the opcode. """
        unimplemented

    def return_val(self, jtype):
        """ Returns a value from top of stack of the JvmType 'jtype' """
        self._instr(jvm.RETURN.for_type(jtype))

    def load_class_name(self):
        """ Loads the name of the *Java* class of the object on the top of
        the stack as a Java string.  Note that the result for a PyPy
        generated class will look something like 'pypy.some.pkg.cls' """
        self.emit(jvm.OBJECTGETCLASS)
        self.emit(jvm.CLASSGETNAME)

    def load_string(self, str):
        """ Pushes a Java version of a Python string onto the stack.
        'str' should be a Python string encoded in UTF-8 (I think) """
        # Create an escaped version of str:
        def escape(char):
            if char == '"': return r'\"'
            if char == '\n': return r'\n'
            if char == "\\": return r'\\'
            if ord(char) > 127: return r'\u%04x' % ord(char)
            return char
        res = ('"' + 
               "".join(escape(c) for c in str) +
               '"')
        # Use LDC to load the Java version:
        #     XXX --- support byte arrays here?  Would be trickier!
        self._instr(jvm.LDC, res)

    def load_jvm_var(self, jvartype, varidx):
        """ Loads from jvm slot #varidx, which is expected to hold a value of
        type vartype """
        assert varidx < self.curfunc.next_offset
        if jvartype is jVoid:
            return
        opc = jvm.LOAD.for_type(jvartype)
        self._instr(opc, varidx)

    def store_jvm_var(self, vartype, varidx):
        """ Loads from jvm slot #varidx, which is expected to hold a value of
        type vartype """
        self._instr(jvm.STORE.for_type(vartype), varidx)

    def load_from_array(self, elemtype):
        """ Loads something from an array; the result will be of type 'elemtype'
        (and hence the array is of type 'array_of(elemtype)'), where
        'elemtype' is a JvmType.  Assumes that the array ref and index are
        already pushed onto stack (in that order). """
        self._instr(jvm.ARRLOAD.for_type(elemtype))

    def store_to_array(self, elemtype):
        """ Stores something into an array; the result will be of type
        'elemtype' (and hence the array is of type
        'array_of(elemtype)'), where 'elemtype' is a JvmType.  Assumes
        that the array ref, index, and value are already pushed onto
        stack (in that order)."""
        self._instr(jvm.ARRLOAD.for_type(elemtype))

    def unique_label(self, desc, mark=False):
        """ Returns an opaque, unique label object that can be passed an
        argument for branching opcodes, or the mark instruction.

        'desc' should be a comment describing the use of the label.
        It is for decorative purposes only and should be a valid C
        identifier.

        'mark' --- if True, then also calls self.mark() with the new lbl """
        res = Label(self.label_counter, desc)
        self.label_counter += 1
        if mark:
            self.mark(res)
        return res

    def load_this_ptr(self):
        """ Convenience method.  Be sure you only call it from a
        virtual method, not static methods. """
        self.load_jvm_var(jvm.jObject, 0)

    def load_function_argument(self, index):
        """ Convenience method.  Loads function argument #index; note that
        the this pointer is index #0. """
        jtype, jidx = self.curfunc.function_arguments[index]
        self.load_jvm_var(jtype, jidx)

    def prepare_generic_argument(self, ITEMTYPE):
        jty = self.db.lltype_to_cts(ITEMTYPE)
        self.prepare_generic_argument_with_jtype(jty)
        
    def prepare_generic_argument_with_jtype(self, jty):
        if jty is jVoid:
            self.emit(jvm.ACONST_NULL)
        elif isinstance(jty, jvm.JvmScalarType):
            self.box_value(jty)

    def prepare_generic_result(self, ITEMTYPE):
        jresty = self.db.lltype_to_cts(ITEMTYPE)
        self.prepare_generic_result_with_jtype(jresty)
        
    def prepare_generic_result_with_jtype(self, jresty):
        if jresty is jVoid:
            self.emit(jvm.POP)
        elif isinstance(jresty, jvm.JvmScalarType):
            # Perform any un-boxing required:
            self.downcast_jtype(jresty.box_type)
            self.unbox_value(jresty)
        else:
            # Perform any casting required:
            self.downcast_jtype(jresty)

    def box_value(self, jscalartype):
        """ Assuming that an value of type jscalartype is on the stack,
        boxes it into an Object. """
        jclasstype = jscalartype.box_type
        jmethod = jvm.Method.s(
            jclasstype, 'valueOf', (jscalartype,), jclasstype)
        self.emit(jmethod)

    def unbox_value(self, jscalartype):
        """ Assuming that a boxed value of type jscalartype is on the stack,
        unboxes it.  """        
        jclasstype = jscalartype.box_type
        jmethod = jvm.Method.v(
            jclasstype, jscalartype.unbox_method, (), jscalartype)
        self.emit(jmethod)

    def swap(self):
        """ Swaps the two words highest on the stack. """
        self.emit(jvm.SWAP)

    # __________________________________________________________________
    # Exception Handling
    #
    # You can demarcate regions of code as "try/catch" regions using
    # the various functions included here.  Either invoke
    # try_catch_region(), in which case you must supply all the
    # relevant labels, or use the begin_try()/end_try()/begin_catch()
    # methods.  In the latter case, you define the 3 needed labels as
    # you go.  Both begin_try() and end_try() must have been invoked
    # before begin_catch() is invoked (i.e., the try region must
    # appear before the corresponding catch regions).  Note that
    # end_try() can be called again to reset the end of the try
    # region.

    def begin_try(self):
        self.begintrylbl = self.unique_label("begin_try", mark=True)

    def end_try(self):
        self.endtrylbl = self.unique_label("end_try", mark=True)

    def begin_catch(self, jexcclsty):
        catchlbl = self.unique_label("catch", mark=True)
        self.try_catch_region(
            jexcclsty, self.begintrylbl, self.endtrylbl, catchlbl)
 
    def end_catch(self):
        return
        
    def try_catch_region(self, jexcclsty, trystartlbl, tryendlbl, catchlbl):
        """
        Indicates a try/catch region.

        Either invoked directly, or from the begin_catch() routine:
        the latter is invoked by the oosupport code.
        
        'jexcclsty' --- a JvmType for the class of exception to be caught
        'trystartlbl', 'tryendlbl' --- labels marking the beginning and end
        of the try region
        'catchlbl' --- label marking beginning of catch region
        """
        unimplemented

    _equals = {
        ootype.Void:             (None,None),
        ootype.SignedLongLong:   (jvm.LCMP,  jvm.IFEQ),
        ootype.UnsignedLongLong: (jvm.LCMP,  jvm.IFEQ),
        ootype.Float:            (jvm.DCMPG, jvm.IFEQ),
        ootype.Signed:           (None,jvm.IF_ICMPNE),
        ootype.Unsigned:         (None,jvm.IF_ICMPNE),
        ootype.Bool:             (None,jvm.IF_ICMPNE),
        ootype.Char:             (None,jvm.IF_ICMPNE),
        ootype.UniChar:          (None,jvm.IF_ICMPNE),
        }
    def compare_values(self, OOTYPE, unequal_lbl):
        """ Assumes that two instances of OOTYPE are pushed on the stack;
        compares them and jumps to 'unequal_lbl' if they are unequal """
        if OOTYPE in self._equals:
            i1, i2 = self._equals[OOTYPE]
            if i1: self.emit(i1)
            if i2: self.emit(i2, unequal_lbl)
            return
        self.emit(jvm.OBJEQUALS)
        self.emit(jvm.IFEQ, unequal_lbl)

    _hash = {
        ootype.Void:             jvm.ICONST_0,
        ootype.SignedLongLong:   jvm.L2I,
        ootype.UnsignedLongLong: jvm.L2I,
        ootype.Float:            jvm.D2I,
        ootype.Signed:           None,
        ootype.Unsigned:         None,
        ootype.Bool:             None,
        ootype.Char:             None,
        ootype.UniChar:          None,
        }
    def hash_value(self, OOTYPE):
        """ Assumes that an instance of OOTYPE is pushed on the stack.
        When finished, an int will be on the stack as a hash value. """
        if OOTYPE in self._hash:
            i1 = self._hash[OOTYPE]
            if i1: self.emit(i1)
            return
        self.emit(jvm.OBJHASHCODE)

    # __________________________________________________________________
    # Generator methods and others that are invoked by MicroInstructions
    # 
    # These translate into calls to the above methods.

    def emit(self, instr, *args):
        """ 'instr' in our case must be either a string, in which case
        it is the name of a method to invoke, or an Opcode/Method
        object (defined above)."""

        if instr is None:
            return

        if isinstance(instr, str):
            return getattr(self, instr)(*args)

        if isinstance(instr, jvm.Opcode):
            return self._instr(instr, *args)

        if isinstance(instr, jvm.BaseMethod):
            return instr.invoke(self)

        if isinstance(instr, jvm.Field) or isinstance(instr, jvm.Property):
            return instr.load(self)

        raise Exception("Unknown object in call to emit(): "+repr(instr))

    def _var_data(self, v):
        # Determine java type:
        jty = self.db.lltype_to_cts(v.concretetype)
        import sys
        # Determine index in stack frame slots:
        #   note that arguments and locals can be treated the same here
        return jty, self.curfunc.var_offset(v, jty)
        
    def load(self, value):
        if isinstance(value, flowmodel.Variable):
            jty, idx = self._var_data(value)
            return self.load_jvm_var(jty, idx)

        if isinstance(value, SubOperation):
            return render_sub_op(value, self.db, self)

        if isinstance(value, flowmodel.Constant):
            return push_constant(self.db, value.concretetype, value.value, self)
            
        raise Exception('Unexpected type for v in load(): '+
                        repr(value.concretetype) + " v=" + repr(value))

    def store(self, v):
        # Ignore Void values
        if v.concretetype is ootype.Void:
            return

        if isinstance(v, flowmodel.Variable):
            jty, idx = self._var_data(v)
            return self.store_jvm_var(jty, idx)
        raise Exception('Unexpected type for v in store(): '+v)

    def set_field(self, CONCRETETYPE, fieldname):
        clsobj = self.db.pending_class(CONCRETETYPE)
        fieldobj = clsobj.lookup_field(fieldname)
        fieldobj.store(self)

    def push_pypy(self):
        """ Pushes the PyPy object which contains all of our helper methods
        onto the stack """
        self.db.pypy_field.load(self)

    def push_interlink(self):
        """ Pushes the Interlink object which contains the methods
        from prebuildnodes.py onto the stack """
        self.db.interlink_field.load(self)

    def get_field(self, CONCRETETYPE, fieldname):
        clsobj = self.db.pending_class(CONCRETETYPE)
        fieldobj = clsobj.lookup_field(fieldname)
        fieldobj.load(self)

    def downcast(self, TYPE):
        jtype = self.db.lltype_to_cts(TYPE)
        self.downcast_jtype(jtype)

    def downcast_jtype(self, jtype):
        self._instr(jvm.CHECKCAST, jtype)
        
    def instanceof(self, TYPE):
        jtype = self.db.lltype_to_cts(TYPE)
        self._instr(jvm.INSTANCEOF, jtype)

    # included for compatibility with oosupport, but instanceof_jtype
    # follows our naming convention better
    def isinstance(self, jtype):
        return self.instanceof_jtype(jtype)
    
    def instanceof_jtype(self, jtype):
        self._instr(jvm.INSTANCEOF, jtype)

    def branch_unconditionally(self, target_label):
        self.goto(target_label)

    def branch_conditionally(self, cond, target_label):
        if cond:
            self._instr(jvm.IFNE, target_label)
        else:
            self._instr(jvm.IFEQ, target_label)

    def branch_if_equal(self, target_label):
        self._instr(jvm.IF_ICMPEQ, target_label)

    def branch_if_not_equal(self, target_label):
        self._instr(jvm.IF_ICMPNE, target_label)

    def call_graph(self, graph):
        mthd = self.db.pending_function(graph)
        mthd.invoke(self)

    def call_method(self, OOCLASS, method_name):
        clsobj = self.db.pending_class(OOCLASS)
        mthd = clsobj.lookup_method(method_name)
        mthd.invoke(self)

        # Check if we have to convert the result type at all:
        gener = jvm.Generifier(OOCLASS)
        RETTYPE = gener.full_types(method_name)[1]
        jrettype = self.db.lltype_to_cts(RETTYPE)
        if jrettype != mthd.return_type:
            # if the intended return type is not the same as the
            # actual return type in the JVM (mthd.return_type),
            # we have to "deal with it"
            self.prepare_generic_result(RETTYPE)

    def prepare_call_primitive(self, op, module, name):
        # Load the PyPy object pointer onto the stack:
        self.push_pypy()

        # If necessary, load the ll_os object pointer instead:
        if module == 'll_os':
            jvm.PYPYOS.load(self)
        
    def call_primitive(self, op, module, name):
        from pypy.translator.simplify import get_functype
        callee = op.args[0].value
        # it could be an rffi lltype, see test_primitive.test_rffi_ooprimitive
        TYPE = get_functype(callee._TYPE)
        jargtypes, jrettype = self.db.types_for_signature(TYPE.ARGS, TYPE.RESULT)

        # Determine what class the primitive is implemented in:
        if module == 'll_os':
            jcls = jvm.jll_os
        else:
            jcls = jPyPy

        # Determine the method signature:
        #    n.b.: if the method returns a generated type, then
        #    it's static type will be Object.  This is because
        #    the method cannot directly refer to the Java type in
        #    .java source, as its name is not yet known.
        if jrettype.is_generated():
            mthd = jvm.Method.v(jcls, name, jargtypes, jvm.jObject)
        else:
            mthd = jvm.Method.v(jcls, name, jargtypes, jrettype)

        # Invoke the method
        self.emit(mthd)

        # Cast the result, if needed
        if jrettype.is_generated():
            self.downcast_jtype(jrettype)

    def prepare_call_oostring(self, OOTYPE):
        # Load the PyPy object pointer onto the stack:
        self.push_pypy()

    def call_oostring(self, OOTYPE):
        cts_type = self.db.lltype_to_cts(OOTYPE)

        # treat all objects the same:
        if isinstance(cts_type, jvm.JvmClassType):
            cts_type = jvm.jObject
            
        mthd = jvm.Method.v(jPyPy, 'oostring', [cts_type, jInt], jString)
        self.emit(mthd)
        if self.db.using_byte_array:
            self.emit(jvm.PYPYSTRING2BYTES)

    def prepare_call_oounicode(self, OOTYPE):
        # Load the PyPy object pointer onto the stack:
        self.push_pypy()

    def call_oounicode(self, OOTYPE):
        cts_type = self.db.lltype_to_cts(OOTYPE)
        mthd = jvm.Method.v(jPyPy, 'oounicode', [cts_type], jString)
        self.emit(mthd)
        if self.db.using_byte_array:
            self.emit(jvm.PYPYSTRING2BYTES)
        
    def new(self, TYPE):
        jtype = self.db.lltype_to_cts(TYPE)
        self.new_with_jtype(jtype)

    def new_with_jtype(self, jtype, ctor=None):
        if ctor is None:
            ctor = jvm.Method.c(jtype, ())
        self.emit(jvm.NEW, jtype)
        self.emit(jvm.DUP)
        self.emit(ctor)
        
    def oonewarray(self, TYPE, length):
        jtype = self.db.lltype_to_cts(TYPE)
        self.load(length)
        jtype.make(self)

    def instantiate(self):
        self.emit(jvm.PYPYRUNTIMENEW)

    def getclassobject(self, OOINSTANCE):
        jtype = self.db.lltype_to_cts(OOINSTANCE)
        self.load_string(jtype.name)
        jvm.CLASSFORNAME.invoke(self)
        
    def dup(self, OOTYPE):
        jtype = self.db.lltype_to_cts(OOTYPE)
        self.dup_jtype(jtype)

    def dup_jtype(self, jtype):
        if jtype.descriptor.type_width() == 1:
            self.emit(jvm.DUP)
        else:
            self.emit(jvm.DUP2)
            
    def pop(self, OOTYPE):
        jtype = self.db.lltype_to_cts(OOTYPE)
        if jtype.descriptor.type_width() == 1:
            self.emit(jvm.POP)
        else:
            self.emit(jvm.POP2)

    def push_null(self, OOTYPE):
        self.emit(jvm.ACONST_NULL)

    # we can't assume MALLOC_ZERO_FILLED, because for scalar type the
    # default item for ArrayList is null, not e.g. Integer(0) or
    # Char(0).
    DEFINED_INT_SYMBOLICS = {'MALLOC_ZERO_FILLED':0,
                             '0 /* we are not jitted here */': 0}
                            
    def push_primitive_constant(self, TYPE, value):

        if TYPE is ootype.Void:
            return
        elif isinstance(value, CDefinedIntSymbolic):
            self.emit(jvm.ICONST, self.DEFINED_INT_SYMBOLICS[value.expr])
        elif TYPE in (ootype.Bool, ootype.Signed):
            self.emit(jvm.ICONST, int(value))
        elif TYPE is ootype.Unsigned:
            # Converts the unsigned int into its corresponding signed value:
            if value > 0x7FFFFFFF:
                value = -((int(value) ^ 0xFFFFFFFF)+1)
            self.emit(jvm.ICONST, value)
        elif TYPE is ootype.Char or TYPE is ootype.UniChar:
            self.emit(jvm.ICONST, ord(value))
        elif TYPE is ootype.SignedLongLong:
            self._push_long_constant(long(value))
        elif TYPE is ootype.UnsignedLongLong:
            # Converts the unsigned long into its corresponding signed value:
            if value > 0x7FFFFFFFFFFFFFFF:
                value = -((long(value) ^ 0xFFFFFFFFFFFFFFFF)+1)
            self._push_long_constant(value)
        elif TYPE is ootype.Float:
            self._push_double_constant(float(value))
        elif TYPE in (ootype.String, ootype.Unicode):
            if value == ootype.null(TYPE):
                self.emit(jvm.ACONST_NULL)
            else:
                self.load_string(value._str)
        else:
            assert False, 'Unknown constant type: %s' % TYPE

    def _push_long_constant(self, value):
        if value == 0:
            self.emit(jvm.LCONST_0)
        elif value == 1:
            self.emit(jvm.LCONST_1)
        else:
            self.emit(jvm.LDC2, value)

    def _push_double_constant(self, value):
        if isnan(value):
            jvm.DOUBLENAN.load(self)
        elif isinf(value):
            if value > 0: jvm.DOUBLEPOSINF.load(self)
            else: jvm.DOUBLENEGINF.load(self)
        elif value == 0.0:
            self.emit(jvm.DCONST_0)
        elif value == 1.0:
            self.emit(jvm.DCONST_1)
        else:
            # Big hack to avoid exponential notation:
            self.emit(jvm.LDC2, "%22.22f" % value)
        
    def create_weakref(self, OOTYPE):
        """
        After prepare_cast_ptr_to_weak_address has been called, and the
        ptr to cast has been pushed, you can invoke this routine.
        OOTYPE should be the type of value which was pushed.
        The result will be that at the top of the stack is a weak reference.
        """
        self.prepare_generic_argument(OOTYPE) 
        self.emit(jvm.PYPYWEAKREFCREATE)
    
    def deref_weakref(self, OOTYPE):
        """
        If a weak ref is at the top of the stack, yields the object
        that this weak ref is a pointer to.  OOTYPE is the kind of object
        you had a weak reference to.
        """
        self.emit(jvm.PYPYWEAKREFGET)
        self.prepare_generic_result(OOTYPE)

    # __________________________________________________________________
    # Methods invoked directly by strings in jvm/opcode.py

    def throw(self):
        """ Throw the object from top of the stack as an exception """
        self._instr(jvm.ATHROW)

    def iabs(self):
        jvm.MATHIABS.invoke(self)

    def dbl_abs(self):
        jvm.MATHDABS.invoke(self)

    def bitwise_negate(self):
        """ Invert all the bits in the "int" on the top of the stack """
        self._instr(jvm.ICONST, -1)
        self._instr(jvm.IXOR)

    def goto(self, label):
        """ Jumps unconditionally """
        self._instr(jvm.GOTO, label)

    def goto_if_true(self, label):
        """ Jumps if the top of stack is true """
        self._instr(jvm.IFNE, label)

    def goto_if_false(self, label):
        """ Jumps if the top of stack is false """
        self._instr(jvm.IFEQ, label)
        
class JasminGenerator(JVMGenerator):

    def __init__(self, db, outdir):
        JVMGenerator.__init__(self, db)
        self.outdir = outdir

    def _begin_class(self, abstract, interface):
        """
        Invoked by begin_class.  It is expected that self.curclass will
        be set when this method is invoked.  

        abstract: True if the class to generate is abstract

        interface: True if the 'class' to generate is an interface
        """

        iclassnm = self.current_type().descriptor.int_class_name()
        isuper = self.curclass.superclass_type.descriptor.int_class_name()
        
        jfile = self.outdir.join("%s.j" % iclassnm)

        jfile.dirpath().ensure(dir=True)
        self.curclass.file = jfile.open('w')
        self.db.add_jasmin_file(str(jfile))

        # Determine the "declaration string"
        if interface: decl_str = "interface"
        else: decl_str = "class"

        # Write the JasminXT header
        fields = ["public"]
        if abstract: fields.append('abstract')
        self.curclass.out(".%s %s %s\n" % (
            decl_str, " ".join(fields), iclassnm))
        self.curclass.out(".super %s\n" % isuper)
        
    def _end_class(self):
        self.curclass.file.close()

    def close(self):
        assert self.curclass is None

    def add_comment(self, comment):
        if self.curclass:
            self.curclass.out("  ; %s\n" % comment)

    def implements(self, jinterface):
        self.curclass.out(
            '.implements ' + jinterface.descriptor.int_class_name() + '\n')
        
    def add_field(self, fobj):
        try:
            fobj.jtype.descriptor
        except AttributeError:
            if mypycrash is not None:
                mypycrash.forceDump()
                mypycrash.saveToFile("/tmp/test_jvm_weakref.pycrash")

        kw = ['public']
        if fobj.is_static: kw.append('static')
        self.curclass.out('.field %s %s %s\n' % (
            " ".join(kw), fobj.field_name, fobj.jtype.descriptor))

    def _begin_function(self, funcname, argtypes, rettype, static, abstract, final):

        if not static: argtypes = argtypes[1:]

        # Throws clause?  Only use RuntimeExceptions?
        kw = ['public']
        if static: kw.append('static')
        if abstract: kw.append('abstract')
        if final: kw.append('final')
        
        self.curclass.out('.method %s %s(%s)%s\n' % (
            " ".join(kw),
            funcname,
            "".join([a.descriptor for a in argtypes]),
            rettype.descriptor))
        self.abstract_method = abstract

        if not self.abstract_method:
            self.function_start_label = self.unique_label(
                'function_start', True)

    def _end_function(self):
        
        if not self.abstract_method:
            function_end_label = self.unique_label('function_end', True)
            
            self.curclass.out('.limit stack 100\n') # HACK, track max offset
            self.curclass.out('.limit locals %d\n' % self.curfunc.next_offset)

            # Declare debug information for each variable:
            var_info_list = self.curfunc.var_info_list()
            for idx, data in enumerate(var_info_list):
                if data:
                    name, jtype = data
                    if jtype is not jVoid:
                        self.curclass.out(
                            '.var %d is %s %s from %s to %s\n' % (
                            idx,
                            name,
                            jtype.descriptor,
                            self.function_start_label.label,
                            function_end_label.label))
        
        self.curclass.out('.end method\n')

    def mark(self, lbl):
        """ Marks the point that a label indicates. """
        assert isinstance(lbl, Label)
        self.curclass.out('  %s:\n' % lbl.jasmin_syntax())

        # We count labels as instructions because ASM does:
        self.curfunc.instr_counter += 1 

    def _instr(self, opcode, *args):
        jvmstr, args = opcode.specialize(args)
        def jasmin_syntax(arg):
            if hasattr(arg, 'jasmin_syntax'): return arg.jasmin_syntax()
            return str(arg)
        strargs = [jasmin_syntax(arg) for arg in args]
        instr_text = '%s %s' % (jvmstr, " ".join(strargs))
        self.curclass.out('    .line %d\n' % self.curclass.line_number)
        self.curclass.out('    %s\n' % (instr_text,))
        self.curfunc.instr_counter+=1

    def try_catch_region(self, jexcclsty, trystartlbl, tryendlbl, catchlbl):
        self.curclass.out('  .catch %s from %s to %s using %s\n' % (
            jexcclsty.descriptor.int_class_name(),
            trystartlbl.jasmin_syntax(),
            tryendlbl.jasmin_syntax(),
            catchlbl.jasmin_syntax()))
                       
    def get_instruction_count(self):
        return self.curfunc.instr_counter

    def emit_tableswitch(self, low, lbls, default):
        self.curclass.out('    tableswitch %d\n' % low)
        for label in lbls:
            self.curclass.out('        %s\n' % label.jasmin_syntax())
        self.curclass.out('        default: %s\n' % default.jasmin_syntax())

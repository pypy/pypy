import os # 
from pypy.objspace.flow import model as flowmodel
from pypy.translator.oosupport.metavm import Generator
from pypy.translator.jvm.typesystem import JvmType

# ___________________________________________________________________________
# JVM Opcode Flags:
#
#   Indicates certain properties of each opcode.  Used mainly for debugging
#   assertions

NOFLAGS   = 0
BRANCH    = 1   # Opcode is a branching opcode (implies a label argument)
INTARG    = 2   # Opcode has an integer argument
CONSTSPEC = 6   # Opcode has specialized variants (implies INTARG)
INVOKE    = 8   # Opcode is some kind of method invocation

# ___________________________________________________________________________
# JVM Opcodes:
#
#   Map from symbolic name to an instance of the Opcode class

class Opcode(object):
    def __init__(self, flags, jvmstr):
        """
        flags is a set of flags (see above) that describe opcode
        jvmstr is the name for jasmin printouts
        """
        self.flags = flags
        self.jvmstr = jvmstr
        
class OpcodeFamily(object):
    """
    Many opcodes in JVM have variants that depend on the type of the
    operands; for example, one must choose the correct ALOAD, ILOAD,
    or DLOAD depending on whether one is loading a reference, integer,
    or double variable respectively.  Each instance of this class
    defines one 'family' of opcodes, such as the LOAD family shown
    above, and produces Opcode objects specific to a particular type.
    """
    def __init__(self, flags, suffix):
        """
        flags is a set of flags (see above) that describe opcode
        jvmstr is the name for jasmin printouts
        """
        self.flags = flags
        self.suffix = suffix
        self.cache = {}

    def _o(self, prefix):
        try:
            return self.cache[prefix]
        except KeyError:
            self.cache[prefix] = obj = Opcode(self.flags, prefix+self.suffix)
            return obj
        
    def for_type(self, argtype):
        """ Returns a customized opcode of this family appropriate to
        'argtype', a JvmType object. """

        # These are always true:
        if self[0] == 'L': return self._o("A")   # Objects
        if self[0] == '[': return self._o("A")   # Arrays
        if self == 'I':    return self._o("I")   # Integers
        if self == 'J':    return self._o("L")   # Integers
        if self == 'D':    return self._o("D")   # Doubles
        if self == 'C':    return self._o("C")   # Characters
        if self == 'B':    return self._o("B")   # Bytes
        if self == 'V':    return self._o("")    # Void [used by RETURN]

        # TODO --- extend?  etc
        unimplemented

# Define the opcodes for IFNE, IFEQ, IFLT, IF_ICMPLT, etc.  The IFxx
# variants compare a single integer arg against 0, and the IF_ICMPxx
# variants compare 2 integer arguments against each other.
for cmpop in ('ne', 'eq', 'lt', 'gt', 'le', 'ge'):
    ifop = "if%s" % cmpop
    if_icmpop = "if_icmp%s" % cmpop
    globals()[ifop.upper()] = Opcode(BRANCH, ifop)
    globals()[if_icmpop.upper()] = Opcode(BRANCH, if_icmpop)

# Compare references, either against NULL or against each other
IFNULL =    Opcode(BRANCH, 'ifnull')
IFNONNULL = Opcode(BRANCH, 'ifnonnull')
IF_ACMPEQ = Opcode(BRANCH, 'if_acmpeq')
IF_ACMPNE = Opcode(BRANCH, 'if_acmpne')

# Method invocation
INVOKESTATIC = Opcode(INVOKE, 'invokestatic')

# Other opcodes
GOTO =      Opcode(BRANCH, 'goto')
ICONST =    Opcode(CONSTSPEC, 'iconst')
DCONST_0 =  Opcode(NOFLAGS, 'dconst_0')
DCONST_1 =  Opcode(NOFLAGS, 'dconst_1')
LCONST_0 =  Opcode(NOFLAGS, 'lconst_0')
LCONST_1 =  Opcode(NOFLAGS, 'lconst_1')
GETFIELD =  Opcode(NOFLAGS, 'getfield')
PUTFIELD =  Opcode(NOFLAGS, 'putfield')
GETSTATIC = Opcode(NOFLAGS, 'getstatic')
PUTSTATIC = Opcode(NOFLAGS, 'putstatic')
CHECKCAST = Opcode(NOFLAGS, 'checkcast')
INEG =      Opcode(NOFLAGS, 'ineg')
IXOR =      Opcode(NOFLAGS, 'ixor')
IADD =      Opcode(NOFLAGS, 'iadd')
ISUB =      Opcode(NOFLAGS, 'isub')
IMUL =      Opcode(NOFLAGS, 'imul')
IDIV =      Opcode(NOFLAGS, 'idiv')
IREM =      Opcode(NOFLAGS, 'irem')
IAND =      Opcode(NOFLAGS, 'iand')
IOR =       Opcode(NOFLAGS, 'ior')
ISHL =      Opcode(NOFLAGS, 'ishl')
ISHR =      Opcode(NOFLAGS, 'ishr')
IUSHR =     Opcode(NOFLAGS, 'iushr')
DCMPG =     Opcode(NOFLAGS, 'dcmpg')
DCMPL =     Opcode(NOFLAGS, 'dcmpl')
NOP =       Opcode(NOFLAGS, 'nop')
I2D =       Opcode(NOFLAGS, 'i2d')
I2L =       Opcode(NOFLAGS, 'i2l')
D2I=        Opcode(NOFLAGS, 'd2i')
L2I =       Opcode(NOFLAGS, 'l2i')
ATHROW =    Opcode(NOFLAGS, 'athrow')
DNEG =      Opcode(NOFLAGS, 'dneg')
DADD =      Opcode(NOFLAGS, 'dadd')
DSUB =      Opcode(NOFLAGS, 'dsub')
DMUL =      Opcode(NOFLAGS, 'dmul')
DDIV =      Opcode(NOFLAGS, 'ddiv')
DREM =      Opcode(NOFLAGS, 'drem')
LNEG =      Opcode(NOFLAGS, 'lneg')
LADD =      Opcode(NOFLAGS, 'ladd')
LSUB =      Opcode(NOFLAGS, 'lsub')
LMUL =      Opcode(NOFLAGS, 'lmul')
LDIV =      Opcode(NOFLAGS, 'ldiv')
LREM =      Opcode(NOFLAGS, 'lrem')
LAND =      Opcode(NOFLAGS, 'land')
LOR =       Opcode(NOFLAGS, 'lor')
LXOR =      Opcode(NOFLAGS, 'lxor')
LSHL =      Opcode(NOFLAGS, 'lshl')
LSHR =      Opcode(NOFLAGS, 'lshr')
LUSHR =     Opcode(NOFLAGS, 'lushr')

# Loading/storing local variables
LOAD =      OpcodeFamily(INTARG, "load")
STORE =     OpcodeFamily(INTARG, "store")
RETURN =    OpcodeFamily(NOFLAGS, "return")

# Loading/storing from arrays
#   *NOTE*: This family is characterized by the type of the ELEMENT,
#   not the type of the ARRAY.  
#   
#   Also: here I break from convention by naming the objects ARRLOAD
#   rather than ALOAD, even though the suffix is 'aload'.  This is to
#   avoid confusion with the ALOAD opcode.
ARRLOAD =      OpcodeFamily(NOFLAGS, "aload")
ARRSTORE =     OpcodeFamily(NOFLAGS, "astore")

# ___________________________________________________________________________
# Helper Method Information
#
# These are used by code outside of this module as well.

class Method(object):
    def __init__(self, classnm, methnm, desc, opcode=INVOKESTATIC):
        self.opcode = opcode
        self.class_name = classnm
        self.method_name = methnm
        self.descriptor = desc
    def invoke(self, gen):
        gen._instr(self.opcode, self)

MATHIABS =              Method('java.lang.Math', 'abs', '(I)I')
MATHLABS =              Method('java.lang.Math', 'abs', '(L)L')
MATHDABS =              Method('java.lang.Math', 'abs', '(D)D')
MATHFLOOR =             Method('java.lang.Math', 'floor', '(D)D')
PYPYUINTCMP =           Method('pypy.PyPy', 'uint_cmp', '(II)I')
PYPYULONGCMP =          Method('pypy.PyPy', 'ulong', '(LL)I')
PYPYUINTTODOUBLE =      Method('pypy.PyPy', 'uint_to_double', '(I)D')
PYPYDOUBLETOUINT =      Method('pypy.PyPy', 'double_to_uint', '(D)I')
PYPYLONGBITWISENEGATE = Method('pypy.PyPy', 'long_bitwise_negate', '(L)L')
PYPYARRAYTOLIST =       Method('pypy.PyPy', 'array_to_list',
                               '([Ljava/lang/Object;)Ljava/util/List;')
PYPYSTRTOINT =          Method('pypy.PyPy', 'str_to_int',
                               '([Ljava/lang/String;)I')
PYPYSTRTOUINT =         Method('pypy.PyPy', 'str_to_uint',
                               '([Ljava/lang/String;)I')
PYPYSTRTOLONG =         Method('pypy.PyPy', 'str_to_long',
                               '([Ljava/lang/String;)J')
PYPYSTRTOULONG =        Method('pypy.PyPy', 'str_to_ulong',
                               '([Ljava/lang/String;)J')
PYPYSTRTOBOOL =         Method('pypy.PyPy', 'str_to_bool',
                               '([Ljava/lang/String;)B')
PYPYSTRTODOUBLE =       Method('pypy.PyPy', 'str_to_double',
                               '([Ljava/lang/String;)D')
PYPYSTRTOCHAR =         Method('pypy.PyPy', 'str_to_char',
                               '([Ljava/lang/String;)C')

class JVMGenerator(Generator):

    """ Base class for all JVM generators.  Invokes a small set of '_'
    methods which indicate which opcodes to emit; these can be
    translated by a subclass into Jasmin assembly, binary output, etc.
    Must be inherited from to specify a particular output format;
    search for the string 'unimplemented' to find the methods that
    must be overloaded. """

    def __init__(self, type_system):
        self.type_system = type_system

    # __________________________________________________________________
    # JVM specific methods to be overloaded by a subclass
    #
    # If the name does not begin with '_', it will be called from
    # outside the generator.

    def begin_class(self, classnm):
        """
        classnm --- full Java name of the class (i.e., "java.lang.String")
        """
        unimplemented

    def end_class(self):
        unimplemented

    def add_field(self, fname, ftype):
        """
        fname --- name of the field (a string)
        ftype --- JvmType for the field
        """
        # TODO --- should fdesc be an ootype??
        unimplemented

    def begin_function(self, funcname, argvars, argtypes, rettype,
                       static=False):
        """
        funcname --- name of the function
        argvars --- list of objects passed to load() that represent arguments;
                    should be in order, or () if load() will not be used
        argtypes --- JvmType for each argument
        rettype --- JvmType for the return value
        static --- keyword, if true then a static func is generated

        This function also defines the scope for variables passed to
        load()/store().
        """
        # Compute the indicates of each argument in the local variables
        # for the function.  Note that some arguments take up two slots
        # depending on their type [this is compute by type_width()]
        self.next_offset = 0
        self.local_vars = {}
        for idx, var in enumerate(argvars):
            self.local_vars[var] = self.next_offset
            self.next_offset += argtypes[idx].type_width()
        # Prepare a map for the local variable indices we will add
        # Let the subclass do the rest of the work; note that it does
        # not need to know the argvars parameter, so don't pass it
        self._begin_function(funcname, argtypes, rettype, static)

    def _begin_function(self, funcname, argtypes, rettype, static):
        """
        Main implementation of begin_function.  The begin_function()
        does some generic handling of args.
        """
        unimplemented        

    def end_function(self):
        del self.next_offset
        del self.local_vars
        self._end_function()

    def _end_function(self):
        unimplemented

    def mark(self, lbl):
        """ Marks the point that a label indicates. """
        unimplemented

    def _instr(self, opcode, *args):
        """ Emits an instruction with the given opcode and arguments.
        The correct opcode and their types depends on the opcode. """
        unimplemented

    def return_val(self, vartype):
        """ Returns a value from top of stack of the JvmType 'vartype' """
        self._instr(RETURN.for_type(vartype))

    def load_jvm_var(self, vartype, varidx):
        """ Loads from jvm slot #varidx, which is expected to hold a value of
        type vartype """
        self._instr(LOAD.for_type(vartype), varidx)

    def store_jvm_var(self, vartype, varidx):
        """ Loads from jvm slot #varidx, which is expected to hold a value of
        type vartype """
        self._instr(STORE.for_type(vartype), varidx)

    def load_from_array(self, elemtype):
        """ Loads something from an array; the result will be of type 'elemtype'
        (and hence the array is of type 'array_of(elemtype)'), where
        'elemtype' is a JvmType.  Assumes that the array ref and index are
        already pushed onto stack (in that order). """
        self._instr(ARRLOAD.for_type(elemtype))

    def store_to_array(self, elemtype):
        """ Stores something into an array; the result will be of type
        'elemtype' (and hence the array is of type
        'array_of(elemtype)'), where 'elemtype' is a JvmType.  Assumes
        that the array ref, index, and value are already pushed onto
        stack (in that order)."""
        self._instr(ARRLOAD.for_type(elemtype))

    def unique_label(self, desc, mark=False):
        """ Returns an opaque, unique label object that can be passed an
        argument for branching opcodes, or the mark instruction.

        'desc' should be a comment describing the use of the label.
        It is for decorative purposes only and should be a valid C
        identifier.

        'mark' --- if True, then also calls self.mark() with the new lbl """
        labelnum = len(self._labels)
        self._labels.append(desc)
        res = ('Label', labelnum)
        if mark:
            self.mark(res)
        return res
    
    # __________________________________________________________________
    # Exception Handling

    def begin_try(self):
        """
        Begins a try/catch region.  Must be followed by a call to end_try()
        after the code w/in the try region is complete.
        """
        self.begintrylbl = self.unique_label("begin_try", mark=True)

    def end_try(self):
        """
        Ends a try/catch region.  Must be followed immediately
        by a call to begin_catch().
        """
        self.endtrylbl = self.unique_label("end_try", mark=True)

    def begin_catch(self, excclsty):
        """
        Begins a catch region corresponding to the last try; there can
        be more than one call to begin_catch, in which case the last
        try region is reused.
        'excclsty' --- a JvmType for the class of exception to be caught
        """
        catchlbl = self.unique_label("catch")
        self.mark(catchlbl, mark=True)
        self.try_catch_region(
            excclsty, self.begintrylbl, send.endtrylbl, catchlbl)

    def end_catch(self):
        """
        Ends a catch region.
        (Included for CLI compatibility)
        """
        return
        
    def try_catch_region(self, excclsty, trystartlbl, tryendlbl, catchlbl):
        """
        Indicates a try/catch region:
        'excclsty' --- a JvmType for the class of exception to be caught
        'trystartlbl', 'tryendlbl' --- labels marking the beginning and end
        of the try region
        'catchlbl' --- label marking beginning of catch region
        """
        unimplemented
        
    # __________________________________________________________________
    # Generator methods and others that are invoked by MicroInstructions
    # 
    # These translate into calls to the above methods.

    def emit(self, instr, *args):
        """ 'instr' in our case must be either a string, in which case
        it is the name of a method to invoke, or an Opcode/Method
        object (defined above)."""

        if isinstance(instr, str):
            return getattr(self, instr)(*args)

        if isinstance(instr, Opcode):
            return self._instr(instr, *args)

        if isinstance(instr, Method):
            return instr.invoke(self)

        raise Exception("Unknown object in call to emit(): "+repr(instr))

    def _var_data(self, v):
        # Determine java type:
        jty = self.type_system.ootype_to_jvm(v.concretetype)
        # Determine index in stack frame slots:
        #   note that arguments and locals can be treated the same here
        if v in self.local_vars:
            idx = self.local_vars[v]
        else:
            idx = self.local_vars[v] = self.next_offset
            self.next_offset += jty.type_width()
        return jty, idx
        
    def load(self, v):
        if isinstance(v, flowmodel.Variable):
            jty, idx = _var_data(v)
            return self.load_jvm_var(jty, idx)

        if isinstance(v, flowmodel.Constant):
            # TODO: Refactor and complete this code?  Maybe more like cli code?
            if TYPE is ootype.Void:
                pass
            elif TYPE is ootype.Bool:
                self._instr(ICONST, int(value))
            elif TYPE is ootype.Char or TYPE is ootype.UniChar:
                self._instr(ICONST, ord(value))
            elif isinstance(value, CDefinedIntSymbolic):
                self._instr(ICONST, DEFINED_INT_SYMBOLICS[value.expr])
            elif TYPE in (ootype.Signed, ootype.Unsigned):
                self._instr(ICONST, value) # handle Unsigned better!
            
        raise Exception('Unexpected type for v in load(): '+v)

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            jty, idx = _var_data(v)
            return self.store_jvm_var(jty, idx)
        raise Exception('Unexpected type for v in store(): '+v)

    def set_field(self, concretetype, value):
        self._instr(SETFIELD, concretetype, value)

    def get_field(self, concretetype, value):
        self._instr(GETFIELD, concretetype, value)

    def downcast(self, type):
        self._instr(CHECKCAST, type)

    # __________________________________________________________________
    # Methods invoked directly by strings in jvm/opcode.py

    def goto(self, lbl):
        self._instr(GOTO, lbl)

    def throw(self):
        """ Throw the object from top of the stack as an exception """
        self._instr(ATHROW)

    def iabs(self):
        MATHIABS.invoke(self)

    def dbl_abs(self):
        MATHDABS.invoke(self)

    def bitwise_negate(self):
        """ Invert all the bits in the "int" on the top of the stack """
        self._instr(ICONST, -1)
        self._instr(IXOR)

    def goto_if_true(self, label):
        """ Jumps if the top of stack is true """
        self._instr(IFNE, label)

    ##### Comparison methods
    
    def _compare_op(self, cmpopcode):
        """
        Converts a comparison operation into a boolean value on the
        stack.  For example, compare_op(IFEQ) emits the instructions
        to perform a logical inversion [because it is true if the
        instruction equals zero].  Consumes as many operands from the
        stack as the cmpopcode consumes, typically 1 or 2.
        """
        midlbl = self.unique_label('cmpop')
        endlbl = self.unique_label('cmpop')
        self._instr(cmpopcode, midlbl)
        self._instr(ICONST, 0)
        self._instr(GOTO, endlbl)
        self.mark(midlbl)
        self._instr(ICONST, 1)
        self.mark(endlbl)

    logical_not = lambda self: self._compare_op(IFEQ)
    equals_zero = logical_not
    not_equals_zero = lambda self: self._compare_op(IFNE)
    equals = lambda self: self._compare_op(IF_ICMPEQ)
    not_equals = lambda self: self._compare_op(IF_ICMPNE)
    less_than = lambda self: self._compare_op(IF_ICMPLT)
    greater_than = lambda self: self._compare_op(IF_ICMPGT)
    less_equals = lambda self: self._compare_op(IF_ICMPLT)
    greater_equals = lambda self: self._compare_op(IF_ICMPGT)

    def _uint_compare_op(self, cmpopcode):
        PYPYUINTCMP.invoke(self)
        self._compare_op(cmpopcode)

    u_equals = equals
    u_not_equals = not_equals
    u_less_than = lambda self: self._uint_compare_op(IFLT)
    u_greater_than = lambda self: self._uint_compare_op(IFGT)
    u_less_equals = lambda self: self._uint_compare_op(IFLE)
    u_greater_equals = lambda self: self._uint_compare_op(IFGE)

    def _dbl_compare_op(self, cmpopcode):
        # XXX --- NaN behavior?
        self._invoke(DCMPG)
        self._compare_op(cmpopcode)

    dbl_equals = lambda self: self._dbl_compare_op(IFEQ)
    dbl_not_equals = lambda self: self._dbl_compare_op(IFNE)
    dbl_less_than = lambda self: self._dbl_compare_op(IFLT)
    dbl_greater_than = lambda self: self._dbl_compare_op(IFGT)
    dbl_less_equals = lambda self: self._dbl_compare_op(IFLE)
    dbl_greater_equals = lambda self: self._dbl_compare_op(IFGE)

    def _long_compare_op(self, cmpopcode):
        self._invoke(LCMP)
        self._compare_op(cmpopcode)

    long_equals = lambda self: self._long_compare_op(IFEQ)
    long_not_equals = lambda self: self._long_compare_op(IFNE)
    long_less_than = lambda self: self._long_compare_op(IFLT)
    long_greater_than = lambda self: self._long_compare_op(IFGT)
    long_less_equals = lambda self: self._long_compare_op(IFLE)
    long_greater_equals = lambda self: self._long_compare_op(IFGE)

    def _ulong_compare_op(self, cmpopcode):
        PYPYULONGCMP.invoke(self)
        self._compare_op(cmpopcode)

    ulong_equals = long_equals
    ulong_not_equals = long_not_equals
    ulong_less_than = lambda self: self._ulong_compare_op(IFLT)
    ulong_greater_than = lambda self: self._ulong_compare_op(IFGT)
    ulong_less_equals = lambda self: self._ulong_compare_op(IFLE)
    ulong_greater_equals = lambda self: self._ulong_compare_op(IFGE)
        
class JasminGenerator(JVMGenerator):

    def __init__(self, outdir, package):
        self.outdir = outdir

    def begin_class(self, classnm):
        """
        classnm --- full Java name of the class (i.e., "java.lang.String")
        """
        
        iclassnm = classnm.replace('.', '/')
        jfile = "%s/%s.j" % (self.outdir, iclassnm)

        try:
            jdir = jfile[:jfile.rindex('/')]
            os.makedirs(jdir)
        except OSError: pass
        self.out = open(jfile, 'w')

        # Write the JasminXT header
        self.out.write(".bytecode XX\n")
        #self.out.write(".source \n")
        self.out.write(".class public %s\n" % iclassnm)
        self.out.write(".super java/lang/Object\n") # ?
        
    def end_class(self):
        self.out.close()
        self.out = None

    def add_field(self, fname, fdesc):
        # TODO --- Signature for generics?
        # TODO --- these must appear before methods, do we want to buffer
        # them up to allow out of order calls to add_field()?
        assert isinstance(fdesc, JvmType)
        self.out.write('.field public %s %s\n' % (fname, fdesc))

    def _begin_function(self, funcname, argtypes, rettype, static):
        # Throws clause?  Only use RuntimeExceptions?
        kw = ['public']
        if static: kw.append('static')
        self.out.write('.method %s %s (%s)%s\n' % (
            funcname, " ".join(kw),
            "".join(argtypes), rettype))

    def _end_function(self):
        self.out.write('.end method\n')

    def mark(self, lbl):
        """ Marks the point that a label indicates. """
        _, lblnm = lbl
        assert _ == "Label"
        self.out.write('  %s:\n' % lblnm)

    def _instr(self, opcode, *args):
        jvmstr = opcode.jvmstr
        
        # Hack: this should be somewhere else, just not sure where yet
        if opcode.flags & CONSTSPEC:
            if args[0] == -1:
                jvmstr += "_m1"
            elif args[0] >= 0 and args[0] <= 5:
                jvmstr += "_%d" % args[0]
            
        self.out.write('    %s %s\n' % (
            jvmstr, " ".join([str(s) for s in args])))

    def try_catch_region(self, excclsty, trystartlbl, tryendlbl, catchlbl):
        self.out.write('  .catch %s from %s to %s using %s\n' % (
            excclsty.int_class_name(), trystartlbl, tryendlbl, catchlbl))
                       

from pypy.translator.oosupport.metavm import Generator

__all__ = ['JasminGenerator']

# ___________________________________________________________________________
# JVM Opcode Flags:
#
#   Indicates certain properties of each opcode.  Used mainly for debugging
#   assertions

NOFLAGS = 0
BRANCH  = 1   # Opcode is a branching opcode (implies a label argument)
INTARG  = 2   # Opcode has an integer argument
CONST   = 6   # Opcode has specialized variants (implies INTARG)
INVOKE  = 8   # Opcode is some kind of method invocation

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
ICONST =    Opcode(CONST, 'iconst')
DCONST_0 =  Opcode(CONST, 'dconst_0')
DCONST_1 =  Opcode(CONST, 'dconst_1')
LCONST_0 =  Opcode(CONST, 'lconst_0')
LCONST_1 =  Opcode(CONST, 'lconst_1')
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
ISHL =      Opcode(NOFLAGS, 'ishl')
ISHR =      Opcode(NOFLAGS, 'ishr')
DCMPG =     Opcode(NOFLAGS, 'dcmpg')
DCMPL =     Opcode(NOFLAGS, 'dcmpl')
NOP =       Opcode(NOFLAGS, 'nop')
I2D =       Opcode(NOFLAGS, 'i2d')
I2L =       Opcode(NOFLAGS, 'i2l')

# ___________________________________________________________________________
# Helper Method Information

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

class JVMGenerator(Generator):

    """ Base class for all JVM generators.  Invokes a small set of '_'
    methods which indicate which opcodes to emit; these can be
    translated by a subclass into Jasmin assembly, binary output, etc."""

    # __________________________________________________________________
    # JVM specific methods to be overloaded by a subclass

    def begin_class(self, classnm):
        """
        classnm --- full Java name of the class (i.e., "java.lang.String")
        """
        unimplemented

    def end_class(self):
        unimplemented

    def begin_function(self, funcname, argtypes, static=False):
        """
        funcname --- name of the function
        argtypes --- types of each argument (in what format??)
        static --- keyword, if true then a static func is generated
        """
        unimplemented

    def end_function(self):
        unimplemented

    def _unique_label(self, desc):
        """ Returns an opaque, unique label object that can be passed an
        argument for branching opcodes, or the _mark instruction.

        'desc' should be a comment describing the use of the label.
        It is for decorative purposes only and should be a valid C
        identifier."""
        labelnum = len(self._labels)
        self._labels.append(desc)
        return ('Label', labelnum)

    def _mark(self, lbl):
        """ Marks the point that a label indicates. """
        unimplemented

    def _instr(self, opcode, *args):
        """ Emits an instruction with the given opcode and arguments.
        The correct opcode and their types depends on the opcode. """
        unimplemented

    # __________________________________________________________________
    # Generator methods and others that are invoked by MicroInstructions
    # 
    # These translate into calls to the above methods.

    def emit(self, instr, *args):
        """ 'instr' in our case must be the name of another method, or
        a JVM opcode (as named above) """
        
        if hasattr(self, instr):
            return getattr(self, instr)(*args)
        
        glob = globals()
        if instr in glob:
            val = glob[instr]
            if isinstance(val, Opcode):
                self._instr(glob[opcode], *args)
            else if isinstance(val, Method):
                val.invoke(self)

        assert False
        
    def load(self, v):
        unimplemented

    def store(self, v):
        unimplemented

    def set_field(self, concretetype, value):
        self._instr(SETFIELD, concretetype, value)

    def get_field(self, concretetype, value):
        self._instr(GETFIELD, concretetype, value)

    def downcast(self, type):
        self._instr(CHECKCAST, type)

    # __________________________________________________________________
    # Methods invoked directly by strings in jvm/opcode.py

    def iabs(self):
        MATHIABS.invoke(self)

    def dbl_abs(self):
        MATHDABS.invoke(self)

    def bitwise_negate(self):
        """ Invert all the bits in the "int" on the top of the stack """
        self._instr(ICONST, -1)
        self._instr(IXOR)

    ##### Comparison methods
    
    def _compare_op(self, cmpopcode):
        """
        Converts a comparison operation into a boolean value on the
        stack.  For example, compare_op(IFEQ) emits the instructions
        to perform a logical inversion [because it is true if the
        instruction equals zero].  Consumes as many operands from the
        stack as the cmpopcode consumes, typically 1 or 2.
        """
        midlbl = self._unique_label()
        endlbl = self._unique_label()
        self._instr(cmpopcode, midlbl)
        self._instr(ICONST, 0)
        self._instr(GOTO, endlbl)
        self._mark(midlbl)
        self._instr(ICONST, 1)
        self._mark(endlbl)

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
    pass

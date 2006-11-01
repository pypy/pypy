import os # 
from pypy.objspace.flow import model as flowmodel
from pypy.translator.oosupport.metavm import Generator
from pypy.translator.jvm.typesystem import \
     JvmType, jObject, jPrintStream, jvm_for_class, jVoid
from pypy.rpython.ootypesystem import ootype

# ___________________________________________________________________________
# JVM Opcode Flags:
#
#   Indicates certain properties of each opcode.  Used mainly for debugging
#   assertions

NOFLAGS   = 0
BRANCH    = 1          # Opcode is a branching opcode (implies a label argument)
INVOKE    = 2          # Opcode is a Method object
CONST5    = 4          # Opcode is specialized for int arguments from -1 to 5
CONST3    = 8          # Opcode is specialized for int arguments from 0 to 3
CLASSINM  = 16         # Argument is an internal class name
FIELD     = 32         # Opcode is a Field object

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

    def __repr__(self):
        return "<Opcode %s:%x>" % (self.jvmstr, self.flags)
        
    def specialize_opcode(self, args):
        """ Process the argument list according to the various flags.
        Returns a tuple (OPCODE, ARGS) where OPCODE is a string representing
        the new opcode, and ARGS is a list of arguments or empty tuple """

        if self.flags & CONST5: 
            assert len(args) == 1
            if args[0] == -1:
                return self.jvmstr + "_m1", ()
            elif args[0] >= 0 and args[0] <= 5:
                return self.jvmstr + "_" + str(args[0]), ()
            else:
                return "ldc", args # HACK

        if self.flags & CONST3: 
            assert len(args) == 1
            if args[0] >= 0 and args[0] <= 3:
                return self.jvmstr + "_" + str(args[0]), ()

        if self.flags & CLASSINM:
            assert len(args) == 1
            args = [args[0].int_class_name()]

        return self.jvmstr, args
        
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
        if argtype[0] == 'L': return self._o("a")   # Objects
        if argtype[0] == '[': return self._o("a")   # Arrays
        if argtype == 'I':    return self._o("i")   # Integers
        if argtype == 'J':    return self._o("l")   # Integers
        if argtype == 'D':    return self._o("d")   # Doubles
        if argtype == 'V':    return self._o("")    # Void [used by RETURN]

        # Chars/Bytes/Booleans are normally represented as ints
        # in the JVM, but some opcodes are different.  They use a
        # different OpcodeFamily (see ArrayOpcodeFamily for ex)
        if argtype == 'C':    return self._o("i")   # Characters
        if argtype == 'B':    return self._o("i")   # Bytes
        if argtype == 'Z':    return self._o("i")   # Boolean

        assert False, "Unknown argtype=%s" % repr(argtype)
        raise NotImplementedError

class ArrayOpcodeFamily(OpcodeFamily):
    """ Opcode family specialized for array access instr """
    def for_type(self, argtype):
        if argtype == 'J':    return self._o("l")   # Integers
        if argtype == 'D':    return self._o("d")   # Doubles
        if argtype == 'C':    return self._o("c")   # Characters
        if argtype == 'B':    return self._o("b")   # Bytes
        if argtype == 'Z':    return self._o("b")   # Boolean (access as bytes)
        return OpcodeFamily.for_type(self, argtype)

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
INVOKEVIRTUAL = Opcode(INVOKE, 'invokevirtual')
INVOKESPECIAL = Opcode(INVOKE, 'invokespecial')

# Other opcodes
LDC =       Opcode(NOFLAGS, 'ldc')       # single-word types
LDC2 =      Opcode(NOFLAGS, 'ldc2_w')    # double-word types: doubles and longs
GOTO =      Opcode(BRANCH,  'goto')
ICONST =    Opcode(CONST5,  'iconst')
ACONST_NULL=Opcode(NOFLAGS, 'aconst_null')
DCONST_0 =  Opcode(NOFLAGS, 'dconst_0')
DCONST_1 =  Opcode(NOFLAGS, 'dconst_0')
LCONST_0 =  Opcode(NOFLAGS, 'lconst_1')
LCONST_1 =  Opcode(NOFLAGS, 'lconst_1')
GETFIELD =  Opcode(FIELD, 'getfield')
PUTFIELD =  Opcode(FIELD, 'putfield')
GETSTATIC = Opcode(FIELD, 'getstatic')
PUTSTATIC = Opcode(FIELD, 'putstatic')
CHECKCAST = Opcode(CLASSINM, 'checkcast')
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
NEW =       Opcode(CLASSINM, 'new')
DUP =       Opcode(NOFLAGS, 'dup')
POP =       Opcode(NOFLAGS, 'pop')
INSTANCEOF= Opcode(CLASSINM, 'instanceof')
# Loading/storing local variables
LOAD =      OpcodeFamily(CONST3, "load")
STORE =     OpcodeFamily(CONST3, "store")
RETURN =    OpcodeFamily(NOFLAGS, "return")

# Loading/storing from arrays
#   *NOTE*: This family is characterized by the type of the ELEMENT,
#   not the type of the ARRAY.  
#   
#   Also: here I break from convention by naming the objects ARRLOAD
#   rather than ALOAD, even though the suffix is 'aload'.  This is to
#   avoid confusion with the ALOAD opcode.
ARRLOAD =      ArrayOpcodeFamily(NOFLAGS, "aload")
ARRSTORE =     ArrayOpcodeFamily(NOFLAGS, "astore")

# ___________________________________________________________________________
# Methods
#
# "Method" objects describe all the information needed to invoke a
# method.  We create one for each node.Function object, as well as for
# various helper methods (defined below).  To invoke a method, you
# push its arguments and then use generator.emit(methobj) where
# methobj is its Method instance.

class Method(object):
    def __init__(self, classnm, methnm, desc, opcode=INVOKESTATIC):
        self.opcode = opcode
        self.class_name = classnm  # String, ie. "java.lang.Math"
        self.method_name = methnm  # String "abs"
        self.descriptor = desc     # String, (I)I
    def invoke(self, gen):
        gen._instr(self.opcode, self)
    def jasmin_syntax(self):
        return "%s/%s%s" % (self.class_name.replace('.','/'),
                            self.method_name,
                            self.descriptor)

MATHIABS =              Method('java.lang.Math', 'abs', '(I)I')
MATHLABS =              Method('java.lang.Math', 'abs', '(L)L')
MATHDABS =              Method('java.lang.Math', 'abs', '(D)D')
MATHFLOOR =             Method('java.lang.Math', 'floor', '(D)D')
PRINTSTREAMPRINTSTR =   Method('java.io.PrintStream', 'print',
                               '(Ljava/lang/String;)V', opcode=INVOKEVIRTUAL)
PYPYUINTCMP =           Method('pypy.PyPy', 'uint_cmp', '(II)I')
PYPYULONGCMP =          Method('pypy.PyPy', 'ulong', '(LL)I')
PYPYUINTTODOUBLE =      Method('pypy.PyPy', 'uint_to_double', '(I)D')
PYPYDOUBLETOUINT =      Method('pypy.PyPy', 'double_to_uint', '(D)I')
PYPYLONGBITWISENEGATE = Method('pypy.PyPy', 'long_bitwise_negate', '(L)L')
PYPYARRAYTOLIST =       Method('pypy.PyPy', 'array_to_list',
                               '([Ljava/lang/Object;)Ljava/util/List;')
PYPYSTRTOINT =          Method('pypy.PyPy', 'str_to_int',
                               '(Ljava/lang/String;)I')
PYPYSTRTOUINT =         Method('pypy.PyPy', 'str_to_uint',
                               '(Ljava/lang/String;)I')
PYPYSTRTOLONG =         Method('pypy.PyPy', 'str_to_long',
                               '(Ljava/lang/String;)J')
PYPYSTRTOULONG =        Method('pypy.PyPy', 'str_to_ulong',
                               '(Ljava/lang/String;)J')
PYPYSTRTOBOOL =         Method('pypy.PyPy', 'str_to_bool',
                               '(Ljava/lang/String;)Z')
PYPYSTRTODOUBLE =       Method('pypy.PyPy', 'str_to_double',
                               '(Ljava/lang/String;)D')
PYPYSTRTOCHAR =         Method('pypy.PyPy', 'str_to_char',
                               '(Ljava/lang/String;)C')
PYPYDUMPINDENTED  =     Method('pypy.PyPy', 'dump_indented',
                                 '(ILjava/lang/String;)V')
PYPYDUMPINT  =          Method('pypy.PyPy', 'dump_int', '(II)V')
PYPYDUMPUINT  =         Method('pypy.PyPy', 'dump_uint', '(II)V')
PYPYDUMPLONG  =         Method('pypy.PyPy', 'dump_long', '(LI)V')
PYPYDUMPDOUBLE  =       Method('pypy.PyPy', 'dump_double', '(DI)V')
PYPYDUMPSTRING  =       Method('pypy.PyPy', 'dump_string', '([BI)V')
PYPYDUMPBOOLEAN =       Method('pypy.PyPy', 'dump_boolean', '(ZI)V')
PYPYDUMPOBJECT =        Method('pypy.PyPy', 'dump_object',
                               '(Ljava/lang/Object;I)V')
PYPYRUNTIMENEW =        Method('pypy.PyPy', 'RuntimeNew',
                               '(Ljava/lang/Class;)Ljava/lang/Object;')


# ___________________________________________________________________________
# Fields
#
# Field objects encode information about fields.

class Field(object):
    def __init__(self, classnm, fieldnm, jtype, static):
        # All fields are public
        self.class_name = classnm  # String, ie. "java.lang.Math"
        self.field_name = fieldnm  # String "someField"
        self.jtype = jtype         # JvmType
        self.is_static = static    # True or False
    def load(self, gen):
        if self.is_static:
            gen._instr(GETSTATIC, self)
        else:
            gen._instr(GETFIELD, self)
    def store(self, gen):
        if self.is_static:
            gen._instr(PUTSTATIC, self)
        else:
            gen._instr(PUTFIELD, self)
    def jasmin_syntax(self):
        return "%s/%s %s" % (
            self.class_name.replace('.','/'), self.field_name, self.jtype)

SYSTEMOUT = Field('java.lang.System', 'out', jPrintStream, True)
SYSTEMERR = Field('java.lang.System', 'err', jPrintStream, True)

# ___________________________________________________________________________
# Constants
#
# Constant objects record constants of various types, and can be used
# to emit the required instructions to load their value.

class Const(object):
    def load(self, gen):
        """ Emits code required to reference a constant.  Usually invoked
        by generator.emit() """
        raise NotImplementedError
    def initialize(self, gen):
        """ Emits code required to DEFINE a constant (if any).  Default
        version does nothing. """
        pass

class VoidConst(object):
    def load(self, gen):
        pass

class NullConst(object):
    def load(self, gen):
        gen.emit(ACONST_NULL)

class WarnNullConst(NullConst):
    def load(self, gen):
        gen.add_comment("   substituting NULL")
        NullConst.load(self, gen)

class SignedIntConst(Const):
    def __init__(self, value):
        self.value = value
    def load(self, gen):
        # In theory, we could get rid of CONST5 flag and do optimization
        # here, but then all code would have to use SignedIntConst, and
        # that seems uglier
        gen.emit(ICONST, self.value)

class UnsignedIntConst(SignedIntConst):
    def __init__(self, value):
        assert value >= 0
        if value <= 0x7FFFFFFF:
            SignedIntConst.__init__(self, value)
        else:
            # Find the negative version of the value that will
            # represent this constant, and treat it like a signed
            # integer:
            value = value ^ 0xFFFFFFFF
            value += 1
            value *= -1
            assert value < 0
            value = int(value)
            SignedIntConst.__init__(self, value)

class DoubleConst(Const):
    def __init__(self, value):
        self.value = value
    def load(self, gen):
        if value == 0.0:
            gen.emit(DCONST_0)
        elif value == 1.0:
            gen.emit(DCONST_1)
        else:
            gen.emit(LDC2, self.value)

class SignedLongConst(Const):
    def __init__(self, value):
        self.value = value
    def load(self, gen):
        if value == 0:
            gen.emit(LCONST_0)
        elif value == 1:
            gen.emit(LCONST_1)
        else:
            gen.emit(LDC2, self.value)

class UnsignedLongConst(SignedLongConst):
    def __init__(self, value):
        assert value >= 0
        if value <= 0x7FFFFFFFFFFFFFFFL:
            SignedIntConst.__init__(self, value)
        else:
            # Find the negative version of the value that will
            # represent this constant, and treat it like a signed
            # integer:
            value = value ^ 0xFFFFFFFFFFFFFFFF
            value += 1
            value *= -1
            assert value < 0
            SignedLongConst.__init__(self, value)

class UnicodeConst(Const):
    def __init__(self, value):
        self.value = value
    def load(self, gen):
        assert isinstance(self.value, unicode)
        def escape(char):
            if char == '"': return r'\"'
            if char == '\n': return r'\n'
            return char
        res = ('"' + 
               "".join(escape(c) for c in self.value.encode('utf-8')) +
               '"')
        gen.emit(LDC, res)

class ComplexConst(Const):
    def __init__(self, fieldinfo, methodinfo):
        """
        Stores information about "complex" constants.  These are constants
        that we cannot embed in the Java file and which require a method
        to initialize.  They are stored in static fields, and initialized
        with static methods that should be embedded in a class's static{}
        section.
        
        fieldinfo --- the static field that will hold the value
        methodinfo --- a static method that initializes the value.  Should
        have no arguments.
        """
        self.fieldinfo = fieldinfo
        self.methodinfo = methodinfo
    def load(self, gen):
        self.fieldinfo.load(gen)
    def initialize(self, gen):
        gen.emit(self.methodinfo)

# ___________________________________________________________________________
# Generator State

class ClassState(object):
    """ When you invoked begin_class(), one of these objects is allocated
    and tracks the state as we go through the definition process. """
    def __init__(self, classnm, superclassnm):
        self.class_name = classnm
        self.superclass_name = superclassnm
    def out(self, arg):
        self.file.write(arg)

class FunctionState(object):
    """ When you invoked begin_function(), one of these objects is allocated
    and tracks the state as we go through the definition process. """
    def __init__(self):
        self.next_offset = 0
        self.local_vars = {}
        self.instr_counter = 0
    def add_var(self, jvar, jtype):
        """ Adds new entry for variable 'jvar', of java type 'jtype' """
        idx = self.next_offset
        self.next_offset += jtype.type_width()
        if jvar:
            assert jvar not in self.local_vars # never been added before
            self.local_vars[jvar] = idx
        return idx
    def var_offset(self, jvar, jtype):
        """ Returns offset for variable 'jvar', of java type 'jtype' """
        if jvar in self.local_vars:
            return self.local_vars[jvar]
        return self.add_var(jvar, jtype)


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

    def begin_class(self, classnm, superclsnm):
        """
        Begins a class declaration.  Overall flow of class declaration
        looks like:

        begin_class()
        [add_field()]
        emit_constructor()
        [begin_function()...end_function()]
        end_class()

        Where items in brackets may appear anywhere from 0 to inf times.
        
        classnm --- full Java name of the class (i.e., "java.lang.String")
        superclassnm --- full Java name of the super class
        """
        assert not self.curclass
        self.curclass = ClassState(classnm, superclsnm)
        self._begin_class()

    def end_class(self):
        self._end_class()
        self.curclass = None
        self.curfunc = None

    def _begin_class(self):
        """ Main implementation of begin_class """
        raise NotImplementedError

    def _end_class(self):
        """ Main implementation of end_class """
        raise NotImplementedError    

    def add_field(self, fobj):
        """
        fobj: a Field object
        """
        unimplemented

    def emit_constructor(self):
        """
        Emits the constructor for this class, which merely invokes the
        parent constructor.
        
        superclsnm --- same Java name of super class as from begin_class
        """
        jtype = jvm_for_class(self.curclass.class_name)
        self.begin_function("<init>", [], [jtype], jVoid)
        self.load_jvm_var(jtype, 0)
        jmethod = Method(self.curclass.superclass_name, "<init>", "()V",
                         opcode=INVOKESPECIAL)
        jmethod.invoke(self)
        self.return_val(jVoid)
        self.end_function()

    def begin_function(self, funcname, argvars, argtypes, rettype,
                       static=False):
        """
        funcname --- name of the function
        argvars --- list of objects passed to load() that represent arguments;
                    should be in order, or () if load() will not be used
        argtypes --- JvmType for each argument [INCLUDING this]
        rettype --- JvmType for the return value
        static --- keyword, if true then a static func is generated

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
            self.curfunc.add_var(var, ty)
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

    def return_val(self, vartype):
        """ Returns a value from top of stack of the JvmType 'vartype' """
        self._instr(RETURN.for_type(vartype))

    def load_string(self, str):
        uni = str.decode('utf-8')
        UnicodeConst(uni).load(self)

    def load_jvm_var(self, vartype, varidx):
        """ Loads from jvm slot #varidx, which is expected to hold a value of
        type vartype """
        assert varidx < self.curfunc.next_offset
        opc = LOAD.for_type(vartype)
        self.add_comment("     load_jvm_jar: vartype=%s varidx=%s" % (
            repr(vartype), repr(varidx)))
        self._instr(opc, varidx)

    def store_jvm_var(self, vartype, varidx):
        """ Loads from jvm slot #varidx, which is expected to hold a value of
        type vartype """
        self.add_comment("     store_jvm_jar: vartype=%s varidx=%s" % (
            repr(vartype), repr(varidx)))
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
        labelnum = self.label_counter
        self.label_counter += 1
        res = ('Label', labelnum, desc)
        if mark:
            self.mark(res)
        return res

    def load_this_ptr(self):
        """ Convenience method.  Be sure you only call it from a
        virtual method, not static methods. """
        self.load_jvm_var(jObject, 0)
    
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
        jty = self.db.lltype_to_cts(v.concretetype)
        # Determine index in stack frame slots:
        #   note that arguments and locals can be treated the same here
        return jty, self.curfunc.var_offset(v, jty)
        
    def load(self, value):
        if isinstance(value, flowmodel.Variable):
            jty, idx = self._var_data(value)
            return self.load_jvm_var(jty, idx)

        if isinstance(value, flowmodel.Constant):
            return self.db.record_const(value).load(self)
            
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
        if fieldname == "meta":
            # temporary hack
            self.add_comment("      WARNING: emulating meta for now")
            self.emit(POP)
            self.emit(POP)
        else:
            clsobj = self.db.pending_class(CONCRETETYPE)
            fieldobj = clsobj.lookup_field(fieldname)
            fieldobj.store(self)

    def get_field(self, CONCRETETYPE, fieldname):
        if fieldname == 'meta':
            self.add_comment("      WARNING: emulating meta for now")
            self.emit(POP)
            self.emit(ACONST_NULL)
        else:
            clsobj = self.db.pending_class(CONCRETETYPE)
            fieldobj = clsobj.lookup_field(fieldname)
            fieldobj.load(self)

    def downcast(self, TYPE):
        jtype = self.db.lltype_to_cts(TYPE)
        self._instr(CHECKCAST, jtype)
        
    def instanceof(self, TYPE):
        jtype = self.db.lltype_to_cts(TYPE)
        self._instr(INSTANCEOF, jtype)

    def branch_unconditionally(self, target_label):
        self._instr(GOTO, target_label)

    def branch_conditionally(self, cond, target_label):
        if cond:
            self._instr(IFNE, target_label)
        else:
            self._instr(IFEQ, target_label)

    def call_graph(self, graph):
        mthd = self.db.pending_function(graph)
        mthd.invoke(self)

    def call_method(self, OOCLASS, method_name):
        clsobj = self.db.pending_class(OOCLASS)
        mthd = clsobj.lookup_method(method_name)
        mthd.invoke(self)

    def call_primitive(self, graph):
        raise NotImplementedError

    def new(self, TYPE):
        clsobj = self.db.pending_class(TYPE)
        ctor = Method(clsobj.name, "<init>", "()V", opcode=INVOKESPECIAL)
        self.emit(NEW, clsobj.jvm_type())
        self.emit(DUP)
        self.emit(ctor)
        
    def instantiate(self):
        self.emit(PYPYRUNTIMENEW)

    # __________________________________________________________________
    # Methods invoked directly by strings in jvm/opcode.py

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

    is_null = lambda self: self._compare_op(IFNULL)
    is_not_null = lambda self: self._compare_op(IFNOTNULL)

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

    def __init__(self, db, outdir, package):
        JVMGenerator.__init__(self, db)
        self.outdir = outdir

    def _begin_class(self):
        """
        classnm --- full Java name of the class (i.e., "java.lang.String")
        """

        iclassnm = self.curclass.class_name.replace('.', '/')
        isuper = self.curclass.superclass_name.replace('.', '/')
        
        jfile = "%s/%s.j" % (self.outdir, iclassnm)

        try:
            jdir = jfile[:jfile.rindex('/')]
            os.makedirs(jdir)
        except OSError: pass
        self.curclass.file = open(jfile, 'w')

        # Write the JasminXT header
        self.curclass.out(".class public %s\n" % iclassnm)
        self.curclass.out(".super %s\n" % isuper)
        
    def _end_class(self):
        self.curclass.file.close()

    def close(self):
        assert self.curclass is None

    def add_comment(self, comment):
        self.curclass.out("  ; %s\n" % comment)

    def add_field(self, fobj):
        self.curclass.out('.field public %s %s\n' % (
            fobj.field_name, fobj.jtype))

    def _begin_function(self, funcname, argtypes, rettype, static):

        if not static: argtypes = argtypes[1:]

        # Throws clause?  Only use RuntimeExceptions?
        kw = ['public']
        if static: kw.append('static')
        self.curclass.out('.method %s %s(%s)%s\n' % (
            " ".join(kw), funcname,
            "".join(argtypes), rettype))

    def _end_function(self):
        self.curclass.out('.limit stack 100\n') # HACK, track max offset
        self.curclass.out('.limit locals %d\n' % self.curfunc.next_offset)
        self.curclass.out('.end method\n')

    def mark(self, lbl):
        """ Marks the point that a label indicates. """
        _, lblnum, lbldesc = lbl
        assert _ == "Label"
        self.curclass.out('  %s_%s:\n' % (lbldesc, lblnum))

    def _instr(self, opcode, *args):
        jvmstr, args = opcode.specialize_opcode(args)
        # XXX this whole opcode flag things is stupid, redo to be class based
        if opcode.flags & BRANCH:
            assert len(args) == 1
            _, lblnum, lbldesc = args[0]
            args = ('%s_%s' % (lbldesc, lblnum),)
        if opcode.flags & (INVOKE|FIELD):
            assert len(args) == 1
            args = (args[0].jasmin_syntax(),)
        instr_text = '    %s %s' % (jvmstr, " ".join([str(s) for s in args]))
        self.curclass.out('    %-60s ; %d\n' % (
            instr_text, self.curfunc.instr_counter))
        self.curfunc.instr_counter+=1

    def try_catch_region(self, excclsty, trystartlbl, tryendlbl, catchlbl):
        self.curclass.out('  .catch %s from %s to %s using %s\n' % (
            excclsty.int_class_name(), trystartlbl, tryendlbl, catchlbl))
                       

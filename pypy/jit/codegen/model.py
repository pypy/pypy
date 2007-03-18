from pypy.rlib.objectmodel import specialize


class NotConstant(Exception):
    pass

# all the following classes will be subclassed by each backend.

class GenVarOrConst(object):
    '''Instances of this "doubly abstract" class contains values,
    either run-time values or compile time constants.'''

    @specialize.arg(1)
    def revealconst(self, T):
        '''Return a value of low-level type T, or raise NotConstant.

        Some simple conversion may be required, e.g. casting an address to a
        pointer, but not converting a float to an integer.'''
        raise NotConstant(self)

class GenVar(GenVarOrConst):
    is_const = False

class GenConst(GenVarOrConst):
    is_const = True

# a word about "tokens":

# several llops take Void arguments, for example the fieldname of a
# getfield.  these need to be represented in some way during code
# generation, in the getfield example it might be the offset and size
# of the field in the structure.  but this is not enough in general,
# because on the powerpc you need to know if the value should be
# loaded into a general purpose or floating point register.

# for this kind of possibly machine dependent information, we have the
# concept of "token".  the tokens are created by specialize.memo()ed
# staticmethods on the RGenOp class, in particular fieldToken,
# allocToken, varsizeAllocToken, kindToken and sigToken.  See their
# docstrings for more.

# as they are memo-specialized, these methods can be full Python
# inside, but each method must always return the same type so the jit
# can store the results in a list, for example (each backend can
# decide what this type is independently, though)

class GenBuilder(object):
    '''Instances of GenBuilder -- generally referred to as "builders"
    -- are responsible for actually generating machine code.  One
    instance is responsible for one chunk of memory, and when it is
    filled or the generated code jumps away the builder is
    thrown away.'''

    # the genop methods should emit the machine code for a single llop.
    # for most llops, the genop1 and genop2 methods suffice, but some
    # (generally those that take Void arguments, or depend on the
    # types of the arguments) require special attention, and these are
    # handled by the genop_OPNAME methods.

    # the gv_* arguments are instances of GenVarOrConst

##     @specialize.arg(1)
##     def genop1(self, opname, gv_arg):

##     @specialize.arg(1)
##     def genop2(self, opname, gv_arg1, gv_arg2):

##     @specialize.arg(1)
##     def genraisingop1(self, opname, gv_arg):
##         return a pair (gv_result, gv_flag_set_if_exception)

##     @specialize.arg(1)
##     def genraisingop2(self, opname, gv_arg1, gv_arg2):
##         return a pair (gv_result, gv_flag_set_if_exception)

##     def genop_getfield(self, fieldtoken, gv_ptr):
##     def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
##     def genop_getsubstruct(self, fieldtoken, gv_ptr):
##     def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
##     def genop_getarraysize(self, arraytoken, gv_ptr):
##     def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
##     def genop_malloc_fixedsize(self, alloctoken):
##     def genop_malloc_varsize(self, varsizealloctoken, gv_size):
##     def genop_call(self, sigtoken, gv_fnptr, args_gv):
##     def genop_same_as(self, kindtoken, gv_x):
##     def genop_debug_pdb(self):    # may take an args_gv later
##     def genop_ptr_iszero(self, kindtoken, gv_ptr)
##     def genop_ptr_nonzero(self, kindtoken, gv_ptr)
##     def genop_ptr_eq(self, kindtoken, gv_ptr1, gv_ptr2)
##     def genop_ptr_ne(self, kindtoken, gv_ptr1, gv_ptr2)

    # the other thing that happens for a given chunk is entering and
    # leaving basic blocks inside it.

    def enter_next_block(self, kinds, args_gv):
        '''Called before generating the code for a basic block.

        zip(kinds, args_gv) gives the kindtoken and GenVarOrConst for
        each inputarg of the block.

        The Obscure Bit: args_gv must be mutated in place until it is a
        list of unique GenVars.  So GenConsts must be replaced with
        GenVars, and duplicate GenVars must be made unique.  Optionally,
        *all* GenVars can be replaced with new GenVars, for example if
        the same value might live in different locations (registers,
        places on the stack) in different basic blocks.

        Returns an instance of GenLabel that can later be jumped to.
        '''
        raise NotImplementedError

    def jump_if_false(self, gv_condition, args_for_jump_gv):
        '''Make a fresh builder, insert in the current block a
        check of gv_condition and a conditional jump to the new block
        that is taken if gv_condition is false and return the new
        builder.

        The current builder stays open.  To make the backend\'s life
        easier it must be closed before the fresh builder is used at
        all, and the first thing to call on the latter is
        start_writing().'''
        raise NotImplementedError

    def jump_if_true(self, gv_condition, args_for_jump_gv):
        '''See above, with the obvious difference :)'''
        raise NotImplementedError

    def finish_and_return(self, sigtoken, gv_returnvar):
        '''Emit the epilogue code for the function, and the code to
        return gv_returnvar.  This "closes" the current builder.'''
        raise NotImplementedError

    def finish_and_goto(self, outputargs_gv, target):
        '''Insert an unconditional jump to target.

        outputargs_gv is a list of GenVarOrConsts which corresponds to Link.args
        target is an instance of GenLabel.

        This must insert code to make sure that the values in
        outputargs_gv go where the target block expects them to be.

        This "closes" the current builder.
        '''
        raise NotImplementedError

    def flexswitch(self, gv_exitswitch, args_gv):
        '''The Fun Stuff.

        Generates a switch on the value of gv_exitswitch that can have
        cases added to it later, i.e. even after it\'s been executed a
        few times.

        args_gv is the list of live variables.  It\'s the list of
        variables that can be used in each switch case.

        Returns a tuple:
        - an instance of CodeGenSwitch (see below)
        - a new builder for the default case, that will be jumped to
          when the switched-on GenVar does not take the value of any case.

        This "closes" the current builder.
        '''
        raise NotImplementedError

    def show_incremental_progress(self):
        '''Give some indication of the code that this instance has generated.

        So far, the machine code backends don\'t actually do anything for this.
        '''

    def log(self, msg):
        '''Optional method: prints or logs the position of the generated code
        along with the given msg.
        '''
    def pause_writing(self, args_gv):
        '''Optional method: Called when the builder will not be used for a
        while. This allows the builder to be freed. The pause_writing()
        method returns the next builder, on which you will have to call
        start_writing() before you continue.
        '''
        return self

    def start_writing(self):
        '''Start a builder returned by jump_if_xxx(), or resumes a paused
        builder.'''


    # read frame var support
    
    def genop_get_frame_base(self):
        '''Generate an operation that reads the current stack frame pointer.
        The pointer can later be passed to read_frame_var() and
        write_frame_place().  This returns a GenVar.
        '''
        raise NotImplementedError

    def get_frame_info(self, vars_gv):
        '''Return a constant object that describes where the variables are
        inside the stack frame.  The result should be correct for the
        current basic block.  It forces the listed variables to live in the
        stack instead of being allocated to registers (or at least to be
        copied into the stack when get_frame_info is called; a copy is ok
        because there is no way to change the value of a variable).
        '''
        raise NotImplementedError

    def alloc_frame_place(self, kind, gv_initial_value=None):
        '''Reserve a "place" in the frame stack where called functions
        can write to, with write_frame_place().  The place is not valid
        any more after the current basic block.

        Return value: any object representing the place.
        '''
        raise NotImplementedError

    def genop_absorb_place(self, kind, place):
        '''Absorb a place.  This turns it into a regular variable,
        containing the last value written into that place.  The place
        itself is no longer a valid target for write_frame_place()
        afterwards.

        Return value: a fresh GenVar.
        '''
        raise NotImplementedError


class GenLabel(object):
    '''A "smart" label.  Represents an address of the start of a basic
    block and the location of the inputargs on entry to that block.'''


class AbstractRGenOp(object):
    '''An RGenOp instance is responsible for coordinating the
    generation of machine code for a given architecture.

    Conceptually at least, instances do not have much state, although
    pratically they have some state relating to management of buffers
    being written to.
    '''

    def newgraph(self, sigtoken, name):
        """Begin code generation for a new function, which signature
        described by sigtoken.  Returns a new builder, entrypoint,
        inputargs_gv where the new builder is for the startblock,
        entrypoint is the address of the new function as GenConst and
        inputargs_gv is the location of each argument on entry to the
        function.  name is for debugging purposes.  The fresh builder
        is initially paused, you must call start_writing() before
        actually putting operations in it.
        """
        raise NotImplementedError

    # all staticmethods commented out for the sake of the annotator

    #@specialize.genconst(0)
    #def genconst(self, llvalue):
    #    """Convert an llvalue to an instance of (a subclass of)
    #    GenConst.  The difference between this and
    #    constPrebuiltGlobal is that this method can use storage
    #    associated with the current RGenOp, i.e. self.  If self is
    #    thrown away, it's safe for anything that this method has
    #    returned to disappear too."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.genconst(0)
    #def constPrebuiltGlobal(llvalue):
    #    """Convert an llvalue to an instance of (a subclass of) GenConst.
    #    This is for immortal prebuilt data."""
    #    raise NotImplementedError

    #@staticmethod
    #def genzeroconst(kind):
    #    """Get a GenConst containing the value 0 (or NULL) of the
    #    correct kind."""
    #    raise NotImplementedError

    def replay(self, label, kinds):
        '''Return a builder that will "generate" exactly the same code
        as was already generated, starting from label.  kinds is a
        list of kindTokens for the inputargs associated with label.

        The purpose of this is to reconstruct the knowledge of the
        locations of the GenVars at some later point in the code, any
        code actually generated during replaying is thrown away.'''
        raise NotImplementedError

    #@staticmethod
    #def erasedType(T):
    #    '''Return the canonical type T2 such that kindToken(T) == kindToken(T2).
    #    For example, it\'s common to erase all Ptrs to llmemory.GCREF.
    #    '''

    #@staticmethod
    #@specialize.memo()
    #def fieldToken(T, name):
    #    """Return a token describing the location and type of the field 'name'
    #    within the Struct T."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def allocToken(T):
    #    """Return a token describing the size of the fixed-size type T."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def varsizeAllocToken(T):
    #    """Return a token describing the size of the var-size type T,
    #    i.e. enough information to, when given the item count,
    #    compute how much memory to allocate."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def arrayToken(A):
    #    """Return a token describing the Array A, enough information
    #    to read and write the length, find the base of the items
    #    array and find the size of each item."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def kindToken(T):
    #    """Return a token that describes how to store the low-level
    #    type T.  For example, on PowerPC this might just indicate
    #    whether values of type T live in the FPU or not."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.memo()
    #def sigToken(FUNCTYPE):
    #    """Return a token describing the signature of FUNCTYPE."""
    #    raise NotImplementedError

    #@staticmethod
    #@specialize.arg(0)
    #def read_frame_var(T, base, info, index):
    #    """Read from the stack frame of a caller.  The 'base' is the
    #    frame stack pointer captured by the operation generated by
    #    genop_get_frame_base().  The 'info' is the object returned by
    #    get_frame_info(); we are looking for the index-th variable
    #    in the list passed to get_frame_info()."""

    #@staticmethod
    #@specialize.arg(0)
    #def write_frame_place(T, base, place, value):
    #    """Write into a place in the stack frame of a caller.  The
    #    'base' is the frame stack pointer captured by the operation
    #    generated by genop_get_frame_base()."""

    #@staticmethod
    #@specialize.arg(0)
    #def read_frame_place(T, base, place):
    #    """Read from a place in the stack frame of a caller.  The
    #    'base' is the frame stack pointer captured by the operation
    #    generated by genop_get_frame_base()."""

    @staticmethod
    def get_python_callable(FUNC, gv):
        """NOT_RPYTHON
        Turn a GenConst containing the address of a function into a
        Python callable object, for testing purposes.
        """
        from pypy.rpython.lltypesystem import lltype
        from ctypes import cast, c_void_p, CFUNCTYPE, c_int, c_float
        def _to_ctypes(t): #limited type support for now
            if t == lltype.Float:
                return c_float
            if t == lltype.Void:
                return None
            return c_int
        ctypestypes = [_to_ctypes(t) for t in FUNC.TO.ARGS]
        ctypesres = _to_ctypes(FUNC.TO.RESULT)
        return cast(c_void_p(gv.value), CFUNCTYPE(ctypesres, *ctypestypes))


class CodeGenSwitch(object):
    '''A CodeGenSwitch is a flexible switch on a given GenVar that can have cases added
    to it "later", i.e. after it has been executed a few times.'''

    def add_case(self, gv_case):
        '''Make a new builder that will be jumped to when the
        switched-on GenVar takes the value of the GenConst gv_case.'''
        raise NotImplementedError

# ____________________________________________________________

dummy_var = GenVar()

class ReplayFlexSwitch(CodeGenSwitch):

    def __init__(self, replay_builder):
        self.replay_builder = replay_builder

    def add_case(self, gv_case):
        return self.replay_builder

class ReplayBuilder(GenBuilder):

    def __init__(self, rgenop):
        self.rgenop = rgenop

    def end(self):
        pass

    @specialize.arg(1)
    def genop1(self, opname, gv_arg):
        return dummy_var

    @specialize.arg(1)
    def genraisingop1(self, opname, gv_arg):
        return dummy_var, dummy_var

    @specialize.arg(1)
    def genop2(self, opname, gv_arg1, gv_arg2):
        return dummy_var

    @specialize.arg(1)
    def genraisingop2(self, opname, gv_arg1, gv_arg2):
        return dummy_var, dummy_var

    def genop_ptr_iszero(self, kind, gv_ptr):
        return dummy_var

    def genop_ptr_nonzero(self, kind, gv_ptr):
        return dummy_var

    def genop_ptr_eq(self, kind, gv_ptr1, gv_ptr2):
        return dummy_var

    def genop_ptr_ne(self, kind, gv_ptr1, gv_ptr2):
        return dummy_var

    def genop_getfield(self, fieldtoken, gv_ptr):
        return dummy_var

    def genop_setfield(self, fieldtoken, gv_ptr, gv_value):
        return dummy_var

    def genop_getsubstruct(self, fieldtoken, gv_ptr):
        return dummy_var

    def genop_getarrayitem(self, arraytoken, gv_ptr, gv_index):
        return dummy_var

    def genop_getarraysubstruct(self, arraytoken, gv_ptr, gv_index):
        return dummy_var

    def genop_getarraysize(self, arraytoken, gv_ptr):
        return dummy_var

    def genop_setarrayitem(self, arraytoken, gv_ptr, gv_index, gv_value):
        return dummy_var

    def genop_malloc_fixedsize(self, size):
        return dummy_var

    def genop_malloc_varsize(self, varsizealloctoken, gv_size):
        return dummy_var
        
    def genop_call(self, sigtoken, gv_fnptr, args_gv):
        return dummy_var

    def genop_same_as(self, kind, gv_x):
        return dummy_var

    def genop_debug_pdb(self):    # may take an args_gv later
        pass

    def enter_next_block(self, kinds, args_gv):
        return None

    def jump_if_false(self, gv_condition, args_gv):
        return self

    def jump_if_true(self, gv_condition, args_gv):
        return self

    def finish_and_return(self, sigtoken, gv_returnvar):
        pass

    def finish_and_goto(self, outputargs_gv, target):
        pass

    def flexswitch(self, gv_exitswitch, args_gv):
        flexswitch = ReplayFlexSwitch(self)
        return flexswitch, self

    def show_incremental_progress(self):
        pass

    def genop_get_frame_base(self):
        return dummy_var

    def get_frame_info(self, vars_gv):
        return None

    def alloc_frame_place(self, kind, gv_initial_value=None):
        return None

    def genop_absorb_place(self, kind, place):
        return dummy_var

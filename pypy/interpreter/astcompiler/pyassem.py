import sys
from pypy.interpreter.astcompiler.consts \
     import CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pycode import PyCode
from pypy.tool import stdlib_opcode as pythonopcode
from pypy.interpreter.error import OperationError


class InternalCompilerError(Exception):
    """Something went wrong in the ast compiler."""


class PyFlowGraph(object):

    def __init__(self, space, name, filename, argnames=None,
                 optimized=0, klass=0, newlocals=0):
        self.space = space
        if argnames is None:
            argnames = []
        self.name = name
        self.filename = filename
        self.w_docstring = space.w_None
        self.argcount = len(argnames)
        self.klass = klass
        self.flags = 0
        if optimized:
            self.flags |= CO_OPTIMIZED
        if newlocals:
            self.flags |= CO_NEWLOCALS

        self.atomic_types = [space.type(space.w_None),
                             space.w_int,
                             space.w_str,
                             space.w_unicode,
                             space.w_bool,
                             space.w_float,
                             space.w_long,
                             space.w_complex,
                             space.type(space.w_Ellipsis),
                             ]
        self.const2index = [None] * len(self.atomic_types)
        # ^^^ each item is a wrapped dict {w_key: wrap(index in consts_w)}
        self.consts_w = []
        self.names = []
        # Free variables found by the symbol table scan, including
        # variables used only in nested scopes, are included here.
        self.freevars = []
        self.cellvars = []
        self.varnames = list(argnames)
        # The bytecode we are building, as a list of characters
        self.co_code = []
        # Pending label targets to fix: [(label, index-in-co_code-to-fix, abs)]
        self.pending_label_fixes = []
        self.lnotab = None

    def setDocstring(self, w_docstring):
        self.w_docstring = w_docstring

    def setFlag(self, flag):
        self.flags = self.flags | flag
        if flag == CO_VARARGS:
            self.argcount = self.argcount - 1

    def checkFlag(self, flag):
        return self.flags & flag

    def setFreeVars(self, names):
        self.freevars = list(names)

    def setCellVars(self, names):
        self.cellvars = names

    # ____________________________________________________________
    # Simple instructions

    def emit(self, opname):
        self.co_code.append(chr(pythonopcode.opmap[opname]))

    def emitop_extended_arg(self, intval):
        assert intval <= 0x7FFFFFFF
        self.emit('EXTENDED_ARG')
        self.co_code.append(chr((intval >> 16) & 0xFF))
        self.co_code.append(chr((intval >> 24) & 0xFF))
        return intval & 0xFFFF
    emitop_extended_arg._dont_inline_ = True

    def emitop_setlineno(self, lineno):
        if self.lnotab is None:
            self.lnotab = LineAddrTable(lineno)
        else:
            self.lnotab.nextLine(len(self.co_code), lineno)
    emitop_setlineno._dont_inline_ = True

    def emitop_int(self, opname, intval):
        assert intval >= 0
        if opname == "SET_LINENO":
            self.emitop_setlineno(intval)
            return
        if intval > 0xFFFF:
            intval = self.emitop_extended_arg(intval)
        self.emit(opname)
        self.co_code.append(chr(intval & 0xFF))
        self.co_code.append(chr(intval >> 8))

    # ____________________________________________________________
    # Instructions with an object argument (LOAD_CONST)

    def emitop_obj(self, opname, w_obj):
        index = self._lookupConst(w_obj)
        self.emitop_int(opname, index)

    def _lookupConst(self, w_obj):
        # insert the docstring first, if necessary
        if len(self.consts_w) == 0:
            index = self._lookupConstInternal(self.w_docstring)
            assert index == 0
        return self._lookupConstInternal(w_obj)

    def _lookupConstInternal(self, w_obj):
        # Some types of object can be shared if equal values appear
        # several times in the consts_w.
        space = self.space
        w_type = space.type(w_obj)
        w_const2index = None
        for i in range(len(self.atomic_types)):
            if space.is_w(w_type, self.atomic_types[i]):
                w_const2index = self.const2index[i]
                if w_const2index is None:
                    w_const2index = self.const2index[i] = space.newdict()
                else:
                    w_index = space.finditem(w_const2index, w_obj)
                    if w_index is not None:
                        return space.int_w(w_index)
                break
        result = len(self.consts_w)
        self.consts_w.append(w_obj)
        if w_const2index is not None:
            space.setitem(w_const2index, w_obj, space.wrap(result))
        return result

    # ____________________________________________________________
    # Instructions with a name argument

    def emitop_name(self, opname, name):
        conv = self._converters[opname]
        index = conv(self, name)
        self.emitop_int(opname, index)

    def _lookupName(self, name, list):
        """Return index of name in list, appending if necessary
        """
        # XXX use dicts instead of lists
        assert isinstance(name, str)
        for i in range(len(list)):
            if list[i] == name:
                return i
        end = len(list)
        list.append(name)
        return end

    def _lookupClosureName(self, name):
        """Return index of name in (self.cellvars + self.freevars)
        """
        assert isinstance(name, str)
        list = self.cellvars
        for i in range(len(list)):
            if list[i] == name:
                return i
        list = self.freevars
        for i in range(len(list)):
            if list[i] == name:
                return len(self.cellvars) + i
        raise InternalCompilerError("name '%s' not found in cell or free vars"
                                    % name)

    def _convert_LOAD_FAST(self, arg):
        self._lookupName(arg, self.names)
        return self._lookupName(arg, self.varnames)
    _convert_STORE_FAST = _convert_LOAD_FAST
    _convert_DELETE_FAST = _convert_LOAD_FAST

    def _convert_NAME(self, arg):
        return self._lookupName(arg, self.names)
    _convert_LOAD_NAME = _convert_NAME
    _convert_STORE_NAME = _convert_NAME
    _convert_DELETE_NAME = _convert_NAME
    _convert_IMPORT_NAME = _convert_NAME
    _convert_IMPORT_FROM = _convert_NAME
    _convert_STORE_ATTR = _convert_NAME
    _convert_LOAD_ATTR = _convert_NAME
    _convert_DELETE_ATTR = _convert_NAME
    _convert_LOAD_GLOBAL = _convert_NAME
    _convert_STORE_GLOBAL = _convert_NAME
    _convert_DELETE_GLOBAL = _convert_NAME
    _convert_LOOKUP_METHOD = _convert_NAME

    def _convert_DEREF(self, arg):
        self._lookupName(arg, self.names)
        return self._lookupClosureName(arg)
    _convert_LOAD_DEREF = _convert_DEREF
    _convert_STORE_DEREF = _convert_DEREF

    def _convert_LOAD_CLOSURE(self, arg):
        return self._lookupClosureName(arg)

    _cmp = list(pythonopcode.cmp_op)
    def _convert_COMPARE_OP(self, arg):
        return self._cmp.index(arg)

    _converters = {}
    for name, obj in locals().items():
        if name[:9] == "_convert_":
            opname = name[9:]
            _converters[opname] = obj
    del name, obj, opname

    # ____________________________________________________________
    # Labels and jumps

    def newBlock(self):
        """This really returns a new label, initially not pointing anywhere."""
        return Label()

    def nextBlock(self, label):
        if label.position >= 0:
            raise InternalCompilerError("Label target already seen")
        label.position = len(self.co_code)

    def emitop_block(self, opname, label):
        absolute = opname in self.hasjabs
        target = label.position
        if target < 0:     # unknown yet
            i = len(self.co_code)
            self.pending_label_fixes.append((label, i, absolute))
            target = 0xFFFF
        else:
            if not absolute:
                # if the target was already seen, it must be backward,
                # which is forbidden for these instructions
                raise InternalCompilerError("%s cannot do a back jump" %
                                            (opname,))
        self.emitop_int(opname, target)

    hasjrel = {}
    for i in pythonopcode.hasjrel:
        hasjrel[pythonopcode.opname[i]] = True
    hasjabs = {}
    for i in pythonopcode.hasjabs:
        hasjabs[pythonopcode.opname[i]] = True
    del i

    # ____________________________________________________________

    def dump(self):
        try:
            self.fixLabelTargets()
        except:
            pass
        if not hasattr(self, 'stacksize'):
            self.stacksize = 99    # temporarily
        co = self.newCodeObject()
        co.dump()

    def getCode(self):
        self.fixLabelTargets()
        self.computeStackDepth()
        return self.newCodeObject()

    def _setdepth(self, i, stackdepth):
        if stackdepth < 0:
            raise InternalCompilerError("negative stack depth")
        depths = self._stackdepths
        previous_value = depths[i]
        if previous_value < 0:
            if i <= self._stackdepth_seen_until:
                raise InternalCompilerError("back jump to code that is "
                                            "otherwise not reachable")
            depths[i] = stackdepth
        else:
            if previous_value != stackdepth:
                raise InternalCompilerError("inconsistent stack depth")

    def computeStackDepth(self):
        UNREACHABLE = -1
        co_code = self.co_code
        self._stackdepths = [UNREACHABLE] * len(co_code)
        self._stackdepths[0] = 0
        consts_w = self.getConsts()
        finally_targets = {}
        largestsize = 0
        i = 0

        while i < len(co_code):
            curstackdepth = self._stackdepths[i]
            if curstackdepth > largestsize:
                largestsize = curstackdepth
            self._stackdepth_seen_until = i

            # decode the next instruction
            opcode = ord(co_code[i])
            if opcode >= pythonopcode.HAVE_ARGUMENT:
                oparg = ord(co_code[i+1]) | (ord(co_code[i+2]) << 8)
                i += 3
                if opcode == pythonopcode.opmap['EXTENDED_ARG']:
                    opcode = ord(co_code[i])
                    assert opcode >= pythonopcode.HAVE_ARGUMENT
                    oparg = ((oparg << 16) |
                             ord(co_code[i+1]) | (ord(co_code[i+2]) << 8))
                    i += 3
            else:
                oparg = sys.maxint
                i += 1

            if curstackdepth == UNREACHABLE:
                continue    # ignore unreachable instructions

            if opcode in DEPTH_OP_EFFECT_ALONG_JUMP:
                if opcode in pythonopcode.hasjabs:
                    target_i = oparg
                else:
                    target_i = i + oparg
                effect = DEPTH_OP_EFFECT_ALONG_JUMP[opcode]
                self._setdepth(target_i, curstackdepth + effect)
                if opcode == pythonopcode.opmap['SETUP_FINALLY']:
                    finally_targets[target_i] = None

            try:
                tracker = DEPTH_OP_TRACKER[opcode]
            except KeyError:
                pass
            else:
                effect = tracker(oparg)
                curstackdepth += effect
                if i in finally_targets:
                    curstackdepth += 2  # see pyopcode.FinallyBlock.cleanup()
                self._setdepth(i, curstackdepth)

        self.stacksize = largestsize

    def fixLabelTargets(self):
        for label, i, absolute in self.pending_label_fixes:
            target = label.position
            if target < 0:
                raise InternalCompilerError("Label target not found")
            if not absolute:
                target = target - (i+3)   # relative jump
                if target < 0:
                    raise InternalCompilerError("Unexpected backward jump")
            if target > 0xFFFF:
                # CPython has the same limitation, for the same practical
                # reason
                msg = "function too large (bytecode would jump too far away)"
                space = self.space
                raise OperationError(space.w_SystemError, space.wrap(msg))
            self.co_code[i+1] = chr(target & 0xFF)
            self.co_code[i+2] = chr(target >> 8)

    def newCodeObject(self):
        if (self.flags & CO_NEWLOCALS) == 0:
            nlocals = 0
        else:
            nlocals = len(self.varnames)
        argcount = self.argcount
        if self.flags & CO_VARKEYWORDS:
            argcount = argcount - 1
        if self.lnotab is None:    # obscure case
            firstline = 0
            lnotab = ""
        else:
            firstline = self.lnotab.firstline
            lnotab = self.lnotab.getTable()
        return PyCode( self.space, argcount, nlocals,
                       self.stacksize, self.flags,
                       ''.join(self.co_code),
                       self.getConsts(),
                       self.names,
                       self.varnames,
                       self.filename, self.name,
                       firstline,
                       lnotab,
                       self.freevars,
                       self.cellvars
                       )

    def getConsts(self):
        """Return a tuple for the const slot of the code object
        """
        # sanity-check
        index = self._lookupConst(self.w_docstring)
        if index != 0:
            raise InternalCompilerError("setDocstring() called too late")
        return self.consts_w[:]

# ____________________________________________________________

class Label(object):
    position = -1

# ____________________________________________________________
# Encoding the line numbers in lnotab

class LineAddrTable:
    """lnotab

    This class builds the lnotab, which is documented in compile.c.
    Here's a brief recap:

    For each SET_LINENO instruction after the first one, two bytes are
    added to lnotab.  (In some cases, multiple two-byte entries are
    added.)  The first byte is the distance in bytes between the
    instruction for the last SET_LINENO and the current SET_LINENO.
    The second byte is offset in line numbers.  If either offset is
    greater than 255, multiple two-byte entries are added -- see
    compile.c for the delicate details.
    """

    def __init__(self, firstline):
        self.firstline = firstline
        self.lastline = firstline
        self.lastoff = 0
        self.lnotab = []     # list of characters

    def nextLine(self, codeOffset, lineno):
        # compute deltas
        addr = codeOffset - self.lastoff
        line = lineno - self.lastline
        # Python assumes that lineno always increases with
        # increasing bytecode address (lnotab is unsigned char).
        # Depending on when SET_LINENO instructions are emitted
        # this is not always true.  Consider the code:
        #     a = (1,
        #          b)
        # In the bytecode stream, the assignment to "a" occurs
        # after the loading of "b".  This works with the C Python
        # compiler because it only generates a SET_LINENO instruction
        # for the assignment.
        if line >= 0:
            push = self.lnotab.append
            while addr > 255:
                push(chr(255)); push(chr(0))
                addr -= 255
            while line > 255:
                push(chr(addr)); push(chr(255))
                line -= 255
                addr = 0
            if addr > 0 or line > 0:
                push(chr(addr)); push(chr(line))
            self.lastline = lineno
            self.lastoff = codeOffset

    def getTable(self):
        return ''.join(self.lnotab)

# ____________________________________________________________
# Stack depth tracking

def depth_UNPACK_SEQUENCE(count):
    return count-1
def depth_BUILD_TUPLE(count):
    return -count+1
def depth_BUILD_LIST(count):
    return -count+1
def depth_CALL_FUNCTION(argc):
    hi = argc//256
    lo = argc%256
    return -(lo + hi * 2)
def depth_CALL_FUNCTION_VAR(argc):
    return depth_CALL_FUNCTION(argc)-1
def depth_CALL_FUNCTION_KW(argc):
    return depth_CALL_FUNCTION(argc)-1
def depth_CALL_FUNCTION_VAR_KW(argc):
    return depth_CALL_FUNCTION(argc)-2
def depth_CALL_METHOD(argc):
    return -argc-1
def depth_CALL_LIKELY_BUILTIN(argc):
    nargs = argc & 0xFF
    return -nargs+1
def depth_MAKE_FUNCTION(argc):
    return -argc
def depth_MAKE_CLOSURE(argc):
    return -argc-1
def depth_BUILD_SLICE(argc):
    if argc == 2:
        return -1
    elif argc == 3:
        return -2
    assert False, 'Unexpected argument %s to depth_BUILD_SLICE' % argc
    
def depth_DUP_TOPX(argc):
    return argc

def setup_stack_depth_tracker():
    effect = {
        'STOP_CODE': 0,
        'NOP': 0,
        'EXTENDED_ARG': 0,
        'POP_TOP': -1,
        'DUP_TOP': 1,
        'SLICE+0': 0,
        'SLICE+1': -1,
        'SLICE+2': -1,
        'SLICE+3': -2,
        'STORE_SLICE+0': -2,
        'STORE_SLICE+1': -3,
        'STORE_SLICE+2': -3,
        'STORE_SLICE+3': -4,
        'DELETE_SLICE+0': -1,
        'DELETE_SLICE+1': -2,
        'DELETE_SLICE+2': -2,
        'DELETE_SLICE+3': -3,
        'STORE_SUBSCR': -3,
        'DELETE_SUBSCR': -2,
        'PRINT_EXPR': -1,
        'PRINT_ITEM': -1,
        'PRINT_ITEM_TO': -2,
        'PRINT_NEWLINE': 0,
        'PRINT_NEWLINE_TO': -1,
        'YIELD_VALUE': 0,
        'EXEC_STMT': -3,
        'BUILD_CLASS': -2,
        'STORE_NAME': -1,
        'DELETE_NAME': 0,
        'STORE_ATTR': -2,
        'DELETE_ATTR': -1,
        'STORE_GLOBAL': -1,
        'DELETE_GLOBAL': 0,
        'STORE_DEREF': -1,
        'BUILD_MAP': 1,
        'COMPARE_OP': -1,
        'STORE_FAST': -1,
        'DELETE_FAST': 0,
        'IMPORT_STAR': -1,
        'IMPORT_NAME': -1,
        'IMPORT_FROM': 1,
        'LOAD_ATTR': 0, # unlike other loads
        'GET_ITER': 0,
        'FOR_ITER': 1,
        'POP_BLOCK': 0,
        'END_FINALLY': -3,
        'WITH_CLEANUP': -1,
        'LOOKUP_METHOD': 1,
        'LIST_APPEND': -2,
        }
    # use pattern match
    patterns = [
        ('ROT_', 0),
        ('UNARY_', 0),
        ('BINARY_', -1),
        ('INPLACE_', -1),
        ('LOAD_', 1),
        ('SETUP_', 0),
        ('JUMP_IF_', 0),
        ]

    def gettracker(opname):
        # first look for an explicit tracker
        try:
            return globals()['depth_' + opname]
        except KeyError:
            pass
        # then look for an explicit constant effect
        try:
            delta = effect[opname]
        except KeyError:
            # then do pattern matching
            for pat, delta in patterns:
                if opname.startswith(pat):
                    break
            else:
                raise InternalCompilerError("no stack effect registered for "
                                            + opname)
        def tracker(argc):
            return delta
        return tracker

    effect_along_jump = {
        'JUMP_FORWARD': 0,
        'JUMP_ABSOLUTE': 0,
        'JUMP_IF_TRUE': 0,
        'JUMP_IF_FALSE': 0,
        'FOR_ITER': -1,
        'SETUP_LOOP': 0,
        'SETUP_EXCEPT': 3,
        'SETUP_FINALLY': 3,
        }
    def geteffect_jump(opname):
        try:
            return effect_along_jump[opname]
        except KeyError:
            raise InternalCompilerError("no stack effect registered for "
                                        "the branch of " + opname)

    for opname, opcode in pythonopcode.opmap.items():
        if opname in ops_interrupt_unconditionally:
            continue
        if opname not in ops_jump_unconditionally:
            # the effect on the stack depth when execution goes from
            # this instruction to the next one
            DEPTH_OP_TRACKER[opcode] = gettracker(opname)
        if opname in ops_jumps:
            DEPTH_OP_EFFECT_ALONG_JUMP[opcode] = geteffect_jump(opname)


ops_interrupt_unconditionally = ('RETURN_VALUE', 'RAISE_VARARGS',
                                 'CONTINUE_LOOP', 'BREAK_LOOP')
ops_jump_unconditionally = ('JUMP_ABSOLUTE', 'JUMP_FORWARD')
ops_jumps = list(PyFlowGraph.hasjrel) + list(PyFlowGraph.hasjabs)

DEPTH_OP_TRACKER = {}
DEPTH_OP_EFFECT_ALONG_JUMP = {}
setup_stack_depth_tracker()

"""A flow graph representation for Python bytecode"""

import sys

from pypy.interpreter.astcompiler import misc, ast
from pypy.interpreter.astcompiler.consts \
     import CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_VARKEYWORDS
from pypy.interpreter.pycode import PyCode
from pypy.interpreter.baseobjspace import W_Root
from pypy.tool import stdlib_opcode as pythonopcode

class BlockSet:
    """A Set implementation specific to Blocks
    it uses Block.bid as keys to underlying dict"""
    def __init__(self):
        self.elts = {}
    def __len__(self):
        return len(self.elts)
    def __contains__(self, elt):
        return elt.bid in self.elts
    def add(self, elt):
        self.elts[elt.bid] = elt
    def elements(self):
        return self.elts.values()
    def has_elt(self, elt):
        return elt.bid in self.elts
    def remove(self, elt):
        del self.elts[elt.bid]
    def copy(self):
        c = BlockSet()
        c.elts.update(self.elts)
        return c


class Instr:
    has_arg = False
    
    def __init__(self, op):
        self.op = op

class InstrWithArg(Instr):
    has_arg = True

class InstrName(InstrWithArg):
    def __init__(self, inst, name):
        Instr.__init__(self, inst)
        self.name = name

    def getArg(self):
        "NOT_RPYTHON"
        return self.name

class InstrInt(InstrWithArg):
    def __init__(self, inst, intval):
        Instr.__init__(self, inst)
        self.intval = intval

    def getArg(self):
        "NOT_RPYTHON"
        return self.intval        

class InstrBlock(InstrWithArg):
    def __init__(self, inst, block):
        Instr.__init__(self, inst)
        self.block = block

    def getArg(self):
        "NOT_RPYTHON"
        return self.block        

class InstrObj(InstrWithArg):
    def __init__(self, inst, obj):
        Instr.__init__(self, inst)
        self.obj = obj

    def getArg(self):
        "NOT_RPYTHON"
        return self.obj

class InstrCode(InstrWithArg):
    def __init__(self, inst, gen):
        Instr.__init__(self, inst)
        self.gen = gen

    def getArg(self):
        "NOT_RPYTHON"
        return self.gen

class FlowGraph:
    def __init__(self, space):
        self.space = space
        self.current = self.entry = Block(space)
        self.exit = Block(space,"exit")
        self.blocks = BlockSet()
        self.blocks.add(self.entry)
        self.blocks.add(self.exit)

    def startBlock(self, block):
        if self._debug:
            if self.current:
                print "end", repr(self.current)
                print "    next", self.current.next
                print "   ", self.current.get_children()
            print repr(block)
        assert block is not None
        self.current = block

    def nextBlock(self, block=None):
        # XXX think we need to specify when there is implicit transfer
        # from one block to the next.  might be better to represent this
        # with explicit JUMP_ABSOLUTE instructions that are optimized
        # out when they are unnecessary.
        #
        # I think this strategy works: each block has a child
        # designated as "next" which is returned as the last of the
        # children.  because the nodes in a graph are emitted in
        # reverse post order, the "next" block will always be emitted
        # immediately after its parent.
        # Worry: maintaining this invariant could be tricky
        if block is None:
            block = self.newBlock()

        # Note: If the current block ends with an unconditional
        # control transfer, then it is incorrect to add an implicit
        # transfer to the block graph.  The current code requires
        # these edges to get the blocks emitted in the right order,
        # however. :-(  If a client needs to remove these edges, call
        # pruneEdges().

        self.current.addNext(block)
        self.startBlock(block)

    def newBlock(self):
        b = Block(self.space)
        self.blocks.add(b)
        return b

    def startExitBlock(self):
        self.startBlock(self.exit)

    _debug = 0

    def _enable_debug(self):
        self._debug = 1

    def _disable_debug(self):
        self._debug = 0

    def emit(self, inst):
        if self._debug:
            print "\t", inst
        if inst in ['RETURN_VALUE', 'YIELD_VALUE']:
            self.current.addOutEdge(self.exit)
        self.current.emit( Instr(inst) )

    #def emitop(self, inst, arg ):
    #    if self._debug:
    #        print "\t", inst, arg
    #    self.current.emit( (inst,arg) )

    def emitop_obj(self, inst, obj ):
        if self._debug:
            print "\t", inst, repr(obj)
        self.current.emit( InstrObj(inst,obj) )

    def emitop_code(self, inst, obj ):
        if self._debug:
            print "\t", inst, repr(obj)
        self.current.emit( InstrCode(inst, obj) )

    def emitop_int(self, inst, intval ):
        if self._debug:
            print "\t", inst, intval
        assert isinstance(intval,int)
        self.current.emit( InstrInt(inst,intval) )
        
    def emitop_block(self, inst, block):
        if self._debug:
            print "\t", inst, block
        assert isinstance(block, Block)
        self.current.addOutEdge( block )
        self.current.emit( InstrBlock(inst,block) )

    def emitop_name(self, inst, name ):
        if self._debug:
            print "\t", inst, name
        assert isinstance(name,str)
        self.current.emit( InstrName(inst,name) )

    def getBlocksInOrder(self):
        """Return the blocks in reverse postorder

        i.e. each node appears before all of its successors
        """
        # TODO: What we need here is a topological sort that
        
        
        # XXX make sure every node that doesn't have an explicit next
        # is set so that next points to exit
        for b in self.blocks.elements():
            if b is self.exit:
                continue
            if not b.next:
                b.addNext(self.exit)
        order = dfs_postorder(self.entry, {})
        order.reverse()
        self.fixupOrder(order, self.exit)
        # hack alert
        if not self.exit in order:
            order.append(self.exit)

        return order

    def fixupOrder(self, blocks, default_next):
        """Fixup bad order introduced by DFS."""

        # XXX This is a total mess.  There must be a better way to get
        # the code blocks in the right order.

        self.fixupOrderHonorNext(blocks, default_next)
        self.fixupOrderForward(blocks, default_next)

    def fixupOrderHonorNext(self, blocks, default_next):
        """Fix one problem with DFS.

        The DFS uses child block, but doesn't know about the special
        "next" block.  As a result, the DFS can order blocks so that a
        block isn't next to the right block for implicit control
        transfers.
        """
        new_blocks = blocks
        blocks = blocks[:]
        del new_blocks[:]
        i = 0
        while i < len(blocks) - 1:
            b = blocks[i]
            n = blocks[i + 1]
            i += 1
            new_blocks.append(b)
            if not b.next or b.next[0] == default_next or b.next[0] == n:
                continue
            # The blocks are in the wrong order.  Find the chain of
            # blocks to insert where they belong.
            cur = b
            chain = []
            elt = cur
            while elt.next and elt.next[0] != default_next:
                chain.append(elt.next[0])
                elt = elt.next[0]
            # Now remove the blocks in the chain from the current
            # block list, so that they can be re-inserted.
            for b in chain:
                for j in range(i + 1, len(blocks)):
                    if blocks[j] == b:
                        del blocks[j]
                        break
                else:
                    assert False, "Can't find block"
                    
            new_blocks.extend(chain)
        if i == len(blocks) - 1:
            new_blocks.append(blocks[i])
            
    def fixupOrderForward(self, blocks, default_next):
        """Make sure all JUMP_FORWARDs jump forward"""
        index = {}
        chains = []
        cur = []
        for b in blocks:
            index[b.bid] = len(chains)
            cur.append(b)
            if b.next and b.next[0] == default_next:
                chains.append(cur)
                cur = []
        chains.append(cur)

        while 1:
            constraints = []

            for i in range(len(chains)):
                l = chains[i]
                for b in l:
                    for c in b.get_children():
                        if index[c.bid] < i:
                            forward_p = 0
                            for inst in b.insts:
                                if inst.op == 'JUMP_FORWARD':
                                    assert isinstance(inst, InstrBlock)
                                    if inst.block == c:
                                        forward_p = 1
                            if not forward_p:
                                continue
                            constraints.append((index[c.bid], i))

            if not constraints:
                break

            # XXX just do one for now
            # do swaps to get things in the right order
            goes_before, a_chain = constraints[0]
            assert a_chain > goes_before >= 0
            c = chains[a_chain]
            del chains[a_chain]
            chains.insert(goes_before, c)

        del blocks[:]
        for c in chains:
            for b in c:
                blocks.append(b)

    def getBlocks(self):
        return self.blocks.elements()

    def getRoot(self):
        """Return nodes appropriate for use with dominator"""
        return self.entry

    def getContainedGraphs(self):
        l = []
        for b in self.getBlocks():
            l.extend(b.getContainedGraphs())
        return l

def dfs_postorder(b, seen):
    """Depth-first search of tree rooted at b, return in postorder"""
    order = []
    seen[b.bid] = b
    for c in b.get_children():
        if c.bid in seen:
            continue
        order = order + dfs_postorder(c, seen)
    order.append(b)
    return order

BlockCounter = misc.Counter(0)

class Block:

    def __init__(self, space, label=''):
        self.insts = []
        self.inEdges = BlockSet()
        self.outEdges = BlockSet()
        self.label = label
        self.bid = BlockCounter.next()
        self.next = []
        self.space = space

    def __repr__(self):
        if self.label:
            return "<block %s id=%d>" % (self.label, self.bid)
        else:
            return "<block id=%d>" % (self.bid)

    def __str__(self):
        insts = [ str(i) for i in  self.insts ]
        return "<block %s %d:\n%s>" % (self.label, self.bid,
                                       '\n'.join(insts))

    def emit(self, inst):
        op = inst.op
        if op[:4] == 'JUMP':
            assert isinstance(inst, InstrBlock)
            self.outEdges.add(inst.block)
##         if op=="LOAD_CONST":
##             assert isinstance( inst[1], W_Root ) or hasattr( inst[1], 'getCode')
        self.insts.append( inst )

    def getInstructions(self):
        return self.insts

    def addInEdge(self, block):
        self.inEdges.add(block)

    def addOutEdge(self, block):
        self.outEdges.add(block)

    def addNext(self, block):
        self.next.append(block)
        assert len(self.next) == 1, [ str(i) for i in self.next ]

    _uncond_transfer = ('RETURN_VALUE', 'RAISE_VARARGS', 'YIELD_VALUE',
                        'JUMP_ABSOLUTE', 'JUMP_FORWARD', 'CONTINUE_LOOP')

    def pruneNext(self):
        """Remove bogus edge for unconditional transfers

        Each block has a next edge that accounts for implicit control
        transfers, e.g. from a JUMP_IF_FALSE to the block that will be
        executed if the test is true.

        These edges must remain for the current assembler code to
        work. If they are removed, the dfs_postorder gets things in
        weird orders.  However, they shouldn't be there for other
        purposes, e.g. conversion to SSA form.  This method will
        remove the next edge when it follows an unconditional control
        transfer.
        """
        try:
            inst = self.insts[-1]
        except (IndexError, ValueError):
            return
        if inst.op in self._uncond_transfer:
            self.next = []

    def get_children(self):
        if self.next and self.next[0].bid in self.outEdges.elts:
            self.outEdges.remove(self.next[0])
        return self.outEdges.elements() + self.next

    def getContainedGraphs(self):
        """Return all graphs contained within this block.

        For example, a MAKE_FUNCTION block will contain a reference to
        the graph for the function body.
        """
        contained = []
        for inst in self.insts:
            if isinstance(inst, InstrCode):
                gen = inst.gen
                if gen:
                    contained.append(gen)
        return contained

# flags for code objects

# the FlowGraph is transformed in place; it exists in one of these states
RAW = "RAW"
FLAT = "FLAT"
CONV = "CONV"
DONE = "DONE"

class PyFlowGraph(FlowGraph):

    def __init__(self, space, name, filename, argnames=None,
                 optimized=0, klass=0, newlocals=0):
        FlowGraph.__init__(self, space)
        if argnames is None:
            argnames = []
        self.name = name
        self.filename = filename
        self.docstring = space.w_None
        self.argcount = len(argnames)
        self.klass = klass
        self.flags = 0
        if optimized:
            self.flags |= CO_OPTIMIZED
        if newlocals:
            self.flags |= CO_NEWLOCALS

        self.consts = []
        self.names = []
        # Free variables found by the symbol table scan, including
        # variables used only in nested scopes, are included here.
        self.freevars = []
        self.cellvars = []
        # The closure list is used to track the order of cell
        # variables and free variables in the resulting code object.
        # The offsets used by LOAD_CLOSURE/LOAD_DEREF refer to both
        # kinds of variables.
        self.closure = []
        self.varnames = list(argnames)
        self.stage = RAW
        self.orderedblocks = []

    def setDocstring(self, doc):
        self.docstring = doc

    def setFlag(self, flag):
        self.flags = self.flags | flag
        if flag == CO_VARARGS:
            self.argcount = self.argcount - 1

    def checkFlag(self, flag):
        if self.flags & flag:
            return 1

    def setFreeVars(self, names):
        self.freevars = list(names)

    def setCellVars(self, names):
        self.cellvars = names

    def getCode(self):
        """Get a Python code object"""
        if self.stage == RAW:
            self.computeStackDepth()
            self.convertArgs()
        if self.stage == CONV:
            self.flattenGraph()
        if self.stage == FLAT:
            self.makeByteCode()
        if self.stage == DONE:
            return self.newCodeObject()
        raise RuntimeError, "inconsistent PyFlowGraph state"

    def dump(self, io=None):
        if io:
            save = sys.stdout
            sys.stdout = io
        pc = 0
        for t in self.insts:
            opname = t.op
            if opname == "SET_LINENO":
                print
            if not t.has_arg:
                print "\t", "%3d" % pc, opname
                pc = pc + 1
            else:
                print "\t", "%3d" % pc, opname, t.getArg()
                pc = pc + 3
        if io:
            sys.stdout = save

    def _max_depth(self, depth, seen, b, d):
        if b in seen:
            return d
        seen[b] = 1
        d = d + depth[b]
        children = b.get_children()
        if children:
            maxd = -1
            for c in children:
                childd =self._max_depth(depth, seen, c, d)
                if childd > maxd:
                    maxd = childd
            return maxd
        else:
            if not b.label == "exit":
                return self._max_depth(depth, seen, self.exit, d)
            else:
                return d

    def computeStackDepth(self):
        """Compute the max stack depth.

        Approach is to compute the stack effect of each basic block.
        Then find the path through the code with the largest total
        effect.
        """
        depth = {}
        exit = None
        for b in self.getBlocks():
            depth[b] = findDepth(b.getInstructions())

        seen = {}

        self.stacksize = self._max_depth( depth, seen, self.entry, 0)

    def flattenGraph(self):
        """Arrange the blocks in order and resolve jumps"""
        assert self.stage == CONV
        self.insts = insts = []
        firstline = 0
        pc = 0
        begin = {}
        end = {}
        forward_refs = []
        for b in self.orderedblocks:
            # Prune any setlineno before the 'implicit return' block.
            if b is self.exit:
                while len(insts) and insts[-1].op == "SET_LINENO":
                    insts.pop()
            begin[b] = pc
            for inst in b.getInstructions():
                if not inst.has_arg:
                    insts.append(inst)
                    pc = pc + 1
                elif inst.op != "SET_LINENO":
                    if inst.op in self.hasjrel:
                        assert isinstance(inst, InstrBlock)
                        # relative jump - no extended arg
                        block = inst.block
                        inst = InstrInt(inst.op, 0)
                        forward_refs.append( (block,  inst, pc) )
                        insts.append(inst)
                        pc = pc + 3
                    elif inst.op in self.hasjabs:
                        # absolute jump - can be extended if backward
                        assert isinstance(inst, InstrBlock)
                        arg = inst.block
                        if arg in begin:
                            # can only extend argument if backward
                            offset = begin[arg]
                            hi = offset // 65536
                            lo = offset % 65536
                            if hi>0:
                                # extended argument
                                insts.append( InstrInt("EXTENDED_ARG", hi) )
                                pc = pc + 3
                            inst = InstrInt(inst.op, lo)
                        else:
                            inst = InstrInt(inst.op, 0)
                            forward_refs.append( (arg,  inst, pc ) )
                        insts.append(inst)
                        pc = pc + 3
                    else:
                        assert isinstance(inst, InstrInt)
                        arg = inst.intval
                        # numerical arg
                        hi = arg // 65536
                        lo = arg % 65536
                        if hi>0:
                            # extended argument
                            insts.append( InstrInt("EXTENDED_ARG", hi) )
                            inst.intval = lo
                            pc = pc + 3    
                        insts.append(inst)
                        pc = pc + 3
                else:
                    insts.append(inst)
                    if firstline == 0:
                        firstline = inst.intval
            end[b] = pc
        pc = 0

        for block, inst, pc in forward_refs:
            opname = inst.op
            abspos = begin[block]
            if opname in self.hasjrel:
                offset = abspos - pc - 3
                inst.intval = offset
            else:
                inst.intval = abspos
        self.firstline = firstline
        self.stage = FLAT

    hasjrel = {}
    for i in pythonopcode.hasjrel:
        hasjrel[pythonopcode.opname[i]] = True
    hasjabs = {}
    for i in pythonopcode.hasjabs:
        hasjabs[pythonopcode.opname[i]] = True

    def convertArgs(self):
        """Convert arguments from symbolic to concrete form"""
        assert self.stage == RAW
        self.orderedblocks = self.getBlocksInOrder()
        self.consts.insert(0, self.docstring)
        self.sort_cellvars()

        for b in self.orderedblocks:
            insts = b.getInstructions()
            for i in range(len(insts)):
                inst = insts[i]
                if inst.has_arg:
                    opname = inst.op
                    conv = self._converters.get(opname, None)
                    if conv:
                        insts[i] = conv(self, inst)
        self.stage = CONV

    def sort_cellvars(self):
        """Sort cellvars in the order of varnames and prune from freevars.
        """
        cells = {}
        for name in self.cellvars:
            cells[name] = 1
        self.cellvars = [name for name in self.varnames
                         if name in cells]
        for name in self.cellvars:
            del cells[name]
        self.cellvars = self.cellvars + cells.keys()
        self.closure = self.cellvars + self.freevars

    def _lookupName(self, name, list):
        """Return index of name in list, appending if necessary
        """
        assert isinstance(name, str)
        for i in range(len(list)):
            if list[i] == name:
                return i
        end = len(list)
        list.append(name)
        return end

    def _cmpConsts(self, w_left, w_right):
        space = self.space
        t = space.type(w_left)
        if space.is_w(t, space.type(w_right)):
            if space.is_w(t, space.w_tuple):
                left_len = space.int_w(space.len(w_left))
                right_len = space.int_w(space.len(w_right))
                if left_len == right_len:
                    for i in range(left_len):
                        w_lefti = space.getitem(w_left, space.wrap(i))
                        w_righti = space.getitem(w_right, space.wrap(i))
                        if not self._cmpConsts(w_lefti, w_righti):
                            return False
                    return True
            elif space.eq_w(w_left, w_right):
                 return True
        return False

    def _lookupConst(self, w_obj, list_w):
        """
        This routine uses a list instead of a dictionary, because a
        dictionary can't store two different keys if the keys have the
        same value but different types, e.g. 2 and 2L.  The compiler
        must treat these two separately, so it does an explicit type
        comparison before comparing the values.
        """
        space = self.space
        w_obj_type = space.type(w_obj)
        for i in range(len(list_w)):
            if self._cmpConsts(w_obj, list_w[i]):
                return i
        end = len(list_w)
        list_w.append(w_obj)
        return end

    _converters = {}

    def _convert_LOAD_CONST(self, inst):
        if isinstance(inst, InstrCode):
            w_obj = inst.gen.getCode()
        else:
            assert isinstance(inst, InstrObj)
            w_obj = inst.obj
        #assert w_obj is not None
        index = self._lookupConst(w_obj, self.consts)
        return InstrInt(inst.op, index)

    def _convert_LOAD_FAST(self, inst):
        assert isinstance(inst, InstrName)
        arg = inst.name
        self._lookupName(arg, self.names)
        index= self._lookupName(arg, self.varnames)
        return InstrInt(inst.op, index)
    _convert_STORE_FAST = _convert_LOAD_FAST
    _convert_DELETE_FAST = _convert_LOAD_FAST

    def _convert_NAME(self, inst):
        assert isinstance(inst, InstrName)
        arg = inst.name        
        index = self._lookupName(arg, self.names)
        return InstrInt(inst.op, index)        
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

    def _convert_DEREF(self, inst):
        assert isinstance(inst, InstrName)
        arg = inst.name               
        self._lookupName(arg, self.names)
        index = self._lookupName(arg, self.closure)
        return InstrInt(inst.op, index)                
    _convert_LOAD_DEREF = _convert_DEREF
    _convert_STORE_DEREF = _convert_DEREF

    def _convert_LOAD_CLOSURE(self, inst):
        assert isinstance(inst, InstrName)
        arg = inst.name                
        index = self._lookupName(arg, self.closure)
        return InstrInt(inst.op, index)
    
    _cmp = list(pythonopcode.cmp_op)
    def _convert_COMPARE_OP(self, inst):
        assert isinstance(inst, InstrName)
        arg = inst.name                        
        index = self._cmp.index(arg)
        return InstrInt(inst.op, index)
    

    # similarly for other opcodes...

    for name, obj in locals().items():
        if name[:9] == "_convert_":
            opname = name[9:]
            _converters[opname] = obj
    del name, obj, opname

    def makeByteCode(self):
        assert self.stage == FLAT
        self.lnotab = lnotab = LineAddrTable(self.firstline)
        for t in self.insts:
            opname = t.op
            if self._debug:
                if not t.has_arg:
                    print "x",opname
                else:
                    print "x",opname, t.getArg()
            if not t.has_arg:
                lnotab.addCode1(self.opnum[opname])
            else:
                assert isinstance(t, InstrInt)
                oparg = t.intval
                if opname == "SET_LINENO":
                    lnotab.nextLine(oparg)
                    continue
                hi, lo = twobyte(oparg)
                try:
                    lnotab.addCode3(self.opnum[opname], lo, hi)
                except ValueError:
                    if self._debug:
                        print opname, oparg
                        print self.opnum[opname], lo, hi
                    raise
        self.stage = DONE

    opnum = {}
    for num in range(len(pythonopcode.opname)):
        opnum[pythonopcode.opname[num]] = num
        # This seems to duplicate dis.opmap from opcode.opmap
    del num

    def newCodeObject(self):
        assert self.stage == DONE
        if (self.flags & CO_NEWLOCALS) == 0:
            nlocals = 0
        else:
            nlocals = len(self.varnames)
        argcount = self.argcount
        if self.flags & CO_VARKEYWORDS:
            argcount = argcount - 1
        # was return new.code, now we just return the parameters and let
        # the caller create the code object
        return PyCode( self.space, argcount, nlocals,
                       self.stacksize, self.flags,
                       self.lnotab.getCode(),
                       self.getConsts(),
                       self.names,
                       self.varnames,
                       self.filename, self.name,
                       self.firstline,
                       self.lnotab.getTable(),
                       self.freevars,
                       self.cellvars
                       )

    def getConsts(self):
        """Return a tuple for the const slot of the code object

        Must convert references to code (MAKE_FUNCTION) to code
        objects recursively.
        """
        return self.consts[:]

def isJump(opname):
    if opname[:4] == 'JUMP':
        return 1

def twobyte(val):
    """Convert an int argument into high and low bytes"""
    assert isinstance(val,int)
    hi = val // 256
    lo = val % 256
    return hi, lo

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
        self.code = []
        self.codeOffset = 0
        self.firstline = firstline
        self.lastline = firstline
        self.lastoff = 0
        self.lnotab = []

    def addCode1(self, op ):
        self.code.append(chr(op))
        self.codeOffset = self.codeOffset + 1

    def addCode3(self, op, hi, lo):
        self.code.append(chr(op))
        self.code.append(chr(hi))
        self.code.append(chr(lo))
        self.codeOffset = self.codeOffset + 3

    def nextLine(self, lineno):
        # compute deltas
        addr = self.codeOffset - self.lastoff
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
                push(255); push(0)
                addr -= 255
            while line > 255:
                push(addr); push(255)
                line -= 255
                addr = 0
            if addr > 0 or line > 0:
                push(addr); push(line)
            self.lastline = lineno
            self.lastoff = self.codeOffset

    def getCode(self):
        return ''.join(self.code)

    def getTable(self):
        return ''.join( [ chr(i) for i in  self.lnotab ] )


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
def depth_MAKE_FUNCTION(argc):
    return -argc
def depth_MAKE_CLOSURE(argc):
    # XXX need to account for free variables too!
    return -argc
def depth_BUILD_SLICE(argc):
    if argc == 2:
        return -1
    elif argc == 3:
        return -2
    assert False, 'Unexpected argument %s to depth_BUILD_SLICE' % argc
    
def depth_DUP_TOPX(argc):
    return argc

DEPTH_OP_TRACKER = {
    "UNPACK_SEQUENCE" : depth_UNPACK_SEQUENCE,
    "BUILD_TUPLE" : depth_BUILD_TUPLE,
    "BUILD_LIST" : depth_BUILD_LIST,
    "CALL_FUNCTION" : depth_CALL_FUNCTION,
    "CALL_FUNCTION_VAR" : depth_CALL_FUNCTION_VAR,
    "CALL_FUNCTION_KW" : depth_CALL_FUNCTION_KW,
    "CALL_FUNCTION_VAR_KW" : depth_CALL_FUNCTION_VAR_KW,
    "MAKE_FUNCTION" : depth_MAKE_FUNCTION,
    "MAKE_CLOSURE" : depth_MAKE_CLOSURE,
    "BUILD_SLICE" : depth_BUILD_SLICE,
    "DUP_TOPX" : depth_DUP_TOPX,
    }

class StackDepthTracker:
    # XXX 1. need to keep track of stack depth on jumps
    # XXX 2. at least partly as a result, this code is broken
    # XXX 3. Don't need a class here!

    def findDepth(self, insts, debug=0):
        depth = 0
        maxDepth = 0
        for i in insts:
            opname = i.op
            if debug:
                print i,
            delta = self.effect.get(opname, sys.maxint)
            if delta != sys.maxint:
                depth = depth + delta
            else:
                # now check patterns
                for pat, pat_delta in self.patterns:
                    if opname[:len(pat)] == pat:
                        delta = pat_delta
                        depth = depth + delta
                        break
                # if we still haven't found a match
                if delta == sys.maxint:
                    meth = DEPTH_OP_TRACKER.get( opname, None )
                    if meth is not None:
                        assert isinstance(i, InstrInt)
                        depth = depth + meth(i.intval)
            if depth > maxDepth:
                maxDepth = depth
            if debug:
                print depth, maxDepth
        return maxDepth

    effect = {
        'POP_TOP': -1,
        'DUP_TOP': 1,
        'SLICE+1': -1,
        'SLICE+2': -1,
        'SLICE+3': -2,
        'STORE_SLICE+0': -1,
        'STORE_SLICE+1': -2,
        'STORE_SLICE+2': -2,
        'STORE_SLICE+3': -3,
        'DELETE_SLICE+0': -1,
        'DELETE_SLICE+1': -2,
        'DELETE_SLICE+2': -2,
        'DELETE_SLICE+3': -3,
        'STORE_SUBSCR': -3,
        'DELETE_SUBSCR': -2,
        # PRINT_EXPR?
        'PRINT_ITEM': -1,
        'RETURN_VALUE': -1,
        'YIELD_VALUE': -1,
        'EXEC_STMT': -3,
        'BUILD_CLASS': -2,
        'STORE_NAME': -1,
        'STORE_ATTR': -2,
        'DELETE_ATTR': -1,
        'STORE_GLOBAL': -1,
        'BUILD_MAP': 1,
        'COMPARE_OP': -1,
        'STORE_FAST': -1,
        'IMPORT_STAR': -1,
        'IMPORT_NAME': 0,
        'IMPORT_FROM': 1,
        'LOAD_ATTR': 0, # unlike other loads
        # close enough...
        'SETUP_EXCEPT': 3,
        'SETUP_FINALLY': 3,
        'FOR_ITER': 1,
        'WITH_CLEANUP': 3,
        'LOOKUP_METHOD': 1,
        }
    # use pattern match
    patterns = [
        ('BINARY_', -1),
        ('LOAD_', 1),
        ]


findDepth = StackDepthTracker().findDepth

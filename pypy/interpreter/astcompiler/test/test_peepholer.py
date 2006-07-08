from pypy.interpreter.astcompiler import pyassem

class BlockOptimizer:
    def __init__(self, matchers):
        self.matchers = matchers

    def process(self, block):
        while 1:
            didSomething = False
            for matcher in self.matchers:
                if matcher.process(block):
                    didSomething = True
            if not didSomething:
                return

def isSimpleLoad(instr):
    return instr.op in ('LOAD_CONST', 'LOAD_NAME', 'LOAD_FAST', 'LOAD_GLOBAL')

def isSimpleStore(instr):
    return instr.op in ('STORE_NAME', 'STORE_FAST', 'STORE_GLOBAL')

def isUnpack(instr):
    return instr.op in ['UNPACK_TUPLE', 'UNPACK_SEQUENCE']

TM_LOOKING_FOR_LOADS, TM_COUNTING_LOADS, TM_COUNTING_STORES = range(3)

class TupleMatcher:
    def __init__(self):
        self.state = TM_LOOKING_FOR_LOADS
        self.loadcount = -1
        self.storecount = -1
        self.stores = {}
    def process(self, block):
        i = 0
        while i < len(block.insts):
            inst = block.insts[i]
            #print inst.op, getattr(inst, 'intval', None), self.state
            if self.state == TM_LOOKING_FOR_LOADS:
                if isSimpleLoad(inst):
                    self.state = TM_COUNTING_LOADS
                    self.loadcount = 1
            elif self.state == TM_COUNTING_LOADS:
                if isSimpleLoad(inst):
                    self.loadcount += 1
                elif inst.op == 'BUILD_TUPLE' and self.loadcount >= inst.intval:
                    if i+1 < len(block.insts):
                        nextinst = block.insts[i+1]
                        if isUnpack(nextinst) and nextinst.intval == inst.intval:
                            self.state = TM_COUNTING_STORES
                            self.storecount = 0
                            self.stores = {}
                            i += 2
                            continue
                    self.state = TM_LOOKING_FOR_LOADS
            elif self.state == TM_COUNTING_STORES:
                if isSimpleStore(inst) and inst.intval not in self.stores:
                    self.storecount += 1
                    self.stores[inst.intval] = True
                    if self.storecount == self.loadcount:
                        self.performOptimization(block, i, self.loadcount)
                        self.state = TM_LOOKING_FOR_LOADS
                        i -= 2
                else:
                    self.state = TM_LOOKING_FOR_LOADS
            i += 1
    def performOptimization(self, block, i, loadcount):
        index = i-loadcount-1
        assert block.insts[index].op == 'BUILD_TUPLE'
        del block.insts[index]
        assert isUnpack(block.insts[index])
        del block.insts[index]
        saveops = block.insts[index:index+loadcount]
        saveops.reverse()
        block.insts[index:index+loadcount] = saveops
        

def tuple_assign_block(n):
    block = pyassem.Block(None)

    for i in range(n):
        block.emit(pyassem.InstrInt('LOAD_CONST', i))
    block.emit(pyassem.InstrInt('BUILD_TUPLE', n))
    block.emit(pyassem.InstrInt('UNPACK_TUPLE', n))
    for i in range(n):
        block.emit(pyassem.InstrInt('STORE_NAME', i))
    
    return block
    
def test_tuple_assignment():
    for i in range(1, 10):
        block = tuple_assign_block(i)
        
        tm = TupleMatcher()
        tm.process(block)

        opnames = [inst.op for inst in block.insts]

        assert 'BUILD_TUPLE' not in opnames
    
def test_no_tuple_rearrangement():
    # if both stores are to the same variable, the optimization is not
    # valid:
    # a, a = 1, 2
    # is not the same as
    # a = 2; a = 1
    block = tuple_assign_block(2)
    block.insts[-1].intval = block.insts[-2].intval
    tm = TupleMatcher()
    tm.process(block)

    opnames = [inst.op for inst in block.insts]

    assert 'BUILD_TUPLE' in opnames
    
    

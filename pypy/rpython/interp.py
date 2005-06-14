from pypy.rpython.lltype import * 


class LLInterpreter(object): 
    """ low level interpreter working with concrete values. """ 
    def __init__(self, flowgraphs): 
        self.flowgraphs = flowgraphs 
        self.bindings = {}

    # _______________________________________________________
    # variable setters/getters helpers 
    
    def fillvars(self, block, values): 
        vars = block.inputargs 
        assert len(vars) == len(values), (
                   "block %s received %d args, expected %d" % (
                    block, len(values), len(vars)))
        for var, val in zip(vars, values): 
            self.setvar(var, val) 
        
    def setvar(self, var, val): 
        # XXX assert that val "matches" lowlevel type 
        assert var not in self.bindings 
        self.bindings[var] = val 

    def getval(self, varorconst): 
        try: 
            return varorconst.value
        except AttributeError: 
            return self.bindings[varorconst]

    # _______________________________________________________
    # evaling functions 

    def eval_function(self, func, args=()): 
        graph = self.flowgraphs[func]
        nextblock = graph.startblock
        while 1: 
            self.fillvars(nextblock, args) 
            nextblock, args = self.eval_block(nextblock) 
            if nextblock is None: 
                return args 

    def eval_block(self, block): 
        """ return (nextblock, values) tuple. If nextblock 
            is None, values is the concrete return value. 
        """
        for op in block.operations: 
            self.eval_operation(op) 

        # determine nextblock and/or return value 
        if len(block.exits) == 0: 
            # return block 
            resvar, = block.getvariables()
            return None, self.getval(resvar) 
        elif len(block.exits) == 1: 
            index = 0 
        else: 
            index = self.getval(block.exitswitch) 
        link = block.exits[index]
        return link.target, [self.getval(x) for x in link.args]
    
    def eval_operation(self, operation): 
        g = globals()
        opname = operation.opname
        assert opname in g, (
                "cannot handle operation %r yet" %(opname,))
        ophandler = g[opname]
        vals = [self.getval(x) for x in operation.args]
        retval = ophandler(*vals) 
        self.setvar(operation.result, retval)

##############################
# int operations 

def int_add(x, y): 
    return x + y 

from pypy.rpython.lltype import * 
import py


class LLInterpreter(object): 
    """ low level interpreter working with concrete values. """ 
    log = py.log.Producer('llinterp') 

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
        self.bindings[var] = val 

    def getval(self, varorconst): 
        try: 
            return varorconst.value
        except AttributeError: 
            return self.bindings[varorconst]

    # _______________________________________________________
    # other helpers 
    def getoperationhandler(self, opname): 
        try: 
            return getattr(self, 'op_' + opname) 
        except AttributeError: 
            g = globals()
            assert opname in g, (
                    "cannot handle operation %r yet" %(opname,))
            ophandler = g[opname]
            return ophandler

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
            resultvar, = block.getvariables()
            result = self.getval(resultvar) 
            self.log.operation("returning", result) 
            return None, result 
        elif len(block.exits) == 1: 
            index = 0 
        else: 
            index = self.getval(block.exitswitch) 
        link = block.exits[index]
        return link.target, [self.getval(x) for x in link.args]
    
    def eval_operation(self, operation): 
        self.log.operation("considering", operation) 
        ophandler = self.getoperationhandler(operation.opname) 
        vals = [self.getval(x) for x in operation.args]
        retval = ophandler(*vals) 
        self.setvar(operation.result, retval)

    # __________________________________________________________
    # misc LL operation implementations 

    def op_same_as(self, x): 
        return x

    def op_setfield(self, obj, fieldname, fieldvalue): 
        # obj should be pointer 
        setattr(obj, fieldname, fieldvalue) # is that right? 


# __________________________________________________________
# primitive operations 
from pypy.objspace.flow.operation import FunctionByName 
opimpls = FunctionByName.copy()
opimpls['is_true'] = bool 

for typ in (float, int): 
    typname = typ.__name__
    for opname in ('add', 'sub', 'mul', 'div', 'gt', 'lt', 
                   'ge', 'ne', 'le', 'eq'): 
        assert opname in opimpls 
        exec py.code.Source("""
            def %(typname)s_%(opname)s(x, y): 
                assert isinstance(x, %(typname)s)
                assert isinstance(y, %(typname)s)
                func = opimpls[%(opname)r]
                return func(x, y) 
        """ % locals()).compile()
    for opname in 'is_true',: 
        assert opname in opimpls 
        exec py.code.Source("""
            def %(typname)s_%(opname)s(x): 
                assert isinstance(x, %(typname)s)
                func = opimpls[%(opname)r]
                return func(x) 
        """ % locals()).compile()


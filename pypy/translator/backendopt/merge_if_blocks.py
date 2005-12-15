from pypy.objspace.flow.model import Block, Constant, Variable, flatten, checkgraph
from pypy.translator.backendopt.support import log

log = log.mergeifblocks

'''
[backendopt:mergeifblocks] merge1
[backendopt:mergeifblocks] 1
[backendopt:mergeifblocks] int_eq, args[n_0, (1)], result=v0
[backendopt:mergeifblocks] exitswitch...v0
[backendopt:mergeifblocks] exits...(link from block@-1 to block@-1, link from block@-1 to codeless block)
[backendopt:mergeifblocks] merge1
[backendopt:mergeifblocks] 1
[backendopt:mergeifblocks] int_eq, args[n_1, (2)], result=v1
[backendopt:mergeifblocks] exitswitch...v1
[backendopt:mergeifblocks] exits...(link from block@-1 to block@-1, link from block@-1 to codeless block)
[backendopt:mergeifblocks] merge1
[backendopt:mergeifblocks] 1
[backendopt:mergeifblocks] int_eq, args[v2, (3)], result=v3
[backendopt:mergeifblocks] exitswitch...v3
[backendopt:mergeifblocks] exits...(link from block@-1 to codeless block, link from block@-1 to codeless block)
[backendopt:mergeifblocks] merge1
[backendopt:mergeifblocks] 0
[backendopt:mergeifblocks] exitswitch...None
[backendopt:mergeifblocks] exits...()  
'''

def is_chain_block(block, first=False):
    if len(block.operations) == 0:
        return False
    if len(block.operations) > 1 and not first:
        return False
    op = block.operations[-1]
    if op.opname != 'int_eq' or op.result != block.exitswitch:
        return False
    if isinstance(op.args[0], Variable) and isinstance(op.args[1], Variable):
        return False
    return True

def merge_chain(chain, checkvar, varmap):
    def get_new_arg(var_or_const):
        if isinstance(var_or_const, Constant):
            return var_or_const
        return varmap[var_or_const]
    print chain, checkvar
    firstblock, case = chain[0]
    firstblock.operations = firstblock.operations[:-1]
    firstblock.exitswitch = checkvar 
    links = []
    default = chain[-1][0].exits[0]
    default.exitcase = "default"
    default.llexitcase = None
    default.prevblock = firstblock
    default.args = [get_new_arg(arg) for arg in default.args]
    for block, case in chain:
    	link = block.exits[1]
        links.append(link)
	link.exitcase = case
        link.llexitcase = case.value
        link.prevblock = firstblock
        link.args = [get_new_arg(arg) for arg in link.args]
    links.append(default)
    firstblock.exits = links

def merge_if_blocks_once(graph):
    """Convert consecutive blocks that all compare a variable (of Primitive type)
    with a constant into one block with multiple exits. The backends can in
    turn output this block as a switch statement.
    """
    candidates = [block for block in graph.iterblocks()
                      if is_chain_block(block, first=True)]
    print "candidates", candidates
    for firstblock in candidates:
        chain = []
        checkvars = []
        varmap = {}  # {var in a block in the chain: var in the first block}
        for var in firstblock.exits[0].args:
            varmap[var] = var
        for var in firstblock.exits[1].args:
            varmap[var] = var
        def add_to_varmap(var, newvar):
            if isinstance(var, Variable):
                varmap[newvar] = varmap[var]
            else:
                varmap[newvar] = var
        current = firstblock
        while 1:
            # check whether the chain can be extended with the block that follows the
            # False link
            checkvar = [var for var in current.operations[-1].args
                           if isinstance(var, Variable)][0]
            case = [var for var in current.operations[-1].args
                       if isinstance(var, Constant)][0]
            chain.append((current, case))
            checkvars.append(checkvar)
            falseexit = current.exits[0]
            assert not falseexit.exitcase
            trueexit = current.exits[1]
            for i, var in enumerate(trueexit.args):
                add_to_varmap(var, trueexit.target.inputargs[i])
            for i, var in enumerate(falseexit.args):
                add_to_varmap(var, falseexit.target.inputargs[i])
            targetblock = falseexit.target
            if checkvar not in falseexit.args:
                break
            newcheckvar = targetblock.inputargs[falseexit.args.index(checkvar)]
            if not is_chain_block(targetblock):
                break
            if newcheckvar not in targetblock.operations[0].args:
                break
            current = targetblock
        if len(chain) > 1:
            break
    else:
        return False
    merge_chain(chain, checkvars[0], varmap)
    checkgraph(graph)

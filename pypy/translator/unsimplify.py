from pypy.objspace.flow.model import *

def copyvar(translator, v):
    """Make a copy of the Variable v, preserving annotations and concretetype."""
    assert isinstance(v, Variable)
    newvar = Variable(v)
    if translator is not None:
        annotator = translator.annotator
        if annotator is not None and v in annotator.bindings:
            annotator.bindings[newvar] = annotator.bindings[v]
    if hasattr(v, 'concretetype'):
        newvar.concretetype = v.concretetype
    return newvar

def insert_empty_block(translator, link, newops=[]):
    """Insert and return a new block along the given link."""
    vars = {}
    for v in link.args:
        if isinstance(v, Variable):
            vars[v] = True
    for op in newops:
        for v in op.args:
            if isinstance(v, Variable):
                vars.setdefault(v, True)
        vars[op.result] = False
    vars = [v for v, keep in vars.items() if keep]
    mapping = {}
    for v in vars:
        mapping[v] = copyvar(translator, v)
    newblock = Block(vars)
    newblock.operations.extend(newops)
    newblock.closeblock(Link(link.args, link.target))
    newblock.renamevariables(mapping)
    link.args[:] = vars
    link.target = newblock
    return newblock

def insert_empty_startblock(translator, graph):
    vars = [copyvar(translator, v) for v in graph.startblock.inputargs]
    newblock = Block(vars)
    newblock.closeblock(Link(vars, graph.startblock))
    graph.startblock.isstartblock = False
    graph.startblock = newblock
    graph.startblock.isstartblock = True

def split_block(translator, block, index):
    """return a link where prevblock is the block leading up but excluding the
    index'th operation and target is a new block with the neccessary variables 
    passed on.  NOTE: if you call this after rtyping, you WILL need to worry
    about keepalives, you may use backendopt.support.split_block_with_keepalive."""
    assert 0 <= index <= len(block.operations)
    if block.exitswitch == c_last_exception:
        assert index < len(block.operations)
    #varmap is the map between names in the new and the old block
    #but only for variables that are produced in the old block and needed in
    #the new one
    varmap = {}
    vars_produced_in_new_block = {}
    def get_new_name(var):
        if var is None:
            return None
        if isinstance(var, Constant):
            return var
        if var in vars_produced_in_new_block:
            return var
        if var not in varmap:
            varmap[var] = copyvar(translator, var)
        return varmap[var]
    moved_operations = block.operations[index:]
    new_moved_ops = []
    for op in moved_operations:
        newop = SpaceOperation(op.opname,
                               [get_new_name(arg) for arg in op.args],
                               op.result)
        new_moved_ops.append(newop)
        vars_produced_in_new_block[op.result] = True
    moved_operations = new_moved_ops
    links = block.exits
    block.exits = None
    for link in links:
        for i, arg in enumerate(link.args):
            #last_exception and last_exc_value are considered to be created
            #when the link is entered
            if link.args[i] not in [link.last_exception, link.last_exc_value]:
                link.args[i] = get_new_name(link.args[i])
    exitswitch = get_new_name(block.exitswitch)
    #the new block gets all the attributes relevant to outgoing links
    #from block the old block
    newblock = Block(varmap.values())
    newblock.operations = moved_operations
    newblock.exits = links
    newblock.exitswitch = exitswitch
    newblock.exc_handler = block.exc_handler
    for link in newblock.exits:
        link.prevblock = newblock
    link = Link(varmap.keys(), newblock)
    link.prevblock = block
    block.operations = block.operations[:index]
    block.exits = [link]
    block.exitswitch = None
    block.exc_handler = False
    return link

def remove_direct_loops(translator, graph):
    """This is useful for code generators: it ensures that no link has
    common input and output variables, which could occur if a block's exit
    points back directly to the same block.  It allows code generators to be
    simpler because they don't have to worry about overwriting input
    variables when generating a sequence of assignments."""
    def visit(link):
        if isinstance(link, Link) and link.prevblock is link.target:
            insert_empty_block(translator, link)
    traverse(visit, graph)

def remove_double_links(translator, graph):
    """This can be useful for code generators: it ensures that no block has
    more than one incoming links from one and the same other block. It allows
    argument passing along links to be implemented with phi nodes since the
    value of an argument can be determined by looking from which block the
    control passed. """
    def visit(block):
        if isinstance(block, Block):
            double_links = []
            seen = {}
            for link in block.exits:
                if link.target in seen:
                    double_links.append(link)
                seen[link.target] = True
            for link in double_links:
                insert_empty_block(translator, link)
    traverse(visit, graph)

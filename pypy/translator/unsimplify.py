from pypy.objspace.flow.model import *

def copyvar(annotator, v):
    """Make a copy of the Variable v, preserving annotations and concretetype."""
    assert isinstance(v, Variable)
    newvar = Variable(v)
    if annotator is not None and v in annotator.bindings:
        annotator.transfer_binding(newvar, v)
    if hasattr(v, 'concretetype'):
        newvar.concretetype = v.concretetype
    return newvar

def varoftype(concretetype, name=None):
    var = Variable(name)
    var.concretetype = concretetype
    return var

def insert_empty_block(annotator, link, newops=[]):
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
        mapping[v] = copyvar(annotator, v)
    newblock = Block(vars)
    newblock.operations.extend(newops)
    newblock.closeblock(Link(link.args, link.target))
    newblock.renamevariables(mapping)
    link.args[:] = vars
    link.target = newblock
    return newblock

def insert_empty_startblock(annotator, graph):
    vars = [copyvar(annotator, v) for v in graph.startblock.inputargs]
    newblock = Block(vars)
    newblock.closeblock(Link(vars, graph.startblock))
    graph.startblock.isstartblock = False
    graph.startblock = newblock
    graph.startblock.isstartblock = True

def starts_with_empty_block(graph):
    return (not graph.startblock.operations
            and graph.startblock.exitswitch is None
            and graph.startblock.exits[0].args == graph.getargs())

def split_block(annotator, block, index, _forcelink=None):
    """return a link where prevblock is the block leading up but excluding the
    index'th operation and target is a new block with the neccessary variables 
    passed on.
    """
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
            varmap[var] = copyvar(annotator, var)
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
    if _forcelink is not None:
        assert index == 0
        linkargs = list(_forcelink)
    else:
        linkargs = varmap.keys()
    newblock = Block([get_new_name(v) for v in linkargs])
    newblock.operations = moved_operations
    newblock.recloseblock(*links)
    newblock.exitswitch = exitswitch
    link = Link(linkargs, newblock)
    block.operations = block.operations[:index]
    block.recloseblock(link)
    block.exitswitch = None
    return link

def split_block_at_start(annotator, block):
    # split before the first op, preserve order and inputargs
    # in the second block!
    return split_block(annotator, block, 0, _forcelink=block.inputargs)

def call_initial_function(translator, initial_func, annhelper=None):
    """Before the program starts, call 'initial_func()'."""
    from pypy.annotation import model as annmodel
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

    own_annhelper = (annhelper is None)
    if own_annhelper:
        annhelper = MixLevelHelperAnnotator(translator.rtyper)
    c_initial_func = annhelper.constfunc(initial_func, [], annmodel.s_None)
    if own_annhelper:
        annhelper.finish()

    entry_point = translator.entry_point_graph
    args = [copyvar(translator.annotator, v) for v in entry_point.getargs()]
    extrablock = Block(args)
    v_none = varoftype(lltype.Void)
    newop = SpaceOperation('direct_call', [c_initial_func], v_none)
    extrablock.operations = [newop]
    extrablock.closeblock(Link(args, entry_point.startblock))
    entry_point.startblock.isstartblock = False
    entry_point.startblock = extrablock
    entry_point.startblock.isstartblock = True
    checkgraph(entry_point)

def call_final_function(translator, final_func, annhelper=None):
    """When the program finishes normally, call 'final_func()'."""
    from pypy.annotation import model as annmodel
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython.annlowlevel import MixLevelHelperAnnotator

    own_annhelper = (annhelper is None)
    if own_annhelper:
        annhelper = MixLevelHelperAnnotator(translator.rtyper)
    c_final_func = annhelper.constfunc(final_func, [], annmodel.s_None)
    if own_annhelper:
        annhelper.finish()

    entry_point = translator.entry_point_graph
    v = copyvar(translator.annotator, entry_point.getreturnvar())
    extrablock = Block([v])
    v_none = varoftype(lltype.Void)
    newop = SpaceOperation('direct_call', [c_final_func], v_none)
    extrablock.operations = [newop]
    extrablock.closeblock(Link([v], entry_point.returnblock))
    for block in entry_point.iterblocks():
        if block is not extrablock:
            for link in block.exits:
                if link.target is entry_point.returnblock:
                    link.target = extrablock
    checkgraph(entry_point)

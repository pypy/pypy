from pypy.objspace.flow.model import *

def copyvar(translator, v):
    """Make a copy of the Variable v, preserving annotations and type_cls."""
    assert isinstance(v, Variable)
    newvar = Variable(v)
    annotator = translator.annotator
    if annotator is not None and v in annotator.bindings:
        annotator.bindings[newvar] = annotator.bindings[v]
    if hasattr(v, 'type_cls'):
        newvar.type_cls = v.type_cls
    return newvar

def insert_empty_block(translator, link):
    """Insert and return a new block along the given link."""
    vars = uniqueitems([v for v in link.args if isinstance(v, Variable)])
    mapping = {}
    for v in vars:
        mapping[v] = copyvar(translator, v)
    newblock = Block(vars)
    newblock.closeblock(Link(link.args, link.target))
    newblock.renamevariables(mapping)
    link.args[:] = vars
    link.target = newblock
    return newblock

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

def uniqueitems(lst):
    "Returns a list with duplicate elements removed."
    result = []
    seen = {}
    for item in lst:
        if item not in seen:
            result.append(item)
            seen[item] = True
    return result

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
                seen[link.target] = True
                if link.target in seen:
                    double_links.append(link)
            for link in double_links[:-1]:
                insert_empty_block(translator, link)
    traverse(visit, graph)

import autopath
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import Variable, Constant, Block, Link
from pypy.objspace.flow.model import traverse, mkentrymap, checkgraph


def remove_same_as(graph):
    """Remove all 'same_as' operations.
    """
    same_as_positions = []
    def visit(node): 
        if isinstance(node, Block): 
            for i, op in enumerate(node.operations):
                if op.opname == 'same_as': 
                    same_as_positions.append((node, i))
    traverse(visit, graph)
    while same_as_positions:
        block, index = same_as_positions.pop()
        same_as_result = block.operations[index].result
        same_as_arg = block.operations[index].args[0]
        # replace the new variable (same_as_result) with the old variable
        # (from all subsequent positions)
        for op in block.operations[index:]:
            if op is not None:
                for i in range(len(op.args)):
                    if op.args[i] == same_as_result:
                        op.args[i] = same_as_arg
        for link in block.exits:
            for i in range(len(link.args)):
                if link.args[i] == same_as_result:
                    link.args[i] = same_as_arg
        if block.exitswitch == same_as_result:
            block.exitswitch = same_as_arg
        block.operations[index] = None
       
    # remove all same_as operations
    def visit(node): 
        if isinstance(node, Block) and node.operations:
            node.operations[:] = filter(None, node.operations)
    traverse(visit, graph)


def SSI_to_SSA(graph):
    """Rename the variables in a flow graph as much as possible without
    violating the SSA rule.  'SSI' means that each Variable in a flow graph is
    defined only once in the whole graph; all our graphs are SSI.  This
    function does not break that rule, but changes the 'name' of some
    Variables to give them the same 'name' as other Variables.  The result
    looks like an SSA graph.  'SSA' means that each var name appears as the
    result of an operation only once in the whole graph, but it can be
    passed to other blocks across links.
    """
    entrymap = mkentrymap(graph)
    consider_blocks = entrymap
    renamed = {}

    while consider_blocks:
        blocklist = consider_blocks.keys()
        consider_blocks = {}
        for block in blocklist:
            if block is graph.startblock:
                continue
            links = entrymap[block]
            assert links
            mapping = {}
            for i in range(len(block.inputargs)):
                # list of possible vars that can arrive in i'th position
                v1 = block.inputargs[i]
                names = {v1.name: True}
                key = []
                for link in links:
                    v = link.args[i]
                    if not isinstance(v, Variable):
                        break
                    names[v.name] = True
                else:
                    if len(names) == 2:
                        oldname = v1.name
                        del names[oldname]
                        newname, = names.keys()
                        while oldname in renamed:
                            oldname = renamed[oldname]
                        while newname in renamed:
                            newname = renamed[newname]
                        if oldname == newname:
                            continue
                        renamed[oldname] = newname
                        v1._name = newname
                        # mark all the following blocks as subject to
                        # possible further optimization
                        for link in block.exits:
                            consider_blocks[link.target] = True
    # sanity-check that the same name is never used several times in a block
    variables_by_name = {}
    for block in entrymap:
        vars = [op.result for op in block.operations]
        for link in block.exits:
            vars += link.getextravars()
        assert len(dict.fromkeys([v.name for v in vars])) == len(vars), (
            "duplicate variable name in %r" % (block,))
        for v in vars:
            variables_by_name.setdefault(v.name, []).append(v)
    # sanity-check that variables with the same name have the same concretetype
    for vname, vlist in variables_by_name.items():
        vct = [getattr(v, 'concretetype', None) for v in vlist]
        assert vct == vct[:1] * len(vct), (
            "variables called %s have mixed concretetypes: %r" % (vname, vct))


# ____________________________________________________________

if __name__ == '__main__':

    def is_perfect_number(n=int):
        div = 1
        sum = 0
        while div < n:
            if n % div == 0:
                sum += div
            div += 1
        return n == sum

    t = Translator(is_perfect_number)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    graph = t.getflowgraph()
    remove_same_as(graph)
    SSI_to_SSA(graph)
    checkgraph(graph)
    t.view()
    f = t.ccompile()
    for i in range(1, 33):
        print '%3d' % i, is_perfect_number(i)

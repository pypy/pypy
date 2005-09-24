from pypy.objspace.flow.model import Variable, mkentrymap, flatten, Block
from pypy.tool.unionfind import UnionFind

def data_flow_families(graph):
    """Follow the flow of the data in the graph.  Returns a UnionFind grouping
    all the variables by families: each family contains exactly one variable
    where a value is stored into -- either by an operation or a merge -- and
    all following variables where the value is just passed unmerged into the
    next block.
    """

    # Build a list of "unification opportunities": for each block and each 'n',
    # an "opportunity" is the list of the block's nth input variable plus
    # the nth output variable from each of the incoming links.
    opportunities = []
    for block, links in mkentrymap(graph).items():
        if block is graph.startblock:
            continue
        assert links
        for n, inputvar in enumerate(block.inputargs):
            vars = [inputvar]
            for link in links:
                var = link.args[n]
                if not isinstance(var, Variable):
                    break
                vars.append(var)
            else:
                # if no Constant found in the incoming links
                opportunities.append(vars)

    # An "opportunitiy" that lists exactly two distinct variables means that
    # the two variables can be unified.  We maintain the unification status in
    # 'variable_families'.  When variables are unified, it might reduce the
    # number of distinct variables and thus open other "opportunities" for
    # unification.
    progress = True
    variable_families = UnionFind()
    while progress:
        progress = False
        pending_opportunities = []
        for vars in opportunities:
            repvars = [variable_families.find_rep(v1) for v1 in vars]
            repvars = dict.fromkeys(repvars).keys()
            if len(repvars) > 2:
                # cannot unify now, but maybe later?
                pending_opportunities.append(repvars)
            elif len(repvars) == 2:
                # unify!
                variable_families.union(*repvars)
                progress = True
        opportunities = pending_opportunities
    return variable_families

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
    variable_families = data_flow_families(graph)
    # rename variables to give them the name of their familiy representant
    for v in variable_families.keys():
        v1 = variable_families.find_rep(v)
        if v1 != v:
            v._name = v1.name

    # sanity-check that the same name is never used several times in a block
    variables_by_name = {}
    for block in flatten(graph):
        if not isinstance(block, Block):
            continue
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

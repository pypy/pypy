from pypy.rpython.l3interp import l3interp
from pypy.rpython.l3interp import model
from pypy.rpython.l3interp.model import Op
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem import lltype


class LL2L3Converter(object):
    def __init__(self):
        pass

    def convert_graph(self, graph):
        l3block = convert_block(graph.startblock, {})
        nargs = {'int': 0,
                 'dbl': 0,
                 'ptr': 0}
        for v in graph.getargs():
            nargs[getkind(v.concretetype)] += 1
        return model.Graph(graph.name, l3block,
                           nargs['int'], nargs['dbl'], nargs['ptr'])


def getkind(T):
    assert isinstance(T, lltype.LowLevelType)
    if isinstance(T, lltype.Primitive):
        if T == lltype.Float:
            return 'dbl'
        elif T == lltype.Void:
            raise Exception("Void not implemented")
        else:
            return 'int'
    else:
        return 'ptr'

def convert_block(block, memo):
    if block in memo:
        return memo[block]

    stacksizes = {'int': 0,
                  'dbl': 0,
                  'ptr': 0}
    constants = {'int': [],
                 'dbl': [],
                 'ptr': []}
    var2stack = {}

    def push(v):
        kind = getkind(v.concretetype)
        position = stacksizes[kind]
        stacksizes[kind] += 1
        var2stack[v] = position

    def get(v):
        kind = getkind(v.concretetype)
        if isinstance(v, flowmodel.Constant):
            clist = constants[kind]
            try:
                res = clist.index(v.value)
            except ValueError:
                res = len(clist)
                clist.append(v.value)
            return res
        else:
            position = var2stack[v]
            return position - stacksizes[kind]    # < 0

    for v in block.inputargs:
        push(v)

    insns = []
    l3block = model.Block(insns)
    memo[block] = l3block

    if block.operations == ():
        if len(block.inputargs) == 1:  # return block
            if block.inputargs[0].concretetype is lltype.Void:
                l3block.insns.append(Op.void_return)
            else:
                kind = getkind(block.inputargs[0].concretetype)
                l3block.insns.append(model.very_low_level_opcode[
                    {'int': 'int_return',
                     'dbl': 'float_return',
                     'ptr': 'adr_return'}[kind]])
                l3block.insns.append(-1)
        else:
            raise NotImplementedError("except block")
        return l3block

    for spaceop in block.operations:
        insns.append(model.very_low_level_opcode[spaceop.opname])
        for v in spaceop.args:
            insns.append(get(v))
        if spaceop.result.concretetype is not lltype.Void:
            push(spaceop.result)

    def convert_link(link):
        targetregs = {'int': [],
                      'dbl': [],
                      'ptr': []}
        for v in link.args:
            kind = getkind(v.concretetype)
            targetregs[kind].append(get(v))
        return model.Link(convert_block(link.target, memo),
                          targetregs['int'] or None,
                          targetregs['dbl'] or None,
                          targetregs['ptr'] or None)

    if block.exitswitch is None:
        insns.append(Op.jump)
        link, = block.exits
        l3block.exit0 = convert_link(link)

    elif block.exitswitch != flowmodel.Constant(flowmodel.last_exception):
        link0, link1 = block.exits
        if link0.exitcase:
            link0, link1 = link1, link0
        assert not link0.exitcase
        assert link1.exitcase
        insns.append(Op.jump_cond)
        insns.append(get(block.exitswitch))
        l3block.exit0 = convert_link(link0)
        l3block.exit1 = convert_link(link1)

    else:
        raise NotImplementedError("exceptions")

    if constants['int']: l3block.constants_int = constants['int']
    if constants['dbl']: l3block.constants_dbl = constants['dbl']
    if constants['ptr']: l3block.constants_ptr = constants['ptr']

    return l3block

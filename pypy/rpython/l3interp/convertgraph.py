from pypy.rpython.l3interp import l3interp
from pypy.rpython.l3interp import model
from pypy.rpython.l3interp.model import Op
from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.llmemory import FieldOffset, \
     ItemOffset, ArrayItemsOffset, fakeaddress


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

def getaccesskind(T):
    assert isinstance(T, lltype.LowLevelType)
    if isinstance(T, lltype.Primitive):
        if T == lltype.Float:
            return 'dbl'
        if T == lltype.Signed:
            return 'int'
        if T == lltype.Char:
            return 'char'
        elif T == lltype.Void:
            raise Exception("accessing a Void value?")
        else:
            raise Exception("don't know how to acess %s value"%T)
    else:
        return 'ptr'
def convert_block(block, memo):
    if block in memo:
        return memo[block]
    converter = BlockConverter(block, memo)
    return converter.convert()

class BlockConverter:

    def __init__(self, block, memo):
        self.block = block
        self.memo = memo
        self.stacksizes = {'int': 0,
                           'dbl': 0,
                           'ptr': 0}
        self.constants = {'int': [],
                          'dbl': [],
                          'ptr': []}
        self.var2stack = {}

    def push(self, v):
        kind = getkind(v.concretetype)
        position = self.stacksizes[kind]
        self.stacksizes[kind] += 1
        self.var2stack[v] = position

    def get(self, v):
        kind = getkind(v.concretetype)
        if isinstance(v, flowmodel.Constant):
            clist = self.constants[kind]
            if kind == 'ptr':
                value = fakeaddress(v.value)
            else:
                value = v.value
            try:
                res = clist.index(value)
            except ValueError:
                res = len(clist)
                clist.append(value)
            return res
        else:
            position = self.var2stack[v]
            return position - self.stacksizes[kind]    # < 0

    def getoffset(self, offset):
        clist = self.constants['int']
        try:
            res = clist.index(offset)
        except ValueError:
            res = len(clist)
            clist.append(offset)
        return res

    def convert_link(self, link):
        targetregs = {'int': [],
                      'dbl': [],
                      'ptr': []}
        for v in link.args:
            if v.concretetype is not lltype.Void:
                kind = getkind(v.concretetype)
                targetregs[kind].append(self.get(v))
        return model.Link(convert_block(link.target, self.memo),
                          targetregs['int'] or None,
                          targetregs['dbl'] or None,
                          targetregs['ptr'] or None)

    def convert(self, memo=None):
        block = self.block
        for v in block.inputargs:
            if v.concretetype is not lltype.Void:
                self.push(v)

        self.insns = []
        l3block = model.Block(self.insns)
        self.memo[block] = l3block

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
            getattr(self, 'convert_'+spaceop.opname,
                    self.default_convert)(spaceop)
            
        if block.exitswitch is None:
            self.insns.append(Op.jump)
            link, = block.exits
            l3block.exit0 = self.convert_link(link)

        elif block.exitswitch != flowmodel.Constant(flowmodel.last_exception):
            link0, link1 = block.exits
            if link0.exitcase:
                link0, link1 = link1, link0
            assert not link0.exitcase
            assert link1.exitcase
            self.insns.append(Op.jump_cond)
            self.insns.append(self.get(block.exitswitch))
            l3block.exit0 = self.convert_link(link0)
            l3block.exit1 = self.convert_link(link1)

        else:
            raise NotImplementedError("exceptions")

        if self.constants['int']: l3block.constants_int = self.constants['int']
        if self.constants['dbl']: l3block.constants_dbl = self.constants['dbl']
        if self.constants['ptr']: l3block.constants_ptr = self.constants['ptr']

        return l3block

    def default_convert(self, spaceop):
        self.insns.append(model.very_low_level_opcode[spaceop.opname])
        for v in spaceop.args:
            self.insns.append(self.get(v))
        if spaceop.result.concretetype is not lltype.Void:
            self.push(spaceop.result)

    def convert_getfield(self, spaceop):
        opname = spaceop.opname + '_' + \
                 getaccesskind(spaceop.result.concretetype)
        self.insns.append(model.very_low_level_opcode[opname])
        v0, v1 = spaceop.args
        self.insns.append(self.get(v0))

        offset = FieldOffset(v0.concretetype.TO, v1.value)
        self.insns.append(self.getoffset(offset))
        self.push(spaceop.result)

    def convert_setfield(self, spaceop):
        v0, v1, v2 = spaceop.args
        opname = spaceop.opname + '_' + \
                 getaccesskind(v2.concretetype)
        self.insns.append(model.very_low_level_opcode[opname])
        self.insns.append(self.get(v0))

        offset = FieldOffset(v0.concretetype.TO, v1.value)
        self.insns.append(self.getoffset(offset))
        self.insns.append(self.get(v2))

    def convert_getarrayitem(self, spaceop):
        opname = spaceop.opname + '_' + \
                 getaccesskind(spaceop.result.concretetype)
        self.insns.append(model.very_low_level_opcode[opname])
        v0, v1 = spaceop.args
        self.insns.append(self.get(v0))
        self.insns.append(self.get(v1))
        
        offset = ArrayItemsOffset(v0.concretetype.TO)
        self.insns.append(self.getoffset(offset))
        
        offset = ItemOffset(spaceop.result.concretetype)
        self.insns.append(self.getoffset(offset))
        self.push(spaceop.result)

    def convert_setarrayitem(self, spaceop):
        array, index, value = spaceop.args
        opname = spaceop.opname + '_' + \
                 getaccesskind(value.concretetype)
        self.insns.append(model.very_low_level_opcode[opname])
        self.insns.append(self.get(array))
        self.insns.append(self.get(index))
        
        offset = ArrayItemsOffset(array.concretetype.TO)
        self.insns.append(self.getoffset(offset))
        
        offset = ItemOffset(value.concretetype)
        self.insns.append(self.getoffset(offset))
        self.insns.append(self.get(value))
        
    def convert_malloc(self, spaceop):
        type, = spaceop.args
        self.insns.append(Op.malloc)
        self.insns.append(self.getoffset(ItemOffset(type.value)))
        self.push(spaceop.result)
        
    def convert_malloc_varsize(self, spaceop):
        TYPE, nitems = spaceop.args
        
        raise NotImplementedError


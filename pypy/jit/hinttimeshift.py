from pypy.jit import hintmodel
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rmodel import inputconst
from pypy.rpython.rtyper import LowLevelOpList
from pypy.rpython.rstr import string_repr
from pypy.rpython import rgenop
from pypy.objspace.flow import model as flowmodel
from pypy.annotation import model as annmodel
from pypy.jit.rtimeshift import STATE_PTR, REDBOX_PTR 
from pypy.jit import rtimeshift

# ___________________________________________________________

def ll_fixed_items(l):
    return l

VARLIST = lltype.Ptr(lltype.GcArray(rgenop.CONSTORVAR,
                                    adtmeths = {
                                        "ll_items": ll_fixed_items,
                                    }))

class HintTimeshift(object):
    
    def __init__(self, hannotator, rtyper):
        self.hannotator = hannotator
        self.rtyper = rtyper

    def timeshift(self):
        for graph in self.hannotator.translator.graphs:
            self.timeshift_graph(graph)

    def timeshift_graph(self, graph):
        for block in graph.iterblocks():
            self.timeshift_block(block)

    def timeshift_block(self, block):
        if not block.exits:   # ignore return/except blocks
            return  # XXX for now
        self.jitstate = flowmodel.Variable('jitstate')
        self.jitstate.concretetype = STATE_PTR

        self.varcolor = {}
        self.varconcretetype = {}

        def introduce_var(v):
            self.varconcretetype[v] = v.concretetype
            if self.is_green(v):
                color = "green"
            else:
                color = "red"
                v.concretetype = REDBOX_PTR
            self.varcolor[v] = color

        for inputarg in block.inputargs:
            introduce_var(inputarg)

        # look for "red" operations
        newops = LowLevelOpList(self.rtyper)
        for op in block.operations:
            green = True
            for arg in op.args:
                if self.varcolor.get(arg, "green") != "green":
                    green = False
            introduce_var(op.result)
            if green and self.varcolor[op.result] == "green":
                # XXX check for side effect ops
                newops.append(op)
                continue
            print "RED", op
            self.timeshift_op(op, newops)
            
        block.operations[:] = newops

        # pass 'jitstate' as an extra argument around the whole graph
        block.inputargs.insert(0, self.jitstate)
        for link in block.exits:
            link.args.insert(0, self.jitstate)

    def timeshift_op(self, op, newops):
        handler = getattr(self, 'tshift_' + op.opname, self.default_tshift)
        v_res = handler(op, newops)
        if v_res is not None:
            assert v_res.concretetype == op.result.concretetype
            op1 = flowmodel.SpaceOperation('same_as', [v_res], op.result)
            newops.append(op1)

    def is_green(self, var):
        hs_var = self.hannotator.binding(var)
        if hs_var == annmodel.s_ImpossibleValue:
            return True
        elif isinstance(hs_var, hintmodel.SomeLLAbstractConstant):
            return hs_var.eager_concrete or hs_var.is_fixed()
        else:
            return False

    def get_genop_var(self, var, llops):
        color = self.varcolor.get(var, "green")
        if color == "red":
            return llops.gendirectcall(rtimeshift.ll_gvar_from_redbox,
                                       self.jitstate, var)
        elif color == "green":
            return llops.gendirectcall(rtimeshift.ll_gvar_from_constant,
                                       self.jitstate, var)
        else:
            raise NotImplementedError(color)

    # ____________________________________________________________

    def default_tshift(self, op, llops):
        # by default, a red operation converts all its arguments to
        # genop variables, and emits a call to a helper that will generate
        # the same operation at run-time
        # XXX constant propagate if possible        
        v_args = llops.genop('malloc_varsize',
                             [inputconst(lltype.Void, VARLIST.TO),
                              inputconst(lltype.Signed, len(op.args))],
                             resulttype = VARLIST)
        for i, arg in enumerate(op.args):
            v_gvar = self.get_genop_var(arg, llops)
            llops.genop('setarrayitem', [v_args,
                                         inputconst(lltype.Signed, i),
                                         v_gvar])
        v_restype = inputconst(lltype.Void, self.varconcretetype[op.result])
        v_res = llops.gendirectcall(rtimeshift.ll_generate_operation,
                                    self.jitstate, opname2vstr(op.opname),
                                    v_args, v_restype)
        assert self.varcolor[op.result] == "red"   # XXX for now
        return v_res


def opname2vstr(name):
    lls = string_repr.convert_const(name)
    return inputconst(string_repr.lowleveltype, lls)

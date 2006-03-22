from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Void
from pypy.translator.cli import conftest
from pypy.translator.cli import cts

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 


DoNothing = object()
opcodes = {
    'int_add': 'add',
    'int_sub': 'sub',
    'int_gt': 'cgt',
    'int_lt': 'clt',
    'int_is_true': DoNothing,
    'same_as': DoNothing, # TODO: does same_as really do nothing else than renaming?
    }

class Node(object):
    def get_name(self):
        pass

    def render(self, ilasm):
        pass
    

class Function(Node):
    def __init__(self, graph, is_entrypoint = False):
        self.graph = graph
        self.is_entrypoint = is_entrypoint
        self.blocknum = {}

        self._set_args()
        self._set_locals()

    def get_name(self):
        return self.graph.name

    def render(self, ilasm):
        self.ilasm = ilasm
        graph = self.graph
        returntype, returnvar = cts.llvar_to_cts(graph.getreturnvar())
        
        ilasm.begin_function(graph.name, self.args, returntype, self.is_entrypoint)
        ilasm.locals(self.locals)

        for block in graph.iterblocks():
            ilasm.label(self._get_block_name(block))

            for op in block.operations:
                self._render_op(op)

            # if it is the last block, return the result
            if not block.exits:
                assert len(block.inputargs) == 1
                return_var = block.inputargs[0]
                if return_var.concretetype is not Void:
                    self._push(return_var)
                ilasm.opcode('ret')

            # follow block links
            for link in block.exits:
                target = link.target
                for to_load, to_store in zip(link.args, target.inputargs):
                    if to_load.concretetype is not Void:
                        self._push(to_load)
                        self._store(to_store)

                target_label = self._get_block_name(target)
                if link.exitcase is None:
                    self.ilasm.branch(target_label)
                else:
                    assert type(link.exitcase is bool)
                    self._push(block.exitswitch)
                    self.ilasm.branch_if(link.exitcase, target_label)

        ilasm.end_function()

    def _set_locals(self):
        # this code is partly borrowed from pypy.translator.c.funcgen.FunctionCodeGenerator
        # TODO: refactoring to avoid code duplication

        graph = self.graph
        mix = [graph.getreturnvar()]
        for block in graph.iterblocks():
            self.blocknum[block] = len(self.blocknum)
            mix.extend(block.inputargs)

            for op in block.operations:
                mix.extend(op.args)
                mix.append(op.result)
                if getattr(op, "cleanup", None) is not None:
                    cleanup_finally, cleanup_except = op.cleanup
                    for cleanupop in cleanup_finally + cleanup_except:
                        mix.extend(cleanupop.args)
                        mix.append(cleanupop.result)
            for link in block.exits:
                mix.extend(link.getextravars())
                mix.extend(link.args)

        # filter only locals variables, i.e.:
        #  - must be variables
        #  - must appear only once
        #  - must not be function parameters
        #  - must not have 'void' type

        args = {}
        for ctstype, name in self.args:
            args[name] = True
        
        locals = []
        seen = {}
        for v in mix:
            is_var = isinstance(v, flowmodel.Variable)
            if id(v) not in seen and is_var and v.name not in args and v.concretetype is not Void:
                locals.append(cts.llvar_to_cts(v))
                seen[id(v)] = True

        self.locals = locals

    def _set_args(self):
        self.args = map(cts.llvar_to_cts, self.graph.getargs())
        self.argset = set([argname for argtype, argname in self.args])

    def _get_block_name(self, block):
        return 'block%s' % self.blocknum[block]

    def _render_op(self, op):
        opname = op.opname

        cli_opcode = opcodes.get(opname, None)
        if cli_opcode is DoNothing:
            # simply rename the variable
            self._push(op.args[0])
            self._store(op.result)
        elif cli_opcode is not None:
            self._simple_op(cli_opcode, op)
        elif opname == 'direct_call':
            self._call(op)
        else:
            if conftest.option.nostop:
                log.WARNING('Unknown opcode: %s ' % op)
                self.ilasm.opcode(str(op))
            else:
                assert False, 'Unknown opcode: %s ' % op

    def _call(self, op):
        func_name = cts.graph_to_signature(op.args[0].value.graph)

        # push parameters
        for func_arg in op.args[1:]:
            self._push(func_arg)

        self.ilasm.call(func_name)
        self._store(op.result)
        

    def _simple_op(self, cli_opcode, op):
        # push arg on stack
        for arg in op.args:
            self._push(arg)

        # compute and store value
        self.ilasm.opcode(cli_opcode)
        self._store(op.result)

    def _push(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.name in self.argset:
                self.ilasm.opcode('ldarg.s', repr(v.name))
            else:
                self.ilasm.opcode('ldloc.s', repr(v.name))

        elif isinstance(v, flowmodel.Constant):
            iltype, ilvalue = cts.llconst_to_ilasm(v)
            self.ilasm.opcode('ldc.' + iltype, ilvalue)
        else:
            assert False

    def _store(self, v):
        if isinstance(v, flowmodel.Variable):
            self.ilasm.opcode('stloc.s', repr(v.name))
        else:
            assert False

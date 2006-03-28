from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Void
from pypy.translator.cli.option import getoption
from pypy.translator.cli import cts
from pypy.translator.cli.opcodes import opcodes, DoNothing, PushArgs, PushArg

from pypy.tool.ansi_print import ansi_log
import py
log = py.log.Producer("cli") 
py.log.setconsumer("cli", ansi_log) 


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

    def _is_return_block(self, block):
        return (not block.exits) and len(block.inputargs) == 1

    def _is_raise_block(self, block):
        return (not block.exits) and len(block.inputargs) == 2        

    def render(self, ilasm):
        self.ilasm = ilasm
        graph = self.graph
        returntype, returnvar = cts.llvar_to_cts(graph.getreturnvar())
        
        self.ilasm.begin_function(graph.name, self.args, returntype, self.is_entrypoint)
        self.ilasm.locals(self.locals)

        for block in graph.iterblocks():
            self.ilasm.label(self._get_block_name(block))

            handle_exc = (block.exitswitch == flowmodel.c_last_exception)
            if handle_exc:
                self.ilasm.begin_try()

            for op in block.operations:
                self._render_op(op)

            # check for codeless blocks
            if self._is_return_block(block):
                return_var = block.inputargs[0]
                if return_var.concretetype is not Void:
                    self._push(return_var)
                self.ilasm.opcode('ret')
            elif self._is_raise_block(block):
                exc = block.inputargs[1]
                self._push(exc)
                self.ilasm.opcode('throw')

            if handle_exc:
                # search for the "default" block to be executed when no exception is raised
                for link in block.exits:
                    if link.exitcase is None:
                        self._setup_link(link)
                        target_label = self._get_block_name(link.target)
                        self.ilasm.leave(target_label)
                self.ilasm.end_try()

                # catch the exception and dispatch to the appropriate block
                for link in block.exits:
                    if link.exitcase is None:
                        continue # see above

                    assert issubclass(link.exitcase, Exception)
                    cts_exc = cts.pyexception_to_cts(link.exitcase)
                    self.ilasm.begin_catch(cts_exc)

                    target = link.target
                    if self._is_raise_block(target):
                        # the exception value is on the stack, use it as the 2nd target arg
                        assert len(link.args) == 2
                        assert len(target.inputargs) == 2
                        self._store(link.target.inputargs[1])
                    else:
                        # pop the unused exception value
                        self.ilasm.opcode('pop')
                        self._setup_link(link)
                    
                    target_label = self._get_block_name(target)
                    self.ilasm.leave(target_label)
                    self.ilasm.end_catch()

            else:
                # no exception handling, follow block links
                for link in block.exits:
                    self._setup_link(link)
                    target_label = self._get_block_name(link.target)
                    if link.exitcase is None:
                        self.ilasm.branch(target_label)
                    else:
                        assert type(link.exitcase is bool)
                        assert block.exitswitch is not None
                        self._push(block.exitswitch)
                        self.ilasm.branch_if(link.exitcase, target_label)


        # add a block that will never be executed, just to please the
        # .NET runtime that seems to need a return statement at the
        # end of the function
        if returntype != 'void':
            ilasm_type = cts.ctstype_to_ilasm(returntype)
            self.ilasm.opcode('ldc.%s 0' % ilasm_type)

        self.ilasm.opcode('ret')
        self.ilasm.end_function()

    def _setup_link(self, link):
        target = link.target
        for to_load, to_store in zip(link.args, target.inputargs):
            if to_load.concretetype is not Void:
                self._push(to_load)
                self._store(to_store)


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
        if cli_opcode is DoNothing: # simply rename the variable
            self._push(op.args[0])
            self._store(op.result)
        elif cli_opcode is not None:
            self._render_cli_opcode(cli_opcode, op)
        elif opname == 'direct_call':
            self._call(op)
        else:
            if getoption('nostop'):
                log.WARNING('Unknown opcode: %s ' % op)
                self.ilasm.opcode(str(op))
            else:
                assert False, 'Unknown opcode: %s ' % op

    def _render_cli_opcode(self, cli_opcode, op):
        if type(cli_opcode) is str:
            instructions = [PushArgs, cli_opcode]
        else:
            instructions = cli_opcode

        for instr in instructions:
            if instr is PushArgs:
                for arg in op.args:
                    self._push(arg)
            elif isinstance(instr, PushArg):
                self._push(op.args[instr.arg])
            else:
                self.ilasm.opcode(instr)

        self._store(op.result)


    def _call(self, op):
        func_name = cts.graph_to_signature(op.args[0].value.graph)

        # push parameters
        for func_arg in op.args[1:]:
            self._push(func_arg)

        self.ilasm.call(func_name)
        self._store(op.result)

    def _push(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.name in self.argset:
                self.ilasm.opcode('ldarg', repr(v.name))
            else:
                self.ilasm.opcode('ldloc', repr(v.name))

        elif isinstance(v, flowmodel.Constant):
            iltype, ilvalue = cts.llconst_to_ilasm(v)
            self.ilasm.opcode('ldc.' + iltype, ilvalue)
        else:
            assert False

    def _store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.opcode('stloc', repr(v.name))
        else:
            assert False

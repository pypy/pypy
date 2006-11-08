try:
    set
except NameError:
    from sets import Set as set

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Void
from pypy.translator.oosupport.function import Function as OOFunction
from pypy.translator.cli.option import getoption
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.opcodes import opcodes
from pypy.translator.cli.metavm import InstructionList, Generator
from pypy.translator.cli.node import Node
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.support import log
from pypy.translator.cli.ilgenerator import CLIBaseGenerator

class Function(OOFunction, Node, CLIBaseGenerator):

    def __init__(self, *args, **kwargs):
        OOFunction.__init__(self, *args, **kwargs)
        self._set_args()
        self._set_locals()
                 
    def _create_generator(self, ilasm):
        return self # Function implements the Generator interface

    def begin_try(self):
        self.ilasm.begin_try()

    def end_try(self, target_label):
        self.ilasm.leave(target_label)
        self.ilasm.end_try()

    def begin_catch(self, llexitcase):
        ll_meta_exc = llexitcase
        ll_exc = ll_meta_exc._inst.class_._INSTANCE
        cts_exc = self.cts.lltype_to_cts(ll_exc, False)
        self.ilasm.begin_catch(cts_exc)

    def end_catch(self, target_label):
        self.ilasm.leave(target_label)
        self.ilasm.end_catch()

    def store_exception_and_link(self, link):
        if self._is_raise_block(link.target):
            # the exception value is on the stack, use it as the 2nd target arg
            assert len(link.args) == 2
            assert len(link.target.inputargs) == 2
            self.store(link.target.inputargs[1])
        else:
            # the exception value is on the stack, store it in the proper place
            if isinstance(link.last_exception, flowmodel.Variable):
                self.ilasm.opcode('dup')
                self.store(link.last_exc_value)                            
                self.ilasm.get_field(('Object_meta', 'Object', 'meta'))
                self.store(link.last_exception)
            else:
                self.store(link.last_exc_value)
            self._setup_link(link)

    def begin_render(self):
        returntype, returnvar = self.cts.llvar_to_cts(self.graph.getreturnvar())
        if self.is_method:
            args = self.args[1:] # self is implicit
            meth_type = 'virtual' # TODO: mark as virtual only when strictly necessary
        else:
            args = self.args
            meth_type = 'static'
        self.ilasm.begin_function(self.name, args, returntype, self.is_entrypoint, meth_type)        
        self.ilasm.locals(self.locals)

    def end_render(self):
        self.ilasm.end_function()

    def set_label(self, label):
        self.ilasm.label(label)

    def render_return_block(self, block):
        return_var = block.inputargs[0]
        if return_var.concretetype is not Void:
            self.load(return_var)
        self.ilasm.opcode('ret')

    def render_raise_block(self, block):
        exc = block.inputargs[1]
        self.load(exc)
        self.ilasm.opcode('throw')


    # Those parts of the generator interface that are function
    # specific

    def load(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.name in self.argset:
                selftype, selfname = self.args[0]
                if self.is_method and v.name == selfname:
                    self.ilasm.load_self() # special case for 'self'
                else:
                    self.ilasm.load_arg(v)
            else:
                self.ilasm.load_local(v)

        else:
            super(Function, self).load(v)

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.store_local(v)
        else:
            assert False

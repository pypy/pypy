try:
    set
except NameError:
    from sets import Set as set

from pypy.objspace.flow import model as flowmodel
from pypy.rpython.lltypesystem.lltype import Void
from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.function import Function as OOFunction
from pypy.translator.oosupport.constant import push_constant
from pypy.translator.cli.option import getoption
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.opcodes import opcodes
from pypy.translator.cli.metavm import InstructionList, Generator
from pypy.translator.cli.node import Node
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.support import log
from pypy.translator.cli.ilgenerator import CLIBaseGenerator

USE_LAST = False

class NativeExceptionHandler(object):
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

    def render_raise_block(self, block):
        exc = block.inputargs[1]
        self.load(exc)
        self.ilasm.opcode('throw')

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
                self.ilasm.get_field(('class Object_meta', 'Object', 'meta'))
                self.store(link.last_exception)
            else:
                self.store(link.last_exc_value)
            self._setup_link(link)

class LastExceptionHandler(object):
    in_try = False

    def begin_try(self):
        self.in_try = True
        self.ilasm.opcode('// begin_try')

    def end_try(self, target_label):
        self.ilasm.opcode('ldsfld', 'object last_exception')
        self.ilasm.opcode('brnull', target_label)
        self.ilasm.opcode('// end try')
        self.in_try = False

    def begin_catch(self, llexitcase):
        self.ilasm.label(self.current_label('catch'))
        ll_meta_exc = llexitcase
        ll_exc = ll_meta_exc._inst.class_._INSTANCE
        cts_exc = self.cts.lltype_to_cts(ll_exc, False)
        self.ilasm.opcode('ldsfld', 'object last_exception')
        self.isinstance(cts_exc)
        self.ilasm.opcode('dup')
        self.ilasm.opcode('brtrue.s', 6)
        self.ilasm.opcode('pop')
        self.ilasm.opcode('br', self.next_label('catch'))
        # here is the target of the above brtrue.s
        self.ilasm.opcode('ldnull')
        self.ilasm.opcode('stsfld', 'object last_exception')

    def end_catch(self, target_label):
        self.ilasm.opcode('br', target_label)

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
                self.ilasm.get_field(('class Object_meta', 'Object', 'meta'))
                self.store(link.last_exception)
            else:
                self.store(link.last_exc_value)
            self._setup_link(link)

    def before_last_blocks(self):
        self.ilasm.label(self.current_label('catch'))
        self.ilasm.opcode('nop')

    def render_raise_block(self, block):
        exc = block.inputargs[1]
        self.load(exc)
        self.ilasm.opcode('stsfld', 'object last_exception')
        if not self.return_block: # must be a void function
            TYPE = self.graph.getreturnvar().concretetype
            default = TYPE._defl()
            if default is not None: # concretetype is Void
                try:
                    self.db.constant_generator.push_primitive_constant(self, TYPE, default)
                except AssertionError:
                    self.ilasm.opcode('ldnull') # :-(
            self.ilasm.opcode('ret')
        else:
            self.ilasm.opcode('br', self._get_block_name(self.return_block))

    def _render_op(self, op):
        OOFunction._render_op(self, op)
        if op.opname in ('direct_call', 'oosend', 'indirect_call') and not self.in_try:
            self._premature_return()

    def _render_sub_op(self, sub_op):
        OOFunction._render_sub_op(self, sub_op)
        if sub_op.op.opname in ('direct_call', 'oosend', 'indirect_call') and not self.in_try:
            self._premature_return(need_pop=sub_op.op.result is not ootype.Void)


    def _premature_return(self, need_pop=False):
        try:
            return_block = self._get_block_name(self.graph.returnblock)
        except KeyError:
            self.ilasm.opcode('//premature return')
            self.ilasm.opcode('ldsfld', 'object last_exception')
            TYPE = self.graph.getreturnvar().concretetype
            default = TYPE._defl()
            if default is None: # concretetype is Void
                self.ilasm.opcode('brfalse.s', 1)
                self.ilasm.opcode('ret')
            else:
                self.ilasm.opcode('brfalse.s', 3) # ??
                try:
                    self.db.constant_generator.push_primitive_constant(self, TYPE, default)
                except AssertionError:
                    self.ilasm.opcode('ldnull') # :-(
                self.ilasm.opcode('ret')
        else:
            self.ilasm.opcode('ldsfld', 'object last_exception')
            self.ilasm.opcode('brtrue', return_block)


if USE_LAST:
    ExceptionHandler = LastExceptionHandler
else:
    ExceptionHandler = NativeExceptionHandler

class Function(ExceptionHandler, OOFunction, Node, CLIBaseGenerator):

    def __init__(self, *args, **kwargs):
        OOFunction.__init__(self, *args, **kwargs)
        namespace = getattr(self.graph.func, '_namespace_', None)
        str
        if namespace:
            if '.' in namespace:
                self.namespace, self.classname = namespace.rsplit('.', 1)
            else:
                self.namespace = None
                self.classname = namespace
        else:
            self.namespace = None
            self.classname = None

    def _create_generator(self, ilasm):
        return self # Function implements the Generator interface

    def record_ll_meta_exc(self, ll_meta_exc):
        # record the type only if it doesn't belong to a native_class
        ll_exc = ll_meta_exc._inst.class_._INSTANCE
        NATIVE_INSTANCE = ll_exc._hints.get('NATIVE_INSTANCE', None)
        if NATIVE_INSTANCE is None:
            OOFunction.record_ll_meta_exc(self, ll_meta_exc)

    def begin_render(self):
        self._set_args()
        self._set_locals()
        
        returntype, returnvar = self.cts.llvar_to_cts(self.graph.getreturnvar())
        if self.is_method:
            args = self.args[1:] # self is implicit
            meth_type = 'virtual' # TODO: mark as virtual only when strictly necessary
        else:
            args = self.args
            meth_type = 'static'

        if self.namespace:
            self.ilasm.begin_namespace(self.namespace)
        if self.classname:
            self.ilasm.begin_class(self.classname)
        self.ilasm.begin_function(self.name, args, returntype, self.is_entrypoint, meth_type)
        self.ilasm.locals(self.locals)

    def end_render(self):
        self.ilasm.end_function()
        if self.classname:
            self.ilasm.end_class()
        if self.namespace:
            self.ilasm.end_namespace()

    def set_label(self, label):
        self.ilasm.label(label)

    def render_return_block(self, block):
        return_var = block.inputargs[0]
        if return_var.concretetype is not Void:
            self.load(return_var)
        self.ilasm.opcode('ret')

    # XXX: this method should be moved into oosupport, but other
    # backends are not ready :-(
    def render_bool_switch(self, block):
        assert len(block.exits) == 2
        for link in block.exits:
            if link.exitcase:
                link_true = link
            else:
                link_false = link

        true_label = self.next_label('link_true')
        self.generator.load(block.exitswitch)
        self.generator.branch_conditionally(link.exitcase, true_label)
        self._follow_link(link_false) # if here, the exitswitch is false
        self.set_label(true_label)
        self._follow_link(link_true)  # if here, the exitswitch is true

    def render_numeric_switch(self, block):
        if block.exitswitch.concretetype in (ootype.SignedLongLong, ootype.UnsignedLongLong):
            # TODO: it could be faster to check is the values fit in
            # 32bit, and perform a cast in that case
            self.render_numeric_switch_naive(block)
            return

        cases = {}
        naive = False
        for link in block.exits:
            if link.exitcase == "default":
                default = link, self.next_label('switch')
            else:
                if block.exitswitch.concretetype in (ootype.Char, ootype.UniChar):
                    value = ord(link.exitcase)
                else:
                    value = link.exitcase
                if value < 0:
                    naive = True
                    break
                cases[value] = link, self.next_label('switch')

        try:
            max_case = max(cases.keys())
        except ValueError:
            max_case = 0
        if max_case > 3*len(cases) + 10: # the switch is very sparse, better to use the naive version
            naive = True

        if naive:
            self.render_numeric_switch_naive(block)
            return

        targets = []
        for i in xrange(max_case+1):
            link, lbl = cases.get(i, default)
            targets.append(lbl)
        self.generator.load(block.exitswitch)
        self.ilasm.switch(targets)
        self.render_switch_case(*default)
        for link, lbl in cases.itervalues():
            self.render_switch_case(link, lbl)

    def render_switch_case(self, link, label):
        target_label = self._get_block_name(link.target)
        self.set_label(label)
        self._setup_link(link)
        self.generator.branch_unconditionally(target_label)

    # Those parts of the generator interface that are function
    # specific

    def load(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is ootype.Void:
                return # ignore it
            if v.name in self.argset:
                selftype, selfname = self.args[0]
                if self.is_method and v.name == selfname:
                    self.ilasm.load_self() # special case for 'self'
                else:
                    self.ilasm.load_arg(v)
            else:
                self.ilasm.load_local(v)
        elif isinstance(v, SubOperation):
            self._render_sub_op(v)
        else:
            super(Function, self).load(v)

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                self.ilasm.store_local(v)
        else:
            assert False

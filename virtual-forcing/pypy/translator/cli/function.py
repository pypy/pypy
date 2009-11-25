from pypy.objspace.flow import model as flowmodel
from pypy.rlib.objectmodel import CDefinedIntSymbolic
from pypy.rpython.lltypesystem.lltype import Void
from pypy.rpython.ootypesystem import ootype
from pypy.translator.oosupport.treebuilder import SubOperation
from pypy.translator.oosupport.function import Function as OOFunction, render_sub_op
from pypy.translator.oosupport.constant import push_constant
from pypy.translator.cli.option import getoption
from pypy.translator.cli.cts import CTS
from pypy.translator.cli.opcodes import opcodes
from pypy.translator.cli.metavm import InstructionList, Generator
from pypy.translator.cli.node import Node
from pypy.translator.cli.class_ import Class
from pypy.translator.cli.support import log
from pypy.translator.cli.ilgenerator import CLIBaseGenerator

class Function(OOFunction, Node, CLIBaseGenerator):

    auto_propagate_exceptions = True

    def __init__(self, *args, **kwargs):
        OOFunction.__init__(self, *args, **kwargs)

        if hasattr(self.db.genoo, 'exceptiontransformer'):
            self.auto_propagate_exceptions = False
        
        namespace = getattr(self.graph.func, '_namespace_', None)
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
        ll_exc = ll_meta_exc._INSTANCE
        NATIVE_INSTANCE = ll_exc._hints.get('NATIVE_INSTANCE', None)
        if NATIVE_INSTANCE is None:
            OOFunction.record_ll_meta_exc(self, ll_meta_exc)

    def _trace_enabled(self):
        return getoption('trace')

    def _trace(self, s, writeline=False):
        self.ilasm.stderr(s, writeline=writeline)

    def _trace_value(self, prompt, v):
        self.ilasm.stderr('  ' + prompt + ': ', writeline=False)
        self.ilasm.load_stderr()
        self.load(v)
        if v.concretetype is not ootype.String:
            from pypy.translator.cli.test.runtest import format_object
            format_object(v.concretetype, self.cts, self.ilasm)
        self.ilasm.write_stderr()

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

    def begin_try(self, cond):
        if cond:
            self.ilasm.begin_try()

    def end_try(self, target_label, cond):
        if cond:
            self.ilasm.leave(target_label)
            self.ilasm.end_try()
        else:
            self.ilasm.branch(target_label)

    def begin_catch(self, llexitcase):
        ll_meta_exc = llexitcase
        ll_exc = ll_meta_exc._INSTANCE
        cts_exc = self.cts.lltype_to_cts(ll_exc)
        self.ilasm.begin_catch(cts_exc.classname())

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
                self.ilasm.call_method(
                    'class [mscorlib]System.Type object::GetType()',
                    virtual=True)
                self.store(link.last_exception)
            else:
                self.store(link.last_exc_value)
            self._setup_link(link)

    def _dont_store(self, to_load, to_store):
        # ugly workaround to make the exceptiontransformer work with
        # valuetypes: when exceptiontransforming a function whose result is a
        # .NET valuetype, it tries to store a null into the return variable.
        # Since it is not possible to store a null into a valuetype, and that
        # in that case the value is not used anyway, we simply ignore it.
        from pypy.translator.cli.dotnet import NativeInstance
        if isinstance(to_load, flowmodel.Constant):
            value = to_load.value
            is_null = (not isinstance(value, CDefinedIntSymbolic)) and (not value)
            T = ootype.typeOf(to_load.value)
            if isinstance(T, NativeInstance) and T._is_value_type and is_null:
                return True
        return OOFunction._dont_store(self, to_load, to_store)

    def render_numeric_switch(self, block):
        if block.exitswitch.concretetype in (ootype.SignedLongLong, ootype.UnsignedLongLong):
            # TODO: it could be faster to check is the values fit in
            # 32bit, and perform a cast in that case
            self.render_numeric_switch_naive(block)
            return

        cases, min_case, max_case, default = self._collect_switch_cases(block)
        is_sparse = self._is_sparse_switch(cases, min_case, max_case)

        naive = (min_case < 0) or is_sparse
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

    def call_oostring(self, ARGTYPE):
        if isinstance(ARGTYPE, ootype.Instance):
            argtype = self.cts.types.object
        else:
            argtype = self.cts.lltype_to_cts(ARGTYPE)
        self.call_signature('string [pypylib]pypy.runtime.Utils::OOString(%s, int32)' % argtype)

    def call_oounicode(self, ARGTYPE):
        argtype = self.cts.lltype_to_cts(ARGTYPE)
        self.call_signature('string [pypylib]pypy.runtime.Utils::OOUnicode(%s)' % argtype)

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
            render_sub_op(v, self.db, self.generator)
        else:
            super(Function, self).load(v)

    def store(self, v):
        if isinstance(v, flowmodel.Variable):
            if v.concretetype is not Void:
                if v.name in self.argset:
                    self.ilasm.store_arg(v)
                else:
                    self.ilasm.store_local(v)
        else:
            assert False

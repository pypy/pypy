class ExceptionPolicy:
    def __init__(self):
        raise Exception, 'ExceptionPolicy should not be used directly'

    def transform(self, translator, graph=None):
        return

    def new(exceptionpolicy=None):  #factory
        exceptionpolicy = exceptionpolicy or 'invokeunwind'
        if exceptionpolicy == 'invokeunwind':
            from pypy.translator.js.exception import InvokeUnwindExceptionPolicy
            exceptionpolicy = InvokeUnwindExceptionPolicy()
        elif exceptionpolicy == 'explicit':
            from pypy.translator.js.exception import ExplicitExceptionPolicy
            exceptionpolicy = ExplicitExceptionPolicy()
        elif exceptionpolicy == 'none':
            from pypy.translator.js.exception import NoneExceptionPolicy
            exceptionpolicy = NoneExceptionPolicy()
        else:
            raise Exception, 'unknown exceptionpolicy: ' + str(exceptionpolicy)
        return exceptionpolicy
    new = staticmethod(new)


class NoneExceptionPolicy(ExceptionPolicy): #XXX untested
    def __init__(self):
        pass


class InvokeUnwindExceptionPolicy(ExceptionPolicy):  #uses issubclass() and llvm invoke&unwind
    def __init__(self):
        pass

    def invoke(self, codewriter, targetvar, returntype, functionref, args, label, except_label):
        labels = 'to label %%%s except label %%%s' % (label, except_label)
        if returntype == 'void':
            codewriter.llvm('invoke void %s(%s) %s' % (functionref, args, labels))
        else:
            codewriter.llvm('%s = invoke %s %s(%s) %s' % (targetvar, returntype, functionref, args, labels))

    def _is_raise_new_exception(self, db, graph, block):
        from pypy.objspace.flow.model import mkentrymap
        is_raise_new = False
        entrylinks = mkentrymap(graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = db.repr_arg_multi(block.inputargs)
        for i, arg in enumerate(inputargs):
            names = db.repr_arg_multi([link.args[i] for link in entrylinks])
            for name in names:  #These tests-by-name are a bit yikes, but I don't see a better way right now
                if not name.startswith('last_exception_') and not name.startswith('last_exc_value_'):
                    is_raise_new = True
        return is_raise_new

    def write_exceptblock(self, funcnode, codewriter, block):
        assert len(block.inputargs) == 2

        db    = funcnode.db
        graph = funcnode.graph

        if self._is_raise_new_exception(db, graph, block):
            inputargs     = db.repr_arg_multi(block.inputargs)
            inputargtypes = db.repr_arg_type_multi(block.inputargs)

            codewriter.store('last_exception_type' , [], inputargs[0])
            codewriter.store('last_exception_value', [], inputargs[1])
        else:
            codewriter.comment('reraise last exception')
            #Reraising last_exception.
            #Which is already stored in the global variables.
            #So nothing needs to happen here!

        codewriter.append('throw "Pypy exception"')
        codewriter.skip_closeblock()

    def fetch_exceptions(self, codewriter, exc_found_labels, lltype_of_exception_type, lltype_of_exception_value):
        for label, target, last_exc_type_var, last_exc_value_var in exc_found_labels:
            codewriter.label(label)
            if last_exc_type_var:    
                codewriter.load(last_exc_type_var , 'last_exception_type' , [])
            if last_exc_value_var:   
                codewriter.load(last_exc_value_var, 'last_exception_value', [])
            codewriter.br_uncond(target)

    def reraise(self, funcnode, codewriter):
        codewriter.comment('reraise when exception is not caught')
        codewriter.append('throw "Pypy exception"')
        codewriter.skip_closeblock()

    def llc_options(self):
        return '-enable-correct-eh-support'


class ExplicitExceptionPolicy(ExceptionPolicy):    #uses issubclass() and last_exception tests after each call
    def __init__(self):
        self.invoke_count = 0

    def transform(self, translator, graph=None):
        from pypy.translator.llvm.backendopt.exception import create_exception_handling
        if graph:
            create_exception_handling(translator, graph)
        else:
            for graph in translator.flowgraphs.itervalues():
                create_exception_handling(translator, graph)
            #translator.view()

    def invoke(self, codewriter, targetvar, returntype, functionref, args, label, except_label):
        if returntype == 'void':
            codewriter.append('call void %s(%s)' % (functionref, args))
        else:
            codewriter.llvm('%s = call %s %s(%s)' % (targetvar, returntype, functionref, args))
        tmp = '%%invoke.tmp.%d' % self.invoke_count
        exc = '%%invoke.exc.%d' % self.invoke_count
        self.invoke_count += 1
        codewriter.llvm('%(tmp)s = load %%RPYTHON_EXCEPTION_VTABLE** last_exception_type' % locals())
        codewriter.llvm('%(exc)s = seteq %%RPYTHON_EXCEPTION_VTABLE* %(tmp)s, null'         % locals())
        codewriter.llvm('br bool %(exc)s, label %%%(label)s, label %%%(except_label)s'      % locals())

    def write_exceptblock(self, funcnode, codewriter, block):
        assert len(block.inputargs) == 2

        funcnode.write_block_phi_nodes(codewriter, block)

        inputargs     = funcnode.db.repr_arg_multi(block.inputargs)
        inputargtypes = funcnode.db.repr_arg_type_multi(block.inputargs)

        codewriter.store('last_exception_type' , [], inputargs[0])
        codewriter.store('last_exception_value', [], inputargs[1])
        codewriter.ret('void', '')

    def fetch_exceptions(self, codewriter, exc_found_labels, lltype_of_exception_type, lltype_of_exception_value):
        for label, target, last_exc_type_var, last_exc_value_var in exc_found_labels:
            codewriter.label(label)
            if last_exc_type_var:    
                codewriter.load(last_exc_type_var , 'last_exception_type' , [])
            if last_exc_value_var:   
                codewriter.load(last_exc_value_var, 'last_exception_value', [])
            codewriter.store('last_exception_type' , [], 'null')
            codewriter.store('last_exception_value', [], 'null')
            codewriter.br_uncond(target)
            codewriter.skip_closeblock()

    def reraise(self, funcnode, codewriter):
        codewriter.ret('void', '')

    def llc_options(self):
        return ''

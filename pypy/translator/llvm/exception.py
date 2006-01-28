from pypy.objspace.flow.model import Variable, c_last_exception

from pypy.translator.llvm.codewriter import DEFAULT_CCONV
from pypy.translator.llvm.backendopt.exception import create_exception_handling
from pypy.translator.llvm.module.excsupport import invokeunwind_code, \
                                                   explicit_code

def repr_if_variable(db, arg):
    if isinstance(arg, Variable):
        return db.repr_arg(arg)

class ExceptionPolicy:
    def __init__(self, db):
        self.db = db
        raise Exception, 'ExceptionPolicy should not be used directly'

    def transform(self, translator, graph=None):
        return

    def update_phi_data(self, funcnode, entrylinks, block, blocknames):
        """ Exceptions handling code introduces intermediate blocks for
        exception handling cases, hence we modify our input phi data
        accordingly. """
        for ii, link in enumerate(entrylinks):
            if (link.prevblock.exitswitch == c_last_exception and
                link.prevblock.exits[0].target != block):
                blocknames[ii] += '_exception_found_branchto_'
                blocknames[ii] += funcnode.block_to_name[block]

    def _noresult(self, returntype):
        r = returntype.strip()
        if r == 'void':
            return 'void'
        elif r == 'bool':
            return 'bool false'
        elif r in 'float double'.split():
            return r + ' 0.0'
        elif r in 'ubyte sbyte ushort short uint int ulong long'.split():
            return r + ' 0'
        return r + ' null'

    def _noresult2(self, returntype):
        r = returntype.strip()
        if r == 'void':
            return 'void'
        elif r == 'bool':
            return 'false'
        elif r in 'float double'.split():
            return '0.0'
        elif r in 'ubyte sbyte ushort short uint int ulong long'.split():
            return '0'
        return 'null'

    def _nonoderesult(self, node):
        returntype, name, dummy = node.getdecl_parts()
        noresult = self._noresult(returntype)
        return noresult

    def new(db, exceptionpolicy=None):  #factory
        exceptionpolicy = exceptionpolicy or 'explicit'
        if exceptionpolicy == 'invokeunwind':
            exceptionpolicy = InvokeUnwindExceptionPolicy(db)
        elif exceptionpolicy == 'explicit':
            exceptionpolicy = ExplicitExceptionPolicy(db)
        elif exceptionpolicy == 'none':
            exceptionpolicy = NoneExceptionPolicy(db)
        else:
            raise Exception, 'unknown exceptionpolicy: ' + str(exceptionpolicy)
        return exceptionpolicy
    new = staticmethod(new)

class NoneExceptionPolicy(ExceptionPolicy):
    """  XXX untested """

    def __init__(self, db):
        self.db = db

class InvokeUnwindExceptionPolicy(ExceptionPolicy):
    """ uses issubclass() and llvm invoke&unwind
    XXX Untested for a while """
    
    def __init__(self):
        pass

    def llvm_declcode(self):
        return ''

    def llvm_implcode(self, entrynode):
        returntype, entrypointname = entrynode.getdecl().split('%', 1)
        noresult = self._noresult(returntype)
        cconv = DEFAULT_CCONV
        return invokeunwind_code % locals()

    def invoke(self, codewriter, targetvar, tail_, cconv, returntype,
               functionref, args, label, except_label):

        labels = 'to label %%%s except label %%%s' % (label, except_label)
        if returntype == 'void':
            #XXX
            codewriter._indent('%sinvoke %s void %s(%s) %s' % (tail_,
                                                               cconv,
                                                               functionref,
                                                               args,
                                                               labels))
        else:
            codewriter._indent('%s = %sinvoke %s %s %s(%s) %s' % (targetvar,
                                                                  tail_,
                                                                  cconv,
                                                                  returntype,
                                                                  functionref,
                                                                  args,
                                                                  labels))

    def _is_raise_new_exception(self, db, graph, block):
        from pypy.objspace.flow.model import mkentrymap
        is_raise_new = False
        entrylinks = mkentrymap(graph)[block]
        entrylinks = [x for x in entrylinks if x.prevblock is not None]
        inputargs = db.repr_arg_multi(block.inputargs)
        for i, arg in enumerate(inputargs):
            names = db.repr_arg_multi([link.args[i] for link in entrylinks])
            # these tests-by-name are a bit yikes, but I don't see a better way
            # right now
            for name in names:  
                if (not name.startswith('%last_exception_') and
                    not name.startswith('%last_exc_value_')):
                    is_raise_new = True
        return is_raise_new

    def write_exceptblock(self, funcnode, codewriter, block):
        assert len(block.inputargs) == 2

        db    = funcnode.db
        graph = funcnode.graph

        if self._is_raise_new_exception(db, graph, block):
            funcnode.write_block_phi_nodes(codewriter, block)

            inputargs     = db.repr_arg_multi(block.inputargs)
            inputargtypes = db.repr_arg_type_multi(block.inputargs)

            codewriter.store(inputargtypes[0], inputargs[0], '%last_exception_type')
            codewriter.store(inputargtypes[1], inputargs[1], '%last_exception_value')
        else:
            codewriter.comment('reraise last exception')
            # Reraising last_exception.
            # Which is already stored in the global variables.
            # So nothing needs to happen here!

        codewriter.unwind()

    def fetch_exceptions(self, codewriter, exc_found_labels,
                         lltype_of_exception_type, lltype_of_exception_value):
        for label, target, last_exc_type_var, last_exc_value_var in exc_found_labels:
            codewriter.label(label)
            if last_exc_type_var:    
                codewriter.load(last_exc_type_var,
                                lltype_of_exception_type,
                                '%last_exception_type')
            if last_exc_value_var:   
                codewriter.load(last_exc_value_var,
                                lltype_of_exception_value,
                                '%last_exception_value')
            codewriter.br_uncond(target)

    def reraise(self, funcnode, codewriter):
        codewriter.comment('reraise when exception is not caught')
        codewriter.unwind()

    def llc_options(self):
    	import sys
    	if sys.platform == 'linux2' and sys.maxint == 2**63-1:
            s = ' -enable-ia64-dag-isel'
	else:
            s = ''
        return '-enable-correct-eh-support' + s

class ExplicitExceptionPolicy(ExceptionPolicy):
    """ uses issubclass() and last_exception tests after each call """
    def __init__(self, db):
        self.db = db
        self.invoke_count = 0

    def llvm_declcode(self):
        return ''
    
    def llvm_implcode(self, entrynode):
        returntype, entrypointname = entrynode.getdecl().split('%', 1)
        noresult = self._noresult(returntype)
        cconv = DEFAULT_CCONV
        return explicit_code % locals()
 
    def transform(self, translator, graph=None):
        if graph:
            create_exception_handling(translator, graph)
        else:
            for graph in translator.flowgraphs.itervalues():
                create_exception_handling(translator, graph)

    def invoke(self, codewriter, targetvar, returntype, functionref,
               argrefs, argtypes,
               node, block): # XXX Unsure of these being passed in

        assert functionref != '%keepalive'

        # at least one label and one exception label
        assert len(block.exits) >= 2
        link = block.exits[0]
        assert link.exitcase is None

        none_label  = node.block_to_name[link.target]
        block_label = node.block_to_name[block]
        exc_label   = block_label + '_exception_handling'

        tmp = '%%invoke.tmp.%d' % self.invoke_count
        exc = '%%invoke.exc.%d' % self.invoke_count
        self.invoke_count += 1

        # XXX Hardcoded type...
        type_ = "%RPYTHON_EXCEPTION_VTABLE*"

        codewriter.call(targetvar, returntype, functionref, argtypes, argrefs)
        codewriter.load(tmp, type_, "%last_exception_type")
        codewriter.binaryop("seteq", exc, type_, tmp, "null")
        codewriter.br(exc, exc_label, none_label)

        # write exception handling blocks
        
        e = self.db.translator.rtyper.getexceptiondata()
        ll_exception_match = self.db.repr_value(e.fn_exception_match._obj)        
        lltype_of_exception_type = self.db.repr_type(e.lltype_of_exception_type)
        lltype_of_exception_value = self.db.repr_type(e.lltype_of_exception_value)
        
        # start with the exception handling block
        # * load the last exception type
        # * check it with call to ll_exception_match()
        # * branch to to correct block?
        
        codewriter.label(exc_label)

        catch_all = False
        found_blocks_info = []
        last_exception_type = None

        # XXX tmp - debugging info 

        # block_label = "block28"
        # exc_label = "block28_exception_handling"
        # ll_exception_match = function for catching exception
        # lltype_of_exception_type, lltype_of_exception_value = generic
        # catch_all = ???
        # found_blocks_info = list of found block data to write those blocks 
        # last_exception_type = Load exception pointer once for handle and not found blocks

        # link = iteration thru rest of links in block 
        # etype = node for exception
        # current_exception_type = repr for node etype
        # target = label of the destination block 
        # exc_found_label = label of intermediate exc found block
        # last_exc_type_var = ????
        # last_exc_value_var = ???
        
        for link in block.exits[1:]:
            assert issubclass(link.exitcase, Exception)

            # information for found blocks
            target = node.block_to_name[link.target]
            exc_found_label = block_label + '_exception_found_branchto_' + target
            link_exc_type = repr_if_variable(self.db, link.last_exception)
            link_exc_value = repr_if_variable(self.db, link.last_exc_value)
            found_blocks_info.append((exc_found_label, target,
                                      link_exc_type, link_exc_value))

            # XXX fix database to handle this case
            etype = self.db.obj2node[link.llexitcase._obj]
            current_exception_type = etype.get_ref()
            not_this_exception_label = block_label + '_not_exception_' + etype.ref[1:]

            # catch specific exception (class) type

            # load pointer only once
            if not last_exception_type:
                last_exception_type = self.db.repr_tmpvar()
                codewriter.load(last_exception_type,
                                lltype_of_exception_type,
                                '%last_exception_type')
                codewriter.newline()

            ll_issubclass_cond = self.db.repr_tmpvar()

            codewriter.call(ll_issubclass_cond,
                            'bool',
                            ll_exception_match,
                            [lltype_of_exception_type, lltype_of_exception_type],
                            [last_exception_type, current_exception_type])

            codewriter.br(ll_issubclass_cond,
                          not_this_exception_label,
                          exc_found_label)

            codewriter.label(not_this_exception_label)

        if not catch_all:
            self.reraise(node, codewriter)

        self.fetch_exceptions(codewriter,
                              found_blocks_info,
                              lltype_of_exception_type,
                              lltype_of_exception_value)

    def write_exceptblock(self, funcnode, codewriter, block):
        """ Raises an exception - called from FuncNode """
        
        assert len(block.inputargs) == 2

        returntype, name, dummy = funcnode.getdecl_parts()

        funcnode.write_block_phi_nodes(codewriter, block)

        inputargs = funcnode.db.repr_arg_multi(block.inputargs)
        inputargtypes = funcnode.db.repr_arg_type_multi(block.inputargs)

        codewriter.store(inputargtypes[0], inputargs[0], '%last_exception_type')
        codewriter.store(inputargtypes[1], inputargs[1], '%last_exception_value')
        codewriter.ret(returntype, self._noresult2(returntype))

    def fetch_exceptions(self, codewriter, exc_found_labels,
                         lltype_of_exception_type, lltype_of_exception_value):

        for (label, target,
             last_exc_type_var, last_exc_value_var) in exc_found_labels:

            codewriter.label(label)
            if last_exc_type_var:    
                codewriter.load(last_exc_type_var,
                                lltype_of_exception_type,
                                '%last_exception_type')
            if last_exc_value_var:   
                codewriter.load(last_exc_value_var,
                                lltype_of_exception_value,
                                '%last_exception_value')
            codewriter.store(lltype_of_exception_type,
                             'null',
                             '%last_exception_type')
            codewriter.store(lltype_of_exception_value,
                             'null',
                             '%last_exception_value')
            codewriter.br_uncond(target)

    def reraise(self, funcnode, codewriter):
        returntype, name, dummy = funcnode.getdecl_parts()
        codewriter.ret(returntype, self._noresult2(returntype))

    def llc_options(self):
    	import sys
    	if sys.platform == 'linux2' and sys.maxint == 2**63-1:
            s = '-enable-ia64-dag-isel'
	else:
            s = ''
        return s
    

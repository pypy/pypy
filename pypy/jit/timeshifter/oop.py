from pypy.rpython.lltypesystem import lltype
from pypy.rpython import rgenop
from pypy.jit.timeshifter.rcontainer import cachedtype
from pypy.jit.timeshifter import rvalue


class Index:
    def __init__(self, n):
        self.n = n


class OopSpecDesc:
    __metaclass__ = cachedtype

    def __init__(self, fnobj):
        ll_func = fnobj._callable
        FUNCTYPE = lltype.typeOf(fnobj)
        nb_args = len(FUNCTYPE.ARGS)

        # parse the oopspec and fill in the arguments
        operation_name, args = ll_func.oopspec.split('(', 1)
        assert args.endswith(')')
        args = args[:-1] + ','     # trailing comma to force tuple syntax
        argnames = ll_func.func_code.co_varnames[:nb_args]
        d = dict(zip(argnames, [Index(n) for n in range(nb_args)]))
        self.argtuple = eval(args, d)
        # end of rather XXX'edly hackish parsing

        self.argpositions = []
        for i, obj in enumerate(self.argtuple):
            if isinstance(obj, Index):
                self.argpositions.append(obj.n + 1)
            else:
                self.argpositions.append(0)

        for i in range(nb_args):
            ARGTYPE = FUNCTYPE.ARGS[i]
            assert ((i+1) in self.argpositions) == (ARGTYPE is not lltype.Void)

        self.args_gv = [rgenop.placeholder(None)] * nb_args
        self.args_gv.insert(0, rgenop.genconst(fnobj._as_ptr()))
        self.gv_result_type = rgenop.constTYPE(FUNCTYPE.RESULT)
        self.redboxbuilder = rvalue.ll_redboxbuilder(FUNCTYPE.RESULT)

        if operation_name == 'newlist':
            from pypy.jit.timeshifter.vlist import ListTypeDesc, oop_newlist
            self.typedesc = ListTypeDesc(FUNCTYPE.RESULT.TO)
            self.ll_handler = oop_newlist
        else:
            typename, method = operation_name.split('.')
            method = 'oop_%s_%s' % (typename, method)
            vmodule = __import__('pypy.jit.timeshifter.v%s' % (typename,),
                                 None, None, [method])
            self.ll_handler = getattr(vmodule, method)

    def residual_call(self, jitstate, argboxes):
        args_gv = self.args_gv[:]
        argpositions = self.argpositions
        for i in range(len(argpositions)):
            pos = argpositions[i]
            if pos > 0:
                gv_arg = argboxes[i].getgenvar(jitstate)
                args_gv[pos] = gv_arg
        gv_result = rgenop.genop(jitstate.curblock,
                                 'direct_call',
                                 args_gv,
                                 self.gv_result_type)
        return self.redboxbuilder(self.gv_result_type, gv_result)

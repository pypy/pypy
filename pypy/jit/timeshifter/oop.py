from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.jit.timeshifter.rcontainer import cachedtype
from pypy.jit.timeshifter import rvalue, rtimeshift
from pypy.translator.c import exceptiontransform


class Index:
    def __init__(self, n):
        self.n = n


class OopSpecDesc:
    __metaclass__ = cachedtype

    def __init__(self, hrtyper, fnobj):
        ll_func = fnobj._callable
        FUNCTYPE = lltype.typeOf(fnobj)
        nb_args = len(FUNCTYPE.ARGS)

        # parse the oopspec and fill in the arguments
        operation_name, args = ll_func.oopspec.split('(', 1)
        assert args.endswith(')')
        args = args[:-1] + ','     # trailing comma to force tuple syntax
        if args.strip() == ',':
            args = '()'
        argnames = ll_func.func_code.co_varnames[:nb_args]
        d = dict(zip(argnames, [Index(n) for n in range(nb_args)]))
        self.argtuple = eval(args, d)
        # end of rather XXX'edly hackish parsing

        self.argpositions = []
        for i, obj in enumerate(self.argtuple):
            if isinstance(obj, Index):
                self.argpositions.append(obj.n)
            else:
                self.argpositions.append(-1)

        for i in range(nb_args):
            ARGTYPE = FUNCTYPE.ARGS[i]
            assert (i in self.argpositions) == (ARGTYPE is not lltype.Void)

        RGenOp = hrtyper.RGenOp
        self.args_gv = [None] * nb_args
        self.gv_fnptr = RGenOp.constPrebuiltGlobal(fnobj._as_ptr())
        self.result_kind = RGenOp.kindToken(FUNCTYPE.RESULT)
        if FUNCTYPE.RESULT is lltype.Void:
            self.errorbox = None
        else:
            error_value = exceptiontransform.error_value(FUNCTYPE.RESULT)
            self.errorbox = rvalue.redbox_from_prebuilt_value(RGenOp,
                                                              error_value)
        self.redboxbuilder = rvalue.ll_redboxbuilder(FUNCTYPE.RESULT)
        self.sigtoken = RGenOp.sigToken(FUNCTYPE)

        if operation_name == 'newlist':
            typename, method = 'list', 'oop_newlist'
            SELFTYPE = FUNCTYPE.RESULT.TO
            self.is_method = False
        elif operation_name == 'newdict':
            typename, method = 'dict', 'oop_newdict'
            SELFTYPE = FUNCTYPE.RESULT.TO
            self.is_method = False
        else:
            typename, method = operation_name.split('.')
            method = 'oop_%s_%s' % (typename, method)
            SELFTYPE = FUNCTYPE.ARGS[self.argpositions[0]].TO
            self.is_method = True

        vmodule = __import__('pypy.jit.timeshifter.v%s' % (typename,),
                             None, None, [method])
        self.typedesc = vmodule.TypeDesc(hrtyper, SELFTYPE)
        self.ll_handler = getattr(vmodule, method)

        # exception handling
        graph = fnobj.graph
        etrafo = hrtyper.etrafo
        self.can_raise = etrafo.raise_analyzer.analyze_direct_call(graph)
        self.fetch_global_excdata = hrtyper.fetch_global_excdata

    def residual_call(self, jitstate, argboxes):
        builder = jitstate.curbuilder
        args_gv = self.args_gv[:]
        argpositions = self.argpositions
        for i in range(len(argpositions)):
            pos = argpositions[i]
            if pos >= 0:
                gv_arg = argboxes[i].getgenvar(builder)
                args_gv[pos] = gv_arg
        gv_result = builder.genop_call(self.sigtoken, self.gv_fnptr, args_gv)
        if self.can_raise:
            self.fetch_global_excdata(jitstate)
        return self.redboxbuilder(self.result_kind, gv_result)

    def residual_exception(self, jitstate, ExcCls):
        ll_evalue = get_ll_instance_for_exccls(ExcCls)
        ll_etype  = ll_evalue.typeptr
        etypebox  = rvalue.ll_fromvalue(jitstate, ll_etype)
        evaluebox = rvalue.ll_fromvalue(jitstate, ll_evalue)
        rtimeshift.setexctypebox (jitstate, etypebox )
        rtimeshift.setexcvaluebox(jitstate, evaluebox)
        return self.errorbox
    residual_exception._annspecialcase_ = 'specialize:arg(2)'


def get_ll_instance_for_exccls(ExcCls):
    raise NotImplementedError

class Entry(ExtRegistryEntry):
    _about_ = get_ll_instance_for_exccls

    def compute_result_annotation(self, s_exccls):
        from pypy.annotation import model as annmodel
        assert s_exccls.is_constant()
        bk = self.bookkeeper
        excdata = bk.annotator.policy.rtyper.exceptiondata
        return annmodel.lltype_to_annotation(excdata.lltype_of_exception_value)

    def specialize_call(self, hop):
        ExcCls = hop.args_s[0].const
        rtyper = hop.rtyper
        bk = rtyper.annotator.bookkeeper
        clsdef = bk.getuniqueclassdef(ExcCls)
        excdata = rtyper.exceptiondata
        ll_evalue = excdata.get_standard_ll_exc_instance(rtyper, clsdef)
        return hop.inputconst(hop.r_result, ll_evalue)

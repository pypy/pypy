from pypy.rpython.lltypesystem import lltype
from pypy.rpython.extregistry import ExtRegistryEntry
from pypy.jit.timeshifter.rcontainer import cachedtype
from pypy.jit.timeshifter import rvalue, rtimeshift
from pypy.translator.c import exceptiontransform
from pypy.rlib.unroll import unrolling_iterable


class Index:
    def __init__(self, n):
        self.n = n


class OopSpecDesc:
    __metaclass__ = cachedtype

    do_call = None

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

        arg_llsig_to_oopsig = {}
        for i, obj in enumerate(self.argtuple):
            if isinstance(obj, Index):
                arg_llsig_to_oopsig[obj.n] = i

        self.residualargsources = []
        for i in range(nb_args):
            ARGTYPE = FUNCTYPE.ARGS[i]
            if ARGTYPE is not lltype.Void:
                self.residualargsources.append(arg_llsig_to_oopsig[i])

        RGenOp = hrtyper.RGenOp
        self.args_gv = [None] * nb_args
        fnptr = fnobj._as_ptr()
        self.gv_fnptr = RGenOp.constPrebuiltGlobal(fnptr)
        result_kind = RGenOp.kindToken(FUNCTYPE.RESULT)
        self.result_kind = result_kind
        if FUNCTYPE.RESULT is lltype.Void:
            self.errorbox = None
        else:
            error_value = exceptiontransform.error_value(FUNCTYPE.RESULT)
            self.errorbox = rvalue.redbox_from_prebuilt_value(RGenOp,
                                                              error_value)
        redboxbuilder = rvalue.ll_redboxbuilder(FUNCTYPE.RESULT)
        self.redboxbuilder = redboxbuilder
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
            SELFTYPE = FUNCTYPE.ARGS[self.argtuple[0].n].TO
            self.is_method = True

        vmodule = __import__('pypy.jit.timeshifter.v%s' % (typename,),
                             None, None, [method])
        self.typedesc = vmodule.TypeDesc(hrtyper, SELFTYPE)
        self.ll_handler = getattr(vmodule, method)
        self.couldfold = getattr(self.ll_handler, 'couldfold', False)

        # exception handling
        graph = fnobj.graph
        etrafo = hrtyper.etrafo
        self.can_raise = etrafo.raise_analyzer.analyze_direct_call(graph)
        self.fetch_global_excdata = hrtyper.fetch_global_excdata

        if self.couldfold:
            ARGS = FUNCTYPE.ARGS
            residualargsources = self.residualargsources
            unrolling_ARGS = unrolling_iterable(ARGS)

            def do_call(jitstate, argboxes):
                args = ()
                j = 0
                for ARG in unrolling_ARGS:
                    if ARG == lltype.Void:
                        v = None
                    else:
                        argsrc = residualargsources[j]
                        j = j + 1
                        v = rvalue.ll_getvalue(argboxes[argsrc], ARG)
                    args += (v,)
                result = fnptr(*args)
                if FUNCTYPE.RESULT == lltype.Void:
                    return None
                return rvalue.ll_fromvalue(jitstate, result)

            self.do_call = do_call

        # hack! to avoid confusion between the .typedesc attribute
        # of oopspecdescs of different types (lists, dicts, etc.)
        # let's use different subclasses for the oopspecdesc too.
        self.__class__ = globals()['OopSpecDesc_%s' % typename]

    def residual_call(self, jitstate, argboxes, deepfrozen=False):
        builder = jitstate.curbuilder
        args_gv = []
        fold = deepfrozen
        for argsrc in self.residualargsources:
            gv_arg = argboxes[argsrc].getgenvar(jitstate)
            args_gv.append(gv_arg)
            fold &= gv_arg.is_const
        if fold:
            try:
                return self.do_call(jitstate, argboxes)
            except Exception, e:
                jitstate.residual_exception(e)
                return self.errorbox
        gv_result = builder.genop_call(self.sigtoken, self.gv_fnptr, args_gv)
        if self.can_raise:
            self.fetch_global_excdata(jitstate)
        return self.redboxbuilder(self.result_kind, gv_result)

    def residual_exception(self, jitstate, ExcCls):
        ll_evalue = get_ll_instance_for_exccls(ExcCls)
        jitstate.residual_ll_exception(ll_evalue)
        return self.errorbox
    residual_exception._annspecialcase_ = 'specialize:arg(2)'


class OopSpecDesc_list(OopSpecDesc):
    pass

class OopSpecDesc_dict(OopSpecDesc):
    pass


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

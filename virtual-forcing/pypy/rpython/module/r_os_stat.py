"""
RTyping support for os.stat_result objects.
They are rtyped just like a tuple of the correct length supporting
only indexing and the st_xxx attributes.  We need a custom StatResultRepr
because when rtyping for LL backends we have extra platform-dependent
items at the end of the tuple, but for OO backends we only want the
portable items.  This allows the OO backends to assume a fixed shape for
the tuples returned by os.stat().
"""
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.tool.pairtype import pairtype
from pypy.rpython.rmodel import Repr, IntegerRepr
from pypy.rpython.error import TyperError
from pypy.rpython.module import ll_os_stat


class StatResultRepr(Repr):

    def __init__(self, rtyper):
        self.rtyper = rtyper
        if rtyper.type_system.name == "lltypesystem":
            self.stat_fields = ll_os_stat.STAT_FIELDS
        else:
            self.stat_fields = ll_os_stat.PORTABLE_STAT_FIELDS

        self.stat_field_indexes = {}
        for i, (name, TYPE) in enumerate(self.stat_fields):
            self.stat_field_indexes[name] = i

        self.s_tuple = annmodel.SomeTuple([annmodel.lltype_to_annotation(TYPE)
                                           for name, TYPE in self.stat_fields])
        self.r_tuple = rtyper.getrepr(self.s_tuple)
        self.lowleveltype = self.r_tuple.lowleveltype

    def redispatch_getfield(self, hop, index):
        rtyper = self.rtyper
        s_index = rtyper.annotator.bookkeeper.immutablevalue(index)
        hop2 = hop.copy()
        hop2.forced_opname = 'getitem'
        hop2.args_v = [hop2.args_v[0], Constant(index)]
        hop2.args_s = [self.s_tuple, s_index]
        hop2.args_r = [self.r_tuple, rtyper.getrepr(s_index)]
        return hop2.dispatch()

    def rtype_getattr(self, hop):
        s_attr = hop.args_s[1]
        attr = s_attr.const
        try:
            index = self.stat_field_indexes[attr]
        except KeyError:
            raise TyperError("os.stat().%s: field not available" % (attr,))
        return self.redispatch_getfield(hop, index)


class __extend__(pairtype(StatResultRepr, IntegerRepr)):

    def rtype_getitem((r_sta, r_int), hop):
        s_int = hop.args_s[1]
        index = s_int.const
        return r_sta.redispatch_getfield(hop, index)


def specialize_make_stat_result(hop):
    r_StatResult = hop.rtyper.getrepr(ll_os_stat.s_StatResult)
    [v_result] = hop.inputargs(r_StatResult.r_tuple)
    # no-op conversion from r_StatResult.r_tuple to r_StatResult
    return v_result

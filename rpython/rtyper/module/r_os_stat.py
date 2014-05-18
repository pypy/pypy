"""
RTyping support for os.stat_result objects.
They are rtyped just like a tuple of the correct length supporting
only indexing and the st_xxx attributes.  We need a custom StatResultRepr
because when rtyping for LL backends we have extra platform-dependent
items at the end of the tuple, but for OO backends we only want the
portable items.  This allows the OO backends to assume a fixed shape for
the tuples returned by os.stat().
"""
from rpython.annotator import model as annmodel
from rpython.rtyper.llannotation import lltype_to_annotation
from rpython.flowspace.model import Constant
from rpython.tool.pairtype import pairtype
from rpython.rtyper.rmodel import Repr, IntegerRepr
from rpython.rtyper.error import TyperError
from rpython.rtyper.module import ll_os_stat


class StatResultRepr(Repr):

    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.stat_fields = ll_os_stat.STAT_FIELDS

        self.stat_field_indexes = {}
        for i, (name, TYPE) in enumerate(self.stat_fields):
            self.stat_field_indexes[name] = i

        self.s_tuple = annmodel.SomeTuple([lltype_to_annotation(TYPE)
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
    hop.exception_cannot_occur()
    return v_result


class StatvfsResultRepr(Repr):

    def __init__(self, rtyper):
        self.rtyper = rtyper
        self.statvfs_fields = ll_os_stat.STATVFS_FIELDS

        self.statvfs_field_indexes = {}
        for i, (name, TYPE) in enumerate(self.statvfs_fields):
            self.statvfs_field_indexes[name] = i

        self.s_tuple = annmodel.SomeTuple([lltype_to_annotation(TYPE)
                                           for name, TYPE in self.statvfs_fields])
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
            index = self.statvfs_field_indexes[attr]
        except KeyError:
            raise TyperError("os.statvfs().%s: field not available" % (attr,))
        return self.redispatch_getfield(hop, index)


class __extend__(pairtype(StatvfsResultRepr, IntegerRepr)):
    def rtype_getitem((r_sta, r_int), hop):
        s_int = hop.args_s[1]
        index = s_int.const
        return r_sta.redispatch_getfield(hop, index)


def specialize_make_statvfs_result(hop):
    r_StatvfsResult = hop.rtyper.getrepr(ll_os_stat.s_StatvfsResult)
    [v_result] = hop.inputargs(r_StatvfsResult.r_tuple)
    hop.exception_cannot_occur()
    return v_result

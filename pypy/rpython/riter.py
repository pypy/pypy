from pypy.annotation.pairtype import pair, pairtype
from pypy.annotation.model import SomeIterator, SomeList
from pypy.rpython.lltype import *


class __extend__(SomeIterator):

    def getiteratorkind(s_itr):
        s_cont = s_itr.s_container
        if isinstance(s_cont, SomeList):
            if not s_cont.ll_range_step():
                return PlainListIterator
            else:
                return RangeIterator
        else:
            raise TyperError("not implemented yet")

    def lowleveltype(s_itr):
        kind = s_itr.getiteratorkind()
        return kind.lowlevelitertype(s_itr.s_container)

    def rtype_next(s_itr, hop):
        v_itr, = hop.inputargs(s_itr)
        kind = s_itr.getiteratorkind()
        return kind.next(v_itr, hop)

# ____________________________________________________________

class Namespace(object):
    def __init__(self, name, bases, dict):
        assert not bases
        self.__dict__.update(dict)


class PlainListIterator:
    """__________ regular list iterator __________"""
    __metaclass__ = Namespace

    def lowlevelitertype(s_lst):
        return GcPtr(GcStruct('listiter', ('list', s_lst.lowleveltype()),
                                          ('index', Signed)))

    def ll_listiter(ITERPTR, lst):
        iter = malloc(ITERPTR.TO)
        iter.list = lst
        iter.index = 0
        return iter

    def rtype_new_iter(hop):
        s_lst, = hop.args_s
        v_lst, = hop.inputargs(s_lst)
        ITERPTR = PlainListIterator.lowlevelitertype(s_lst)
        citerptr = hop.inputconst(Void, ITERPTR)
        return hop.gendirectcall(PlainListIterator.ll_listiter, citerptr, v_lst)

    def next(v_itr, hop):
        XXX - NotImplementedYet

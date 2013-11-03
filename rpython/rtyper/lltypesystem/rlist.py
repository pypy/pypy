from rpython.rlib import rgc, jit, types
from rpython.rlib.debug import ll_assert
from rpython.rlib.signature import signature
from rpython.rtyper.lltypesystem import rstr
from rpython.rtyper.lltypesystem.lltype import (GcForwardReference, Ptr, GcArray,
     GcStruct, Void, Signed, malloc, typeOf, nullptr, typeMethod)
from rpython.rtyper.rlist import (AbstractBaseListRepr, AbstractListRepr,
    AbstractFixedSizeListRepr, AbstractListIteratorRepr, ll_setitem_nonneg,
    ADTIList, ADTIFixedList, dum_nocheck)
from rpython.rtyper.rmodel import Repr, inputconst, externalvsinternal
from rpython.tool.pairtype import pairtype, pair


# ____________________________________________________________
#
#  The concrete implementation of resized RPython lists is as a GcStruct
#  with only one field: a pointer to an overallocated array of items.
#  This overallocated array is a C-like array in memory preceded by
#  three fields: the GC header, 'allocated_length', and 'used_length'.
#  In the array part, each item contains a primitive value or pointer
#  to the actual list item.
#
#  For fixed-size lists, we just use a GcArray, which has only one
#  'length' after the GC header.
#

class BaseListRepr(AbstractBaseListRepr):
    rstr_ll = rstr.LLHelpers

    def __init__(self, rtyper, item_repr, listitem=None):
        self.rtyper = rtyper
        self.LIST = GcForwardReference()
        self.lowleveltype = Ptr(self.LIST)
        if not isinstance(item_repr, Repr):  # not computed yet, done by setup()
            assert callable(item_repr)
            self._item_repr_computer = item_repr
        else:
            self.external_item_repr, self.item_repr = externalvsinternal(rtyper, item_repr)
        self.listitem = listitem
        self.list_cache = {}
        # setup() needs to be called to finish this initialization

    def null_const(self):
        return nullptr(self.LIST)

    def get_eqfunc(self):
        return inputconst(Void, self.item_repr.get_ll_eq_function())

    def make_iterator_repr(self, *variant):
        if not variant:
            return ListIteratorRepr(self)
        elif variant == ("reversed",):
            return ReversedListIteratorRepr(self)
        else:
            raise NotImplementedError(variant)

    def get_itemarray_lowleveltype(self, overallocated):
        ITEM = self.item_repr.lowleveltype
        hints = {}
        if overallocated:
            hints['overallocated'] = True
        ITEMARRAY = GcArray(ITEM,
                            adtmeths = ADTIFixedList({
                                 "ll_newlist": ll_fixed_newlist,
                                 "ll_newemptylist": ll_fixed_newemptylist,
                                 "ll_length": ll_fixed_length,
                                 "ll_items": ll_fixed_items,
                                 "ITEM": ITEM,
                                 "ll_getitem_fast": ll_fixed_getitem_fast,
                                 "ll_setitem_fast": ll_fixed_setitem_fast,
                            }),
                            hints = hints)
        return ITEMARRAY


class __extend__(pairtype(BaseListRepr, BaseListRepr)):
    def rtype_is_((r_lst1, r_lst2), hop):
        if r_lst1.lowleveltype != r_lst2.lowleveltype:
            # obscure logic, the is can be true only if both are None
            v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
            return hop.gendirectcall(ll_both_none, v_lst1, v_lst2)

        return pairtype(Repr, Repr).rtype_is_(pair(r_lst1, r_lst2), hop)


class ListRepr(AbstractListRepr, BaseListRepr):

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = externalvsinternal(self.rtyper, self._item_repr_computer())
        if isinstance(self.LIST, GcForwardReference):
            ITEM = self.item_repr.lowleveltype
            ITEMARRAY = self.get_itemarray_lowleveltype(True)
            # XXX we might think of turning length stuff into Unsigned
            self.LIST.become(GcStruct("list", ("items", Ptr(ITEMARRAY)),
                                      adtmeths = ADTIList({
                                          "ll_newlist": ll_newlist,
                                          "ll_newlist_hint": ll_newlist_hint,
                                          "ll_newemptylist": ll_newemptylist,
                                          "ll_length": ll_length,
                                          "ll_items": ll_items,
                                          "ITEM": ITEM,
                                          "ll_getitem_fast": ll_getitem_fast,
                                          "ll_setitem_fast": ll_setitem_fast,
                                          "_ll_resize_ge": _ll_list_resize_ge,
                                          "_ll_resize_le": _ll_list_resize_le,
                                          "_ll_resize": _ll_list_resize,
                                          "_ll_resize_hint": _ll_list_resize_hint,
                                      }),
                                      hints = {'list': True})
                             )

    def compact_repr(self):
        return 'ListR %s' % (self.item_repr.compact_repr(),)

    def prepare_const(self, n):
        result = malloc(self.LIST, immortal=True)
        result.items = malloc(self.LIST.items.TO, n)
        result.items.used_length = n
        return result


class FixedSizeListRepr(AbstractFixedSizeListRepr, BaseListRepr):

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = externalvsinternal(self.rtyper, self._item_repr_computer())
        if isinstance(self.LIST, GcForwardReference):
            ITEMARRAY = self.get_itemarray_lowleveltype(overallocated=False)
            self.LIST.become(ITEMARRAY)

    def compact_repr(self):
        return 'FixedSizeListR %s' % (self.item_repr.compact_repr(),)

    def prepare_const(self, n):
        result = malloc(self.LIST, n, immortal=True)
        return result


# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

# adapted C code

@jit.look_inside_iff(lambda l, newsize, overallocate:
                     jit.isconstant(l.items.allocated_length) and
                     jit.isconstant(newsize))
@signature(types.any(), types.int(), types.bool(), returns=types.none())
def _ll_list_resize_hint_really(l, newsize, overallocate):
    """
    Ensure l.items has room for at least newsize elements.  Note that
    l.items may change, and even if newsize is less than used_length on
    entry.
    """
    # This over-allocates proportional to the list size, making room
    # for additional growth.  The over-allocation is eager for small
    # lists, and mild for large ones (but enough to give linear-time
    # amortized behavior over a long sequence of appends()).
    #
    # The idea is that small lists exist in the nursery; if they
    # survive, they will be copied out of it by the GC, which will
    # reduce their allocated_length down to their used_length.
    #
    # The growth pattern is:
    #      0, 8, 16, 32,  (doubling region, adding 'newsize')
    #      48, 72, 108,   (adding 'newsize >> 1')
    #      135, 168, 210, (adding 'newsize >> 2')
    #      236, ...       (adding 'newsize >> 3' from now on)
    if newsize <= 0:
        ll_assert(newsize == 0, "negative list length")
        l.items = _ll_new_empty_item_array(typeOf(l).TO)
        return
    elif overallocate:
        if newsize <= 4:
            new_allocated = 8
        elif newsize < 32:
            new_allocated = newsize + newsize
        elif newsize < 128:
            new_allocated = newsize + (newsize >> 1)
        elif newsize < 224:
            new_allocated = newsize + (newsize >> 2)
        else:
            new_allocated = newsize + (newsize >> 3)
    else:
        new_allocated = newsize
    # new_allocated is a bit more than newsize, enough to ensure an amortized
    # linear complexity for e.g. repeated usage of l.append().  In case
    # it overflows sys.maxint, it is guaranteed negative, and the following
    # malloc() will fail.
    newitems = malloc(typeOf(l).TO.items.TO, new_allocated)
    items = l.items
    before_len = items.used_length
    if before_len:   # avoids copying GC flags from the prebuilt_empty_array
        p = min(before_len, newsize)
        newitems.used_length = p
        rgc.ll_arraycopy(items, newitems, 0, 0, p)
    l.items = newitems

@jit.look_inside_iff(lambda l, newsize:
                     jit.isconstant(l.items.allocated_length) and
                     jit.isconstant(newsize))
def _ll_list_resize_hint(l, newsize):
    """Ensure l.items has room for at least newsize elements without
    setting used_length to newsize.

    Used before (and after) a batch operation that will likely grow the
    list to the newsize (and after the operation incase the initial
    guess lied).
    """
    assert newsize >= 0, "negative list length"
    allocated = l.items.allocated_length
    if newsize > allocated:
        overallocate = True
    elif newsize < (allocated >> 1) - 5:
        overallocate = False
    else:
        return
    _ll_list_resize_hint_really(l, newsize, overallocate)

@signature(types.any(), types.int(), types.bool(), returns=types.none())
def _ll_list_resize_really(l, newsize, overallocate):
    """
    Ensure l.items has room for at least newsize elements, and set
    used_length to newsize.  Note that l.items may change, and even if
    newsize is less than used_length on entry.
    """
    _ll_list_resize_hint_really(l, newsize, overallocate)
    l.items.used_length = newsize

# this common case was factored out of _ll_list_resize
# to see if inlining it gives some speed-up.

@jit.dont_look_inside
def _ll_list_resize(l, newsize):
    """Called only in special cases.  Forces the allocated and actual size
    of the list to be 'newsize'."""
    _ll_list_resize_really(l, newsize, False)


def _ll_list_resize_ge(l, newsize):
    """This is called with 'newsize' larger than the current length of the
    list.  If the list storage doesn't have enough space, then really perform
    a realloc().  In the common case where we already overallocated enough,
    then this is a very fast operation.
    """
    allocated = l.items.allocated_length
    cond = allocated < newsize
    if jit.isconstant(allocated) and jit.isconstant(newsize):
        if cond:
            _ll_list_resize_hint_really(l, newsize, True)
    else:
        jit.conditional_call(cond,
                             _ll_list_resize_hint_really, l, newsize, True)
    l.items.used_length = newsize

def _ll_list_resize_le(l, newsize):
    """This is called with 'newsize' smaller than the current length of the
    list.  If 'newsize' falls lower than half the allocated size, proceed
    with the realloc() to shrink the list.
    """
    cond = newsize < (l.items.allocated_length >> 1) - 5
    # note: overallocate=False should be safe here
    if jit.isconstant(l.items.allocated_length) and jit.isconstant(newsize):
        if cond:
            _ll_list_resize_hint_really(l, newsize, False)
    else:
        jit.conditional_call(cond, _ll_list_resize_hint_really, l, newsize,
                             False)
    l.items.used_length = newsize


def ll_both_none(lst1, lst2):
    return not lst1 and not lst2


# ____________________________________________________________
#
#  Accessor methods

def ll_newlist(LIST, length):
    ll_assert(length >= 0, "negative list length")
    l = malloc(LIST)
    items = malloc(LIST.items.TO, length)
    items.used_length = length
    l.items = items
    return l
ll_newlist = typeMethod(ll_newlist)
ll_newlist.oopspec = 'newlist(length)'

def ll_newlist_hint(LIST, lengthhint):
    ll_assert(lengthhint >= 0, "negative list length")
    l = malloc(LIST)
    l.items = malloc(LIST.items.TO, lengthhint)
    return l
ll_newlist_hint = typeMethod(ll_newlist_hint)
ll_newlist_hint.oopspec = 'newlist_hint(lengthhint)'

# should empty lists start with no allocated memory, or with a preallocated
# minimal number of entries?  XXX compare memory usage versus speed, and
# check how many always-empty lists there are in a typical pypy-c run...
INITIAL_EMPTY_LIST_ALLOCATION = 0

def _ll_prebuilt_empty_array(LISTITEM):
    return malloc(LISTITEM, 0)     # memo!
_ll_prebuilt_empty_array._annspecialcase_ = 'specialize:memo'

def _ll_new_empty_item_array(LIST):
    if INITIAL_EMPTY_LIST_ALLOCATION > 0:
        return malloc(LIST.items.TO, INITIAL_EMPTY_LIST_ALLOCATION)
    else:
        return _ll_prebuilt_empty_array(LIST.items.TO)

def ll_newemptylist(LIST):
    l = malloc(LIST)
    l.items = _ll_new_empty_item_array(LIST)
    return l
ll_newemptylist = typeMethod(ll_newemptylist)
ll_newemptylist.oopspec = 'newlist(0)'

def ll_length(l):
    return l.items.used_length
ll_length.oopspec = 'list.len(l)'

def ll_items(l):
    return l.items

def ll_getitem_fast(l, index):
    ll_assert(index < l.ll_length(), "getitem out of bounds")
    return l.ll_items()[index]
ll_getitem_fast.oopspec = 'list.getitem(l, index)'

def ll_setitem_fast(l, index, item):
    ll_assert(index < l.ll_length(), "setitem out of bounds")
    l.ll_items()[index] = item
ll_setitem_fast.oopspec = 'list.setitem(l, index, item)'

# fixed size versions

@typeMethod
def ll_fixed_newlist(LIST, length):
    ll_assert(length >= 0, "negative fixed list length")
    l = malloc(LIST, length)
    return l
ll_fixed_newlist.oopspec = 'newlist(length)'

@typeMethod
def ll_fixed_newemptylist(LIST):
    return ll_fixed_newlist(LIST, 0)

def ll_fixed_length(l):
    return len(l)
ll_fixed_length.oopspec = 'list.len(l)'

def ll_fixed_items(l):
    return l

def ll_fixed_getitem_fast(l, index):
    ll_assert(index < len(l), "fixed getitem out of bounds")
    return l[index]
ll_fixed_getitem_fast.oopspec = 'list.getitem(l, index)'

def ll_fixed_setitem_fast(l, index, item):
    ll_assert(index < len(l), "fixed setitem out of bounds")
    l[index] = item
ll_fixed_setitem_fast.oopspec = 'list.setitem(l, index, item)'

def newlist(llops, r_list, items_v, v_sizehint=None):
    LIST = r_list.LIST
    if len(items_v) == 0:
        if v_sizehint is None:
            v_result = llops.gendirectcall(LIST.ll_newemptylist)
        else:
            v_result = llops.gendirectcall(LIST.ll_newlist_hint, v_sizehint)
    else:
        assert v_sizehint is None
        cno = inputconst(Signed, len(items_v))
        v_result = llops.gendirectcall(LIST.ll_newlist, cno)
    v_func = inputconst(Void, dum_nocheck)
    for i, v_item in enumerate(items_v):
        ci = inputconst(Signed, i)
        llops.gendirectcall(ll_setitem_nonneg, v_func, v_result, ci, v_item)
    return v_result

# ____________________________________________________________
#
#  Iteration.

class ListIteratorRepr(AbstractListIteratorRepr):

    def __init__(self, r_list):
        self.r_list = r_list
        self.external_item_repr = r_list.external_item_repr
        self.lowleveltype = Ptr(GcStruct('listiter',
                                         ('list', r_list.lowleveltype),
                                         ('index', Signed)))
        self.ll_listiter = ll_listiter
        if (isinstance(r_list, FixedSizeListRepr)
                and not r_list.listitem.mutated):
            self.ll_listnext = ll_listnext_foldable
        else:
            self.ll_listnext = ll_listnext
        self.ll_getnextindex = ll_getnextindex


def ll_listiter(ITERPTR, lst):
    iter = malloc(ITERPTR.TO)
    iter.list = lst
    iter.index = 0
    return iter

def ll_listnext(iter):
    l = iter.list
    index = iter.index
    if index >= l.ll_length():
        raise StopIteration
    iter.index = index + 1      # cannot overflow because index < used_length
    return l.ll_getitem_fast(index)

def ll_listnext_foldable(iter):
    from rpython.rtyper.rlist import ll_getitem_foldable_nonneg
    l = iter.list
    index = iter.index
    if index >= l.ll_length():
        raise StopIteration
    iter.index = index + 1      # cannot overflow because index < used_length
    return ll_getitem_foldable_nonneg(l, index)

def ll_getnextindex(iter):
    return iter.index


class ReversedListIteratorRepr(AbstractListIteratorRepr):
    def __init__(self, r_list):
        self.r_list = r_list
        self.lowleveltype = Ptr(GcStruct('revlistiter',
            ('list', r_list.lowleveltype),
            ('index', Signed),
        ))
        self.ll_listnext = ll_revlistnext
        self.ll_listiter = ll_revlistiter


def ll_revlistiter(ITERPTR, lst):
    iter = malloc(ITERPTR.TO)
    iter.list = lst
    iter.index = lst.ll_length() - 1
    return iter


def ll_revlistnext(iter):
    l = iter.list
    index = iter.index
    if index < 0:
        raise StopIteration
    iter.index -= 1
    return l.ll_getitem_fast(index)

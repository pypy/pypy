from pypy.annotation.pairtype import pairtype, pair
from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IntegerRepr, inputconst
from pypy.rpython.rmodel import IteratorRepr, externalvsinternal
from pypy.rpython.rslice import SliceRepr
from pypy.rpython.rslice import startstop_slice_repr, startonly_slice_repr
from pypy.rpython.rslice import minusone_slice_repr
from pypy.rpython.lltypesystem. lltype import \
     GcForwardReference, Ptr, GcArray, GcStruct, \
     Void, Signed, malloc, typeOf, Primitive, \
     Bool, nullptr, typeMethod
from pypy.rpython import rstr
from pypy.rpython import robject

# ____________________________________________________________
#
#  Concrete implementation of RPython lists:
#
#    struct list {
#        int length;
#        items_array *items;
#    }
#
#    'items' points to a C-like array in memory preceded by a 'length' header,
#    where each item contains a primitive value or pointer to the actual list
#    item.
#
#    or for fixed-size lists an array is directly used:
#
#    item_t list_items[]
#

class __extend__(annmodel.SomeList):
    def rtyper_makerepr(self, rtyper):
        from pypy.rpython import rrange
        listitem = self.listdef.listitem
        s_value = listitem.s_value
        if listitem.range_step is not None and not listitem.mutated:
            return rrange.RangeRepr(listitem.range_step)
        elif (s_value.__class__ is annmodel.SomeObject and s_value.knowntype == object):
            return robject.pyobj_repr
        else:
            # cannot do the rtyper.getrepr() call immediately, for the case
            # of recursive structures -- i.e. if the listdef contains itself
            if self.listdef.listitem.resized:
                return ListRepr(rtyper, lambda: rtyper.getrepr(listitem.s_value),
                                listitem)
            else:
                return FixedSizeListRepr(rtyper, lambda: rtyper.getrepr(listitem.s_value),
                                         listitem)

    def rtyper_makekey(self):
        return self.__class__, self.listdef.listitem


class BaseListRepr(Repr):

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
        self.list_builder = ListBuilder()
        # setup() needs to be called to finish this initialization

    def _setup_repr_final(self):
        self.list_builder.setup(self)

    def recast(self, llops, v):
        return llops.convertvar(v, self.item_repr, self.external_item_repr)

    def convert_const(self, listobj):
        # get object from bound list method
        #listobj = getattr(listobj, '__self__', listobj)
        if listobj is None:
            return nullptr(self.LIST)
        if not isinstance(listobj, list):
            raise TyperError("expected a list: %r" % (listobj,))
        try:
            key = Constant(listobj)
            return self.list_cache[key]
        except KeyError:
            self.setup()
            n = len(listobj)
            result = self.prepare_const(n)
            self.list_cache[key] = result
            r_item = self.item_repr
            items = result.ll_items()
            for i in range(n):
                x = listobj[i]
                items[i] = r_item.convert_const(x)
            return result

    def prepare_const(self, nitems):
        raise NotImplementedError

    def get_eqfunc(self):
        return inputconst(Void, self.item_repr.get_ll_eq_function())

    def rtype_bltn_list(self, hop):
        v_lst = hop.inputarg(self, 0)
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        return hop.gendirectcall(ll_copy, cRESLIST, v_lst)
    
    def rtype_len(self, hop):
        v_lst, = hop.inputargs(self)
        return hop.gendirectcall(ll_len, v_lst)

    def rtype_is_true(self, hop):
        v_lst, = hop.inputargs(self)
        return hop.gendirectcall(ll_list_is_true, v_lst)

    def rtype_method_index(self, hop):
        v_lst, v_value = hop.inputargs(self, self.item_repr)
        hop.has_implicit_exception(ValueError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_listindex, v_lst, v_value, self.get_eqfunc())
    
    def rtype_method_reverse(self, hop):
        v_lst, = hop.inputargs(self)
        hop.exception_cannot_occur()
        hop.gendirectcall(ll_reverse,v_lst)

    def make_iterator_repr(self):
        return ListIteratorRepr(self)

    def ll_str(self, l):
        items = l.ll_items()
        length = l.ll_length()
        item_repr = self.item_repr

        temp = malloc(TEMP, length)
        i = 0
        while i < length:
            temp[i] = item_repr.ll_str(items[i])
            i += 1

        return rstr.ll_strconcat(
            rstr.list_str_open_bracket,
            rstr.ll_strconcat(rstr.ll_join(rstr.list_str_sep,
                                           length,
                                           temp),
                              rstr.list_str_close_bracket))

class ListBuilder(object):
    """Interface to allow lazy list building by the JIT."""
    # This should not keep a reference to the RTyper, even indirectly via
    # the list_repr.

    def setup(self, list_repr):
        # Precompute the c_newitem and c_setitem_nonneg function pointers,
        # needed below.
        if list_repr.rtyper is None:
            return     # only for test_rlist, which doesn't need this anyway
        LIST = list_repr.LIST
        LISTPTR = list_repr.lowleveltype
        ITEM = list_repr.item_repr.lowleveltype
        self.LIST = LIST
        self.LISTPTR = LISTPTR

        argtypes = [Signed]
        fnptr = list_repr.rtyper.annotate_helper_fn(LIST.ll_newlist, argtypes)
        self.c_newlist = inputconst(typeOf(fnptr), fnptr)

        bk = list_repr.rtyper.annotator.bookkeeper
        argtypes = [bk.immutablevalue(dum_nocheck), LISTPTR, Signed, ITEM]
        fnptr = list_repr.rtyper.annotate_helper_fn(ll_setitem_nonneg, argtypes)
        self.c_setitem_nonneg = inputconst(typeOf(fnptr), fnptr)
        self.c_dum_nocheck = inputconst(Void, dum_nocheck)

    def build(self, llop, items_v):
        """Make the operations that would build a list containing the
        provided items."""
        # This is called by the JIT with llop.rtyper == None, so
        # llop.gendirectcall() doesn't work.  Instead, we need to call
        # directly the c_newitem and c_setitem_nonneg precomputed above.
        c_list = inputconst(Void, self.LIST)
        c_len  = inputconst(Signed, len(items_v))
        v_result = llop.genop('direct_call', [self.c_newlist, c_list, c_len],
                              resulttype = self.LISTPTR)
        for i, v in enumerate(items_v):
            llop.genop('direct_call', [self.c_setitem_nonneg,
                                       self.c_dum_nocheck,
                                       v_result, inputconst(Signed, i), v])
        return v_result

class ListRepr(BaseListRepr):

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = externalvsinternal(self.rtyper, self._item_repr_computer())
        if isinstance(self.LIST, GcForwardReference):
            ITEM = self.item_repr.lowleveltype
            ITEMARRAY = GcArray(ITEM)
            # XXX we might think of turning length stuff into Unsigned
            self.LIST.become(GcStruct("list", ("length", Signed),
                                              ("items", Ptr(ITEMARRAY)),
                                      adtmeths = {
                                          "ll_newlist": ll_newlist,
                                          "ll_length": ll_length,
                                          "ll_items": ll_items,
                                          "list_builder": self.list_builder.build,
                                      })
                             )

    def compact_repr(self):
        return 'ListR %s' % (self.item_repr.compact_repr(),)

    def prepare_const(self, n):
        result = malloc(self.LIST, immortal=True)
        result.length = n
        result.items = malloc(self.LIST.items.TO, n)
        return result

    def rtype_method_append(self, hop):
        v_lst, v_value = hop.inputargs(self, self.item_repr)
        hop.exception_cannot_occur()
        hop.gendirectcall(ll_append, v_lst, v_value)

    def rtype_method_insert(self, hop):
        v_lst, v_index, v_value = hop.inputargs(self, Signed, self.item_repr)
        arg1 = hop.args_s[1]
        args = v_lst, v_index, v_value
        if arg1.is_constant() and arg1.const == 0:
            llfn = ll_prepend
            args = v_lst, v_value
        elif arg1.nonneg:
            llfn = ll_insert_nonneg
        else:
            raise TyperError("insert() index must be proven non-negative")
        hop.exception_cannot_occur()
        hop.gendirectcall(llfn, *args)

    def rtype_method_extend(self, hop):
        v_lst1, v_lst2 = hop.inputargs(*hop.args_r)
        hop.exception_cannot_occur()
        hop.gendirectcall(ll_extend, v_lst1, v_lst2)

    def rtype_method_pop(self, hop):
        if hop.has_implicit_exception(IndexError):
            spec = dum_checkidx
        else:
            spec = dum_nocheck
        v_func = hop.inputconst(Void, spec)
        if hop.nb_args == 2:
            args = hop.inputargs(self, Signed)
            assert hasattr(args[1], 'concretetype')
            arg1 = hop.args_s[1]
            if arg1.is_constant() and arg1.const == 0:
                llfn = ll_pop_zero
                args = args[:1]
            elif hop.args_s[1].nonneg:
                llfn = ll_pop_nonneg
            else:
                llfn = ll_pop
        else:
            args = hop.inputargs(self)
            llfn = ll_pop_default
        hop.exception_is_here()
        v_res = hop.gendirectcall(llfn, v_func, *args)
        return self.recast(hop.llops, v_res)

class FixedSizeListRepr(BaseListRepr):

    def _setup_repr(self):
        if 'item_repr' not in self.__dict__:
            self.external_item_repr, self.item_repr = externalvsinternal(self.rtyper, self._item_repr_computer())
        if isinstance(self.LIST, GcForwardReference):
            ITEM = self.item_repr.lowleveltype
            ITEMARRAY = GcArray(ITEM,
                                adtmeths = {
                                     "ll_newlist": ll_fixed_newlist,
                                     "ll_length": ll_fixed_length,
                                     "ll_items": ll_fixed_items,
                                     "list_builder": self.list_builder.build,
                                })

            self.LIST.become(ITEMARRAY)

    def compact_repr(self):
        return 'FixedSizeListR %s' % (self.item_repr.compact_repr(),)

    def prepare_const(self, n):
        result = malloc(self.LIST, n, immortal=True)
        return result

class __extend__(pairtype(BaseListRepr, Repr)):

    def rtype_contains((r_lst, _), hop):
        v_lst, v_any = hop.inputargs(r_lst, r_lst.item_repr)
        return hop.gendirectcall(ll_listcontains, v_lst, v_any, r_lst.get_eqfunc())


class __extend__(pairtype(BaseListRepr, IntegerRepr)):

    def rtype_getitem((r_lst, r_int), hop):
        if hop.has_implicit_exception(IndexError):
            spec = dum_checkidx
        else:
            spec = dum_nocheck
        v_func = hop.inputconst(Void, spec)
        v_lst, v_index = hop.inputargs(r_lst, Signed)
        if hop.args_s[1].nonneg:
            llfn = ll_getitem_nonneg
        else:
            llfn = ll_getitem
        hop.exception_is_here()
        v_res = hop.gendirectcall(llfn, v_func, v_lst, v_index)
        return r_lst.recast(hop.llops, v_res)

    def rtype_setitem((r_lst, r_int), hop):
        if hop.has_implicit_exception(IndexError):
            spec = dum_checkidx
        else:
            spec = dum_nocheck
        v_func = hop.inputconst(Void, spec)
        v_lst, v_index, v_item = hop.inputargs(r_lst, Signed, r_lst.item_repr)
        if hop.args_s[1].nonneg:
            llfn = ll_setitem_nonneg
        else:
            llfn = ll_setitem
        hop.exception_is_here()
        return hop.gendirectcall(llfn, v_func, v_lst, v_index, v_item)

    def rtype_mul((r_lst, r_int), hop):
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        v_lst, v_factor = hop.inputargs(r_lst, Signed)
        return hop.gendirectcall(ll_mul, cRESLIST, v_lst, v_factor)

class __extend__(pairtype(ListRepr, IntegerRepr)):

    def rtype_delitem((r_lst, r_int), hop):
        if hop.has_implicit_exception(IndexError):
            spec = dum_checkidx
        else:
            spec = dum_nocheck
        v_func = hop.inputconst(Void, spec)
        v_lst, v_index = hop.inputargs(r_lst, Signed)
        if hop.args_s[1].nonneg:
            llfn = ll_delitem_nonneg
        else:
            llfn = ll_delitem
        hop.exception_is_here()
        return hop.gendirectcall(llfn, v_func, v_lst, v_index)

    def rtype_inplace_mul((r_lst, r_int), hop):
        v_lst, v_factor = hop.inputargs(r_lst, Signed)
        return hop.gendirectcall(ll_inplace_mul, v_lst, v_factor)

class __extend__(pairtype(BaseListRepr, SliceRepr)):

    def rtype_getitem((r_lst, r_slic), hop):
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        if r_slic == startonly_slice_repr:
            v_lst, v_start = hop.inputargs(r_lst, startonly_slice_repr)
            return hop.gendirectcall(ll_listslice_startonly, cRESLIST, v_lst, v_start)
        if r_slic == startstop_slice_repr:
            v_lst, v_slice = hop.inputargs(r_lst, startstop_slice_repr)
            return hop.gendirectcall(ll_listslice, cRESLIST, v_lst, v_slice)
        if r_slic == minusone_slice_repr:
            v_lst, v_ignored = hop.inputargs(r_lst, minusone_slice_repr)
            return hop.gendirectcall(ll_listslice_minusone, cRESLIST, v_lst)
        raise TyperError('getitem does not support slices with %r' % (r_slic,))

    def rtype_setitem((r_lst, r_slic), hop):
        #if r_slic == startonly_slice_repr:
        #    not implemented
        if r_slic == startstop_slice_repr:
            v_lst, v_slice, v_lst2 = hop.inputargs(r_lst, startstop_slice_repr,
                                                   hop.args_r[2])
            hop.gendirectcall(ll_listsetslice, v_lst, v_slice, v_lst2)
            return
        raise TyperError('setitem does not support slices with %r' % (r_slic,))

class __extend__(pairtype(ListRepr, SliceRepr)):

    def rtype_delitem((r_lst, r_slic), hop):
        if r_slic == startonly_slice_repr:
            v_lst, v_start = hop.inputargs(r_lst, startonly_slice_repr)
            hop.gendirectcall(ll_listdelslice_startonly, v_lst, v_start)
            return
        if r_slic == startstop_slice_repr:
            v_lst, v_slice = hop.inputargs(r_lst, startstop_slice_repr)
            hop.gendirectcall(ll_listdelslice, v_lst, v_slice)
            return
        raise TyperError('delitem does not support slices with %r' % (r_slic,))

class __extend__(pairtype(BaseListRepr, BaseListRepr)):
    def convert_from_to((r_lst1, r_lst2), v, llops):
        if r_lst1.listitem is None or r_lst2.listitem is None:
            return NotImplemented
        if r_lst1.listitem is not r_lst2.listitem:
            if r_lst1.lowleveltype != r_lst2.lowleveltype:
                return NotImplemented
        return v

    def rtype_is_((r_lst1, r_lst2), hop):
        if r_lst1.lowleveltype != r_lst2.lowleveltype:
            # obscure logic, the is can be true only if both are None
            v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
            return hop.gendirectcall(ll_both_none, v_lst1, v_lst2)

        return pairtype(Repr, Repr).rtype_is_(pair(r_lst1, r_lst2), hop)

    def rtype_add((r_lst1, r_lst2), hop):
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        return hop.gendirectcall(ll_concat, cRESLIST, v_lst1, v_lst2)

    def rtype_eq((r_lst1, r_lst2), hop):
        assert r_lst1.item_repr == r_lst2.item_repr
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        return hop.gendirectcall(ll_listeq, v_lst1, v_lst2, r_lst1.get_eqfunc())

    def rtype_ne((r_lst1, r_lst2), hop):
        assert r_lst1.item_repr == r_lst2.item_repr
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        flag = hop.gendirectcall(ll_listeq, v_lst1, v_lst2, r_lst1.get_eqfunc())
        return hop.genop('bool_not', [flag], resulttype=Bool)

def ll_both_none(lst1, lst2):
    return not lst1 and not lst2

class __extend__(pairtype(ListRepr, BaseListRepr)):

    def rtype_inplace_add((r_lst1, r_lst2), hop):
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        hop.gendirectcall(ll_extend, v_lst1, v_lst2)
        return v_lst1


# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.

# adapted C code

def _ll_list_resize_really(l, newsize):
    """
    Ensure ob_item has room for at least newsize elements, and set
    ob_size to newsize.  If newsize > ob_size on entry, the content
    of the new slots at exit is undefined heap trash; it's the caller's
    responsiblity to overwrite them with sane values.
    The number of allocated elements may grow, shrink, or stay the same.
    Failure is impossible if newsize <= self.allocated on entry, although
    that partly relies on an assumption that the system realloc() never
    fails when passed a number of bytes <= the number of bytes last
    allocated (the C standard doesn't guarantee this, but it's hard to
    imagine a realloc implementation where it wouldn't be true).
    Note that self->ob_item may change, and even if newsize is less
    than ob_size on entry.
    """
    allocated = len(l.items)

    # This over-allocates proportional to the list size, making room
    # for additional growth.  The over-allocation is mild, but is
    # enough to give linear-time amortized behavior over a long
    # sequence of appends() in the presence of a poorly-performing
    # system realloc().
    # The growth pattern is:  0, 4, 8, 16, 25, 35, 46, 58, 72, 88, ...
    ## (newsize < 9 ? 3 : 6)
    if newsize < 9:
        some = 3
    else:
        some = 6
    new_allocated = (newsize >> 3) + some + newsize
    if newsize == 0:
        new_allocated = 0
    # XXX consider to have a real realloc
    items = l.items
    newitems = malloc(typeOf(l).TO.items.TO, new_allocated)
    if allocated < new_allocated:
        p = allocated - 1
    else:
        p = new_allocated - 1
    while p >= 0:
            newitems[p] = items[p]
            ITEM = typeOf(l).TO.items.TO.OF
            if isinstance(ITEM, Ptr):
                items[p] = nullptr(ITEM.TO)
            p -= 1
    l.length = newsize
    l.items = newitems

# this common case was factored out of _ll_list_resize
# to see if inlining it gives some speed-up.

def _ll_list_resize(l, newsize):
    # Bypass realloc() when a previous overallocation is large enough
    # to accommodate the newsize.  If the newsize falls lower than half
    # the allocated size, then proceed with the realloc() to shrink the list.
    allocated = len(l.items)
    if allocated >= newsize and newsize >= ((allocated >> 1) - 5):
        l.length = newsize
    else:
        _ll_list_resize_really(l, newsize)

def _ll_list_resize_ge(l, newsize):
    if len(l.items) >= newsize:
        l.length = newsize
    else:
        _ll_list_resize_really(l, newsize)

def _ll_list_resize_le(l, newsize):
    if newsize >= (len(l.items) >> 1) - 5:
        l.length = newsize
    else:
        _ll_list_resize_really(l, newsize)


def ll_copy(RESLIST, l):
    items = l.ll_items()
    length = l.ll_length()
    new_lst = RESLIST.ll_newlist(length)
    i = 0
    new_items = new_lst.ll_items()
    while i < length:
        new_items[i] = items[i]
        i += 1
    return new_lst
ll_copy.oopspec = 'list.copy(l)'

def ll_len(l):
    return l.ll_length()
ll_len.oopspec = 'list.len(l)'

def ll_list_is_true(l):
    # check if a list is True, allowing for None
    return bool(l) and l.ll_length() != 0
ll_list_is_true.oopspec = 'list.nonzero(l)'

def ll_append(l, newitem):
    length = l.length
    _ll_list_resize_ge(l, length+1)
    l.items[length] = newitem
ll_append.oopspec = 'list.append(l, newitem)'

# this one is for the special case of insert(0, x)
def ll_prepend(l, newitem):
    length = l.length
    _ll_list_resize_ge(l, length+1)
    items = l.items
    dst = length
    while dst > 0:
        src = dst - 1
        items[dst] = items[src]
        dst = src
    items[0] = newitem
ll_prepend.oopspec = 'list.insert(l, 0, newitem)'

def ll_insert_nonneg(l, index, newitem):
    length = l.length
    _ll_list_resize_ge(l, length+1)
    items = l.items
    dst = length
    while dst > index:
        src = dst - 1
        items[dst] = items[src]
        dst = src
    items[index] = newitem
ll_insert_nonneg.oopspec = 'list.insert(l, index, newitem)'

def dum_checkidx(): pass
def dum_nocheck(): pass

def ll_pop_nonneg(func, l, index):
    if func is dum_checkidx and (index >= l.length):
        raise IndexError
    res = l.items[index]
    ll_delitem_nonneg(dum_nocheck, l, index)
    return res
ll_pop_nonneg.oopspec = 'list.pop(l, index)'

def ll_pop_default(func, l):
    length = l.length
    if func is dum_checkidx and (length == 0):
        raise IndexError
    index = length - 1
    newlength = index
    items = l.items
    res = items[index]
    ITEM = typeOf(l).TO.items.TO.OF
    if isinstance(ITEM, Ptr):
        items[index] = nullptr(ITEM.TO)
    _ll_list_resize_le(l, newlength)
    return res
ll_pop_default.oopspec = 'list.pop(l)'

def ll_pop_zero(func, l):
    length = l.length
    if func is dum_checkidx and (length == 0):
        raise IndexError
    newlength = length - 1
    res = l.items[0]
    j = 0
    items = l.items
    j1 = j+1
    while j < newlength:
        items[j] = items[j1]
        j = j1
        j1 += 1
    ITEM = typeOf(l).TO.items.TO.OF
    if isinstance(ITEM, Ptr):
        items[newlength] = nullptr(ITEM.TO)
    _ll_list_resize_le(l, newlength)
    return res
ll_pop_zero.oopspec = 'list.pop(l, 0)'

def ll_pop(func, l, index):
    length = l.length
    if index < 0:
        index += length
    if func is dum_checkidx and (index < 0 or index >= length):
        raise IndexError
    res = l.items[index]
    ll_delitem_nonneg(dum_nocheck, l, index)
    return res
ll_pop.oopspec = 'list.pop(l, index)'

def ll_reverse(l):
    length = l.ll_length()
    i = 0
    items = l.ll_items()
    length_1_i = length-1-i
    while i < length_1_i:
        tmp = items[i]
        items[i] = items[length_1_i]
        items[length_1_i] = tmp
        i += 1
        length_1_i -= 1
ll_reverse.oopspec = 'list.reverse(l)'

def ll_getitem_nonneg(func, l, index):
    if func is dum_checkidx and (index >= l.ll_length()):
        raise IndexError
    return l.ll_items()[index]
ll_getitem_nonneg.oopspec = 'list.getitem(l, index)'

def ll_getitem(func, l, index):
    length = l.ll_length()
    if index < 0:
        index += length
    if func is dum_checkidx and (index < 0 or index >= length):
        raise IndexError
    return l.ll_items()[index]
ll_getitem.oopspec = 'list.getitem(l, index)'

def ll_setitem_nonneg(func, l, index, newitem):
    if func is dum_checkidx and (index >= l.ll_length()):
        raise IndexError
    l.ll_items()[index] = newitem
ll_setitem_nonneg.oopspec = 'list.setitem(l, index, newitem)'

def ll_setitem(func, l, index, newitem):
    length = l.ll_length()
    if index < 0:
        index += length
    if func is dum_checkidx and (index < 0 or index >= length):
        raise IndexError
    l.ll_items()[index] = newitem
ll_setitem.oopspec = 'list.setitem(l, index, newitem)'

def ll_delitem_nonneg(func, l, index):
    length = l.length
    if func is dum_checkidx and (index >= length):
        raise IndexError
    newlength = length - 1
    j = index
    items = l.items
    j1 = j+1
    while j < newlength:
        items[j] = items[j1]
        j = j1
        j1 += 1
    ITEM = typeOf(l).TO.items.TO.OF
    if isinstance(ITEM, Ptr):
        items[newlength] = nullptr(ITEM.TO)
    _ll_list_resize_le(l, newlength)
ll_delitem_nonneg.oopspec = 'list.delitem(l, index)'

def ll_delitem(func, l, i):
    length = l.length
    if i < 0:
        i += length
    if func is dum_checkidx and (i < 0 or i >= length):
        raise IndexError
    ll_delitem_nonneg(dum_nocheck, l, i)
ll_delitem.oopspec = 'list.delitem(l, i)'

def ll_concat(RESLIST, l1, l2):
    len1 = l1.ll_length()
    len2 = l2.ll_length()
    newlength = len1 + len2
    l = RESLIST.ll_newlist(newlength)
    newitems = l.ll_items()
    j = 0
    source = l1.ll_items()
    while j < len1:
        newitems[j] = source[j]
        j += 1
    i = 0
    source = l2.ll_items()
    while i < len2:
        newitems[j] = source[i]
        i += 1
        j += 1
    return l
ll_concat.oopspec = 'list.concat(l1, l2)'

def ll_extend(l1, l2):
    len1 = l1.length
    len2 = l2.ll_length()
    newlength = len1 + len2
    _ll_list_resize_ge(l1, newlength)
    items = l1.items
    source = l2.ll_items()
    i = 0
    j = len1
    while i < len2:
        items[j] = source[i]
        i += 1
        j += 1

def ll_listslice_startonly(RESLIST, l1, start):
    len1 = l1.ll_length()
    newlength = len1 - start
    l = RESLIST.ll_newlist(newlength)
    newitems = l.ll_items()
    j = 0
    source = l1.ll_items()
    i = start
    while i < len1:
        newitems[j] = source[i]
        i += 1
        j += 1
    return l

def ll_listslice(RESLIST, l1, slice):
    start = slice.start
    stop = slice.stop
    length = l1.ll_length()
    if stop > length:
        stop = length
    newlength = stop - start
    l = RESLIST.ll_newlist(newlength)
    newitems = l.ll_items()
    j = 0
    source = l1.ll_items()
    i = start
    while i < stop:
        newitems[j] = source[i]
        i += 1
        j += 1
    return l

def ll_listslice_minusone(RESLIST, l1):
    newlength = l1.ll_length() - 1
    assert newlength >= 0
    l = RESLIST.ll_newlist(newlength)
    newitems = l.ll_items()
    j = 0
    source = l1.ll_items()
    while j < newlength:
        newitems[j] = source[j]
        j += 1
    return l

def ll_listdelslice_startonly(l, start):
    newlength = start
    ITEM = typeOf(l).TO.items.TO.OF
    if isinstance(ITEM, Ptr):
        j = l.length - 1
        items = l.items
        while j >= newlength:
            items[j] = nullptr(ITEM.TO)
            j -= 1
    _ll_list_resize_le(l, newlength)

def ll_listdelslice(l, slice):
    start = slice.start
    stop = slice.stop
    if stop > l.length:
        stop = l.length
    newlength = l.length - (stop-start)
    j = start
    items = l.items
    i = stop
    while j < newlength:
        items[j] = items[i]
        i += 1
        j += 1
    ITEM = typeOf(l).TO.items.TO.OF
    if isinstance(ITEM, Ptr):
        j = l.length - 1
        while j >= newlength:
            items[j] = nullptr(ITEM.TO)
            j -= 1
    _ll_list_resize_le(l, newlength)

def ll_listsetslice(l1, slice, l2):
    count = l2.ll_length()
    assert count == slice.stop - slice.start, (
        "setslice cannot resize lists in RPython")
    # XXX but it should be easy enough to support, soon
    start = slice.start
    j = start
    items1 = l1.ll_items()
    items2 = l2.ll_items()
    i = 0
    while i < count:
        items1[j] = items2[i]
        i += 1
        j += 1

# ____________________________________________________________
#
#  Comparison.

def ll_listeq(l1, l2, eqfn):
    if not l1 and not l2:
        return True
    if not l1 or not l2:
        return False
    len1 = l1.ll_length()
    len2 = l2.ll_length()
    if len1 != len2:
        return False
    j = 0
    items1 = l1.ll_items()
    items2 = l2.ll_items()
    while j < len1:
        if eqfn is None:
            if items1[j] != items2[j]:
                return False
        else:
            if not eqfn(items1[j], items2[j]):
                return False
        j += 1
    return True

def ll_listcontains(lst, obj, eqfn):
    items = lst.ll_items()
    lng = lst.ll_length()
    j = 0
    while j < lng:
        if eqfn is None:
            if items[j] == obj:
                return True
        else:
            if eqfn(items[j], obj):
                return True
        j += 1
    return False

def ll_listindex(lst, obj, eqfn):
    items = lst.ll_items()
    lng = lst.ll_length()
    j = 0
    while j < lng:
        if eqfn is None:
            if items[j] == obj:
                return j
        else:
            if eqfn(items[j], obj):
                return j
        j += 1
    raise ValueError # can't say 'list.index(x): x not in list'

TEMP = GcArray(Ptr(rstr.STR))

def ll_inplace_mul(l, factor):
    length = l.ll_length()
    if factor < 0:
        factor = 0
    resultlen = length * factor
    res = l
    _ll_list_resize(res, resultlen)
    j = length
    source = l.ll_items()
    target = res.ll_items()
    while j < resultlen:
        i = 0
        while i < length:
            p = j + i
            target[p] = source[i]
            i += 1
        j += length
    return res


def ll_mul(RESLIST, l, factor):
    length = l.ll_length()
    if factor < 0:
        factor = 0
    resultlen = length * factor
    res = RESLIST.ll_newlist(resultlen)
    j = 0
    source = l.ll_items()
    target = res.ll_items()
    while j < resultlen:
        i = 0
        while i < length:
            p = j + i
            target[p] = source[i]
            i += 1
        j += length
    return res
        

# ____________________________________________________________
#
#  Irregular operations.

def ll_newlist(LIST, length):
    l = malloc(LIST)
    l.length = length
    l.items = malloc(LIST.items.TO, length)
    return l
ll_newlist = typeMethod(ll_newlist)
ll_newlist.oopspec = 'newlist(length)'

def ll_length(l):
    return l.length

def ll_items(l):
    return l.items

# fixed size versions

def ll_fixed_newlist(LIST, length):
    l = malloc(LIST, length)
    return l
ll_fixed_newlist = typeMethod(ll_fixed_newlist)
ll_fixed_newlist.oopspec = 'newlist(length)'

def ll_fixed_length(l):
    return len(l)

def ll_fixed_items(l):
    return l

def rtype_newlist(hop):
    nb_args = hop.nb_args
    r_list = hop.r_result
    if r_list == robject.pyobj_repr: # special case: SomeObject lists!
        clist = hop.inputconst(robject.pyobj_repr, list)
        v_result = hop.genop('simple_call', [clist], resulttype = robject.pyobj_repr)
        cname = hop.inputconst(robject.pyobj_repr, 'append')
        v_meth = hop.genop('getattr', [v_result, cname], resulttype = robject.pyobj_repr)
        for i in range(nb_args):
            v_item = hop.inputarg(robject.pyobj_repr, arg=i)
            hop.genop('simple_call', [v_meth, v_item], resulttype = robject.pyobj_repr)
        return v_result
    r_listitem = r_list.item_repr
    LIST = r_list.LIST
    cno = hop.inputconst(Signed, nb_args)
    v_result = hop.gendirectcall(LIST.ll_newlist, cno)
    v_func = hop.inputconst(Void, dum_nocheck)
    for i in range(nb_args):
        ci = hop.inputconst(Signed, i)
        v_item = hop.inputarg(r_listitem, arg=i)
        hop.gendirectcall(ll_setitem_nonneg, v_func, v_result, ci, v_item)
    return v_result

def ll_alloc_and_set(LIST, count, item):
    if count < 0:
        count = 0
    l = LIST.ll_newlist(count)
    if item: # as long as malloc it is known to zero the allocated memory avoid zeroing twice
        i = 0
        items = l.ll_items()
        while i < count:
            items[i] = item
            i += 1
    return l
ll_alloc_and_set.oopspec = 'newlist(count, item)'

def rtype_alloc_and_set(hop):
    r_list = hop.r_result
    v_count, v_item = hop.inputargs(Signed, r_list.item_repr)
    cLIST = hop.inputconst(Void, r_list.LIST)
    return hop.gendirectcall(ll_alloc_and_set, cLIST, v_count, v_item)

# ____________________________________________________________
#
#  Iteration.

class ListIteratorRepr(IteratorRepr):

    def __init__(self, r_list):
        self.r_list = r_list
        self.lowleveltype = Ptr(GcStruct('listiter',
                                         ('list', r_list.lowleveltype),
                                         ('index', Signed)))

    def newiter(self, hop):
        v_lst, = hop.inputargs(self.r_list)
        citerptr = hop.inputconst(Void, self.lowleveltype)
        return hop.gendirectcall(ll_listiter, citerptr, v_lst)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        hop.has_implicit_exception(StopIteration) # record that we know about it
        hop.exception_is_here()
        v_res = hop.gendirectcall(ll_listnext, v_iter)
        return self.r_list.recast(hop.llops, v_res)

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
    iter.index = index + 1
    return l.ll_items()[index]

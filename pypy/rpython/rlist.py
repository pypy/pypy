from pypy.tool.pairtype import pairtype, pair
from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.rpython.error import TyperError
from pypy.rpython.rmodel import Repr, IteratorRepr, IntegerRepr, inputconst
from pypy.rpython.rslice import AbstractSliceRepr
from pypy.rpython.rstr import AbstractStringRepr, AbstractCharRepr
from pypy.rpython.lltypesystem.lltype import typeOf, Ptr, Void, Signed, Bool
from pypy.rpython.lltypesystem.lltype import nullptr, Char, UniChar
from pypy.rpython import robject
from pypy.rlib.objectmodel import malloc_zero_filled
from pypy.rlib.debug import ll_assert
from pypy.rlib.rarithmetic import ovfcheck
from pypy.rpython.annlowlevel import ADTInterface

ADTIFixedList = ADTInterface(None, {
    'll_newlist':      (['SELF', Signed        ], 'self'),
    'll_length':       (['self'                ], Signed),
    'll_getitem_fast': (['self', Signed        ], 'item'),
    'll_setitem_fast': (['self', Signed, 'item'], Void),
})
ADTIList = ADTInterface(ADTIFixedList, {
    '_ll_resize_ge':   (['self', Signed        ], Void),
    '_ll_resize_le':   (['self', Signed        ], Void),
    '_ll_resize':      (['self', Signed        ], Void),
})


def dum_checkidx(): pass
def dum_nocheck(): pass


class __extend__(annmodel.SomeList):
    def rtyper_makerepr(self, rtyper):
        listitem = self.listdef.listitem
        s_value = listitem.s_value
        if (listitem.range_step is not None and not listitem.mutated and
            not isinstance(s_value, annmodel.SomeImpossibleValue)):
            return rtyper.type_system.rrange.RangeRepr(listitem.range_step)
        elif (s_value.__class__ is annmodel.SomeObject and s_value.knowntype == object):
            return robject.pyobj_repr
        else:
            # cannot do the rtyper.getrepr() call immediately, for the case
            # of recursive structures -- i.e. if the listdef contains itself
            rlist = rtyper.type_system.rlist
            if self.listdef.listitem.resized:
                return rlist.ListRepr(rtyper,
                        lambda: rtyper.getrepr(listitem.s_value), listitem)
            else:
                return rlist.FixedSizeListRepr(rtyper,
                        lambda: rtyper.getrepr(listitem.s_value), listitem)

    def rtyper_makekey(self):
        self.listdef.listitem.dont_change_any_more = True
        return self.__class__, self.listdef.listitem


class AbstractBaseListRepr(Repr):
    eq_func_cache = None

    def recast(self, llops, v):
        return llops.convertvar(v, self.item_repr, self.external_item_repr)

    def convert_const(self, listobj):
        # get object from bound list method
        if listobj is None:
            return self.null_const()
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
            if r_item.lowleveltype is not Void:
                for i in range(n):
                    x = listobj[i]
                    result.ll_setitem_fast(i, r_item.convert_const(x))
            return result

    def null_const(self):
        raise NotImplementedError

    def prepare_const(self, nitems):
        raise NotImplementedError

    def ll_str(self, l):
        constant = self.rstr_ll.ll_constant
        start    = self.rstr_ll.ll_build_start
        push     = self.rstr_ll.ll_build_push
        finish   = self.rstr_ll.ll_build_finish

        length = l.ll_length()
        if length == 0:
            return constant("[]")

        buf = start(2 * length + 1)
        push(buf, constant("["), 0)
        item_repr = self.item_repr
        i = 0
        while i < length:
            if i > 0:
                push(buf, constant(", "), 2 * i)
            item = l.ll_getitem_fast(i)
            push(buf, item_repr.ll_str(item), 2 * i + 1)
            i += 1
        push(buf, constant("]"), 2 * length)
        return finish(buf)

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
    
    def rtype_method_reverse(self, hop):
        v_lst, = hop.inputargs(self)
        hop.exception_cannot_occur()
        hop.gendirectcall(ll_reverse,v_lst)

    def rtype_method_remove(self, hop):
        v_lst, v_value = hop.inputargs(self, self.item_repr)
        hop.has_implicit_exception(ValueError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_listremove, v_lst, v_value,
                                 self.get_eqfunc())

    def rtype_method_index(self, hop):
        v_lst, v_value = hop.inputargs(self, self.item_repr)
        hop.has_implicit_exception(ValueError)   # record that we know about it
        hop.exception_is_here()
        return hop.gendirectcall(ll_listindex, v_lst, v_value, self.get_eqfunc())

    def get_ll_eq_function(self):
        result = self.eq_func_cache
        if result is not None:
            return result
        def list_eq(l1, l2):
            return ll_listeq(l1, l2, item_eq_func)
        self.eq_func_cache = list_eq
        # ^^^ do this first, before item_repr.get_ll_eq_function()
        item_eq_func = self.item_repr.get_ll_eq_function()
        return list_eq


class AbstractListRepr(AbstractBaseListRepr):

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


class AbstractFixedSizeListRepr(AbstractBaseListRepr):
    pass


class __extend__(pairtype(AbstractBaseListRepr, Repr)):

    def rtype_contains((r_lst, _), hop):
        v_lst, v_any = hop.inputargs(r_lst, r_lst.item_repr)
        return hop.gendirectcall(ll_listcontains, v_lst, v_any, r_lst.get_eqfunc())

class __extend__(pairtype(AbstractBaseListRepr, IntegerRepr)):

    def rtype_getitem((r_lst, r_int), hop, checkidx=False):
        if checkidx:
            spec = dum_checkidx
        else:
            spec = dum_nocheck
        v_func = hop.inputconst(Void, spec)
        v_lst, v_index = hop.inputargs(r_lst, Signed)
        if hop.args_s[1].nonneg:
            llfn = ll_getitem_nonneg
        else:
            llfn = ll_getitem
        if checkidx:
            hop.exception_is_here()
        else:
            hop.exception_cannot_occur()
        v_res = hop.gendirectcall(llfn, v_func, v_lst, v_index)
        return r_lst.recast(hop.llops, v_res)

    rtype_getitem_key = rtype_getitem

    def rtype_getitem_idx((r_lst, r_int), hop):
        return pair(r_lst, r_int).rtype_getitem(hop, checkidx=True)

    rtype_getitem_idx_key = rtype_getitem_idx
    
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


class __extend__(pairtype(AbstractListRepr, IntegerRepr)):

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


class __extend__(pairtype(AbstractBaseListRepr, AbstractBaseListRepr)):
    def convert_from_to((r_lst1, r_lst2), v, llops):
        if r_lst1.listitem is None or r_lst2.listitem is None:
            return NotImplemented
        if r_lst1.listitem is not r_lst2.listitem:
            return NotImplemented
        return v

##    # TODO: move it to lltypesystem
##    def rtype_is_((r_lst1, r_lst2), hop):
##        if r_lst1.lowleveltype != r_lst2.lowleveltype:
##            # obscure logic, the is can be true only if both are None
##            v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
##            return hop.gendirectcall(ll_both_none, v_lst1, v_lst2)

##        return pairtype(Repr, Repr).rtype_is_(pair(r_lst1, r_lst2), hop)
 
    def rtype_eq((r_lst1, r_lst2), hop):
        assert r_lst1.item_repr == r_lst2.item_repr
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        return hop.gendirectcall(ll_listeq, v_lst1, v_lst2, r_lst1.get_eqfunc())

    def rtype_ne((r_lst1, r_lst2), hop):
        assert r_lst1.item_repr == r_lst2.item_repr
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        flag = hop.gendirectcall(ll_listeq, v_lst1, v_lst2, r_lst1.get_eqfunc())
        return hop.genop('bool_not', [flag], resulttype=Bool)


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
    items_v = [hop.inputarg(r_listitem, arg=i) for i in range(nb_args)]
    return hop.rtyper.type_system.rlist.newlist(hop.llops, r_list, items_v)

def rtype_alloc_and_set(hop):
    r_list = hop.r_result
    # XXX the special case for pyobj_repr needs to be implemented here as well
    # will probably happen during NFS
    if r_list == robject.pyobj_repr:
        raise Exception, 'please implement this!'
    v_count, v_item = hop.inputargs(Signed, r_list.item_repr)
    cLIST = hop.inputconst(Void, r_list.LIST)
    return hop.gendirectcall(ll_alloc_and_set, cLIST, v_count, v_item)


class __extend__(pairtype(AbstractBaseListRepr, AbstractBaseListRepr)):

    def rtype_add((r_lst1, r_lst2), hop):
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        return hop.gendirectcall(ll_concat, cRESLIST, v_lst1, v_lst2)

class __extend__(pairtype(AbstractListRepr, AbstractBaseListRepr)):

    def rtype_inplace_add((r_lst1, r_lst2), hop):
        v_lst1, v_lst2 = hop.inputargs(r_lst1, r_lst2)
        hop.gendirectcall(ll_extend, v_lst1, v_lst2)
        return v_lst1

class __extend__(pairtype(AbstractListRepr, AbstractStringRepr)):

    def rtype_inplace_add((r_lst1, r_str2), hop):
        if r_lst1.item_repr.lowleveltype not in (Char, UniChar):
            raise TyperError('"lst += string" only supported with a list '
                             'of chars or unichars')
        string_repr = r_str2.repr
        v_lst1, v_str2 = hop.inputargs(r_lst1, string_repr)
        c_strlen  = hop.inputconst(Void, string_repr.ll.ll_strlen)
        c_stritem = hop.inputconst(Void, string_repr.ll.ll_stritem_nonneg)
        hop.gendirectcall(ll_extend_with_str, v_lst1, v_str2,
                          c_strlen, c_stritem)
        return v_lst1

    def rtype_extend_with_str_slice((r_lst1, r_str2), hop):
        if r_lst1.item_repr.lowleveltype not in (Char, UniChar):
            raise TyperError('"lst += string" only supported with a list '
                             'of chars or unichars')
        rs = r_lst1.rtyper.type_system.rslice
        string_repr = r_lst1.rtyper.type_system.rstr.string_repr
        c_strlen  = hop.inputconst(Void, string_repr.ll.ll_strlen)
        c_stritem = hop.inputconst(Void, string_repr.ll.ll_stritem_nonneg)
        r_slic = hop.args_r[2]
        v_lst1, v_str2, v_slice = hop.inputargs(r_lst1, string_repr, r_slic)
        if r_slic == rs.startonly_slice_repr:
            hop.gendirectcall(ll_extend_with_str_slice_startonly,
                              v_lst1, v_str2, c_strlen, c_stritem, v_slice)
        elif r_slic == rs.startstop_slice_repr:
            hop.gendirectcall(ll_extend_with_str_slice,
                              v_lst1, v_str2, c_strlen, c_stritem, v_slice)
        elif r_slic == rs.minusone_slice_repr:
            hop.gendirectcall(ll_extend_with_str_slice_minusone,
                              v_lst1, v_str2, c_strlen, c_stritem)
        else:
            raise TyperError('lst += str[:] does not support slices with %r' %
                             (r_slic,))
        return v_lst1

class __extend__(pairtype(AbstractListRepr, AbstractCharRepr)):

    def rtype_extend_with_char_count((r_lst1, r_chr2), hop):
        if r_lst1.item_repr.lowleveltype not in (Char, UniChar):
            raise TyperError('"lst += string" only supported with a list '
                             'of chars or unichars')
        char_repr = r_lst1.rtyper.type_system.rstr.char_repr
        v_lst1, v_chr, v_count = hop.inputargs(r_lst1, char_repr, Signed)
        hop.gendirectcall(ll_extend_with_char_count, v_lst1, v_chr, v_count)
        return v_lst1


class __extend__(pairtype(AbstractBaseListRepr, AbstractSliceRepr)):

    def rtype_getitem((r_lst, r_slic), hop):
        rs = r_lst.rtyper.type_system.rslice
        cRESLIST = hop.inputconst(Void, hop.r_result.LIST)
        if r_slic == rs.startonly_slice_repr:
            v_lst, v_start = hop.inputargs(r_lst, rs.startonly_slice_repr)
            return hop.gendirectcall(ll_listslice_startonly, cRESLIST, v_lst, v_start)
        if r_slic == rs.startstop_slice_repr:
            v_lst, v_slice = hop.inputargs(r_lst, rs.startstop_slice_repr)
            return hop.gendirectcall(ll_listslice, cRESLIST, v_lst, v_slice)
        if r_slic == rs.minusone_slice_repr:
            v_lst, v_ignored = hop.inputargs(r_lst, rs.minusone_slice_repr)
            return hop.gendirectcall(ll_listslice_minusone, cRESLIST, v_lst)
        raise TyperError('getitem does not support slices with %r' % (r_slic,))

    def rtype_setitem((r_lst, r_slic), hop):
        #if r_slic == startonly_slice_repr:
        #    not implemented
        rs = r_lst.rtyper.type_system.rslice        
        if r_slic == rs.startstop_slice_repr:
            v_lst, v_slice, v_lst2 = hop.inputargs(r_lst, rs.startstop_slice_repr,
                                                   hop.args_r[2])
            hop.gendirectcall(ll_listsetslice, v_lst, v_slice, v_lst2)
            return
        raise TyperError('setitem does not support slices with %r' % (r_slic,))


class __extend__(pairtype(AbstractListRepr, AbstractSliceRepr)):

    def rtype_delitem((r_lst, r_slic), hop):
        rs = r_lst.rtyper.type_system.rslice        
        if r_slic == rs.startonly_slice_repr:
            v_lst, v_start = hop.inputargs(r_lst, rs.startonly_slice_repr)
            hop.gendirectcall(ll_listdelslice_startonly, v_lst, v_start)
            return
        if r_slic == rs.startstop_slice_repr:
            v_lst, v_slice = hop.inputargs(r_lst, rs.startstop_slice_repr)
            hop.gendirectcall(ll_listdelslice, v_lst, v_slice)
            return
        raise TyperError('delitem does not support slices with %r' % (r_slic,))


# ____________________________________________________________
#
#  Iteration.

class AbstractListIteratorRepr(IteratorRepr):

    def newiter(self, hop):
        v_lst, = hop.inputargs(self.r_list)
        citerptr = hop.inputconst(Void, self.lowleveltype)
        return hop.gendirectcall(self.ll_listiter, citerptr, v_lst)

    def rtype_next(self, hop):
        v_iter, = hop.inputargs(self)
        hop.has_implicit_exception(StopIteration) # record that we know about it
        hop.exception_is_here()
        v_res = hop.gendirectcall(self.ll_listnext, v_iter)
        return self.r_list.recast(hop.llops, v_res)



# ____________________________________________________________
#
#  Low-level methods.  These can be run for testing, but are meant to
#  be direct_call'ed from rtyped flow graphs, which means that they will
#  get flowed and annotated, mostly with SomePtr.
#
#  === a note about overflows ===
#
#  The maximal length of RPython lists is bounded by the assumption that
#  we can never allocate arrays more than sys.maxint bytes in size.
#  Our arrays have a length and some GC headers, so a list of characters
#  could come near sys.maxint in length (but not reach it).  A list of
#  pointers could only come near sys.maxint/sizeof(void*) elements.  There
#  is the list of Voids that could reach exactly sys.maxint elements,
#  but for now let's ignore this case -- the reasoning is that even if
#  the length of a Void list overflows, nothing bad memory-wise can be
#  done with it.  So in the sequel we don't bother checking for overflow
#  when we compute "ll_length() + 1".

def ll_alloc_and_set(LIST, count, item):
    if count < 0:
        count = 0
    l = LIST.ll_newlist(count)
    T = typeOf(item)
    if T is Char or T is UniChar:
        check = ord(item)
    else:
        check = item
    if (not malloc_zero_filled) or check: # as long as malloc it is known to zero the allocated memory avoid zeroing twice
    
        i = 0
        while i < count:
            l.ll_setitem_fast(i, item)
            i += 1
    return l
ll_alloc_and_set.oopspec = 'newlist(count, item)'


# return a nullptr() if lst is a list of pointers it, else None.  Note
# that if we are using ootypesystem there are not pointers, so we
# always return None.
def ll_null_item(lst):
    LIST = typeOf(lst)
    if isinstance(LIST, Ptr):
        ITEM = LIST.TO.ITEM
        if isinstance(ITEM, Ptr):
            return nullptr(ITEM.TO)
    return None

def listItemType(lst):
    LIST = typeOf(lst)
    if isinstance(LIST, Ptr):    # lltype
        LIST = LIST.TO
    return LIST.ITEM


def ll_copy(RESLIST, l):
    length = l.ll_length()
    new_lst = RESLIST.ll_newlist(length)
    i = 0
    while i < length:
        new_lst.ll_setitem_fast(i, l.ll_getitem_fast(i))
        i += 1
    return new_lst
ll_copy.oopspec = 'list.copy(l)'

def ll_len(l):
    return l.ll_length()
ll_len.oopspec = 'list.len(l)'
ll_len.oopargcheck = lambda l: bool(l)

def ll_list_is_true(l):
    # check if a list is True, allowing for None
    return bool(l) and l.ll_length() != 0
ll_list_is_true.oopspec = 'list.nonzero(l)'
ll_list_is_true.oopargcheck = lambda l: True

def ll_append(l, newitem):
    length = l.ll_length()
    l._ll_resize_ge(length+1)           # see "a note about overflows" above
    l.ll_setitem_fast(length, newitem)
ll_append.oopspec = 'list.append(l, newitem)'

# this one is for the special case of insert(0, x)
def ll_prepend(l, newitem):
    length = l.ll_length()
    l._ll_resize_ge(length+1)           # see "a note about overflows" above
    dst = length
    while dst > 0:
        src = dst - 1
        l.ll_setitem_fast(dst, l.ll_getitem_fast(src))
        dst = src
    l.ll_setitem_fast(0, newitem)
ll_prepend.oopspec = 'list.insert(l, 0, newitem)'

def ll_concat(RESLIST, l1, l2):
    len1 = l1.ll_length()
    len2 = l2.ll_length()
    try:
        newlength = ovfcheck(len1 + len2)
    except OverflowError:
        raise MemoryError
    l = RESLIST.ll_newlist(newlength)
    j = 0
    while j < len1:
        l.ll_setitem_fast(j, l1.ll_getitem_fast(j))
        j += 1
    i = 0
    while i < len2:
        l.ll_setitem_fast(j, l2.ll_getitem_fast(i))
        i += 1
        j += 1
    return l
ll_concat.oopspec = 'list.concat(l1, l2)'

def ll_insert_nonneg(l, index, newitem):
    length = l.ll_length()
    ll_assert(0 <= index, "negative list insertion index")
    ll_assert(index <= length, "list insertion index out of bound")
    l._ll_resize_ge(length+1)           # see "a note about overflows" above
    dst = length
    while dst > index:
        src = dst - 1
        l.ll_setitem_fast(dst, l.ll_getitem_fast(src))
        dst = src
    l.ll_setitem_fast(index, newitem)
ll_insert_nonneg.oopspec = 'list.insert(l, index, newitem)'

def ll_pop_nonneg(func, l, index):
    ll_assert(index >= 0, "unexpectedly negative list pop index")
    if func is dum_checkidx:
        if index >= l.ll_length():
            raise IndexError
    else:
        ll_assert(index < l.ll_length(), "list pop index out of bound")
    res = l.ll_getitem_fast(index)
    ll_delitem_nonneg(dum_nocheck, l, index)
    return res
ll_pop_nonneg.oopspec = 'list.pop(l, index)'

def ll_pop_default(func, l):
    length = l.ll_length()
    if func is dum_checkidx and (length == 0):
        raise IndexError
    ll_assert(length > 0, "pop from empty list")
    index = length - 1
    newlength = index
    res = l.ll_getitem_fast(index)
    null = ll_null_item(l)
    if null is not None:
        l.ll_setitem_fast(index, null)
    l._ll_resize_le(newlength)
    return res
ll_pop_default.oopspec = 'list.pop(l)'

def ll_pop_zero(func, l):
    length = l.ll_length()
    if func is dum_checkidx and (length == 0):
        raise IndexError
    ll_assert(length > 0, "pop(0) from empty list")
    newlength = length - 1
    res = l.ll_getitem_fast(0)
    j = 0
    j1 = j+1
    while j < newlength:
        l.ll_setitem_fast(j, l.ll_getitem_fast(j1))
        j = j1
        j1 += 1
    null = ll_null_item(l)
    if null is not None:
        l.ll_setitem_fast(newlength, null)
    l._ll_resize_le(newlength)
    return res
ll_pop_zero.oopspec = 'list.pop(l, 0)'

def ll_pop(func, l, index):
    length = l.ll_length()
    if index < 0:
        index += length
    if func is dum_checkidx:
        if index < 0 or index >= length:
            raise IndexError
    else:
        ll_assert(index >= 0, "negative list pop index out of bound")
        ll_assert(index < length, "list pop index out of bound")
    res = l.ll_getitem_fast(index)
    ll_delitem_nonneg(dum_nocheck, l, index)
    return res
ll_pop.oopspec = 'list.pop(l, index)'

def ll_reverse(l):
    length = l.ll_length()
    i = 0
    length_1_i = length-1-i
    while i < length_1_i:
        tmp = l.ll_getitem_fast(i)
        l.ll_setitem_fast(i, l.ll_getitem_fast(length_1_i))
        l.ll_setitem_fast(length_1_i, tmp)
        i += 1
        length_1_i -= 1
ll_reverse.oopspec = 'list.reverse(l)'

def ll_getitem_nonneg(func, l, index):
    ll_assert(index >= 0, "unexpectedly negative list getitem index")
    if func is dum_checkidx:
        if index >= l.ll_length():
            raise IndexError
    else:
        ll_assert(index < l.ll_length(), "list getitem index out of bound")
    return l.ll_getitem_fast(index)
ll_getitem_nonneg.oopspec = 'list.getitem(l, index)'
ll_getitem_nonneg.oopargcheck = lambda l, index: (bool(l) and
                                                  0 <= index < l.ll_length())

def ll_getitem(func, l, index):
    length = l.ll_length()
    if index < 0:
        index += length
    if func is dum_checkidx:
        if index < 0 or index >= length:
            raise IndexError
    else:
        ll_assert(index >= 0, "negative list getitem index out of bound")
        ll_assert(index < length, "list getitem index out of bound")
    return l.ll_getitem_fast(index)
ll_getitem.oopspec = 'list.getitem(l, index)'
ll_getitem.oopargcheck = lambda l, index: (bool(l) and -l.ll_length() <=
                                                       index < l.ll_length())

def ll_setitem_nonneg(func, l, index, newitem):
    ll_assert(index >= 0, "unexpectedly negative list setitem index")
    if func is dum_checkidx:
        if index >= l.ll_length():
            raise IndexError
    else:
        ll_assert(index < l.ll_length(), "list setitem index out of bound")
    l.ll_setitem_fast(index, newitem)
ll_setitem_nonneg.oopspec = 'list.setitem(l, index, newitem)'

def ll_setitem(func, l, index, newitem):
    length = l.ll_length()
    if index < 0:
        index += length
    if func is dum_checkidx:
        if index < 0 or index >= length:
            raise IndexError
    else:
        ll_assert(index >= 0, "negative list setitem index out of bound")
        ll_assert(index < length, "list setitem index out of bound")
    l.ll_setitem_fast(index, newitem)
ll_setitem.oopspec = 'list.setitem(l, index, newitem)'

def ll_delitem_nonneg(func, l, index):
    ll_assert(index >= 0, "unexpectedly negative list delitem index")
    length = l.ll_length()
    if func is dum_checkidx:
        if index >= length:
            raise IndexError
    else:
        ll_assert(index < length, "list delitem index out of bound")
    newlength = length - 1
    j = index
    j1 = j+1
    while j < newlength:
        l.ll_setitem_fast(j, l.ll_getitem_fast(j1))
        j = j1
        j1 += 1

    null = ll_null_item(l)
    if null is not None:
        l.ll_setitem_fast(newlength, null)
    l._ll_resize_le(newlength)
ll_delitem_nonneg.oopspec = 'list.delitem(l, index)'

def ll_delitem(func, l, i):
    length = l.ll_length()
    if i < 0:
        i += length
    if func is dum_checkidx:
        if i < 0 or i >= length:
            raise IndexError
    else:
        ll_assert(i >= 0, "negative list delitem index out of bound")
        ll_assert(i < length, "list delitem index out of bound")
    ll_delitem_nonneg(dum_nocheck, l, i)
ll_delitem.oopspec = 'list.delitem(l, i)'


def ll_extend(l1, l2):
    len1 = l1.ll_length()
    len2 = l2.ll_length()
    try:
        newlength = ovfcheck(len1 + len2)
    except OverflowError:
        raise MemoryError
    l1._ll_resize_ge(newlength)
    i = 0
    j = len1
    while i < len2:
        l1.ll_setitem_fast(j, l2.ll_getitem_fast(i))
        i += 1
        j += 1

def ll_extend_with_str(lst, s, getstrlen, getstritem):
    return ll_extend_with_str_slice_startonly(lst, s, getstrlen, getstritem, 0)

def ll_extend_with_str_slice_startonly(lst, s, getstrlen, getstritem, start):
    len1 = lst.ll_length()
    len2 = getstrlen(s)
    count2 = len2 - start
    ll_assert(start >= 0, "unexpectedly negative str slice start")
    assert count2 >= 0, "str slice start larger than str length"
    try:
        newlength = ovfcheck(len1 + count2)
    except OverflowError:
        raise MemoryError
    lst._ll_resize_ge(newlength)
    i = start
    j = len1
    while i < len2:
        c = getstritem(s, i)
        if listItemType(lst) is UniChar:
            c = unichr(ord(c))
        lst.ll_setitem_fast(j, c)
        i += 1
        j += 1

def ll_extend_with_str_slice(lst, s, getstrlen, getstritem, slice):
    start = slice.start
    stop = slice.stop
    len1 = lst.ll_length()
    len2 = getstrlen(s)
    ll_assert(start >= 0, "unexpectedly negative str slice start")
    ll_assert(start <= len2, "str slice start larger than str length")
    if stop > len2:
        stop = len2
    count2 = stop - start
    assert count2 >= 0, "str slice stop smaller than start"
    try:
        newlength = ovfcheck(len1 + count2)
    except OverflowError:
        raise MemoryError
    lst._ll_resize_ge(newlength)
    i = start
    j = len1
    while i < stop:
        c = getstritem(s, i)
        if listItemType(lst) is UniChar:
            c = unichr(ord(c))
        lst.ll_setitem_fast(j, c)
        i += 1
        j += 1

def ll_extend_with_str_slice_minusone(lst, s, getstrlen, getstritem):
    len1 = lst.ll_length()
    len2m1 = getstrlen(s) - 1
    assert len2m1 >= 0, "empty string is sliced with [:-1]"
    try:
        newlength = ovfcheck(len1 + len2m1)
    except OverflowError:
        raise MemoryError
    lst._ll_resize_ge(newlength)
    i = 0
    j = len1
    while i < len2m1:
        c = getstritem(s, i)
        if listItemType(lst) is UniChar:
            c = unichr(ord(c))
        lst.ll_setitem_fast(j, c)
        i += 1
        j += 1

def ll_extend_with_char_count(lst, char, count):
    if count <= 0:
        return
    len1 = lst.ll_length()
    try:
        newlength = ovfcheck(len1 + count)
    except OverflowError:
        raise MemoryError
    lst._ll_resize_ge(newlength)
    j = len1
    if listItemType(lst) is UniChar:
        char = unichr(ord(char))
    while j < newlength:
        lst.ll_setitem_fast(j, char)
        j += 1

def ll_listslice_startonly(RESLIST, l1, start):
    len1 = l1.ll_length()
    ll_assert(start >= 0, "unexpectedly negative list slice start")
    ll_assert(start <= len1, "list slice start larger than list length")
    newlength = len1 - start
    l = RESLIST.ll_newlist(newlength)
    j = 0
    i = start
    while i < len1:
        l.ll_setitem_fast(j, l1.ll_getitem_fast(i))
        i += 1
        j += 1
    return l

def ll_listslice(RESLIST, l1, slice):
    start = slice.start
    stop = slice.stop
    length = l1.ll_length()
    ll_assert(start >= 0, "unexpectedly negative list slice start")
    ll_assert(start <= length, "list slice start larger than list length")
    ll_assert(stop >= start, "list slice stop smaller than start")
    if stop > length:
        stop = length
    newlength = stop - start
    l = RESLIST.ll_newlist(newlength)
    j = 0
    i = start
    while i < stop:
        l.ll_setitem_fast(j, l1.ll_getitem_fast(i))
        i += 1
        j += 1
    return l

def ll_listslice_minusone(RESLIST, l1):
    newlength = l1.ll_length() - 1
    ll_assert(newlength >= 0, "empty list is sliced with [:-1]")
    l = RESLIST.ll_newlist(newlength)
    j = 0
    while j < newlength:
        l.ll_setitem_fast(j, l1.ll_getitem_fast(j))
        j += 1
    return l

def ll_listdelslice_startonly(l, start):
    ll_assert(start >= 0, "del l[start:] with unexpectedly negative start")
    ll_assert(start <= l.ll_length(), "del l[start:] with start > len(l)")
    newlength = start
    null = ll_null_item(l)
    if null is not None:
        j = l.ll_length() - 1
        while j >= newlength:
            l.ll_setitem_fast(j, null)
            j -= 1
    l._ll_resize_le(newlength)

def ll_listdelslice(l, slice):
    start = slice.start
    stop = slice.stop
    length = l.ll_length()
    ll_assert(start >= 0, "del l[start:x] with unexpectedly negative start")
    ll_assert(start <= length, "del l[start:x] with start > len(l)")
    ll_assert(stop >= start, "del l[x:y] with x > y")
    if stop > length:
        stop = length
    newlength = length - (stop-start)
    j = start
    i = stop
    while j < newlength:
        l.ll_setitem_fast(j, l.ll_getitem_fast(i))
        i += 1
        j += 1
    null = ll_null_item(l)
    if null is not None:
        j = length - 1
        while j >= newlength:
            l.ll_setitem_fast(j, null)
            j -= 1
    l._ll_resize_le(newlength)

def ll_listsetslice(l1, slice, l2):
    count = l2.ll_length()
    start = slice.start
    ll_assert(start >= 0, "l[start:x] = l with unexpectedly negative start")
    ll_assert(start <= l1.ll_length(), "l[start:x] = l with start > len(l)")
    ll_assert(count == slice.stop - start,
                 "setslice cannot resize lists in RPython")
    # XXX but it should be easy enough to support, soon
    j = start
    i = 0
    while i < count:
        l1.ll_setitem_fast(j, l2.ll_getitem_fast(i))
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
    while j < len1:
        if eqfn is None:
            if l1.ll_getitem_fast(j) != l2.ll_getitem_fast(j):
                return False
        else:
            if not eqfn(l1.ll_getitem_fast(j), l2.ll_getitem_fast(j)):
                return False
        j += 1
    return True

def ll_listcontains(lst, obj, eqfn):
    lng = lst.ll_length()
    j = 0
    while j < lng:
        if eqfn is None:
            if lst.ll_getitem_fast(j) == obj:
                return True
        else:
            if eqfn(lst.ll_getitem_fast(j), obj):
                return True
        j += 1
    return False

def ll_listindex(lst, obj, eqfn):
    lng = lst.ll_length()
    j = 0
    while j < lng:
        if eqfn is None:
            if lst.ll_getitem_fast(j) == obj:
                return j
        else:
            if eqfn(lst.ll_getitem_fast(j), obj):
                return j
        j += 1
    raise ValueError # can't say 'list.index(x): x not in list'

def ll_listremove(lst, obj, eqfn):
    index = ll_listindex(lst, obj, eqfn) # raises ValueError if obj not in lst
    ll_delitem_nonneg(dum_nocheck, lst, index)
ll_listremove.oopspec = 'list.remove(obj)'

def ll_inplace_mul(l, factor):
    length = l.ll_length()
    if factor < 0:
        factor = 0
    try:
        resultlen = ovfcheck(length * factor)
    except OverflowError:
        raise MemoryError
    res = l
    res._ll_resize(resultlen)
    #res._ll_resize_ge(resultlen)
    j = length
    while j < resultlen:
        i = 0
        while i < length:
            p = j + i
            res.ll_setitem_fast(p, l.ll_getitem_fast(i))
            i += 1
        j += length
    return res


def ll_mul(RESLIST, l, factor):
    length = l.ll_length()
    if factor < 0:
        factor = 0
    try:
        resultlen = ovfcheck(length * factor)
    except OverflowError:
        raise MemoryError
    res = RESLIST.ll_newlist(resultlen)
    j = 0
    while j < resultlen:
        i = 0
        while i < length:
            p = j + i
            res.ll_setitem_fast(p, l.ll_getitem_fast(i))
            i += 1
        j += length
    return res

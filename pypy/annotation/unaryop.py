"""
Unary operations on SomeValues.
"""

from types import MethodType
from pypy.annotation.model import \
     SomeObject, SomeInteger, SomeBool, SomeString, SomeChar, SomeList, \
     SomeDict, SomeTuple, SomeImpossibleValue, SomeUnicodeCodePoint, \
     SomeInstance, SomeBuiltin, SomeFloat, SomeIterator, SomePBC, \
     SomeExternalObject, SomeTypedAddressAccess, SomeAddress, \
     s_ImpossibleValue, s_Bool, s_None, \
     unionof, missing_operation, add_knowntypedata, HarmlesslyBlocked, \
     SomeGenericCallable, SomeWeakRef, SomeUnicodeString
from pypy.annotation.bookkeeper import getbookkeeper
from pypy.annotation import builtin
from pypy.annotation.binaryop import _clone ## XXX where to put this?
from pypy.rpython import extregistry
from pypy.tool.error import AnnotatorError

# convenience only!
def immutablevalue(x):
    return getbookkeeper().immutablevalue(x)

UNARY_OPERATIONS = set(['len', 'is_true', 'getattr', 'setattr', 'delattr',
                        'simple_call', 'call_args', 'str', 'repr',
                        'iter', 'next', 'invert', 'type', 'issubtype',
                        'pos', 'neg', 'nonzero', 'abs', 'hex', 'oct',
                        'ord', 'int', 'float', 'long',
                        'hash', 'id',    # <== not supported any more
                        'getslice', 'setslice', 'delslice',
                        'neg_ovf', 'abs_ovf', 'hint', 'unicode', 'unichr'])

for opname in UNARY_OPERATIONS:
    missing_operation(SomeObject, opname)


class __extend__(SomeObject):

    def type(obj, *moreargs):
        if moreargs:
            raise Exception, 'type() called with more than one argument'
        if obj.is_constant():
            if isinstance(obj, SomeInstance):
                r = SomePBC([obj.classdef.classdesc])
            else:
                r = immutablevalue(obj.knowntype)
        else:
            r = SomeObject()
            r.knowntype = type
        bk = getbookkeeper()
        fn, block, i = bk.position_key
        annotator = bk.annotator
        op = block.operations[i]
        assert op.opname == "type"
        assert len(op.args) == 1
        assert annotator.binding(op.args[0]) == obj
        r.is_type_of = [op.args[0]]
        return r

    def issubtype(obj, s_cls):
        if hasattr(obj, 'is_type_of'):
            vars = obj.is_type_of
            annotator = getbookkeeper().annotator
            return builtin.builtin_isinstance(annotator.binding(vars[0]),
                                              s_cls, vars)
        if obj.is_constant() and s_cls.is_constant():
            return immutablevalue(issubclass(obj.const, s_cls.const))
        return s_Bool

    def len(obj):
        return SomeInteger(nonneg=True)

    def is_true_behavior(obj, s):
        if obj.is_immutable_constant():
            s.const = bool(obj.const)
        else:
            s_len = obj.len()
            if s_len.is_immutable_constant():
                s.const = s_len.const > 0

    def is_true(s_obj):
        r = SomeBool()
        s_obj.is_true_behavior(r)

        bk = getbookkeeper()
        knowntypedata = r.knowntypedata = {}
        fn, block, i = bk.position_key
        op = block.operations[i]
        assert op.opname == "is_true" or op.opname == "nonzero"
        assert len(op.args) == 1
        arg = op.args[0]
        s_nonnone_obj = s_obj
        if s_obj.can_be_none():
            s_nonnone_obj = s_obj.nonnoneify()
        add_knowntypedata(knowntypedata, True, [arg], s_nonnone_obj)
        return r
        

    def nonzero(obj):
        return obj.is_true()

    def hash(obj):
        raise TypeError, ("cannot use hash() in RPython; "
                          "see objectmodel.compute_xxx()")

    def str(obj):
        getbookkeeper().count('str', obj)
        return SomeString()

    def unicode(obj):
        getbookkeeper().count('unicode', obj)
        return SomeUnicodeString()

    def repr(obj):
        getbookkeeper().count('repr', obj)
        return SomeString()

    def hex(obj):
        getbookkeeper().count('hex', obj)
        return SomeString()

    def oct(obj):
        getbookkeeper().count('oct', obj)
        return SomeString()

    def id(obj):
        raise Exception("cannot use id() in RPython; "
                        "see objectmodel.compute_xxx()")

    def int(obj):
        return SomeInteger()

    def float(obj):
        return SomeFloat()

    def long(obj):
        return SomeObject()   # XXX

    def delattr(obj, s_attr):
        if obj.__class__ != SomeObject or obj.knowntype != object:
            getbookkeeper().warning(
                ("delattr on potentally non-SomeObjects is not RPythonic: delattr(%r,%r)" %
                 (obj, s_attr)))

    def find_method(obj, name):
        "Look for a special-case implementation for the named method."
        try:
            analyser = getattr(obj.__class__, 'method_' + name)
        except AttributeError:
            return None
        else:
            return SomeBuiltin(analyser, obj, name)

    def getattr(obj, s_attr):
        # get a SomeBuiltin if the SomeObject has
        # a corresponding method to handle it
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            s_method = obj.find_method(attr)
            if s_method is not None:
                return s_method
            # if the SomeObject is itself a constant, allow reading its attrs
            if obj.is_immutable_constant() and hasattr(obj.const, attr):
                return immutablevalue(getattr(obj.const, attr))
        else:
            getbookkeeper().warning('getattr(%r, %r) is not RPythonic enough' %
                                    (obj, s_attr))
        return SomeObject()
    getattr.can_only_throw = []

    def bind_callables_under(obj, classdef, name):
        return obj   # default unbound __get__ implementation

    def simple_call(obj, *args_s):
        return obj.call(getbookkeeper().build_args("simple_call", args_s))

    def call_args(obj, *args_s):
        return obj.call(getbookkeeper().build_args("call_args", args_s))

    def call(obj, args, implicit_init=False):
        #raise Exception, "cannot follow call_args%r" % ((obj, args),)
        getbookkeeper().warning("cannot follow call(%r, %r)" % (obj, args))
        return SomeObject()

    def op_contains(obj, s_element):
        return s_Bool
    op_contains.can_only_throw = []

    def hint(self, *args_s):
        return self

class __extend__(SomeFloat):

    def pos(flt):
        return flt

    def neg(flt):
        return SomeFloat()

    abs = neg

    def is_true(self):
        if self.is_immutable_constant():
            return getbookkeeper().immutablevalue(bool(self.const))
        return s_Bool

class __extend__(SomeInteger):

    def invert(self):
        return SomeInteger(knowntype=self.knowntype)
    invert.can_only_throw = []

    def pos(self):
        return SomeInteger(knowntype=self.knowntype)

    pos.can_only_throw = []
    int = pos

    # these are the only ones which can overflow:

    def neg(self):
        return SomeInteger(knowntype=self.knowntype)

    neg.can_only_throw = []
    neg_ovf = _clone(neg, [OverflowError])

    def abs(self):
        return SomeInteger(nonneg=True, knowntype=self.knowntype)

    abs.can_only_throw = []
    abs_ovf = _clone(abs, [OverflowError])

class __extend__(SomeBool):
    def is_true(self):
        return self

    def invert(self):
        return SomeInteger()

    invert.can_only_throw = []

    def neg(self):
        return SomeInteger()

    neg.can_only_throw = []
    neg_ovf = _clone(neg, [OverflowError])

    def abs(self):
        return SomeInteger(nonneg=True)

    abs.can_only_throw = []
    abs_ovf = _clone(abs, [OverflowError])

    def pos(self):
        return SomeInteger(nonneg=True)

    pos.can_only_throw = []
    int = pos

class __extend__(SomeTuple):

    def len(tup):
        return immutablevalue(len(tup.items))

    def iter(tup):
        getbookkeeper().count("tuple_iter", tup)
        return SomeIterator(tup)
    iter.can_only_throw = []

    def getanyitem(tup):
        return unionof(*tup.items)

    def getslice(tup, s_start, s_stop):
        assert s_start.is_immutable_constant(),"tuple slicing: needs constants"
        assert s_stop.is_immutable_constant(), "tuple slicing: needs constants"
        items = tup.items[s_start.const:s_stop.const]
        return SomeTuple(items)


class __extend__(SomeList):

    def method_append(lst, s_value):
        lst.listdef.resize()
        lst.listdef.generalize(s_value)

    def method_extend(lst, s_iterable):
        lst.listdef.resize()
        if isinstance(s_iterable, SomeList):   # unify the two lists
            lst.listdef.agree(s_iterable.listdef)
        else:
            s_iter = s_iterable.iter()
            lst.method_append(s_iter.next())

    def method_reverse(lst):
        lst.listdef.mutate()

    def method_insert(lst, s_index, s_value):
        lst.method_append(s_value)

    def method_remove(lst, s_value):
        lst.listdef.resize()
        lst.listdef.generalize(s_value)

    def method_pop(lst, s_index=None):
        lst.listdef.resize()
        return lst.listdef.read_item()
    method_pop.can_only_throw = [IndexError]

    def method_index(lst, s_value):
        getbookkeeper().count("list_index")
        lst.listdef.generalize(s_value)
        return SomeInteger(nonneg=True)

    def len(lst):
        s_item = lst.listdef.read_item()
        if isinstance(s_item, SomeImpossibleValue):
            return immutablevalue(0)
        return SomeObject.len(lst)

    def iter(lst):
        return SomeIterator(lst)
    iter.can_only_throw = []

    def getanyitem(lst):
        return lst.listdef.read_item()

    def op_contains(lst, s_element):
        lst.listdef.generalize(s_element)
        return s_Bool
    op_contains.can_only_throw = []

    def hint(lst, *args_s):
        hints = args_s[-1].const
        if 'maxlength' in hints:
            # only for iteration over lists or dicts at the moment,
            # not over an iterator object (because it has no known length)
            s_iterable = args_s[0]
            if isinstance(s_iterable, (SomeList, SomeDict)):
                lst = SomeList(lst.listdef) # create a fresh copy
                lst.known_maxlength = True
                lst.listdef.resize()
                lst.listdef.listitem.hint_maxlength = True
        elif 'fence' in hints:
            lst = lst.listdef.offspring()
        return lst

    def getslice(lst, s_start, s_stop):
        check_negative_slice(s_start, s_stop)
        return lst.listdef.offspring()

    def setslice(lst, s_start, s_stop, s_iterable):
        check_negative_slice(s_start, s_stop)
        if not isinstance(s_iterable, SomeList):
            raise Exception("list[start:stop] = x: x must be a list")
        lst.listdef.agree(s_iterable.listdef)
        # note that setslice is not allowed to resize a list in RPython

    def delslice(lst, s_start, s_stop):
        check_negative_slice(s_start, s_stop)
        lst.listdef.resize()

def check_negative_slice(s_start, s_stop):
    if isinstance(s_start, SomeInteger) and not s_start.nonneg:
        raise TypeError("slicing: not proven to have non-negative start")
    if isinstance(s_stop, SomeInteger) and not s_stop.nonneg and \
           getattr(s_stop, 'const', 0) != -1:
        raise TypeError("slicing: not proven to have non-negative stop")


class __extend__(SomeDict):

    def _is_empty(dct):
        s_key = dct.dictdef.read_key()
        s_value = dct.dictdef.read_value()
        return (isinstance(s_key, SomeImpossibleValue) or
                isinstance(s_value, SomeImpossibleValue))
        
    def len(dct):
        if dct._is_empty():
            return immutablevalue(0)
        return SomeObject.len(dct)

    def iter(dct):
        return SomeIterator(dct)
    iter.can_only_throw = []

    def getanyitem(dct, variant='keys'):
        if variant == 'keys':
            return dct.dictdef.read_key()
        elif variant == 'values':
            return dct.dictdef.read_value()
        elif variant == 'items':
            s_key   = dct.dictdef.read_key()
            s_value = dct.dictdef.read_value()
            if (isinstance(s_key, SomeImpossibleValue) or
                isinstance(s_value, SomeImpossibleValue)):
                return s_ImpossibleValue
            else:
                return SomeTuple((s_key, s_value))
        else:
            raise ValueError

    def method_get(dct, key, dfl):
        dct.dictdef.generalize_key(key)
        dct.dictdef.generalize_value(dfl)
        return dct.dictdef.read_value()

    method_setdefault = method_get

    def method_copy(dct):
        return SomeDict(dct.dictdef)

    def method_update(dct1, dct2):
        if s_None.contains(dct2):
            return SomeImpossibleValue()
        dct1.dictdef.union(dct2.dictdef)

    def method_keys(dct):
        return getbookkeeper().newlist(dct.dictdef.read_key())

    def method_values(dct):
        return getbookkeeper().newlist(dct.dictdef.read_value())

    def method_items(dct):
        return getbookkeeper().newlist(dct.getanyitem('items'))

    def method_iterkeys(dct):
        return SomeIterator(dct, 'keys')

    def method_itervalues(dct):
        return SomeIterator(dct, 'values')

    def method_iteritems(dct):
        return SomeIterator(dct, 'items')

    def method_clear(dct):
        pass

    def method_popitem(dct):
        return dct.getanyitem('items')

    def _can_only_throw(dic, *ignore):
        if dic1.dictdef.dictkey.custom_eq_hash:
            return None    # r_dict: can throw anything
        return []          # else: no possible exception

    def op_contains(dct, s_element):
        dct.dictdef.generalize_key(s_element)
        if dct._is_empty():
            s_bool = SomeBool()
            s_bool.const = False
            return s_bool
        return s_Bool
    op_contains.can_only_throw = _can_only_throw


class __extend__(SomeString,
                 SomeUnicodeString):

    def method_startswith(str, frag):
        return s_Bool

    def method_endswith(str, frag):
        return s_Bool

    def method_find(str, frag, start=None, end=None):
        return SomeInteger()

    def method_rfind(str, frag, start=None, end=None):
        return SomeInteger()

    def method_count(str, frag, start=None, end=None):
        return SomeInteger(nonneg=True)

    def method_strip(str, chr):
        return str.basestringclass()

    def method_lstrip(str, chr):
        return str.basestringclass()

    def method_rstrip(str, chr):
        return str.basestringclass()

    def method_join(str, s_list):
        if s_None.contains(s_list):
            return SomeImpossibleValue()
        getbookkeeper().count("str_join", str)
        s_item = s_list.listdef.read_item()
        if isinstance(s_item, SomeImpossibleValue):
            if isinstance(str, SomeUnicodeString):
                return immutablevalue(u"")
            return immutablevalue("")
        return str.basestringclass()

    def iter(str):
        return SomeIterator(str)
    iter.can_only_throw = []

    def getanyitem(str):
        return str.basecharclass()

    def method_split(str, patt, max=-1):
        getbookkeeper().count("str_split", str, patt)
        return getbookkeeper().newlist(str.basestringclass())

    def method_rsplit(str, patt, max=-1):
        getbookkeeper().count("str_rsplit", str, patt)
        return getbookkeeper().newlist(str.basestringclass())

    def method_replace(str, s1, s2):
        return str.basestringclass()

    def getslice(str, s_start, s_stop):
        check_negative_slice(s_start, s_stop)
        return str.basestringclass()

class __extend__(SomeUnicodeString):
    def method_encode(uni, s_enc):
        if not s_enc.is_constant():
            raise TypeError("Non-constant encoding not supported")
        enc = s_enc.const
        if enc not in ('ascii', 'latin-1'):
            raise TypeError("Encoding %s not supported for unicode" % (enc,))
        return SomeString()
    method_encode.can_only_throw = [UnicodeEncodeError]

class __extend__(SomeString):
    def method_upper(str):
        return SomeString()

    def method_lower(str):
        return SomeString()

    def method_splitlines(str, s_keep_newlines=None):
        s_list = getbookkeeper().newlist(str.basestringclass())
        # Force the list to be resizable because ll_splitlines doesn't
        # preallocate the list.
        s_list.listdef.listitem.resize()
        return s_list

    def method_decode(str, s_enc):
        if not s_enc.is_constant():
            raise TypeError("Non-constant encoding not supported")
        enc = s_enc.const
        if enc not in ('ascii', 'latin-1'):
            raise TypeError("Encoding %s not supported for strings" % (enc,))
        return SomeUnicodeString()
    method_decode.can_only_throw = [UnicodeDecodeError]

class __extend__(SomeChar, SomeUnicodeCodePoint):

    def len(chr):
        return immutablevalue(1)

    def ord(str):
        return SomeInteger(nonneg=True)

class __extend__(SomeChar):

    def method_isspace(chr):
        return s_Bool

    def method_isdigit(chr):
        return s_Bool

    def method_isalpha(chr):
        return s_Bool

    def method_isalnum(chr):
        return s_Bool

    def method_islower(chr):
        return s_Bool

    def method_isupper(chr):
        return s_Bool

class __extend__(SomeIterator):

    def iter(itr):
        return itr
    iter.can_only_throw = []

    def _can_only_throw(itr):
        can_throw = [StopIteration]
        if isinstance(itr.s_container, SomeDict):
            can_throw.append(RuntimeError)
        return can_throw

    def next(itr):
        if itr.variant == ("enumerate",):
            s_item = itr.s_container.getanyitem()
            return SomeTuple((SomeInteger(nonneg=True), s_item))
        return itr.s_container.getanyitem(*itr.variant)
    next.can_only_throw = _can_only_throw
    method_next = next


class __extend__(SomeInstance):

    def getattr(ins, s_attr):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            if attr == '__class__':
                return ins.classdef.read_attr__class__()
            attrdef = ins.classdef.find_attribute(attr)
            position = getbookkeeper().position_key
            attrdef.read_locations[position] = True
            s_result = attrdef.getvalue()
            # hack: if s_result is a set of methods, discard the ones
            #       that can't possibly apply to an instance of ins.classdef.
            # XXX do it more nicely
            if isinstance(s_result, SomePBC):
                s_result = ins.classdef.lookup_filter(s_result, attr,
                                                      ins.flags)
            elif isinstance(s_result, SomeImpossibleValue):
                ins.classdef.check_missing_attribute_update(attr)
                # blocking is harmless if the attribute is explicitly listed
                # in the class or a parent class.
                for basedef in ins.classdef.getmro():
                    if basedef.classdesc.all_enforced_attrs is not None:
                        if attr in basedef.classdesc.all_enforced_attrs:
                            raise HarmlesslyBlocked("get enforced attr")
            elif isinstance(s_result, SomeList):
                s_result = ins.classdef.classdesc.maybe_return_immutable_list(
                    attr, s_result)
            return s_result
        return SomeObject()
    getattr.can_only_throw = []

    def setattr(ins, s_attr, s_value):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            # find the (possibly parent) class where this attr is defined
            clsdef = ins.classdef.locate_attribute(attr)
            attrdef = clsdef.attrs[attr]
            attrdef.modified(clsdef)

            # if the attrdef is new, this must fail
            if attrdef.getvalue().contains(s_value):
                return
            # create or update the attribute in clsdef
            clsdef.generalize_attr(attr, s_value)

    def is_true_behavior(ins, s):
        if not ins.can_be_None:
            s.const = True


class __extend__(SomeBuiltin):
    def _can_only_throw(bltn, *args):
        analyser_func = getattr(bltn.analyser, 'im_func', None)
        can_only_throw = getattr(analyser_func, 'can_only_throw', None)
        if can_only_throw is None or isinstance(can_only_throw, list):
            return can_only_throw
        if bltn.s_self is not None:
            return can_only_throw(bltn.s_self, *args)
        else:
            return can_only_throw(*args)

    def simple_call(bltn, *args):
        if bltn.s_self is not None:
            return bltn.analyser(bltn.s_self, *args)
        else:
            if bltn.methodname:
                getbookkeeper().count(bltn.methodname.replace('.', '_'), *args)
            return bltn.analyser(*args)
    simple_call.can_only_throw = _can_only_throw

    def call(bltn, args, implicit_init=False):
        args_s, kwds = args.unpack()
        # prefix keyword arguments with 's_'
        kwds_s = {}
        for key, s_value in kwds.items():
            kwds_s['s_'+key] = s_value
        if bltn.s_self is not None:
            return bltn.analyser(bltn.s_self, *args_s, **kwds_s)
        else:
            return bltn.analyser(*args_s, **kwds_s)


class __extend__(SomePBC):

    def getattr(pbc, s_attr):
        bookkeeper = getbookkeeper()
        return bookkeeper.pbc_getattr(pbc, s_attr)
    getattr.can_only_throw = []

    def setattr(pbc, s_attr, s_value):
        if not pbc.isNone():
            raise AnnotatorError("setattr on %r" % pbc)

    def call(pbc, args):
        bookkeeper = getbookkeeper()
        return bookkeeper.pbc_call(pbc, args)

    def bind_callables_under(pbc, classdef, name):
        d = [desc.bind_under(classdef, name) for desc in pbc.descriptions]
        return SomePBC(d, can_be_None=pbc.can_be_None)

    def is_true_behavior(pbc, s):
        if pbc.isNone():
            s.const = False
        elif not pbc.can_be_None:
            s.const = True

    def len(pbc):
        if pbc.isNone():
            # this None could later be generalized into an empty list,
            # whose length is the constant 0; so let's tentatively answer 0.
            return immutablevalue(0)
        else:
            return SomeObject()    # len() on a pbc? no chance

class __extend__(SomeGenericCallable):
    def call(self, args):
        bookkeeper = getbookkeeper()
        for arg, expected in zip(args.unpack()[0], self.args_s):
            assert expected.contains(arg)
        
        return self.s_result

class __extend__(SomeExternalObject):
    def getattr(p, s_attr):
        if s_attr.is_constant() and isinstance(s_attr.const, str):
            attr = s_attr.const
            entry = extregistry.lookup_type(p.knowntype)
            s_value = entry.get_field_annotation(p.knowntype, attr)
            return s_value
        else:
            return SomeObject()
    getattr.can_only_throw = []
    
    def setattr(p, s_attr, s_value):
        assert s_attr.is_constant()
        attr = s_attr.const
        entry = extregistry.lookup_type(p.knowntype)
        entry.set_field_annotation(p.knowntype, attr, s_value)
    
    def is_true(p):
        return s_Bool

# annotation of low-level types
from pypy.annotation.model import SomePtr, SomeLLADTMeth
from pypy.annotation.model import SomeOOInstance, SomeOOBoundMeth, SomeOOStaticMeth
from pypy.annotation.model import ll_to_annotation, lltype_to_annotation, annotation_to_lltype

class __extend__(SomePtr):

    def getattr(p, s_attr):
        assert s_attr.is_constant(), "getattr on ptr %r with non-constant field-name" % p.ll_ptrtype
        example = p.ll_ptrtype._example()
        try:
            v = example._lookup_adtmeth(s_attr.const)
        except AttributeError:
            v = getattr(example, s_attr.const)
            return ll_to_annotation(v)
        else:
            if isinstance(v, MethodType):
                from pypy.rpython.lltypesystem import lltype
                ll_ptrtype = lltype.typeOf(v.im_self)
                assert isinstance(ll_ptrtype, (lltype.Ptr, lltype.InteriorPtr))
                return SomeLLADTMeth(ll_ptrtype, v.im_func)
            return getbookkeeper().immutablevalue(v)
    getattr.can_only_throw = []

    def len(p):
        length = p.ll_ptrtype._example()._fixedlength()
        if length is None:
            return SomeObject.len(p)
        else:
            return immutablevalue(length)

    def setattr(p, s_attr, s_value): # just doing checking
        assert s_attr.is_constant(), "setattr on ptr %r with non-constant field-name" % p.ll_ptrtype
        example = p.ll_ptrtype._example()
        if getattr(example, s_attr.const) is not None:  # ignore Void s_value
            v_lltype = annotation_to_lltype(s_value)
            setattr(example, s_attr.const, v_lltype._defl())

    def call(p, args):
        args_s, kwds_s = args.unpack()
        if kwds_s:
            raise Exception("keyword arguments to call to a low-level fn ptr")
        info = 'argument to ll function pointer call'
        llargs = [annotation_to_lltype(s_arg,info)._defl() for s_arg in args_s]
        v = p.ll_ptrtype._example()(*llargs)
        return ll_to_annotation(v)

    def is_true(p):
        return s_Bool

class __extend__(SomeLLADTMeth):

    def call(adtmeth, args):
        bookkeeper = getbookkeeper()
        s_func = bookkeeper.immutablevalue(adtmeth.func)
        return s_func.call(args.prepend(lltype_to_annotation(adtmeth.ll_ptrtype)))

from pypy.rpython.ootypesystem import ootype
class __extend__(SomeOOInstance):
    def getattr(r, s_attr):
        assert s_attr.is_constant(), "getattr on ref %r with non-constant field-name" % r.ootype
        v = getattr(r.ootype._example(), s_attr.const)
        if isinstance(v, ootype._bound_meth):
            return SomeOOBoundMeth(r.ootype, s_attr.const)
        return ll_to_annotation(v)

    def setattr(r, s_attr, s_value): 
        assert s_attr.is_constant(), "setattr on ref %r with non-constant field-name" % r.ootype
        v = annotation_to_lltype(s_value)
        example = r.ootype._example()
        if example is not None:
            setattr(r.ootype._example(), s_attr.const, v._example())

    def is_true(p):
        return s_Bool

class __extend__(SomeOOBoundMeth):
    def simple_call(m, *args_s):
        _, meth = m.ootype._lookup(m.name)
        if isinstance(meth, ootype._overloaded_meth):
            return meth._resolver.annotate(args_s)
        else:
            METH = ootype.typeOf(meth)
            return lltype_to_annotation(METH.RESULT)

    def call(m, args):
        args_s, kwds_s = args.unpack()
        if kwds_s:
            raise Exception("keyword arguments to call to a low-level bound method")
        inst = m.ootype._example()
        _, meth = ootype.typeOf(inst)._lookup(m.name)
        METH = ootype.typeOf(meth)
        return lltype_to_annotation(METH.RESULT)


class __extend__(SomeOOStaticMeth):

    def call(m, args):
        args_s, kwds_s = args.unpack()
        if kwds_s:
            raise Exception("keyword arguments to call to a low-level static method")
        info = 'argument to ll static method call'
        llargs = [annotation_to_lltype(s_arg, info)._defl() for s_arg in args_s]
        v = m.method._example()(*llargs)
        return ll_to_annotation(v)


#_________________________________________
# weakrefs

class __extend__(SomeWeakRef):
    def simple_call(s_wrf):
        if s_wrf.classdef is None:
            return s_None   # known to be a dead weakref
        else:
            return SomeInstance(s_wrf.classdef, can_be_None=True)

#_________________________________________
# memory addresses

from pypy.rpython.lltypesystem import llmemory

class __extend__(SomeAddress):
    def getattr(s_addr, s_attr):
        assert s_attr.is_constant()
        assert isinstance(s_attr, SomeString)
        assert s_attr.const in llmemory.supported_access_types
        return SomeTypedAddressAccess(
            llmemory.supported_access_types[s_attr.const])
    getattr.can_only_throw = []

    def is_true(s_addr):
        return s_Bool

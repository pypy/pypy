import py
from pypy.interpreter.typedef import check_new_dictionary
from pypy.objspace.std.dictmultiobject import W_DictMultiObject
from pypy.objspace.std.dictmultiobject import StrDictImplementation
from pypy.objspace.std.dictmultiobject import IteratorImplementation
from pypy.objspace.std.dictmultiobject import implementation_methods
from pypy.tool.sourcetools import func_with_new_name

def make_mixin(config):
    if config.objspace.std.withsharingdict:
        from pypy.objspace.std.sharingdict import SharedDictImplementation
        return make_inlinedict_mixin(SharedDictImplementation, "structure")
    else:
        return make_inlinedict_mixin(StrDictImplementation, "content")

def make_indirection_method(methname, numargs):
    # *args don't work, the call normalization gets confused
    args = ", ".join(["a" + str(i) for i in range(numargs)])
    code = """def f(self, %s):
    return self.w_obj.%s(%s)
""" % (args, methname, args)
    d = {}
    exec py.code.Source(code).compile() in d
    func = d["f"]
    func.func_name = methname + "_indirect"
    func.func_defaults = getattr(W_DictMultiObject, methname).func_defaults
    return func

def make_inlinedict_mixin(dictimplclass, attrname):
    assert dictimplclass.__base__ is W_DictMultiObject
    class IndirectionIterImplementation(IteratorImplementation):
        def __init__(self, space, dictimpl, itemlist):
            IteratorImplementation.__init__(self, space, dictimpl)
            self.itemlist = itemlist

        def next_entry(self):
            return self.itemlist[self.pos]
            
    class IndirectionDictImplementation(W_DictMultiObject):
        def __init__(self, space, w_obj):
            self.space = space
            self.w_obj = w_obj

        def impl_iter(self):
            # XXX sucky
            items = []
            for w_item in self.impl_items():
                w_key, w_value = self.space.fixedview(w_item)
                items.append((w_key, w_value))
            return IndirectionIterImplementation(self.space, self, items)

    IndirectionDictImplementation.__name__ = "IndirectionDictImplementation" + dictimplclass.__name__

    for methname, numargs in implementation_methods:
        implname = "impl_" + methname
        if implname != "impl_iter":
            setattr(IndirectionDictImplementation, implname,
                    make_indirection_method(implname, numargs))

    init_dictattributes = func_with_new_name(dictimplclass.__init__.im_func,
                                             "init_dictattributes")
    make_rdict = func_with_new_name(dictimplclass._as_rdict.im_func,
                                    "make_rdict")
    clear_fields = func_with_new_name(dictimplclass._clear_fields.im_func,
                                      "clear_fields")

    class InlineDictMixin(object):

        def user_setup(self, space, w_subtype):
            self.space = space
            self.w__class__ = w_subtype
            self.w__dict__ = None
            init_dictattributes(self, space)
            assert getattr(self, attrname) is not None
            self.user_setup_slots(w_subtype.nslots)

        def getdict(self):
            w__dict__ = self.w__dict__
            if w__dict__ is None:
                w__dict__ = IndirectionDictImplementation(self.space, self)
                self.w__dict__ = w__dict__
            assert isinstance(w__dict__, W_DictMultiObject)
            return w__dict__

        def _inlined_dict_valid(self):
            return getattr(self, attrname) is not None

        def getdictvalue(self, space, attr):
            if self._inlined_dict_valid():
                return self.impl_getitem_str(attr)
            w_dict = self.getdict()
            return w_dict.getitem_str(attr)

        def getdictvalue_attr_is_in_class(self, space, attr):
            return self.getdictvalue(space, attr)

        def setdictvalue(self, space, attr, w_value, shadows_type=True):
            if self._inlined_dict_valid():
                # XXX so far we ignore shadows_type, which is a small
                # performance-degradation if the JIT is not used (i.e. shadow
                # tracking does not work). Maybe we don't care.
                self.impl_setitem_str(attr, w_value)
                return True
            w_dict = self.getdict()
            w_dict.setitem_str(attr, w_value)
            return True

        def deldictvalue(self, space, w_attr):
            if self._inlined_dict_valid():
                try:
                    self.impl_delitem(w_attr)
                except KeyError:
                    return False
                return True
            w_dict = self.getdict()
            try:
                w_dict.delitem(w_attr)
            except KeyError:
                return False
            return True

        def setdict(self, space, w_dict):
            # if somebody asked for the __dict__, and it did not devolve, it
            # needs to stay valid even if we set a new __dict__ on this object
            if self.w__dict__ is not None and self._inlined_dict_valid():
                make_rdict(self)
            self._clear_fields() # invalidate attributes on self
            self.w__dict__ = check_new_dictionary(space, w_dict)

        def _as_rdict(self):
            make_rdict(self)
            return self.getdict()

        def initialize_as_rdict(self):
            return self.getdict().initialize_as_rdict()
        
        _clear_fields = clear_fields

    for methname, _ in implementation_methods:
        implname = "impl_" + methname
        meth = func_with_new_name(getattr(dictimplclass, implname).im_func,
                                  implname)
        if not hasattr(InlineDictMixin, implname):
            setattr(InlineDictMixin, implname, meth)
    return InlineDictMixin

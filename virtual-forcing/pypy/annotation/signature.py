
import types
from pypy.annotation.model import SomeBool, SomeInteger, SomeString,\
     SomeFloat, SomeList, SomeDict, s_None, \
     SomeObject, SomeInstance, SomeTuple, lltype_to_annotation,\
     unionof, SomeUnicodeString
from pypy.annotation.listdef import ListDef, MOST_GENERAL_LISTDEF
from pypy.annotation.dictdef import DictDef, MOST_GENERAL_DICTDEF

_annotation_cache = {}

def _annotation_key(t):
    from pypy.rpython import extregistry
    if type(t) is list:
        assert len(t) == 1
        return ('list', _annotation_key(t[0]))
    elif type(t) is dict:
        assert len(t.keys()) == 1
        return ('dict', _annotation_key(t.items()[0]))
    elif isinstance(t, tuple):
        return tuple([_annotation_key(i) for i in t])
    elif extregistry.is_registered(t):
        # XXX should it really be always different?
        return t
    return t

def annotation(t, bookkeeper=None):
    if bookkeeper is None:
        key = _annotation_key(t)
        try:
            return _annotation_cache[key]
        except KeyError:
            t = _compute_annotation(t, bookkeeper)
            _annotation_cache[key] = t
            return t
    return _compute_annotation(t, bookkeeper)

def _compute_annotation(t, bookkeeper=None):
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython import extregistry
    if isinstance(t, SomeObject):
        return t
    elif isinstance(t, lltype.LowLevelType):
        return lltype_to_annotation(t)
    elif isinstance(t, list):
        assert len(t) == 1, "We do not support type joining in list"
        listdef = ListDef(bookkeeper, annotation(t[0]), mutated=True, resized=True)
        return SomeList(listdef)
    elif isinstance(t, tuple):
        return SomeTuple(tuple([annotation(i) for i in t]))
    elif isinstance(t, dict):
        assert len(t) == 1, "We do not support type joining in dict"
        result = SomeDict(DictDef(bookkeeper, annotation(t.keys()[0]),
                                annotation(t.values()[0])))
        return result
    elif type(t) is types.NoneType:
        return s_None
    elif extregistry.is_registered(t):
        entry = extregistry.lookup(t)
        entry.bookkeeper = bookkeeper
        return entry.compute_result_annotation()
    else:
        return annotationoftype(t, bookkeeper)

def annotationoftype(t, bookkeeper=False):
    from pypy.rpython import extregistry

    """The most precise SomeValue instance that contains all
    objects of type t."""
    assert isinstance(t, (type, types.ClassType))
    if t is bool:
        return SomeBool()
    elif t is int:
        return SomeInteger()
    elif t is float:
        return SomeFloat()
    elif issubclass(t, str): # py.lib uses annotated str subclasses
        return SomeString()
    elif t is unicode:
        return SomeUnicodeString()
    elif t is list:
        return SomeList(MOST_GENERAL_LISTDEF)
    elif t is dict:
        return SomeDict(MOST_GENERAL_DICTDEF)
    # can't do tuple
    elif t is types.NoneType:
        return s_None
    elif bookkeeper and extregistry.is_registered_type(t, bookkeeper.policy):
        entry = extregistry.lookup_type(t, bookkeeper.policy)
        return entry.compute_annotation_bk(bookkeeper)
    elif bookkeeper and t.__module__ != '__builtin__' and t not in bookkeeper.pbctypes:
        classdef = bookkeeper.getuniqueclassdef(t)
        return SomeInstance(classdef)
    else:
        o = SomeObject()
        if t != object:
            o.knowntype = t
        return o

class Sig(object):

    def __init__(self, *argtypes):
        self.argtypes = argtypes
        
    def __call__(self, funcdesc, inputcells):
        from pypy.rpython.lltypesystem import lltype
        args_s = []
        from pypy.annotation import model as annmodel
        for i, argtype in enumerate(self.argtypes):
            if isinstance(argtype, (types.FunctionType, types.MethodType)):
                argtype = argtype(*inputcells)
            if isinstance(argtype, lltype.LowLevelType) and\
                argtype is lltype.Void:
                # XXX the mapping between Void and annotation
                # is not quite well defined
                s_input = inputcells[i]
                assert isinstance(s_input, annmodel.SomePBC)
                assert s_input.is_constant()
                args_s.append(s_input)
            elif argtype is None:
                args_s.append(inputcells[i])     # no change
            else:
                args_s.append(annotation(argtype, bookkeeper=funcdesc.bookkeeper))
        if len(inputcells) != len(args_s):
            raise Exception("%r: expected %d args, got %d" % (funcdesc,
                                                              len(args_s),
                                                              len(inputcells)))
        for i, (s_arg, s_input) in enumerate(zip(args_s, inputcells)):
            s_input = unionof(s_input, s_arg)
            if not s_arg.contains(s_input):
                raise Exception("%r argument %d:\n"
                                "expected %s,\n"
                                "     got %s" % (funcdesc, i+1,
                                             s_arg,
                                             s_input))
        inputcells[:] = args_s

"""
This file contains the interpreter-level code for pypy's _sre module.
Really, it's nothing but a very thin wrapper around the underlying
interpreter's _sre module (ie, the one written in C). Since the C
code can't be meaningfully optimized and this is nothing more than
a minimally thin layer that deals with wrapping and unwrapping,
there is no particular reason for any of this code to be RPython


    NOT RPython

"""

# NOTE: In some places, after setting f.unwrap_spec, the property
#   f.return_type has also been set. This has no effect whatsoever,
#   it was just a convenient way of documenting the return type,
#   which can be difficult to look up in _sre.c.


from pypy.interpreter.baseobjspace import Wrappable, W_Root, ObjSpace
from pypy.interpreter.gateway import NoneNotWrapped
from pypy.interpreter.error import OperationError
import _sre # This runs at interpreter level, so here we are importing the
            # C version of _sre provided by underlying virtual machine.



def _unwrap_list_of_ints(space, w_list):
    list_w = space.unpackiterable(w_list)
    list = [space.int_w(w_x) for w_x in list_w]
    return list
    
def _unwrap_dict_of_strings_to_ints(space, w_dict):
    w_items = space.call_method(w_dict, 'iteritems')
    items_w = space.unpackiterable(w_items)
    result = {}
    for item_w in items_w:
        w_key, w_value = space.unpackiterable(item_w)
        key = space.str_w(w_key)
        value = space.int_w(w_value)
        result[key] = value
    return result
    
def _unwrap_list_of_None_or_strings(space, w_list):
    list_w = space.unpackiterable(w_list)
    result = []
    for w_item in list_w:
        if space.is_w(w_item, space.w_None):
            result.append(None)
        else:
            result.append( space.str_w(w_item) )
    return result
    
def _unwrap_int_or_str(space, w_item):
    try:
        return space.int_w(w_item)
    except OperationError, e:
        if not e.match(space, space.w_TypeError):
            raise
        return space.str_w(w_item)
        
def _unwrap_list_of_ints_and_strings(space, w_list):
    list_w = space.unpackiterable(w_list)
    return [_unwrap_int_or_str(space, w_item) for w_item in list_w]
    


def _fget(space, w_wrapped, w_attr):
    """A generalized attribute accessor, this is passed a wrapped
    OpaqueObject and an attribute name. It performs getattr(wrapped, attr)
    and returns the wrapped version of the result."""
    wrapped = space.interpclass_w(w_wrapped).value
    attr = space.str_w(w_attr)
    result = getattr(wrapped, attr)
    return space.wrap(result)


class OpaqueObject(Wrappable):
    """This stores a single interpreter-level object ('value') and can be
    wrapped (via "o_w = space.wrap(o)") and unwrapped (via 
    "o = space.interpclass_w(o_w)").""" 
    def __init__(self, value):
        self.value = value


def getlower(space, character, flags):
    return space.wrap( _sre.getlower(character, flags) )
getlower.unwrap_spec = [ObjSpace, int, int]
getlower.return_type = int # just for documentation


def _compile(space, pattern, flags, w_code, groups=0,
            w_groupindex=NoneNotWrapped, w_indexgroup=NoneNotWrapped):
    """"compile" pattern descriptor to pattern object"""
    code = _unwrap_list_of_ints(space, w_code)
    groupindex = _unwrap_dict_of_strings_to_ints(space, w_groupindex)
    indexgroup = _unwrap_list_of_None_or_strings(space, w_indexgroup)
    
    pattern_obj = _sre.compile(pattern, flags, code, groups, groupindex, indexgroup)
    w_opaque_pattern_obj = space.wrap(OpaqueObject(pattern_obj))
    return w_opaque_pattern_obj
_compile.unwrap_spec = [ObjSpace, str, int, W_Root, int, W_Root, W_Root]


def _SRE_Pattern_match(space, w_wrapped, pattern, pos, endpos):
    wrapped = space.interpclass_w(w_wrapped).value
    match_obj = wrapped.match(pattern, pos, endpos)
    if match_obj is None:
        return space.w_None
    else:
        w_opaque_match_obj = space.wrap(OpaqueObject(match_obj))
        return w_opaque_match_obj
_SRE_Pattern_match.unwrap_spec = [ObjSpace, W_Root, str, int, int]

def _SRE_Pattern_search(space, w_wrapped, pattern, pos, endpos):
    wrapped = space.interpclass_w(w_wrapped).value
    match_obj = wrapped.search(pattern, pos, endpos)
    if match_obj is None:
        return space.w_None
    else:
        w_opaque_match_obj = space.wrap(OpaqueObject(match_obj))
        return w_opaque_match_obj
_SRE_Pattern_search.unwrap_spec = [ObjSpace, W_Root, str, int, int]

def _SRE_Pattern_findall(space, w_wrapped, string):
    wrapped = space.interpclass_w(w_wrapped).value
    result = wrapped.findall(string)
    return space.wrap(result)
_SRE_Pattern_findall.unwrap_spec = [ObjSpace, W_Root, str]
_SRE_Pattern_findall.return_type = 'list<str>' # just for documentation

def _SRE_Pattern_sub(space, w_wrapped, repl, string, count):
    wrapped = space.interpclass_w(w_wrapped).value
    result = wrapped.sub(repl, string, count)
    return space.wrap(result)
_SRE_Pattern_sub.unwrap_spec = [ObjSpace, W_Root, str, str, int]
_SRE_Pattern_sub.return_type = str # just for documentation

def _SRE_Pattern_subn(space, w_wrapped, repl, string, count):
    wrapped = space.interpclass_w(w_wrapped).value
    result = wrapped.subn(repl, string, count)
    return space.wrap(result)
_SRE_Pattern_subn.unwrap_spec = [ObjSpace, W_Root, str, str, int]
_SRE_Pattern_subn.return_type = 'tuple<str,int>' # just for documentation

def _SRE_Pattern_split(space, w_wrapped, string, maxsplit):
    wrapped = space.interpclass_w(w_wrapped).value
    result = wrapped.split(string, maxsplit)
    return space.wrap(result)
_SRE_Pattern_split.unwrap_spec = [ObjSpace, W_Root, str, int]
_SRE_Pattern_split.return_type = 'list<int>' # just for documentation

def _SRE_Pattern_finditer(space, w_wrapped, string):
    wrapped = space.interpclass_w(w_wrapped).value
    iter_obj = wrapped.finditer(string)
    return space.wrap(OpaqueObject(iter_obj))
_SRE_Pattern_finditer.unwrap_spec = [ObjSpace, W_Root, str]

def _SRE_Pattern_scanner(space, w_wrapped, string, start, end):
    wrapped = space.interpclass_w(w_wrapped).value
    scanner_obj = wrapped.scanner(string)
    return space.wrap(OpaqueObject(scanner_obj))
_SRE_Pattern_scanner.unwrap_spec = [ObjSpace, W_Root, str, int, int]


def _SRE_Match_start(space, w_wrapped, w_group):
    wrapped = space.interpclass_w(w_wrapped).value
    group = _unwrap_int_or_str(space, w_group)
    try:
        return space.wrap(wrapped.start(group))
    except IndexError, err:
        raise OperationError(space.w_IndexError, space.wrap(str(err)))
_SRE_Match_start.unwrap_spec = [ObjSpace, W_Root, W_Root]
_SRE_Match_start.return_type = int # just for documentation

def _SRE_Match_end(space, w_wrapped, w_group):
    wrapped = space.interpclass_w(w_wrapped).value
    group = _unwrap_int_or_str(space, w_group)
    try:
        return space.wrap(wrapped.end(group))
    except IndexError, err:
        raise OperationError(space.w_IndexError, space.wrap(str(err)))
_SRE_Match_end.unwrap_spec = [ObjSpace, W_Root, W_Root]
_SRE_Match_end.return_type = int # just for documentation

def _SRE_Match_span(space, w_wrapped, w_group):
    wrapped = space.interpclass_w(w_wrapped).value
    group = _unwrap_int_or_str(space, w_group)
    try:
        result_tuple = wrapped.span(group)
    except IndexError, err:
        raise OperationError(space.w_IndexError, space.wrap(str(err)))
    return space.newtuple( [space.wrap(x) for x in result_tuple] )
_SRE_Match_span.unwrap_spec = [ObjSpace, W_Root, W_Root]
_SRE_Match_span.return_type = '2-tuple<int>' # just for documentation

def _SRE_Match_expand(space, w_wrapped, template):
    wrapped = space.interpclass_w(w_wrapped).value
    return space.wrap(wrapped.expand(template))
_SRE_Match_expand.unwrap_spec = [ObjSpace, W_Root, str]
_SRE_Match_expand.return_type = str # just for documentation


def _SRE_Match_groups(space, w_wrapped, w_default):
    wrapped = space.interpclass_w(w_wrapped).value
    result = wrapped.groups(None)
    result_w = []
    for item in result:
        if item is None:
            result_w.append(w_default)
        else:
            result_w.append(space.wrap(item))
    return space.newtuple(result_w)
_SRE_Match_groups.unwrap_spec = [ObjSpace, W_Root, W_Root]
_SRE_Match_groups.return_type = 'tuple<str|default>' # just for documentation

def _SRE_Match_groupdict(space, w_wrapped, w_default):
    wrapped = space.interpclass_w(w_wrapped).value
    result = wrapped.groupdict(None)
    result_items_w = []
    for key, value in result.iteritems():
        w_key = space.wrap(key)
        if value is None:
            w_value = w_default
        else:
            w_value = space.wrap(value)
        result_items_w.append( (w_key, w_value) )
    w_result = space.newdict(result_items_w)
    return w_result
_SRE_Match_groupdict.unwrap_spec = [ObjSpace, W_Root, W_Root]
_SRE_Match_groupdict.return_type = 'dict<str: (str|default)>' # just for documentation

def _SRE_Match_group(space, w_wrapped, w_args):
    wrapped = space.interpclass_w(w_wrapped).value
    args = _unwrap_list_of_ints_and_strings(space, w_args)
    try:
        return space.wrap( wrapped.group(*args) )
    except IndexError, err:
        raise OperationError(space.w_IndexError, space.wrap(str(err)))
_SRE_Match_group.unwrap_spec = [ObjSpace, W_Root, W_Root]
_SRE_Match_group.return_type = 'str|tuple<str>|w_None' # just for documentation


def _SRE_Finditer_next(space, w_wrapped):
    wrapped = space.interpclass_w(w_wrapped).value
    try:
        match_obj = wrapped.next()
        return space.wrap(OpaqueObject(match_obj))
    except StopIteration, err:
        raise OperationError(space.w_StopIteration, space.wrap(""))
_SRE_Finditer_next.unwrap_spec = [ObjSpace, W_Root]


def _SRE_Scanner_match(space, w_wrapped):
    wrapped = space.interpclass_w(w_wrapped).value
    match_obj = wrapped.match()
    if match_obj is None:
        return space.w_None
    else:
        return space.wrap(OpaqueObject(match_obj))
_SRE_Scanner_match.unwrap_spec = [ObjSpace, W_Root]

def _SRE_Scanner_search(space, w_wrapped):
    wrapped = space.interpclass_w(w_wrapped).value
    match_obj = wrapped.search()
    if match_obj is None:
        return space.w_None
    else:
        return space.wrap(OpaqueObject(match_obj))
_SRE_Scanner_search.unwrap_spec = [ObjSpace, W_Root]

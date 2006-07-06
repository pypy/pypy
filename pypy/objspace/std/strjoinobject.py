from pypy.objspace.std.objspace import *
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import delegate_String2Unicode

from pypy.objspace.std.stringtype import joined

class W_StringJoinObject(W_Object):
    from pypy.objspace.std.stringtype import str_typedef as typedef

    def __init__(w_self, joined_strs):
        w_self.joined_strs = joined_strs

    def force(w_self):
        print "Force"
        if len(w_self.joined_strs) == 1:
            return w_self.joined_strs[0]
        res = "".join(w_self.joined_strs)
        w_self.joined_strs = [res]
        return res

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r)" % (w_self.__class__.__name__, w_self.joined_strs)


registerimplementation(W_StringJoinObject)

def delegate_join2str(space, w_strjoin):
    return W_StringObject(w_strjoin.force())

def delegate_join2unicode(space, w_strjoin):
    w_str = W_StringObject(w_strjoin.force())
    return delegate_String2Unicode(space, w_str)

def len__StringJoin(space, w_self):
    result = 0
    for s in w_self.joined_strs:
        result += len(s)
    return space.wrap(result)

def str_w__StringJoin(space, w_str):
    return w_str.force()

def add__StringJoin_StringJoin(space, w_self, w_other):
    return W_StringJoinObject(w_self.joined_strs + w_other.joined_strs)

def add__StringJoin_String(space, w_self, w_other):
    other = space.str_w(w_other)
    return W_StringJoinObject(w_self.joined_strs + [other])

def str__StringJoin(space, w_str):
    if type(w_str) is W_StringJoinObject:
        return w_str
    return W_StringJoinObject(w_str.joined_strs)

register_all(vars())

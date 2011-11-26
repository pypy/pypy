from pypy.objspace.std.model import registerimplementation, W_Object
from pypy.objspace.std.register_all import register_all
from pypy.objspace.std.stringobject import W_AbstractStringObject
from pypy.objspace.std.stringobject import W_StringObject
from pypy.objspace.std.unicodeobject import delegate_String2Unicode

from pypy.objspace.std.stringtype import wrapstr

class W_StringJoinObject(W_AbstractStringObject):
    from pypy.objspace.std.stringtype import str_typedef as typedef

    def __init__(w_self, joined_strs, until=-1):
        w_self.joined_strs = joined_strs
        if until == -1:
            until = len(joined_strs)
        w_self.until = until

    def force(w_self, always=False):
        if w_self.until == 1 and not always:
            return w_self.joined_strs[0]
        res = "".join(w_self.joined_strs[:w_self.until])
        w_self.joined_strs = [res]
        w_self.until = 1
        return res

    def __repr__(w_self):
        """ representation for debugging purposes """
        return "%s(%r, %r)" % (
            w_self.__class__.__name__, w_self.joined_strs, w_self.until)

    def unwrap(w_self, space):
        return w_self.force()
    str_w = unwrap

registerimplementation(W_StringJoinObject)

def delegate_join2str(space, w_strjoin):
    return wrapstr(space, w_strjoin.force())

def delegate_join2unicode(space, w_strjoin):
    w_str = wrapstr(space, w_strjoin.force())
    return delegate_String2Unicode(space, w_str)

def len__StringJoin(space, w_self):
    result = 0
    for i in range(w_self.until):
        result += len(w_self.joined_strs[i])
    return space.wrap(result)

def add__StringJoin_StringJoin(space, w_self, w_other):
    if len(w_self.joined_strs) > w_self.until:
        w_self.force(True)
    w_self.joined_strs.extend(w_other.joined_strs[:w_other.until])
    return W_StringJoinObject(w_self.joined_strs)

def add__StringJoin_String(space, w_self, w_other):
    if len(w_self.joined_strs) > w_self.until:
        w_self.force(True)
    other = space.str_w(w_other)
    w_self.joined_strs.append(other)
    return W_StringJoinObject(w_self.joined_strs)

def str__StringJoin(space, w_str):
    # you cannot get subclasses of W_StringObject here
    assert type(w_str) is W_StringJoinObject
    return w_str

from pypy.objspace.std import stringtype
register_all(vars(), stringtype)

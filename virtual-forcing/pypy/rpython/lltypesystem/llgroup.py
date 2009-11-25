import weakref
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class GroupType(lltype.ContainerType):
    """A 'group' that stores static structs together in memory.
    The point is that they can be referenced by a GroupMemberOffset
    which only takes 2 bytes (a USHORT), so the total size of a group
    is limited to 18 or 19 bits (= the 16 bits in a USHORT, plus 2 or
    3 bits at the end that are zero and so don't need to be stored).
    """
    _gckind = 'raw'

Group = GroupType()


class group(lltype._container):
    _TYPE = Group
    outdated = None

    def __init__(self, name):
        self.name = name
        self.members = []

    def add_member(self, structptr):
        TYPE = lltype.typeOf(structptr)
        assert isinstance(TYPE.TO, lltype.Struct)
        assert TYPE.TO._gckind == 'raw'
        struct = structptr._as_obj()
        prevgroup = _membership.get(struct)
        if prevgroup is not None:
            prevgroup.outdated = (
                "structure %s was inserted into another group" % (struct,))
        assert struct._parentstructure() is None
        index = len(self.members)
        self.members.append(struct)
        _membership[struct] = self
        return GroupMemberOffset(self, index)

def member_of_group(structptr):
    return _membership.get(structptr._as_obj(), None)

_membership = weakref.WeakValueDictionary()


class GroupMemberOffset(llmemory.Symbolic):
    """The offset of a struct inside a group, stored compactly in a USHORT.
    Can only be used by the lloperation 'get_group_member'.
    """
    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger(knowntype=rffi.r_ushort)

    def lltype(self):
        return rffi.USHORT

    def __init__(self, grp, memberindex):
        assert lltype.typeOf(grp) == Group
        self.grpptr = grp._as_ptr()
        self.index = memberindex
        self.member = grp.members[memberindex]._as_ptr()

    def _get_group_member(self, grpptr):
        assert grpptr == self.grpptr, "get_group_member: wrong group!"
        return self.member

    def _get_next_group_member(self, grpptr, skipoffset):
        # ad-hoc: returns a pointer to the group member that follows this one,
        # given information in 'skipoffset' about how much to skip -- which
        # is the size of the current member.
        assert grpptr == self.grpptr, "get_next_group_member: wrong group!"
        assert isinstance(skipoffset, llmemory.ItemOffset)
        assert skipoffset.TYPE == lltype.typeOf(self.member).TO
        assert skipoffset.repeat == 1
        return self.grpptr._as_obj().members[self.index + 1]._as_ptr()


class CombinedSymbolic(llmemory.Symbolic):
    """A general-purpose Signed symbolic that combines a USHORT and the
    rest of the word (typically flags).  Only supports extracting the USHORT
    with 'llop.extract_ushort', and extracting the rest of the word with
    '&~0xFFFF' or with a direct masking like '&0x10000'.
    """
    def annotation(self):
        from pypy.annotation import model
        return model.SomeInteger()

    def lltype(self):
        return lltype.Signed

    def __init__(self, lowpart, rest):
        assert (rest & 0xFFFF) == 0
        self.lowpart = lowpart
        self.rest = rest

    def __repr__(self):
        return '<CombinedSymbolic %r|%s>' % (self.lowpart, self.rest)

    def __and__(self, other):
        if (other & 0xFFFF) == 0:
            return self.rest & other
        if (other & 0xFFFF) == 0xFFFF:
            return CombinedSymbolic(self.lowpart, self.rest & other)
        raise Exception("other=0x%x" % other)

    def __or__(self, other):
        assert (other & 0xFFFF) == 0
        return CombinedSymbolic(self.lowpart, self.rest | other)

    def __add__(self, other):
        assert (other & 0xFFFF) == 0
        return CombinedSymbolic(self.lowpart, self.rest + other)

    def __sub__(self, other):
        assert (other & 0xFFFF) == 0
        return CombinedSymbolic(self.lowpart, self.rest - other)

    def __eq__(self, other):
        if (isinstance(other, CombinedSymbolic) and
            self.lowpart is other.lowpart):
            return self.rest == other.rest
        else:
            return NotImplemented

    def __ne__(self, other):
        if (isinstance(other, CombinedSymbolic) and
            self.lowpart is other.lowpart):
            return self.rest != other.rest
        else:
            return NotImplemented

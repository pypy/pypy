from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.rpython.lltypesystem import lltype
from pypy.jit.llvalue import LLAbstractValue, newvar, const


class LLAbstractContainer(object):
    """Abstract base class for abstract containers.
    LLAbstractValues that are pointers may point to an LLAbstractContainer.
    """
    # all methods are placeholders meant to be overridden

    def getconcretetype(self):
        raise NotImplementedError("%r object has no concrete type" % (
            self.__class__.__name__,))

    def flatten(self, memo):
        pass

    def match(self, live, memo):
        return self == live

    def freeze(self, memo):
        return self

    def unfreeze(self, memo):
        return self


class LLVirtualContainer(LLAbstractContainer):

    a_parent = None
    parentindex = None

    def __init__(self, T, length=None):
        assert (length is not None) == T._is_varsize()
        self.T = T
        self.length = length
        self.names = self.getnames()
        self.fields = {}

    def getconcretetype(self):
        return lltype.Ptr(self.T)

    def getfield(self, name):
        assert name in self.names   # XXX slow
        return self.fields[name]

    def setfield(self, name, a_value):
        assert name in self.names   # XXX slow
        self.fields[name] = a_value

    def build_runtime_container(self, builder):
        v_result = newvar(lltype.Ptr(self.T))
        if self.a_parent is not None:
            v_parent = self.a_parent.build_runtime_container(builder)
            op = SpaceOperation('getsubstruct', [v_parent,
                                                 const(self.parentindex,
                                                       lltype.Void)],
                                v_result)
            print 'force:', op
            builder.residual_operations.append(op)
        else:
            if self.T._is_varsize():
                op = SpaceOperation('malloc_varsize', [
                                        const(self.T, lltype.Void),
                                        const(self.length, lltype.Signed)],
                                    v_result)
            else:
                op = SpaceOperation('malloc', [const(self.T, lltype.Void)],
                                    v_result)
            print 'force:', op
            builder.residual_operations.append(op)
            self.buildcontent(builder, v_result)
        return v_result

    def buildcontent(self, builder, v_target):
        # initialize all fields
        for name in self.names:
            if name in self.fields:
                a_value = self.fields[name]
                T = self.fieldtype(name)
                if isinstance(T, lltype.ContainerType):
                    # initialize the substructure/subarray
                    v_subptr = newvar(lltype.Ptr(T))
                    op = SpaceOperation('getsubstruct',
                                        [v_target, const(name, lltype.Void)],
                                        v_subptr)
                    print 'force:', op
                    builder.residual_operations.append(op)
                    assert isinstance(a_value.content, LLVirtualContainer)
                    a_value.content.buildcontent(builder, v_subptr)
                else:
                    v_value = a_value.forcevarorconst(builder)
                    op = self.setop(v_target, name, v_value)
                    print 'force:', op
                    builder.residual_operations.append(op)

    def flatten(self, memo):
        assert self not in memo.seen; memo.seen[self] = True  # debugging only
        if self.a_parent is not None:
            # self.a_parent.flatten() will not enumerate 'self' again,
            # because should already be in the memo
            self.a_parent.flatten(memo)
        for name in self.names:
            a_value = self.fields[name]
            a_value.flatten(memo)

    def match(self, live, memo):
        if self.__class__ is not live.__class__:
            return False

        if self in memo.self_alias:
            return live is memo.self_alias[self]
        if live in memo.live_alias:
            return self is memo.live_alias[live]
        memo.self_alias[self] = live
        memo.live_alias[live] = self

        assert self.T == live.T
        if self.length != live.length:
            return False
        assert self.names == live.names
        for name in self.names:
            a1 = self.fields[name]
            a2 = live.fields[name]
            if not a1.match(a2, memo):
                return False
        else:
            return True

    def freeze(self, memo):
        result = self.__class__(self.T, self.length)
        if self.a_parent is not None:
            result.a_parent = self.a_parent.freeze(memo)
            result.parentindex = self.parentindex
        for name in self.names:
            a_frozen = self.fields[name].freeze(memo)
            result.fields[name] = a_frozen
        return result

    def unfreeze(self, memo):
        result = self.__class__(self.T, self.length)
        if self.a_parent is not None:
            result.a_parent = self.a_parent.unfreeze(memo)
            result.parentindex = self.parentindex
        for name in self.names:
            a = self.fields[name].unfreeze(memo)
            result.fields[name] = a
        return result


class LLVirtualStruct(LLVirtualContainer):
    """Stands for a pointer to a malloc'ed structure; the structure is not
    malloc'ed so far, but we record which fields have which value.
    """
    def __str__(self):
        return 'struct %s' % (self.T._name,)

    def __repr__(self):
        items = self.fields.items()
        items.sort()
        flds = ['%s=%r' % item for item in items]
        return '<virtual %s %s>' % (self.T._name, ', '.join(flds))

    def getnames(self):
        return self.T._names

    def fieldtype(self, name):
        return getattr(self.T, name)

    def setop(self, v_target, name, v_value):
        return SpaceOperation('setfield', [v_target,
                                           const(name, lltype.Void),
                                           v_value],
                              newvar(lltype.Void))


class LLVirtualArray(LLVirtualContainer):
    """Stands for a pointer to a malloc'ed array; the array is not
    malloc'ed so far, but we record which fields have which value -- here
    a field is an item, indexed by an integer instead of a string field name.
    """
    def __str__(self):
        return 'array[%d]' % (self.length,)

    def __repr__(self):
        items = self.fields.items()
        items.sort()
        flds = ['%s=%r' % item for item in items]
        return '<virtual [%s]>' % (', '.join(flds),)

    def getnames(self):
        return range(self.length)

    def fieldtype(self, index):
        return self.T.OF

    def setop(self, v_target, name, v_value):
        return SpaceOperation('setarrayitem', [v_target,
                                               const(name, lltype.Signed),
                                               v_value],
                              newvar(lltype.Void))


def virtualcontainervalue(T, length=None):
    """Build and return a LLAbstractValue() corresponding to a
    freshly allocated virtual container.
    """
    if isinstance(T, lltype.Struct):
        cls = LLVirtualStruct
    elif isinstance(T, lltype.Array):
        cls = LLVirtualArray
    else:
        raise TypeError("unsupported container type %r" % (T,))
    content = cls(T, length)
    a_result = LLAbstractValue(content=content)
    # initialize fields to zero and allocate inlined substructures
    for name in content.names:
        a_fld = make_default(content.fieldtype(name), length, a_result, name)
        content.fields[name] = a_fld
    return a_result

def make_default(T, length, a_parent, parentindex):
    if isinstance(T, lltype.ContainerType):
        # inlined substructure/subarray
        a = virtualcontainervalue(T, length)
        a.content.a_parent = a_parent
        a.content.parentindex = parentindex
    else:
        # primitive initialized to zero
        a = LLAbstractValue(const(T._defl()))
    return a

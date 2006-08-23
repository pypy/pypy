from pypy.rpython.lltypesystem import lltype
from pypy.jit.llabstractinterp.llvalue import LLAbstractValue, AConstant, const
from pypy.jit.codegen.llgraph.rgenop import rgenop

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

    def unfreeze(self, memo, block):
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
        RESULT_TYPE = lltype.Ptr(self.T)
        if self.a_parent is not None:
            PARENT_TYPE = self.a_parent.getconcretetype().TO
            parentindex = rgenop.constFieldName(PARENT_TYPE, self.parentindex)
            v_parent = self.a_parent.forcegenvarorconst(builder)
            v_result = builder.genop('getsubstruct',
                                     [v_parent, parentindex], RESULT_TYPE)
        else:
            t = rgenop.constTYPE(self.T)
            if self.T._is_varsize():
                v_result = builder.genop('malloc_varsize',
                                         [t,
                                          builder.genconst(self.length)],
                                         RESULT_TYPE)
            else:
                v_result = builder.genop('malloc', [t], RESULT_TYPE)
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
                    c_name = rgenop.constFieldName(self.T, name)
                    v_subptr = builder.genop('getsubstruct',
                                             [v_target, c_name],
                                             lltype.Ptr(T))
                    assert isinstance(a_value.content, LLVirtualContainer)
                    a_value.content.buildcontent(builder, v_subptr)
                else:
                    v_value = a_value.forcegenvarorconst(builder)
                    self.setop(builder, v_target, name, v_value)

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

        if self.a_parent is not None:
            if (live.a_parent is None or
                not self.a_parent.match(live.a_parent, memo)):
                return False
        elif live.a_parent is not None:
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

    def unfreeze(self, memo, block):
        result = self.__class__(self.T, self.length)
        if self.a_parent is not None:
            result.a_parent = self.a_parent.unfreeze(memo, block)
            result.parentindex = self.parentindex
        for name in self.names:
            a = self.fields[name].unfreeze(memo, block)
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

    def setop(self, builder, v_target, name, v_value):
        c_name = rgenop.constFieldName(self.T, name)
        builder.genop('setfield', [v_target, c_name, v_value],
                      lltype.Void)


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
        builder.genop('setarrayitem', [v_target,
                                       builder.genconst(name),
                                       v_value],
                      lltype.Void)


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
        a = LLAbstractValue(AConstant(T._defl()))
    return a

def hasllcontent(a_ptr):
    return isinstance(a_ptr.content, LLVirtualContainer)

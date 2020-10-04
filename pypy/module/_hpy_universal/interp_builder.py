from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.debug import make_sure_not_resized
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.baseobjspace import W_Root
from pypy.objspace.std.listobject import W_ListObject
from pypy.module._hpy_universal.apiset import API
from pypy.module._hpy_universal import handles

# note that ListBuilder does not necessarily need to be a W_Root: the object
# is never diretly exposed to the user, because the C HPyListBuilder type is
# basically an opaque integer. However, by making it a W_Root, we can just
# (re)use HandleManager to get this unique index.
class W_SequenceBuilder(W_Root):
    """
    This can be used for both HPyListBuilder and HPyTupleBuilder
    """

    def __init__(self, space, initial_size):
        self.space = space
        self.items_w = [None] * initial_size
        make_sure_not_resized(self.items_w)

    def set(self, i, w_obj):
        self.items_w[i] = w_obj

    def build_list(self):
        # XXX is is less efficient that it should. We need to make a copy
        # because newlist expects a resizable list. We could do the opposite a
        # make a copy when calling newtuple, but I suspect that using
        # HPyTupleBuilder will me more common than using HPyListBuilder. A
        # more proper fix would be to use RPython tricks to create two
        # distinct copies of this class, but I'm not sure it's worth the
        # hassle.
        return self.space.newlist(self.items_w[:])

    def build_tuple(self):
        return self.space.newtuple(self.items_w)


# ~~~ common code shared by HPyListBuilder and HPyTupleBuilder ~~~

def _Builder_New(space, initial_size):
    w_builder = W_SequenceBuilder(space, initial_size)
    h = handles.new(space, w_builder)
    return h

def _Builder_Set(space, builder, index, h_item):
    # XXX if builder==0, there was an error inside _New. The C code just exits
    # here, but there is no tests for it. Write it
    w_builder = handles.deref(space, builder)
    assert isinstance(w_builder, W_SequenceBuilder)
    w_item = handles.deref(space, h_item)
    w_builder.set(index, w_item)

def _Builder_Build(space, builder, result_type):
    assert result_type in ('L', 'T')
    # XXX same comment as above in case builder==0
    w_builder = handles.deref(space, builder)
    assert isinstance(w_builder, W_SequenceBuilder)
    if result_type == 'L':
        w_result = w_builder.build_list()
    else:
        w_result = w_builder.build_tuple()
    return handles.new(space, w_result)

def _Builder_Cancel(space, builder):
    raise NotImplementedError


# ~~~ HPyListBuilder ~~~

@API.func("HPyListBuilder HPyListBuilder_New(HPyContext ctx, HPy_ssize_t initial_size)")
def HPyListBuilder_New(space, ctx, initial_size):
    return _Builder_New(space, initial_size)

@API.func("void HPyListBuilder_Set(HPyContext ctx, HPyListBuilder builder, HPy_ssize_t index, HPy h_item)")
def HPyListBuilder_Set(space, ctx, builder, index, h_item):
    return _Builder_Set(space, builder, index, h_item)

@API.func("HPy HPyListBuilder_Build(HPyContext ctx, HPyListBuilder builder)")
def HPyListBuilder_Build(space, ctx, builder):
    return _Builder_Build(space, builder, result_type='L')

@API.func("void HPyListBuilder_Cancel(HPyContext ctx, HPyListBuilder builder)")
def HPyListBuilder_Cancel(space, ctx, builder):
    # XXX write a test
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return
    raise NotImplementedError

# ~~~ HPyTupleBuilder ~~~

@API.func("HPyTupleBuilder HPyTupleBuilder_New(HPyContext ctx, HPy_ssize_t initial_size)")
def HPyTupleBuilder_New(space, ctx, initial_size):
    return _Builder_New(space, initial_size)

@API.func("void HPyTupleBuilder_Set(HPyContext ctx, HPyTupleBuilder builder, HPy_ssize_t index, HPy h_item)")
def HPyTupleBuilder_Set(space, ctx, builder, index, h_item):
    return _Builder_Set(space, builder, index, h_item)

@API.func("HPy HPyTupleBuilder_Build(HPyContext ctx, HPyTupleBuilder builder)")
def HPyTupleBuilder_Build(space, ctx, builder):
    return _Builder_Build(space, builder, result_type='T')

@API.func("void HPyTupleBuilder_Cancel(HPyContext ctx, HPyTupleBuilder builder)")
def HPyTupleBuilder_Cancel(space, ctx, builder):
    # XXX write a test
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return
    raise NotImplementedError

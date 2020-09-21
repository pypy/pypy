from rpython.rtyper.lltypesystem import rffi, lltype
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

    def set(self, i, w_obj):
        self.items_w[i] = w_obj

    def build_list(self):
        return self.space.newlist(self.items_w)


@API.func("HPyListBuilder HPyListBuilder_New(HPyContext ctx, HPy_ssize_t initial_size)")
def HPyListBuilder_New(space, ctx, initial_size):
    w_builder = W_SequenceBuilder(space, initial_size)
    h = handles.new(space, w_builder)
    return h

@API.func("void HPyListBuilder_Set(HPyContext ctx, HPyListBuilder builder, HPy_ssize_t index, HPy h_item)")
def HPyListBuilder_Set(space, ctx, builder, index, h_item):
    # XXX if builder==0, there was an error inside _New. The C code just exits
    # here, but there is no tests for it. Write it
    w_builder = handles.deref(space, builder)
    assert isinstance(w_builder, W_SequenceBuilder)
    w_item = handles.deref(space, h_item)
    w_builder.set(index, w_item)

@API.func("HPy HPyListBuilder_Build(HPyContext ctx, HPyListBuilder builder)")
def HPyListBuilder_Build(space, ctx, builder):
    # XXX same comment as above in case builder==0
    w_builder = handles.deref(space, builder)
    assert isinstance(w_builder, W_SequenceBuilder)
    w_list = w_builder.build_list()
    return handles.new(space, w_list)


@API.func("void HPyListBuilder_Cancel(HPyContext ctx, HPyListBuilder builder)")
def HPyListBuilder_Cancel(space, ctx, builder):
    # XXX write a test
    from rpython.rlib.nonconst import NonConstant # for the annotator
    if NonConstant(False): return
    raise NotImplementedError

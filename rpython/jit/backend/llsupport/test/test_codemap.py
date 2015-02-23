
from rpython.jit.backend.llsupport.codemap import stack_depth_at_loc
from rpython.jit.backend.llsupport.codemap import CodemapStorage,\
     ListStorageMixin, INT_LIST, CodemapBuilder, unpack_traceback
from rpython.rtyper.lltypesystem import lltype


def test_list_storage_mixin():
    class X(ListStorageMixin):
        track_allocation = True
        
        def __init__(self):
            self.x = lltype.malloc(INT_LIST, 4, flavor='raw')
            self.x_used = 0

        def unpack(self):
            return [self.x[i] for i in range(self.x_used)]

        def free_lst(self, name, lst):
            lltype.free(lst, flavor='raw')
        
        def free(self):
            lltype.free(self.x, flavor='raw')

    x = X()
    x.extend_with('x', [1, 2, 3], 0)
    assert x.unpack() == [1, 2, 3]
    x.extend_with('x', [4, 5, 6], 3)
    assert x.unpack() == [1, 2, 3, 4, 5, 6]
    x.extend_with('x', [7, 8, 9], 2, baseline=10)
    assert x.unpack() == [1, 2, 17, 18, 19, 3, 4, 5, 6]
    x.remove('x', 3, 6)
    assert x.unpack() == [1, 2, 17, 4, 5, 6]
    x.extend_with('x', [1] * 6, 6)
    assert x.unpack() == [1, 2, 17, 4, 5, 6, 1, 1, 1, 1, 1, 1]
    x.extend_with('x', [10] * 4, 5)
    assert x.unpack() == [1, 2, 17, 4, 5, 10, 10, 10, 10, 6,
                          1, 1, 1, 1, 1, 1]
    x.free()

def test_find_jit_frame_depth():
    codemap = CodemapStorage()
    codemap.setup()
    codemap.register_frame_depth_map(11, [0, 5, 10], [1, 2, 3])
    codemap.register_frame_depth_map(30, [0, 5, 10], [4, 5, 6])
    codemap.register_frame_depth_map(0, [0, 5, 10], [7, 8, 9])
    assert stack_depth_at_loc(13) == 1
    assert stack_depth_at_loc(-3) == -1
    assert stack_depth_at_loc(41) == -1
    assert stack_depth_at_loc(5) == 8
    assert stack_depth_at_loc(17) == 2
    assert stack_depth_at_loc(38) == 5
    codemap.free_asm_block(11, 22)
    assert stack_depth_at_loc(13) == 9
    assert stack_depth_at_loc(-3) == -1
    assert stack_depth_at_loc(41) == -1
    assert stack_depth_at_loc(5) == 8
    assert stack_depth_at_loc(17) == 9
    assert stack_depth_at_loc(38) == 5

def test_codemaps():
    builder = CodemapBuilder()
    builder.debug_merge_point(0, 102, 0)
    builder.debug_merge_point(0, 102, 13)
    builder.debug_merge_point(1, 104, 15)
    builder.debug_merge_point(1, 104, 16)
    builder.debug_merge_point(2, 106, 20)
    builder.debug_merge_point(2, 106, 25)
    builder.debug_merge_point(1, 104, 30)
    builder.debug_merge_point(0, 102, 35)
    codemap = CodemapStorage()
    codemap.setup()
    codemap.register_codemap(builder.get_final_bytecode(100, 40))
    builder = CodemapBuilder()
    builder.debug_merge_point(0, 202, 0)
    builder.debug_merge_point(0, 202, 10)
    builder.debug_merge_point(1, 204, 20)
    builder.debug_merge_point(1, 204, 30)
    builder.debug_merge_point(2, 206, 40)
    builder.debug_merge_point(2, 206, 50)
    builder.debug_merge_point(1, 204, 60)
    builder.debug_merge_point(0, 202, 70)
    codemap.register_codemap(builder.get_final_bytecode(200, 100))
    assert unpack_traceback(110) == [102]
    assert unpack_traceback(117) == [102, 104]
    assert unpack_traceback(121) == [102, 104, 106]
    assert unpack_traceback(131) == [102, 104]
    assert unpack_traceback(137) == [102]
    assert unpack_traceback(205) == [202]
    assert unpack_traceback(225) == [202, 204]
    assert unpack_traceback(245) == [202, 204, 206]
    assert unpack_traceback(265) == [202, 204]
    assert unpack_traceback(275) == [202]
    codemap.free_asm_block(200, 300)
    assert unpack_traceback(225) == []

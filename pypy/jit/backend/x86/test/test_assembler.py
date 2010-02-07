from pypy.jit.backend.x86.ri386 import *
from pypy.jit.backend.x86.assembler import Assembler386, MachineCodeBlockWrapper
from pypy.jit.backend.x86.regalloc import X86FrameManager, get_ebp_ofs
from pypy.jit.metainterp.history import BoxInt, BoxPtr, BoxFloat
from pypy.rlib.rarithmetic import intmask
from pypy.rpython.lltypesystem import lltype, llmemory, rffi


class FakeCPU:
    rtyper = None
    supports_floats = True

class FakeMC:
    def __init__(self, base_address=0):
        self.content = []
        self._size = 100
        self.base_address = base_address
    def writechr(self, n):
        self.content.append(n)
    def tell(self):
        return self.base_address + len(self.content)
    def get_relative_pos(self):
        return len(self.content)
    def JMP(self, *args):
        self.content.append(("JMP", args))
    def done(self):
        pass


def test_write_failure_recovery_description():
    assembler = Assembler386(FakeCPU())
    mc = FakeMC()
    failargs = [BoxInt(), BoxPtr(), BoxFloat()] * 3
    failargs.insert(6, None)
    failargs.insert(7, None)
    locs = [X86FrameManager.frame_pos(0, 1),
            X86FrameManager.frame_pos(1, 1),
            X86FrameManager.frame_pos(10, 2),
            X86FrameManager.frame_pos(100, 1),
            X86FrameManager.frame_pos(101, 1),
            X86FrameManager.frame_pos(110, 2),
            None,
            None,
            ebx,
            esi,
            xmm2]
    assert len(failargs) == len(locs)
    assembler.write_failure_recovery_description(mc, failargs, locs)
    nums = [Assembler386.DESCR_INT   + 4*(8+0),
            Assembler386.DESCR_REF   + 4*(8+1),
            Assembler386.DESCR_FLOAT + 4*(8+10),
            Assembler386.DESCR_INT   + 4*(8+100),
            Assembler386.DESCR_REF   + 4*(8+101),
            Assembler386.DESCR_FLOAT + 4*(8+110),
            Assembler386.CODE_HOLE,
            Assembler386.CODE_HOLE,
            Assembler386.DESCR_INT   + 4*ebx.op,
            Assembler386.DESCR_REF   + 4*esi.op,
            Assembler386.DESCR_FLOAT + 4*xmm2.op]
    double_byte_nums = []
    for num in nums[3:6]:
        double_byte_nums.append((num & 0x7F) | 0x80)
        double_byte_nums.append(num >> 7)
    assert mc.content == (nums[:3] + double_byte_nums + nums[6:] +
                          [assembler.CODE_STOP])

    # also test rebuild_faillocs_from_descr(), which should not
    # reproduce the holes at all
    bytecode = lltype.malloc(rffi.UCHARP.TO, len(mc.content), flavor='raw')
    for i in range(len(mc.content)):
        assert 0 <= mc.content[i] <= 255
        bytecode[i] = rffi.cast(rffi.UCHAR, mc.content[i])
    bytecode_addr = rffi.cast(lltype.Signed, bytecode)
    newlocs = assembler.rebuild_faillocs_from_descr(bytecode_addr)
    assert ([loc.assembler() for loc in newlocs] ==
            [loc.assembler() for loc in locs if loc is not None])

    # finally, test make_boxes_from_latest_values(), which should
    # reproduce the holes
    expected_classes = [BoxInt, BoxPtr, BoxFloat,
                        BoxInt, BoxPtr, BoxFloat,
                        type(None), type(None),
                        BoxInt, BoxPtr, BoxFloat]
    ptrvalues = {}
    S = lltype.GcStruct('S')
    for i, cls in enumerate(expected_classes):
        if cls == BoxInt:
            assembler.fail_boxes_int.setitem(i, 1000 + i)
        elif cls == BoxPtr:
            s = lltype.malloc(S)
            s_ref = lltype.cast_opaque_ptr(llmemory.GCREF, s)
            ptrvalues[i] = s_ref
            assembler.fail_boxes_ptr.setitem(i, s_ref)
        elif cls == BoxFloat:
            assembler.fail_boxes_float.setitem(i, 42.5 + i)
    boxes = assembler.make_boxes_from_latest_values(bytecode_addr)
    assert len(boxes) == len(locs) == len(expected_classes)
    for i, (box, expected_class) in enumerate(zip(boxes, expected_classes)):
        assert type(box) is expected_class
        if expected_class == BoxInt:
            assert box.value == 1000 + i
        elif expected_class == BoxPtr:
            assert box.value == ptrvalues[i]
        elif expected_class == BoxFloat:
            assert box.value == 42.5 + i

# ____________________________________________________________

def test_failure_recovery_func_no_floats():
    do_failure_recovery_func(withfloats=False)

def test_failure_recovery_func_with_floats():
    do_failure_recovery_func(withfloats=True)

def do_failure_recovery_func(withfloats):
    import random
    S = lltype.GcStruct('S')

    def get_random_int():
        return random.randrange(-10000, 10000)

    def get_random_ptr():
        return lltype.cast_opaque_ptr(llmemory.GCREF, lltype.malloc(S))

    def get_random_float():
        assert withfloats
        value = random.random() - 0.5
        # make sure it fits into 64 bits
        tmp = lltype.malloc(rffi.LONGP.TO, 2, flavor='raw')
        rffi.cast(rffi.DOUBLEP, tmp)[0] = value
        return rffi.cast(rffi.DOUBLEP, tmp)[0], tmp[0], tmp[1]

    # memory locations: 26 integers, 26 pointers, 26 floats
    # main registers: half of them as signed and the other half as ptrs
    # xmm registers: all floats, from xmm0 to xmm7
    # holes: 8
    locations = []
    baseloc = 4
    for i in range(26+26+26):
        if baseloc < 128:
            baseloc += random.randrange(2, 20)
        else:
            baseloc += random.randrange(2, 1000)
        locations.append(baseloc)
    random.shuffle(locations)
    content = ([('int', locations.pop()) for _ in range(26)] +
               [('ptr', locations.pop()) for _ in range(26)] +
               [(['int', 'ptr'][random.randrange(0, 2)], reg)
                         for reg in [eax, ecx, edx, ebx, esi, edi]])
    if withfloats:
        content += ([('float', locations.pop()) for _ in range(26)] +
                    [('float', reg) for reg in [xmm0, xmm1, xmm2, xmm3,
                                                xmm4, xmm5, xmm6, xmm7]])
    for i in range(8):
        content.append(('hole', None))
    random.shuffle(content)

    # prepare the expected target arrays, the descr_bytecode,
    # the 'registers' and the 'stack' arrays according to 'content'
    xmmregisters = lltype.malloc(rffi.LONGP.TO, 16+9, flavor='raw')
    registers = rffi.ptradd(xmmregisters, 16)
    stacklen = baseloc + 10
    stack = lltype.malloc(rffi.LONGP.TO, stacklen, flavor='raw')
    expected_ints = [0] * len(content)
    expected_ptrs = [lltype.nullptr(llmemory.GCREF.TO)] * len(content)
    expected_floats = [0.0] * len(content)

    def write_in_stack(loc, value):
        assert loc >= 0
        ofs = get_ebp_ofs(loc)
        assert ofs < 0
        assert (ofs % 4) == 0
        stack[stacklen + ofs//4] = value

    descr_bytecode = []
    for i, (kind, loc) in enumerate(content):
        if kind == 'hole':
            num = Assembler386.CODE_HOLE
        else:
            if kind == 'float':
                value, lo, hi = get_random_float()
                expected_floats[i] = value
                kind = Assembler386.DESCR_FLOAT
                if isinstance(loc, REG):
                    xmmregisters[2*loc.op] = lo
                    xmmregisters[2*loc.op+1] = hi
                else:
                    write_in_stack(loc, hi)
                    write_in_stack(loc+1, lo)
            else:
                if kind == 'int':
                    value = get_random_int()
                    expected_ints[i] = value
                    kind = Assembler386.DESCR_INT
                elif kind == 'ptr':
                    value = get_random_ptr()
                    expected_ptrs[i] = value
                    kind = Assembler386.DESCR_REF
                    value = rffi.cast(rffi.LONG, value)
                else:
                    assert 0, kind
                if isinstance(loc, REG):
                    registers[loc.op] = value
                else:
                    write_in_stack(loc, value)

            if isinstance(loc, REG):
                num = kind + 4*loc.op
            else:
                num = kind + 4*(8+loc)
            while num >= 0x80:
                descr_bytecode.append((num & 0x7F) | 0x80)
                num >>= 7
        descr_bytecode.append(num)

    descr_bytecode.append(Assembler386.CODE_STOP)
    descr_bytecode.append(0xC3)   # fail_index = 0x1C3
    descr_bytecode.append(0x01)
    descr_bytecode.append(0x00)
    descr_bytecode.append(0x00)
    descr_bytecode.append(0xCC)   # end marker
    descr_bytes = lltype.malloc(rffi.UCHARP.TO, len(descr_bytecode),
                                flavor='raw')
    for i in range(len(descr_bytecode)):
        assert 0 <= descr_bytecode[i] <= 255
        descr_bytes[i] = rffi.cast(rffi.UCHAR, descr_bytecode[i])
    registers[8] = rffi.cast(rffi.LONG, descr_bytes)
    registers[ebp.op] = rffi.cast(rffi.LONG, stack) + 4*stacklen

    # run!
    assembler = Assembler386(FakeCPU())
    assembler.fail_boxes_int.get_addr_for_num(len(content)-1)   # preallocate
    assembler.fail_boxes_ptr.get_addr_for_num(len(content)-1)
    assembler.fail_boxes_float.get_addr_for_num(len(content)-1)
    res = assembler.failure_recovery_func(registers)
    assert res == 0x1C3

    # check the fail_boxes
    for i in range(len(content)):
        assert assembler.fail_boxes_int.getitem(i) == expected_ints[i]
        assert assembler.fail_boxes_ptr.getitem(i) == expected_ptrs[i]
        # note: we expect *exact* results below.  If you have only
        # an approximate result, it might mean that only the first 32
        # bits of the float were correctly saved and restored.
        assert assembler.fail_boxes_float.getitem(i) == expected_floats[i]

class FakeProfileAgent(object):
    def __init__(self):
        self.functions = []

    def native_code_written(self, name, address, size):
        self.functions.append((name, address, size))

class FakeMCWrapper(MachineCodeBlockWrapper):
    count = 0
    def _instantiate_mc(self):
        self.count += 1
        return FakeMC(200 * (self.count - 1))

def test_mc_wrapper_profile_agent():
    agent = FakeProfileAgent()
    mc = FakeMCWrapper(100, agent)
    mc.start_function("abc")
    mc.writechr("x")
    mc.writechr("x")
    mc.writechr("x")
    mc.writechr("x")
    mc.end_function()
    assert agent.functions == [("abc", 0, 4)]
    mc.writechr("x")
    mc.start_function("cde")
    mc.writechr("x")
    mc.writechr("x")
    mc.writechr("x")
    mc.writechr("x")
    mc.end_function()
    assert agent.functions == [("abc", 0, 4), ("cde", 5, 4)]
    mc.start_function("xyz")
    for i in range(50):
        mc.writechr("x")
    mc.end_function()
    assert agent.functions == [("abc", 0, 4), ("cde", 5, 4), ("xyz", 9, 29), ("xyz", 200, 22)]

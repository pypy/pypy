import random
from rpython.jit.backend.x86.guard_compat import *
from rpython.jit.backend.x86.arch import FRAME_FIXED_SIZE, PASS_ON_MY_FRAME
from rpython.jit.backend.x86.arch import DEFAULT_FRAME_BYTES
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.test import test_compatible

CPU = getcpuclass()

class FakeStats(object):
    pass


def test_guard_compat():
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.setup_once()

    mc = codebuf.MachineCodeBlockWrapper()
    for i in range(4 * WORD):
        mc.writechar('\x00')   # 4 gctable entries; 'bchoices' will be #3
    #
    # extracted from _call_header()
    mc.SUB_ri(regloc.esp.value, FRAME_FIXED_SIZE * WORD)
    mc.MOV_sr(PASS_ON_MY_FRAME * WORD, regloc.ebp.value)
    for i, loc in enumerate(cpu.CALLEE_SAVE_REGISTERS):
        mc.MOV_sr((PASS_ON_MY_FRAME + i + 1) * WORD, loc.value)
    #
    if IS_X86_64:
        mc.MOV(regloc.ebp, regloc.edx)    # jitframe
        mc.MOV(regloc.r11, regloc.edi)    # _backend_choices
        mc.MOV(regloc.eax, regloc.esi)    # guarded value
    elif IS_X86_32:
        XXX
        mc.MOV_rs(regloc.edx.value, 4)
        mc.MOV_rs(regloc.eax.value, 8)
        mc.MOV_rs(regloc.ecx.value, 12)
    #
    mc.MOV(regloc.ecx, regloc.imm(0xdddd))
    mc.PUSH(regloc.imm(0xaaaa))
    # jump to guard_compat_search_tree, but carefully: don't overwrite R11
    mc.MOV(regloc.esi, regloc.imm(cpu.assembler.guard_compat_search_tree))
    mc.JMP_r(regloc.esi.value)
    mc.INT3()
    sequel = mc.get_relative_pos()
    #
    mc.force_frame_size(DEFAULT_FRAME_BYTES)
    mc.SUB(regloc.eax, regloc.ecx)
    #
    def call_footer():
        mc.MOV_rs(regloc.ebp.value, PASS_ON_MY_FRAME * WORD)
        for i, loc in enumerate(cpu.CALLEE_SAVE_REGISTERS):
            mc.MOV_rs(loc.value, (PASS_ON_MY_FRAME + i + 1) * WORD)
        mc.ADD_ri(regloc.esp.value, FRAME_FIXED_SIZE * WORD)
        mc.RET()
    call_footer()
    #
    extra_paths = []
    for i in range(11):
        mc.force_frame_size(DEFAULT_FRAME_BYTES)
        extra_paths.append(mc.get_relative_pos())
        mc.MOV(regloc.eax, regloc.imm(1000000 + i))
        call_footer()
    rawstart = mc.materialize(cpu, [])
    print 'rawstart:', hex(rawstart)
    call_me = rffi.cast(lltype.Ptr(lltype.FuncType(
        [lltype.Ptr(BACKEND_CHOICES), llmemory.GCREF,
         lltype.Ptr(jitframe.JITFRAME)], lltype.Signed)),
        rawstart + 4 * WORD)

    guard_compat_descr = GuardCompatibleDescr()
    bchoices = initial_bchoices(guard_compat_descr)
    llop.raw_store(lltype.Void, rawstart, 3 * WORD, bchoices)

    class FakeGuardToken:
        #pos_jump_offset = sequel
        #pos_recovery_stub = failure
        gcmap = rffi.cast(lltype.Ptr(jitframe.GCMAP), 0x10111213)
        faildescr = guard_compat_descr
    guard_token = FakeGuardToken()
    guard_compat_descr._backend_choices_addr = 3

    patch_guard_compatible(guard_token,
                           lambda index: rawstart + index * WORD,
                           lltype.nullptr(llmemory.GCREF.TO),
                           9999)

    # fill in the first choice manually
    bchoices.bc_list[0].gcref = r_uint(111111)
    bchoices.bc_list[0].asmaddr = rawstart + sequel

    # ---- ready ----

    frame_info = lltype.malloc(jitframe.JITFRAMEINFO, flavor='raw')
    frame_info.clear()
    frame_info.update_frame_depth(cpu.get_baseofs_of_frame_field(), 1000)
    frame = jitframe.JITFRAME.allocate(frame_info)

    for i in range(5):
        guard_compat_descr.find_compatible = "don't call"
        gcref = rffi.cast(llmemory.GCREF, 111111)
        print 'calling with the standard gcref'
        res = call_me(bchoices, gcref, frame)
        assert res == 0xaaaa - 0xdddd
        assert bchoices.bc_most_recent.gcref == 111111
        assert bchoices.bc_most_recent.asmaddr == rawstart + sequel

    seen = []
    def call(cpu, descr):
        print 'find_compatible returns 0'
        seen.append(descr)
        return 0

    for i in range(5):
        guard_compat_descr.find_compatible = call
        gcref = rffi.cast(llmemory.GCREF, 123456 + i)
        print 'calling with a gcref never seen before'
        res = call_me(bchoices, gcref, frame)
        assert res == rffi.cast(lltype.Signed, frame)
        assert len(seen) == 1 + i
        assert bchoices.bc_most_recent.gcref == 123456 + i
        assert bchoices.bc_most_recent.asmaddr == (
            cpu.assembler.guard_compat_recovery)

    # ---- grow bchoices ----

    expected = {111111: (0xaaaa - 0xdddd, rawstart + sequel)}
    for j in range(10):
        print 'growing bchoices'
        bchoices = add_in_tree(bchoices, rffi.cast(llmemory.GCREF, 111113 + j),
                               rawstart + extra_paths[j])
        expected[111113 + j] = (1000000 + j, rawstart + extra_paths[j])
    llop.raw_store(lltype.Void, rawstart, 3 * WORD, bchoices)

    for i in range(10):
        lst = expected.items()
        random.shuffle(lst)
        for intgcref, (expected_res, expected_asmaddr) in lst:
            guard_compat_descr.find_compatible = "don't call"
            gcref = rffi.cast(llmemory.GCREF, intgcref)
            print 'calling with new choice', intgcref
            res = call_me(bchoices, gcref, frame)
            assert res == expected_res
            assert bchoices.bc_most_recent.gcref == intgcref
            assert bchoices.bc_most_recent.asmaddr == expected_asmaddr

    lltype.free(frame_info, flavor='raw')


class TestCompatible(Jit386Mixin, test_compatible.TestCompatible):
    pass

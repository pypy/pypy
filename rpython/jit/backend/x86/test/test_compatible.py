import random
from rpython.jit.backend.x86.guard_compat import *
from rpython.jit.backend.x86.test.test_basic import Jit386Mixin
from rpython.jit.backend.detect_cpu import getcpuclass
from rpython.jit.metainterp.test import test_compatible

CPU = getcpuclass()

class FakeStats(object):
    pass


def test_invalidate_cache():
    b = lltype.malloc(BACKEND_CHOICES, 4)
    invalidate_pair(b, BCMOSTRECENT)
    x = b.bc_most_recent.gcref
    assert x == r_uint(-1)

def check_bclist(bchoices, expected):
    assert len(bchoices.bc_list) == len(expected)
    for i in range(len(bchoices.bc_list)):
        pair = bchoices.bc_list[i]
        assert pair.gcref == rffi.cast(lltype.Unsigned, expected[i][0])
        assert pair.asmaddr == expected[i][1]

def test_add_in_tree():
    b = lltype.malloc(BACKEND_CHOICES, 3, zero=True)    # 3 * null
    check_bclist(b, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        ])
    new_gcref = rffi.cast(llmemory.GCREF, 717344)
    new_asmaddr = 1234567
    b2 = add_in_tree(b, new_gcref, new_asmaddr)
    check_bclist(b2, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        (new_gcref, new_asmaddr),
        (-1, -1),  # invalid
        (-1, -1),  # invalid
        (-1, -1),  # invalid
        ])
    new_gcref_2 = rffi.cast(llmemory.GCREF, 717000)   # lower than before
    new_asmaddr_2 = 2345678
    b3 = add_in_tree(b2, new_gcref_2, new_asmaddr_2)
    assert b3 == b2     # was still large enough
    check_bclist(b2, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        (new_gcref_2, new_asmaddr_2),
        (new_gcref,   new_asmaddr),
        (-1, -1),  # invalid
        (-1, -1),  # invalid
        ])
    new_gcref_3 = rffi.cast(llmemory.GCREF, 717984)   # higher than before
    new_asmaddr_3 = 3456789
    b4 = add_in_tree(b3, new_gcref_3, new_asmaddr_3)
    assert b4 == b2     # was still large enough
    check_bclist(b2, [
        (0, 0),    # null
        (0, 0),    # null
        (0, 0),    # null
        (new_gcref_2, new_asmaddr_2),
        (new_gcref,   new_asmaddr),
        (new_gcref_3, new_asmaddr_3),
        (-1, -1),  # invalid
        ])

def test_guard_compat():
    cpu = CPU(rtyper=None, stats=FakeStats())
    cpu.setup_once()

    mc = codebuf.MachineCodeBlockWrapper()
    for i in range(4 * WORD):
        mc.writechar('\x00')   # 4 gctable entries; 'bchoices' will be #3
    #
    mc.PUSH(regloc.ebp)
    mc.SUB(regloc.esp, regloc.imm(448 - 2*WORD)) # make a frame, and align stack
    mc.LEA_rs(regloc.ebp.value, 48)
    #
    mc.PUSH(regloc.imm(0xdddd))
    mc.PUSH(regloc.imm(0xaaaa))
    mc.MOV(regloc.edx, regloc.edi)
    mc.MOV(regloc.eax, regloc.esi)
    mc.JMP(regloc.imm(cpu.assembler.guard_compat_search_tree))
    sequel = mc.get_relative_pos()
    #
    mc.force_frame_size(448)
    mc.SUB(regloc.eax, regloc.edx)
    mc.ADD(regloc.esp, regloc.imm(448 - 2*WORD))
    mc.POP(regloc.ebp)
    mc.RET()
    #
    extra_paths = []
    for i in range(11):
        mc.force_frame_size(448)
        extra_paths.append(mc.get_relative_pos())
        mc.MOV(regloc.eax, regloc.imm(1000000 + i))
        mc.ADD(regloc.esp, regloc.imm(448 - 2*WORD))
        mc.POP(regloc.ebp)
        mc.RET()
    failure = extra_paths[10]
    rawstart = mc.materialize(cpu, [])
    call_me = rffi.cast(lltype.Ptr(lltype.FuncType([lltype.Ptr(BACKEND_CHOICES),
                                                    llmemory.GCREF],
                                                   lltype.Signed)),
                        rawstart + 4 * WORD)

    guard_compat_descr = GuardCompatibleDescr()
    bchoices = initial_bchoices(guard_compat_descr,
                                rffi.cast(llmemory.GCREF, 111111))
    llop.raw_store(lltype.Void, rawstart, 3 * WORD, bchoices)

    class FakeGuardToken:
        guard_compat_bindex = 3
        pos_jump_offset = sequel
        pos_recovery_stub = failure
        gcmap = rffi.cast(lltype.Ptr(jitframe.GCMAP), 0x10111213)
        faildescr = guard_compat_descr
    guard_token = FakeGuardToken()

    patch_guard_compatible(guard_token, rawstart, rawstart)

    # ---- ready ----

    for i in range(5):
        guard_compat_descr.find_compatible = "don't call"
        gcref = rffi.cast(llmemory.GCREF, 111111)
        print 'calling with the standard gcref'
        res = call_me(bchoices, gcref)
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
        res = call_me(bchoices, gcref)
        assert res == 1000010
        assert len(seen) == 1 + i
        assert bchoices.bc_most_recent.gcref == 123456 + i
        assert bchoices.bc_most_recent.asmaddr == rawstart + failure

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
            res = call_me(bchoices, gcref)
            assert res == expected_res
            assert bchoices.bc_most_recent.gcref == intgcref
            assert bchoices.bc_most_recent.asmaddr == expected_asmaddr


class TestCompatible(Jit386Mixin, test_compatible.TestCompatible):
    pass


""" Register allocation scheme.
"""

from pypy.jit.metainterp.history import (Box, Const, ConstInt, ConstPtr,
                                         ResOperation, ConstAddr)
from pypy.jit.backend.x86.ri386 import *
from pypy.rpython.lltypesystem import lltype, ll2ctypes, rffi, rstr
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.resoperation import rop

# esi edi and ebp can be added to this list, provided they're correctly
# saved and restored
REGS = [eax, ecx, edx, ebx]
WORD = 4

class TempBox(Box):
    def __init__(self):
        pass

    def __repr__(self):
        return "<TempVar at %s>" % (id(self),)

class checkdict(dict):
    def __setitem__(self, key, value):
        assert isinstance(key, Box)
        dict.__setitem__(self, key, value)

def newcheckdict():
    if we_are_translated():
        return {}
    return checkdict()

def convert_to_imm(c):
    if isinstance(c, ConstInt):
        return imm(c.value)
    elif isinstance(c, ConstPtr):
        return imm(rffi.cast(lltype.Signed, c.value))
    elif isinstance(c, ConstAddr):
        return imm(ll2ctypes.cast_adr_to_int(c.value))
    else:
        raise ValueError("convert_to_imm: got a %s" % c)

class RegAlloc(object):
    guard_index = -1
    max_stack_depth = 0
    
    def __init__(self, assembler, tree, translate_support_code=False,
                 regalloc=None, guard_op=None):
        # variables that have place in register
        self.assembler = assembler
        self.translate_support_code = translate_support_code
        if regalloc is None:
            self.tree = tree
            self.reg_bindings = newcheckdict()
            self.stack_bindings = newcheckdict()
            # compute longevity of variables
            self._compute_vars_longevity(tree.inputargs, tree.operations)
            self.free_regs = REGS[:]
            self.dirty_stack = {}
            jump = tree.operations[-1]
            #self.startmp = mp
            #if guard_op:
            #    loop_consts, sd = self._start_from_guard_op(guard_op, mp, jump)
            #else:
            loop_consts, sd = self._compute_loop_consts(tree.inputargs, jump)
            self.loop_consts = loop_consts
            self.current_stack_depth = sd
        else:
            inp = guard_op.inputargs
            self.reg_bindings = {}
            self.stack_bindings = {}
            self.dirty_stack = {}
            for arg in inp:
                if arg in regalloc.reg_bindings:
                    self.reg_bindings[arg] = regalloc.reg_bindings[arg]
                if arg in regalloc.stack_bindings:
                    self.stack_bindings[arg] = regalloc.stack_bindings[arg]
                else:
                    assert arg in self.reg_bindings
                if arg in regalloc.dirty_stack:
                    self.dirty_stack[arg] = regalloc.dirty_stack[arg]
            allocated_regs = self.reg_bindings.values()
            self.free_regs = [v for v in REGS if v not in allocated_regs]
            self.current_stack_depth = regalloc.current_stack_depth
            self.longevity = guard_op.longevity
            jump_or_fail = guard_op.suboperations[-1]
            self.loop_consts = {}
            self.tree = regalloc.tree
            if jump_or_fail.opnum == rop.FAIL:
                self.jump_reg_candidates = {}
            else:
                if jump_or_fail.jump_target is regalloc.tree:
                    self.loop_consts = regalloc.loop_consts
                self._create_jump_reg_candidates(jump_or_fail)

    def _create_jump_reg_candidates(self, jump):
        self.jump_reg_candidates = {}
        for i in range(len(jump.args)):
            arg = jump.args[i]
            loc = jump.jump_target.arglocs[i]
            if isinstance(loc, REG):
                self.jump_reg_candidates[arg] = loc

    def copy(self, guard_op):
        return RegAlloc(self.assembler, None, self.translate_support_code,
                        self, guard_op)

#     def _start_from_guard_op(self, guard_op, mp, jump):
#         xxx
#         rev_stack_binds = {}
#         self.jump_reg_candidates = {}
#         j = 0
#         sd = len(mp.args)
#         if len(jump.args) > sd:
#             sd = len(jump.args)
#         for i in range(len(mp.args)):
#             arg = mp.args[i]
#             if not isinstance(arg, Const):
#                 stackpos = guard_op.stacklocs[j]
#                 if stackpos >= sd:
#                     sd = stackpos + 1
#                 loc = guard_op.locs[j]
#                 if isinstance(loc, REG):
#                     self.free_regs = [reg for reg in self.free_regs if reg is not loc]
#                     self.reg_bindings[arg] = loc
#                     self.dirty_stack[arg] = True
#                 self.stack_bindings[arg] = stack_pos(stackpos)
#                 rev_stack_binds[stackpos] = arg
#                 j += 1
#         if jump.opnum != rop.JUMP:
#             return {}, sd
#         for i in range(len(jump.args)):
#             argloc = jump.jump_target.arglocs[i]
#             jarg = jump.args[i]
#             if not isinstance(jarg, Const):
#                 if isinstance(argloc, REG):
#                     self.jump_reg_candidates[jarg] = argloc
#                 if (i in rev_stack_binds and
#                     (self.longevity[rev_stack_binds[i]][1] >
#                      self.longevity[jarg][0])):
#                     # variables cannot occupy the same place on stack,
#                     # because they overlap, but we care only in consider_jump
#                     pass
#                 else:
#                     # optimization for passing around values
#                     if jarg not in self.stack_bindings:
#                         self.dirty_stack[jarg] = True
#                         self.stack_bindings[jarg] = stack_pos(i)
#                 j += 1
#         return {}, sd

    def _compute_loop_consts(self, inputargs, jump):
        self.jump_reg_candidates = {}
        if jump.opnum != rop.JUMP or jump.jump_target is not self.tree:
            loop_consts = {}
        else:
            loop_consts = {}
            for i in range(len(inputargs)):
                if inputargs[i] is jump.args[i]:
                    loop_consts[inputargs[i]] = i
            #for i in range(len(inputargs)):
            #    arg = inputargs[i]
            #    jarg = jump.args[i]
            #    if arg is not jarg and not isinstance(jarg, Const):
            #        if self.longevity[arg][1] <= self.longevity[jarg][0]:
            #            if (jarg not in self.stack_bindings and
            #                arg in self.stack_bindings):
            #                self.stack_bindings[jarg] = stack_pos(i)
            #                self.dirty_stack[jarg] = True
        return loop_consts, len(inputargs)

    def _check_invariants(self):
        if not we_are_translated():
            # make sure no duplicates
            assert len(dict.fromkeys(self.reg_bindings.values())) == len(self.reg_bindings)
            # this is not true, due to jump args
            #assert (len(dict.fromkeys([str(i) for i in self.stack_bindings.values()]
            #                          )) == len(self.stack_bindings))
            rev_regs = dict.fromkeys(self.reg_bindings.values())
            for reg in self.free_regs:
                assert reg not in rev_regs
            assert len(rev_regs) + len(self.free_regs) == len(REGS)
            for v, val in self.stack_bindings.items():
                if (isinstance(v, Box) and (v not in self.reg_bindings) and
                    self.longevity[v][1] > self.position and
                    self.longevity[v][0] <= self.position):
                    assert not v in self.dirty_stack
        else:
            assert len(self.reg_bindings) + len(self.free_regs) == len(REGS)

    def Load(self, v, from_loc, to_loc):
        if not we_are_translated():
            self.assembler.dump('%s <- %s(%s)' % (to_loc, v, from_loc))
        self.assembler.regalloc_load(from_loc, to_loc)

    def Store(self, v, from_loc, to_loc):
        if not we_are_translated():
            self.assembler.dump('%s(%s) -> %s' % (v, from_loc, to_loc))
        self.assembler.regalloc_store(from_loc, to_loc)

    def Perform(self, op, arglocs, result_loc):
        if not we_are_translated():
            self.assembler.dump('%s <- %s(%s)' % (result_loc, op, arglocs))
        self.assembler.regalloc_perform(op, arglocs, result_loc)

    def perform_with_guard(self, op, guard_op, regalloc, arglocs, result_loc,
                           overflow=False):
        if not we_are_translated():
            self.assembler.dump('%s <- %s(%s) [GUARDED]' % (result_loc, op,
                                                            arglocs))
        self.assembler.regalloc_perform_with_guard(op, guard_op, regalloc,
                                                   arglocs, result_loc,
                                                   overflow)
        self.max_stack_depth = max(self.max_stack_depth,
                                   regalloc.max_stack_depth)

    def perform_guard(self, op, regalloc, arglocs, result_loc):
        if not we_are_translated():
            if result_loc is not None:
                self.assembler.dump('%s <- %s(%s)' % (result_loc, op, arglocs))
            else:
                self.assembler.dump('%s(%s)' % (op, arglocs))
        self.assembler.regalloc_perform_guard(op, regalloc, arglocs, result_loc)
        self.max_stack_depth = max(self.max_stack_depth,
                                   regalloc.max_stack_depth)

    def PerformDiscard(self, op, arglocs):
        if not we_are_translated():
            self.assembler.dump('%s(%s)' % (op, arglocs))
        self.assembler.regalloc_perform_discard(op, arglocs)

    def can_optimize_cmp_op(self, op, i, operations):
        if not (op.is_comparison() or op.opnum == rop.OOISNULL or
                op.opnum == rop.OONONNULL):
            return False
        if (operations[i + 1].opnum != rop.GUARD_TRUE and
            operations[i + 1].opnum != rop.GUARD_FALSE):
            return False
        if operations[i + 1].args[0] is not op.result:
            return False
        if self.longevity[op.result][1] > i + 1:
            return False
        if op.result in operations[i + 1].inputargs:
            # XXX implement optimization that replace var with a const
            #     not right now
            return False
        return True

    def walk_operations(self, tree):
        # first pass - walk along the operations in order to find
        # load/store places
        operations = tree.operations
        self.position = -1
        self.process_inputargs(tree)
        self._walk_operations(operations)

    def walk_guard_ops(self, inputargs, operations):
        for arg in inputargs:
            if arg not in self.reg_bindings:
                assert arg in self.stack_bindings
                assert arg not in self.dirty_stack
        self._walk_operations(operations)

    def _walk_operations(self, operations):
        i = 0
        while i < len(operations):
            op = operations[i]
            self.position = i
            if op.has_no_side_effect() and op.result not in self.longevity:
                canfold = True
            else:
                canfold = False
            if not canfold:
                # detect overflow ops
                if op.is_ovf():
                    assert operations[i + 1].opnum == rop.GUARD_NO_EXCEPTION
                    nothing = oplist[op.opnum](self, op, operations[i + 1])
                    i += 1
                elif self.can_optimize_cmp_op(op, i, operations):
                    nothing = oplist[op.opnum](self, op, operations[i + 1])
                    i += 1
                else:
                    nothing = oplist[op.opnum](self, op, None)
                assert nothing is None     # temporary, remove me
                self.eventually_free_var(op.result)
                self._check_invariants()
            else:
                self.eventually_free_vars(op.args)
            i += 1
        assert not self.reg_bindings
        jmp = operations[-1]
        if jmp.opnum == rop.JUMP and jmp.jump_target is not self.tree:
            self.max_stack_depth = max(jmp.jump_target._x86_stack_depth,
                                       self.max_stack_depth)
        self.max_stack_depth = max(self.max_stack_depth,
                                   self.current_stack_depth + 1)

    def _compute_vars_longevity(self, inputargs, operations):
        # compute a dictionary that maps variables to index in
        # operations that is a "last-time-seen"
        longevity = {}
        start_live = {}
        for inputarg in inputargs:
            start_live[inputarg] = 0
        for i in range(len(operations)):
            op = operations[i]
            if op.result is not None:
                start_live[op.result] = i
            for arg in op.args:
                if isinstance(arg, Box):
                    if arg not in start_live:
                        print "Bogus arg in operation %d at %d" % (op.opnum, i)
                        raise AssertionError
                    longevity[arg] = (start_live[arg], i)
            if op.is_guard():
                self._compute_inpargs(op)
                for arg in op.inputargs:
                    if isinstance(arg, Box):
                        if arg not in start_live:
                            print "Bogus arg in guard %d at %d" % (op.opnum, i)
                            raise AssertionError
                        longevity[arg] = (start_live[arg], i)
        for arg in inputargs:
            if arg not in longevity:
                longevity[arg] = (-1, -1)
        for arg in longevity:
            assert isinstance(arg, Box)
        self.longevity = longevity

    def _compute_inpargs(self, guard):
        if guard.inputargs is not None:
            return
        operations = guard.suboperations
        longevity = {}
        end = {}
        for i in range(len(operations)-1, -1, -1):
            op = operations[i]
            if op.is_guard():
                self._compute_inpargs(op)
                for arg in op.inputargs:
                    if isinstance(arg, Box) and arg not in end:
                        end[arg] = i
            for arg in op.args:
                if isinstance(arg, Box) and arg not in end:
                    end[arg] = i
            if op.result:
                if op.result in end:
                    longevity[op.result] = (i, end[op.result])
                    del end[op.result]
                # otherwise this var is never ever used
        for v, e in end.items():
            longevity[v] = (0, e)
        guard.longevity = longevity
        guard.inputargs = end.keys()
        for arg in longevity:
            assert isinstance(arg, Box)
        for arg in guard.inputargs:
            assert isinstance(arg, Box)

    def try_allocate_reg(self, v, selected_reg=None):
        if isinstance(v, Const):
            return convert_to_imm(v)
        if selected_reg is not None:
            res = self.reg_bindings.get(v, None)
            if res:
                if res is selected_reg:
                    return res
                else:
                    del self.reg_bindings[v]
                    self.free_regs.append(res)
            if selected_reg in self.free_regs:
                self.free_regs = [reg for reg in self.free_regs
                                  if reg is not selected_reg]
                self.reg_bindings[v] = selected_reg
                return selected_reg
            return None
        try:
            return self.reg_bindings[v]
        except KeyError:
            if self.free_regs:
                reg = self.jump_reg_candidates.get(v, None)
                if reg:
                    if reg in self.free_regs:
                        self.free_regs = [r for r in self.free_regs if r is not reg]
                        loc = reg
                    else:
                        loc = self.free_regs.pop()
                else:
                    loc = self.free_regs.pop()
                self.reg_bindings[v] = loc
                return loc

    def allocate_new_loc(self, v):
        reg = self.try_allocate_reg(v)
        if reg:
            return reg
        return self.stack_loc(v)

    def return_constant(self, v, forbidden_vars, selected_reg=None,
                        imm_fine=True):
        assert isinstance(v, Const)
        if selected_reg or not imm_fine:
            # this means we cannot have it in IMM, eh
            if selected_reg in self.free_regs:
                self.Load(v, convert_to_imm(v), selected_reg)
                return selected_reg
            if selected_reg is None and self.free_regs:
                loc = self.free_regs.pop()
                self.Load(v, convert_to_imm(v), loc)
                return loc
            v_to_spill = self.pick_variable_to_spill(v, forbidden_vars, selected_reg)
            loc = self.loc(v_to_spill)
            if v_to_spill not in self.stack_bindings or v_to_spill in self.dirty_stack:
                newloc = self.stack_loc(v_to_spill)
                try:
                    del self.dirty_stack[v_to_spill]
                except KeyError:
                    pass
                self.Store(v_to_spill, loc, newloc)
            del self.reg_bindings[v_to_spill]
            self.free_regs.append(loc)
            self.Load(v, convert_to_imm(v), loc)
            return loc
        return convert_to_imm(v)

    def force_allocate_reg(self, v, forbidden_vars, selected_reg=None):
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg)
        if isinstance(v, TempBox):
            self.longevity[v] = (self.position, self.position)
        loc = self.try_allocate_reg(v, selected_reg)
        if loc:
            return loc
        return self._spill_var(v, forbidden_vars, selected_reg)

    def _spill_var(self, v, forbidden_vars, selected_reg):
        v_to_spill = self.pick_variable_to_spill(v, forbidden_vars, selected_reg)
        loc = self.reg_bindings[v_to_spill]
        del self.reg_bindings[v_to_spill]
        self.reg_bindings[v] = loc
        if v_to_spill not in self.stack_bindings or v_to_spill in self.dirty_stack:
            newloc = self.stack_loc(v_to_spill)
            try:
                del self.dirty_stack[v_to_spill]
            except KeyError:
                pass
            self.Store(v_to_spill, loc, newloc)
        return loc

#     def _locs_from_liveboxes(self, guard_op):
#         stacklocs = []
#         locs = []
#         for arg in guard_op.inputargs:
#             assert isinstance(arg, Box)
#             if arg not in self.stack_bindings:
#                 self.dirty_stack[arg] = True
#             stacklocs.append(self.stack_loc(arg).position)
#             locs.append(self.loc(arg))
#         if not we_are_translated():
#             assert len(dict.fromkeys(stacklocs)) == len(stacklocs)
#         guard_op.stacklocs = stacklocs
#         guard_op.locs = locs
#         return locs

    def stack_loc(self, v):
        try:
            res = self.stack_bindings[v]
        except KeyError:
            newloc = stack_pos(self.current_stack_depth)
            self.stack_bindings[v] = newloc
            self.current_stack_depth += 1
            res = newloc
        assert isinstance(res, MODRM)
        return res

    def make_sure_var_in_reg(self, v, forbidden_vars, selected_reg=None,
                             imm_fine=True):
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg,
                                        imm_fine)
        prev_loc = self.loc(v)
        loc = self.force_allocate_reg(v, forbidden_vars, selected_reg)
        if prev_loc is not loc:
            self.Load(v, prev_loc, loc)
        return loc

    def make_sure_var_on_stack(self, v):
        loc = self.stack_loc(v)
        if v not in self.reg_bindings:
            return loc
        self.Store(v, self.reg_bindings[v], loc)
        try:
            del self.dirty_stack[v]
        except KeyError:
            pass
        return loc

    def reallocate_from_to(self, from_v, to_v):
        reg = self.reg_bindings[from_v]
        del self.reg_bindings[from_v]
        self.reg_bindings[to_v] = reg

    def eventually_free_var(self, v):
        if isinstance(v, Const) or v not in self.reg_bindings:
            return
        if v not in self.longevity or self.longevity[v][1] <= self.position:
            self.free_regs.append(self.reg_bindings[v])
            del self.reg_bindings[v]

    def eventually_free_vars(self, vlist):
        for v in vlist:
            self.eventually_free_var(v)

    def loc(self, v):
        if isinstance(v, Const):
            return convert_to_imm(v)
        try:
            return self.reg_bindings[v]
        except KeyError:
            return self.stack_bindings[v]

    def pick_variable_to_spill(self, v, forbidden_vars, selected_reg=None):
        # XXX could be improved
        if v in self.jump_reg_candidates and (selected_reg is None or
           self.jump_reg_candidates[v] is selected_reg):
            for var, reg in self.reg_bindings.items():
                if reg is self.jump_reg_candidates[v] and v not in forbidden_vars:
                    return var
        iter = self.reg_bindings.iterkeys()
        while 1:
            next = iter.next()
            if (next not in forbidden_vars and selected_reg is None or
                self.reg_bindings[next] is selected_reg):
                return next

    def move_variable_away(self, v, prev_loc):
        reg = None
        loc = self.stack_loc(v)
        try:
            del self.dirty_stack[v]
        except KeyError:
            pass
        self.Store(v, prev_loc, loc)

    def force_result_in_reg(self, result_v, v, forbidden_vars,
                            selected_reg=None):
        """ Make sure that result is in the same register as v
        and v is copied away if it's further used
        """
        if isinstance(v, Const):
            loc = self.make_sure_var_in_reg(v, forbidden_vars,
                                            selected_reg,
                                            imm_fine=False)
            assert not isinstance(loc, IMM8)
            self.reg_bindings[result_v] = loc
            self.free_regs = [reg for reg in self.free_regs if reg is not loc]
            return loc
        if v in self.reg_bindings and selected_reg:
            self.make_sure_var_in_reg(v, forbidden_vars, selected_reg)
        elif v not in self.reg_bindings:
            assert v not in self.dirty_stack
            prev_loc = self.stack_bindings[v]
            loc = self.force_allocate_reg(v, forbidden_vars, selected_reg)
            self.Load(v, prev_loc, loc)
        assert v in self.reg_bindings
        if self.longevity[v][1] > self.position:
            # we need to find a new place for variable x and
            # store result in the same place
            loc = self.reg_bindings[v]
            del self.reg_bindings[v]
            if v not in self.stack_bindings or v in self.dirty_stack:
                self.move_variable_away(v, loc)
            self.reg_bindings[result_v] = loc
        else:
            self.reallocate_from_to(v, result_v)
            loc = self.reg_bindings[result_v]
        return loc

    def process_inputargs(self, tree):
        # XXX we can sort out here by longevity if we need something
        # more optimal
        inputargs = tree.inputargs
        locs = [None] * len(inputargs)
        jump = tree.operations[-1]
        if jump.opnum != rop.JUMP:
            jump = None
        elif jump.jump_target is not tree:
            jump = self._create_jump_reg_candidates(jump)
            jump = None
        for i in range(len(inputargs)):
            arg = inputargs[i]
            assert not isinstance(arg, Const)
            reg = None
            if arg not in self.loop_consts and self.longevity[arg][1] > -1:
                reg = self.try_allocate_reg(arg)
            if reg:
                locs[i] = reg
                # it's better to say here that we're always in dirty stack
                # than worry at the jump point
                self.dirty_stack[arg] = True
                if jump is not None:
                    jarg = jump.args[i]
                    self.jump_reg_candidates[jarg] = reg
            else:
                loc = stack_pos(i)
                self.stack_bindings[arg] = loc
                locs[i] = loc
            # otherwise we have it saved on stack, so no worry
        tree.arglocs = locs
        self.assembler.make_merge_point(tree, locs)
        self.eventually_free_vars(inputargs)

    def regalloc_for_guard(self, guard_op):
        regalloc = self.copy(guard_op)
        fop = guard_op.suboperations[-1]
        if fop.opnum == rop.FAIL:
            regalloc.guard_index = self.assembler.cpu.make_guard_index(fop)
        return regalloc

    def _consider_guard(self, op, ignored):
        loc = self.make_sure_var_in_reg(op.args[0], [])
        regalloc = self.regalloc_for_guard(op)
        self.perform_guard(op, regalloc, [loc], None)
        self.eventually_free_var(op.args[0])
        self.eventually_free_vars(op.inputargs)

    consider_guard_true = _consider_guard
    consider_guard_false = _consider_guard

    def consider_fail(self, op, ignored):
        # make sure all vars are on stack
        locs = [self.loc(arg) for arg in op.args]
        self.assembler.generate_failure(op, locs, self.guard_index)
        self.eventually_free_vars(op.args)

    def consider_guard_nonvirtualized(self, op, ignored):
        # XXX implement it
        self.eventually_free_var(op.args[0])
        self.eventually_free_vars(op.inputargs)

    def consider_guard_no_exception(self, op, ignored):
        box = TempBox()
        loc = self.force_allocate_reg(box, [])
        regalloc = self.regalloc_for_guard(op)
        self.perform_guard(op, regalloc, [loc], None)
        self.eventually_free_vars(op.inputargs)
        self.eventually_free_var(box)

    def consider_guard_exception(self, op, ignored):
        loc = self.make_sure_var_in_reg(op.args[0], [])
        box = TempBox()
        loc1 = self.force_allocate_reg(box, op.args)
        if op.result in self.longevity:
            # this means, is it ever used
            resloc = self.force_allocate_reg(op.result, op.args + [box])
        else:
            resloc = None
        regalloc = self.regalloc_for_guard(op)
        self.perform_guard(op, regalloc, [loc, loc1], resloc)
        self.eventually_free_vars(op.inputargs)
        self.eventually_free_vars(op.args)
        self.eventually_free_var(box)

    #def consider_guard2(self, op, ignored):
    #    loc1, ops1 = self.make_sure_var_in_reg(op.args[0], [])
    #    loc2, ops2 = self.make_sure_var_in_reg(op.args[1], [])
    #    locs = [self.loc(arg) for arg in op.liveboxes]
    #    self.eventually_free_vars(op.args + op.liveboxes)
    #    return ops1 + ops2 + [PerformDiscard(op, [loc1, loc2] + locs)]

    #consider_guard_lt = consider_guard2
    #consider_guard_le = consider_guard2
    #consider_guard_eq = consider_guard2
    #consider_guard_ne = consider_guard2
    #consider_guard_gt = consider_guard2
    #consider_guard_ge = consider_guard2
    #consider_guard_is = consider_guard2
    #consider_guard_isnot = consider_guard2

    def consider_guard_value(self, op, ignored):
        x = self.loc(op.args[0])
        if not (isinstance(x, REG) or isinstance(op.args[1], Const)):
            x = self.make_sure_var_in_reg(op.args[0], [], imm_fine=False)
        y = self.loc(op.args[1])
        regalloc = self.regalloc_for_guard(op)
        self.perform_guard(op, regalloc, [x, y], None)
        self.eventually_free_vars(op.inputargs)
        self.eventually_free_vars(op.args)

    def consider_guard_class(self, op, ignored):
        x = self.make_sure_var_in_reg(op.args[0], [], imm_fine=False)
        y = self.loc(op.args[1])
        regalloc = self.regalloc_for_guard(op)
        self.perform_guard(op, regalloc, [x, y], None)
        self.eventually_free_vars(op.inputargs)
        self.eventually_free_vars(op.args)
    
    def _consider_binop_part(self, op, ignored):
        x = op.args[0]
        if isinstance(x, Const):
            res = self.force_allocate_reg(op.result, [])
            argloc = self.loc(op.args[1])
            self.eventually_free_var(op.args[1])
            self.Load(x, self.loc(x), res)
            return res, argloc
        loc = self.force_result_in_reg(op.result, x, op.args)
        argloc = self.loc(op.args[1])
        self.eventually_free_var(op.args[1])
        return loc, argloc

    def _consider_binop(self, op, ignored):
        loc, argloc = self._consider_binop_part(op, ignored)
        self.Perform(op, [loc, argloc], loc)

    consider_int_add = _consider_binop
    consider_int_mul = _consider_binop
    consider_int_sub = _consider_binop
    consider_int_and = _consider_binop
    consider_int_or  = _consider_binop
    consider_int_xor = _consider_binop
    consider_uint_xor = _consider_binop
    consider_uint_add = _consider_binop
    consider_uint_mul = _consider_binop
    consider_uint_sub = _consider_binop
    consider_uint_and = _consider_binop
    
    def _consider_binop_ovf(self, op, guard_op):
        loc, argloc = self._consider_binop_part(op, None)
        self.position += 1
        regalloc = self.regalloc_for_guard(guard_op)
        self.perform_with_guard(op, guard_op, regalloc, [loc, argloc], loc,
                                overflow=True)
        self.eventually_free_vars(guard_op.inputargs)
        self.eventually_free_var(guard_op.result)

    consider_int_mul_ovf = _consider_binop_ovf
    consider_int_sub_ovf = _consider_binop_ovf
    consider_int_add_ovf = _consider_binop_ovf

    def consider_int_neg(self, op, ignored):
        res = self.force_result_in_reg(op.result, op.args[0], [])
        self.Perform(op, [res], res)

    consider_int_invert = consider_int_neg
    consider_bool_not = consider_int_neg

    def consider_int_neg_ovf(self, op, guard_op):
        res = self.force_result_in_reg(op.result, op.args[0], [])
        self.position += 1
        regalloc = self.regalloc_for_guard(guard_op)
        self.perform_with_guard(op, guard_op, regalloc, [res], res,
                                overflow=True)
        self.eventually_free_vars(guard_op.inputargs)
        self.eventually_free_var(guard_op.result)

    def consider_int_lshift(self, op, ignored):
        loc2 = self.make_sure_var_in_reg(op.args[1], [], ecx)
        loc1 = self.force_result_in_reg(op.result, op.args[0], op.args)
        self.Perform(op, [loc1, loc2], loc1)
        self.eventually_free_vars(op.args)

    consider_int_rshift  = consider_int_lshift
    consider_uint_rshift = consider_int_lshift

    def consider_int_lshift_ovf(self, op, guard_op):
        loc2 = self.make_sure_var_in_reg(op.args[1], [], ecx)
        loc1 = self.force_result_in_reg(op.result, op.args[0], op.args)
        tmpvar = TempBox()
        tmploc = self.force_allocate_reg(tmpvar, [])
        self.eventually_free_vars(op.args)
        self.position += 1
        regalloc = self.regalloc_for_guard(guard_op)
        self.perform_with_guard(op, guard_op, regalloc, [loc1, loc2, tmploc],
                                loc1, overflow=True)
        self.eventually_free_vars(guard_op.inputargs)
        self.eventually_free_var(tmpvar)

    def _consider_int_div_or_mod(self, op, resultreg, trashreg):
        l0 = self.make_sure_var_in_reg(op.args[0], [], eax)
        l1 = self.make_sure_var_in_reg(op.args[1], [], ecx)
        l2 = self.force_allocate_reg(op.result, [], resultreg)
        # the register (eax or edx) not holding what we are looking for
        # will be just trash after that operation
        tmpvar = TempBox()
        self.force_allocate_reg(tmpvar, [], trashreg)
        assert (l0, l1, l2) == (eax, ecx, resultreg)
        self.eventually_free_vars(op.args + [tmpvar])

    def consider_int_mod(self, op, ignored):
        self._consider_int_div_or_mod(op, edx, eax)
        self.Perform(op, [eax, ecx], edx)

    def consider_int_mod_ovf(self, op, guard_op):
        self._consider_int_div_or_mod(op, edx, eax)
        self.position += 1
        regalloc = self.regalloc_for_guard(guard_op)
        self.perform_with_guard(op, guard_op, regalloc, [eax, ecx], edx,
                                overflow=True)
        self.eventually_free_vars(guard_op.inputargs)

    def consider_int_floordiv(self, op, ignored):
        self._consider_int_div_or_mod(op, eax, edx)
        self.Perform(op, [eax, ecx], eax)

    def consider_int_floordiv_ovf(self, op, guard_op):
        self._consider_int_div_or_mod(op, eax, edx)
        self.position += 1
        regalloc = self.regalloc_for_guard(guard_op)
        self.perform_with_guard(op, guard_op, regalloc, [eax, ecx], eax,
                                overflow=True)
        self.eventually_free_vars(guard_op.inputargs)

    def _consider_compop(self, op, guard_op):
        vx = op.args[0]
        vy = op.args[1]
        arglocs = [self.loc(vx), self.loc(vy)]
        if (vx in self.reg_bindings or vy in self.reg_bindings or
            isinstance(vx, Const) or isinstance(vy, Const)):
            pass
        else:
            arglocs[0] = self.make_sure_var_in_reg(vx, [])
        self.eventually_free_var(vx)
        self.eventually_free_var(vy)
        if guard_op is None:
            loc = self.force_allocate_reg(op.result, op.args)
            self.Perform(op, arglocs, loc)
        else:
            regalloc = self.regalloc_for_guard(guard_op)
            self.position += 1
            self.perform_with_guard(op, guard_op, regalloc, arglocs, None)
            self.eventually_free_var(op.result)
            self.eventually_free_vars(guard_op.inputargs)

    consider_int_lt = _consider_compop
    consider_int_gt = _consider_compop
    consider_int_ge = _consider_compop
    consider_int_le = _consider_compop
    xxx_consider_char_eq = _consider_compop
    consider_int_ne = _consider_compop
    consider_int_eq = _consider_compop
    consider_uint_gt = _consider_compop
    consider_uint_lt = _consider_compop
    consider_uint_le = _consider_compop
    consider_uint_ge = _consider_compop
    consider_oois = _consider_compop
    consider_ooisnot = _consider_compop

    def sync_var(self, v):
        if v in self.dirty_stack or v not in self.stack_bindings:
            reg = self.reg_bindings[v]
            self.Store(v, reg, self.stack_loc(v))
            try:
                del self.dirty_stack[v]
            except KeyError:
                pass
        # otherwise it's clean

    def sync_var_if_survives(self, v):
        if self.longevity[v][1] > self.position:
            self.sync_var(v)

    def _call(self, op, arglocs, force_store=[]):
        # we need to store all variables which are now in registers
        for v, reg in self.reg_bindings.items():
            if self.longevity[v][1] > self.position or v in force_store:
                self.sync_var(v)
        self.reg_bindings = newcheckdict()
        if op.result is not None:
            self.reg_bindings[op.result] = eax
            self.free_regs = [reg for reg in REGS if reg is not eax]
        else:
            self.free_regs = REGS[:]
        self.Perform(op, arglocs, eax)

    def consider_call(self, op, ignored):
        from pypy.jit.backend.x86.runner import CPU386
        calldescr = op.descr
        numargs, size, _ = CPU386.unpack_calldescr(calldescr)
        assert numargs == len(op.args) - 1
        return self._call(op, [imm(size)] +
                          [self.loc(arg) for arg in op.args])

    consider_call_pure = consider_call

    def consider_new(self, op, ignored):
        from pypy.jit.backend.x86.runner import ConstDescr3
        descr = op.descr
        assert isinstance(descr, ConstDescr3)
        return self._call(op, [imm(descr.v[0])])

    def consider_new_with_vtable(self, op, ignored):
        from pypy.jit.backend.x86.runner import ConstDescr3
        descr = op.descr
        assert isinstance(descr, ConstDescr3)
        return self._call(op, [imm(descr.v[0]), self.loc(op.args[0])])

    def consider_newstr(self, op, ignored):
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.STR, self.translate_support_code)
        assert itemsize == 1
        return self._malloc_varsize(0, ofs_items, ofs, 0, op.args[0],
                                    op.result)

    def consider_newunicode(self, op, ignored):
        ofs_items, itemsize, ofs = symbolic.get_array_token(rstr.UNICODE, self.translate_support_code)
        assert itemsize == 4
        return self._malloc_varsize(0, ofs_items, ofs, 2, op.args[0],
                                    op.result)

    def _malloc_varsize(self, ofs, ofs_items, ofs_length, size, v, res_v):
        if isinstance(v, Box):
            loc = self.make_sure_var_in_reg(v, [v])
            self.sync_var(v)
            if size != 0:
                # XXX lshift?
                self.Perform(ResOperation(rop.INT_MUL, [], None),
                             [loc, imm(1 << size)], loc)
            self.Perform(ResOperation(rop.INT_ADD, [], None),
                         [loc, imm(ofs + ofs_items)], loc)
        else:
            loc = imm(ofs + ofs_items + (v.getint() << size))
        self._call(ResOperation(rop.NEW, [v], res_v),
                   [loc], [v])
        loc = self.make_sure_var_in_reg(v, [res_v])
        assert self.loc(res_v) == eax
        # now we have to reload length to some reasonable place
        self.eventually_free_var(v)
        self.PerformDiscard(ResOperation(rop.SETFIELD_GC, [], None),
                            [eax, imm(ofs + ofs_length), imm(WORD), loc])

    def consider_new_array(self, op, ignored):
        size_of_field, basesize, _ = self._unpack_arraydescr(op.descr)
        return self._malloc_varsize(0, basesize, 0, size_of_field, op.args[0],
                                    op.result)

    def _unpack_arraydescr(self, arraydescr):
        from pypy.jit.backend.x86.runner import CPU386
        return CPU386.unpack_arraydescr(arraydescr)

    def _unpack_fielddescr(self, fielddescr):
        from pypy.jit.backend.x86.runner import CPU386
        ofs, size, _ = CPU386.unpack_fielddescr(fielddescr)
        return imm(ofs), imm(size)

    def consider_setfield_gc(self, op, ignored):
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc, size_loc = self._unpack_fielddescr(op.descr)
        value_loc = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, size_loc, value_loc])

    def consider_strsetitem(self, op, ignored):
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.make_sure_var_in_reg(op.args[1], op.args)
        value_loc = self.make_sure_var_in_reg(op.args[2], op.args)
        self.eventually_free_vars([op.args[0], op.args[1], op.args[2]])
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc])

    consider_unicodesetitem = consider_strsetitem

    def consider_setarrayitem_gc(self, op, ignored):
        scale, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc  = self.make_sure_var_in_reg(op.args[0], op.args)
        value_loc = self.make_sure_var_in_reg(op.args[2], op.args)
        ofs_loc = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars(op.args)
        self.PerformDiscard(op, [base_loc, ofs_loc, value_loc,
                                 imm(scale), imm(ofs)])

    def consider_getfield_gc(self, op, ignored):
        ofs_loc, size_loc = self._unpack_fielddescr(op.descr)
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        self.eventually_free_vars(op.args)
        result_loc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [base_loc, ofs_loc, size_loc], result_loc)

    consider_getfield_gc_pure = consider_getfield_gc

    def consider_getarrayitem_gc(self, op, ignored):
        scale, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars(op.args)
        result_loc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [base_loc, ofs_loc, imm(scale), imm(ofs)], result_loc)

    consider_getfield_raw = consider_getfield_gc
    consider_getarrayitem_gc_pure = consider_getarrayitem_gc

    def _consider_listop(self, op, ignored):
        return self._call(op, [self.loc(arg) for arg in op.args])
    
    xxx_consider_getitem     = _consider_listop
    xxx_consider_len         = _consider_listop
    xxx_consider_append      = _consider_listop
    xxx_consider_pop         = _consider_listop
    xxx_consider_setitem     = _consider_listop
    xxx_consider_newlist     = _consider_listop
    xxx_consider_insert      = _consider_listop
    xxx_consider_listnonzero = _consider_listop

    def _same_as(self, op, ignored):
        x = op.args[0]
        if isinstance(x, Const):
            pos = self.allocate_new_loc(op.result)
            self.Load(op.result, self.loc(x), pos)
            return
        if self.longevity[x][1] > self.position or x not in self.reg_bindings:
            if x in self.reg_bindings:
                res = self.allocate_new_loc(op.result)
                self.Load(op.result, self.loc(x), res)
            else:
                res = self.force_allocate_reg(op.result, op.args)
                self.Load(op.result, self.loc(x), res)
        else:
            self.reallocate_from_to(x, op.result)

    consider_cast_int_to_ptr = _same_as
    consider_cast_ptr_to_int = _same_as

    def consider_int_is_true(self, op, ignored):
        argloc = self.force_allocate_reg(op.args[0], [])
        self.eventually_free_var(op.args[0])
        resloc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [argloc], resloc)

    def consider_int_abs(self, op, ignored):
        argloc = self.force_allocate_reg(op.args[0], [])
        tmpvar = TempBox()
        tmploc = self.force_allocate_reg(tmpvar, [])
        resloc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [argloc, tmploc], resloc)
        self.eventually_free_var(op.args[0])
        self.eventually_free_var(tmpvar)

    def consider_int_abs_ovf(self, op, guard_op):
        argloc = self.force_allocate_reg(op.args[0], [])
        tmpvar = TempBox()
        tmploc = self.force_allocate_reg(tmpvar, [])
        resloc = self.force_allocate_reg(op.result, [])
        self.position += 1
        regalloc = self.regalloc_for_guard(guard_op)
        self.perform_with_guard(op, guard_op, regalloc, [argloc, tmploc],
                                resloc, overflow=True)
        self.eventually_free_vars(guard_op.inputargs)
        self.eventually_free_var(op.args[0])
        self.eventually_free_var(tmpvar)

    def _consider_nullity(self, op, guard_op):
        # doesn't need a register in arg
        if guard_op is not None:
            argloc = self.make_sure_var_in_reg(op.args[0], [])
            self.eventually_free_var(op.args[0])
            regalloc = self.regalloc_for_guard(guard_op)
            self.position += 1
            self.perform_with_guard(op, guard_op, regalloc, [argloc], None)
            self.eventually_free_var(op.result)
            self.eventually_free_vars(guard_op.inputargs)            
        else:
            argloc = self.loc(op.args[0])
            self.eventually_free_var(op.args[0])
            resloc = self.force_allocate_reg(op.result, [])
            self.Perform(op, [argloc], resloc)
    
    consider_ooisnull = _consider_nullity
    consider_oononnull = _consider_nullity

    def consider_strlen(self, op, ignored):
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        self.eventually_free_vars(op.args)
        result_loc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [base_loc], result_loc)

    consider_unicodelen = consider_strlen

    def consider_arraylen_gc(self, op, ignored):
        _, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        self.eventually_free_vars(op.args)
        result_loc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [base_loc, imm(ofs)], result_loc)

    def consider_strgetitem(self, op, ignored):
        base_loc = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars([op.args[0], op.args[1]])
        result_loc = self.force_allocate_reg(op.result, [])
        self.Perform(op, [base_loc, ofs_loc], result_loc)

    consider_unicodegetitem = consider_strgetitem

    def consider_jump(self, op, ignored):
        later_loads = []
        reloaded = []
        middle_busy_regs = []
        for i in range(len(op.args)):
            arg = op.args[i]
            loop = op.jump_target
            res = loop.arglocs[i]
            if not (isinstance(arg, Const) or (arg in self.loop_consts
                                               and self.loop_consts[arg] == i)):
                if arg in self.reg_bindings:
                    if not isinstance(res, REG):
                        self.Store(arg, self.loc(arg), loop.arglocs[i])
                    elif res is self.reg_bindings[arg]:
                        middle_busy_regs.append(res)
                    else:
                        # register, but wrong
                        # we're going to need it (otherwise it'll be dead), so
                        # we spill it and reload
                        # if our register is free, easy
                        for v, reg in self.reg_bindings.items():
                            if reg is res:
                                self.Store(arg, self.loc(arg),
                                           self.stack_loc(arg))
                                later_loads.append((arg, self.stack_loc(arg),
                                                    res))
                                break
                        else:
                            self.Load(arg, self.loc(arg), res)
                else:
                    if arg not in self.stack_bindings:
                        # we can load it correctly, because we don't care
                        # any more about the previous var staying there
                        assert not isinstance(res, REG)
                        self.Store(arg, self.loc(arg), res)
                    else:
                        assert arg not in self.dirty_stack
                        if isinstance(res, REG):
                            later_loads.append((arg, self.loc(arg), res))
                        else:
                            arg0 = self.loc(arg)
                            assert isinstance(arg0, MODRM)
                            assert isinstance(res, MODRM)
                            if arg0.position != res.position:
                                reloaded.append((arg, self.loc(arg), res))
            elif isinstance(arg, Const):
                later_loads.append((arg, self.loc(arg), res))
        if reloaded:
            # XXX performance
            free_reg = None
            for reg in REGS:
                if reg not in middle_busy_regs:
                    free_reg = reg
                    break
            if free_reg is None:
                # a very rare case
                v = self.reg_bindings.keys()[0]
                free_reg = self.reg_bindings[v]
                self.Store(v, self.loc(v), self.stack_loc(v))
                later_loads.insert(0, (v, self.stack_loc(v), self.loc(v)))
            for v, from_l, to_l in reloaded:
                self.Load(v, from_l, free_reg)
                self.Store(v, free_reg, to_l)
        self.eventually_free_vars(op.args)
        for v, from_l, to_l in later_loads:
            self.Load(v, from_l, to_l)
        self.PerformDiscard(op, [])

    def not_implemented_op(self, op, ignored):
        print "[regalloc] Not implemented operation: %s" % op.getopname()
        raise NotImplementedError

oplist = [RegAlloc.not_implemented_op] * rop._LAST

for name, value in RegAlloc.__dict__.iteritems():
    if name.startswith('consider_'):
        name = name[len('consider_'):]
        num = getattr(rop, name.upper())
        oplist[num] = value

def arg_pos(i, framesize):
    res = mem(esp, framesize + WORD * (i + 1))
    res.position = (i + 1) + framesize // WORD
    return res

def stack_pos(i):
    res = mem(esp, WORD * i)
    res.position = i
    return res

def lower_byte(reg):
    # argh
    if isinstance(reg, MODRM):
        return reg
    if isinstance(reg, IMM32):
        return imm8(reg.value)
    if reg is eax:
        return al
    elif reg is ebx:
        return bl
    elif reg is ecx:
        return cl
    elif reg is edx:
        return dl
    else:
        raise NotImplementedError()

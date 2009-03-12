
""" Register allocation scheme. The idea is as follows:
"""

from pypy.jit.metainterp.history import (Box, Const, ConstInt, ConstPtr,
                                         ResOperation, ConstAddr)
from pypy.jit.backend.x86.ri386 import *
from pypy.rpython.lltypesystem import lltype, ll2ctypes, rffi, rstr
from pypy.rlib.objectmodel import we_are_translated
from pypy.rlib.unroll import unrolling_iterable
from pypy.jit.backend.x86 import symbolic
from pypy.jit.metainterp.resoperation import rop, opname

# esi edi and ebp can be added to this list, provided they're correctly
# saved and restored
REGS = [eax, ecx, edx]
WORD = 4
FRAMESIZE = 1024    # XXX should not be a constant at all!!

RETURN = rop._LAST

class TempBox(Box):
    def __init__(self):
        pass

    def __repr__(self):
        return "<TempVar at %s>" % (id(self),)

class PseudoOperation(object):
    def __init__(self, v, from_loc, to_loc):
        self.from_loc = from_loc
        self.to_loc = to_loc
        self.v = v

# pseudo operations for loading/saving reg/mem
class Load(PseudoOperation):
    opname = 'load'

    def __repr__(self):
        return '%s <- %s(%s)' % (self.to_loc, self.v, self.from_loc)

class Store(PseudoOperation):
    opname = 'store'

    def __repr__(self):
        return '%s(%s) -> %s' % (self.v, self.from_loc, self.to_loc)

class Perform(PseudoOperation):
    opname = 'perform'

    def __init__(self, op, arglocs, result_loc):
        self.op = op
        self.result_loc = result_loc
        self.arglocs = arglocs

    def __repr__(self):
        return '%s <- %s(%s)' % (self.result_loc, self.op, self.arglocs)

class PerformWithGuard(PseudoOperation):
    opname = 'perform_with_guard'

    def __init__(self, op, guard_op, arglocs, result_loc):
        self.op = op
        self.guard_op = guard_op
        self.result_loc = result_loc
        self.arglocs = arglocs

    def __repr__(self):
        return '%s <- %s(%s) [GUARDED]' % (self.result_loc, self.op, self.arglocs)

class PerformDiscard(PseudoOperation):
    opname = 'perform_discard'

    def __init__(self, op, arglocs):
        self.op = op
        self.arglocs = arglocs

    def __repr__(self):
        return '%s(%s)' % (self.op, self.arglocs)

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
    def __init__(self, operations, guard_op=None, translate_support_code=False):
        # variables that have place in register
        self.translate_support_code = translate_support_code
        self.reg_bindings = newcheckdict()
        self.stack_bindings = {}
        # compute longevity of variables
        self._compute_vars_longevity(operations)
        self.free_regs = REGS[:]
        self.dirty_stack = {}
        mp = operations[0]
        self.first_merge_point = mp
        jump = operations[-1]
        self.startmp = mp
        if guard_op:
            loop_consts, sd = self._start_from_guard_op(guard_op, mp, jump)
        else:
            loop_consts, sd = self._compute_loop_consts(mp, jump)
        self.current_stack_depth = sd
        self.computed_ops = self.walk_operations(operations, loop_consts)
        assert not self.reg_bindings

    def _start_from_guard_op(self, guard_op, mp, jump):
        rev_stack_binds = {}
        self.jump_reg_candidates = {}
        j = 0
        sd = len(mp.args)
        if len(jump.args) > sd:
            sd = len(jump.args)
        for i in range(len(mp.args)):
            arg = mp.args[i]
            if not isinstance(arg, Const):
                stackpos = guard_op.stacklocs[j]
                if stackpos >= sd:
                    sd = stackpos + 1
                loc = guard_op.locs[j]
                if isinstance(loc, REG):
                    self.free_regs = [reg for reg in self.free_regs if reg is not loc]
                    self.reg_bindings[arg] = loc
                    self.dirty_stack[arg] = True
                self.stack_bindings[arg] = stack_pos(stackpos)
                rev_stack_binds[stackpos] = arg
                j += 1
        if jump.opnum != rop.JUMP:
            return {}, sd
        for i in range(len(jump.args)):
            argloc = jump.jump_target.arglocs[i]
            jarg = jump.args[i]
            if not isinstance(jarg, Const):
                if isinstance(argloc, REG):
                    self.jump_reg_candidates[jarg] = argloc
                if (i in rev_stack_binds and
                    (self.longevity[rev_stack_binds[i]][1] >
                     self.longevity[jarg][0])):
                    # variables cannot occupy the same place on stack,
                    # because they overlap, but we care only in consider_jump
                    pass
                else:
                    # optimization for passing around values
                    if jarg not in self.stack_bindings:
                        self.dirty_stack[jarg] = True
                        self.stack_bindings[jarg] = stack_pos(i)
                j += 1
        return {}, sd

    def _compute_loop_consts(self, mp, jump):
        self.jump_reg_candidates = {}
        if jump.opnum != rop.JUMP:
            loop_consts = {}
        else:
            assert jump.jump_target is mp
            free_regs = REGS[:]
            loop_consts = {}
            for i in range(len(mp.args)):
                if mp.args[i] is jump.args[i]:
                    loop_consts[mp.args[i]] = i
            for i in range(len(mp.args)):
                arg = mp.args[i]
                jarg = jump.args[i]
                if arg is not jarg and not isinstance(jarg, Const):
                    if free_regs:
                        self.jump_reg_candidates[jarg] = free_regs.pop()
                    if self.longevity[arg][1] <= self.longevity[jarg][0]:
                        if jarg not in self.stack_bindings:
                            self.stack_bindings[jarg] = stack_pos(i)
                            self.dirty_stack[jarg] = True
                else:
                    # these are loop consts, but we need stack space anyway
                    self.stack_bindings[jarg] = stack_pos(i)
        return loop_consts, len(mp.args)

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

    def can_optimize_cmp_op(self, op, i, operations):
        if not op.is_comparison():
            return False
        if (operations[i + 1].opnum != rop.GUARD_TRUE and
            operations[i + 1].opnum != rop.GUARD_FALSE):
            return False
        if operations[i + 1].args[0] is not op.result:
            return False
        if self.longevity[op.result][1] > i + 1:
            return False
        return True

    def walk_operations(self, operations, loop_consts):
        # first pass - walk along the operations in order to find
        # load/store places
        new_ops = []
        self.loop_consts = loop_consts
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
                    new_ops += oplist[op.opnum](self, op, operations[i + 1])
                    i += 1
                elif self.can_optimize_cmp_op(op, i, operations):
                    new_ops += oplist[op.opnum](self, op, operations[i + 1])
                    i += 1
                else:
                    new_ops += oplist[op.opnum](self, op, None)
                self.eventually_free_var(op.result)
                self._check_invariants()
            else:
                self.eventually_free_vars(op.args)
            i += 1
        return new_ops

    def _compute_vars_longevity(self, operations):
        # compute a dictionary that maps variables to index in
        # operations that is a "last-time-seen"
        longevity = {}
        start_live = {}
        for v in operations[0].args:
            start_live[v] = 0
        for i in range(len(operations)):
            op = operations[i]
            if op.result is not None:
                start_live[op.result] = i
            for arg in op.args:
                if isinstance(arg, Box):
                    longevity[arg] = (start_live[arg], i)
            if op.is_guard():
                for arg in op.liveboxes:
                    if isinstance(arg, Box):
                        longevity[arg] = (start_live[arg], i)
        self.longevity = longevity

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
                return selected_reg, [Load(v, convert_to_imm(v), selected_reg)]
            if selected_reg is None and self.free_regs:
                loc = self.free_regs.pop()
                return loc, [Load(v, convert_to_imm(v), loc)]
            v_to_spill = self.pick_variable_to_spill(v, forbidden_vars, selected_reg)
            loc = self.loc(v_to_spill)
            if v_to_spill not in self.stack_bindings or v_to_spill in self.dirty_stack:
                newloc = self.stack_loc(v_to_spill)
                try:
                    del self.dirty_stack[v_to_spill]
                except KeyError:
                    pass
                ops = [Store(v_to_spill, loc, newloc)]
            else:
                ops = []
            del self.reg_bindings[v_to_spill]
            self.free_regs.append(selected_reg)
            return selected_reg, ops+[Load(v, convert_to_imm(v), loc)]
        return convert_to_imm(v), []

    def force_allocate_reg(self, v, forbidden_vars, selected_reg=None):
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg)
        if isinstance(v, TempBox):
            self.longevity[v] = (self.position, self.position)
        loc = self.try_allocate_reg(v, selected_reg)
        if loc:
            return loc, []
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
            return loc, [Store(v_to_spill, loc, newloc)]
        return loc, []

    def _locs_from_liveboxes(self, guard_op):
        stacklocs = []
        locs = []
        for arg in guard_op.liveboxes:
            if isinstance(arg, Box):
                if arg not in self.stack_bindings:
                    self.dirty_stack[arg] = True
                stacklocs.append(self.stack_loc(arg).position)
                locs.append(self.loc(arg))
        if not we_are_translated():
            assert len(dict.fromkeys(stacklocs)) == len(stacklocs)
        guard_op.stacklocs = stacklocs
        guard_op.locs = locs
        return locs

    def stack_loc(self, v):
        try:
            res = self.stack_bindings[v]
        except KeyError:
            newloc = stack_pos(self.current_stack_depth)
            self.stack_bindings[v] = newloc
            self.current_stack_depth += 1
            res = newloc
        if res.position > FRAMESIZE/WORD:
            raise NotImplementedError("Exceeded FRAME_SIZE")
        return res

    def make_sure_var_in_reg(self, v, forbidden_vars, selected_reg=None,
                             imm_fine=True):
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg,
                                        imm_fine)
        prev_loc = self.loc(v)
        loc, ops = self.force_allocate_reg(v, forbidden_vars, selected_reg)
        if prev_loc is loc:
            return loc, ops
        return loc, ops + [Load(v, prev_loc, loc)]

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
        if v in self.jump_reg_candidates:
            assert selected_reg is None # I don't want to care...
            # now we need to spill a variable that resides in a place where
            # we would like our var to be.
            # XXX Needs test
            # XXX better storage
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
        return Store(v, prev_loc, loc)

    def force_result_in_reg(self, result_v, v, forbidden_vars,
                            selected_reg=None):
        """ Make sure that result is in the same register as v
        and v is copied away if it's further used
        """
        if isinstance(v, Const):
            loc, ops = self.make_sure_var_in_reg(v, forbidden_vars,
                                                 selected_reg,
                                                 imm_fine=False)
            assert not isinstance(loc, IMM8)
            self.reg_bindings[result_v] = loc
            self.free_regs = [reg for reg in self.free_regs if reg is not loc]
            return loc, ops
        ops = []
        if v in self.reg_bindings and selected_reg:
            _, ops = self.make_sure_var_in_reg(v, forbidden_vars, selected_reg)
        elif v not in self.reg_bindings:
            assert v not in self.dirty_stack
            prev_loc = self.stack_bindings[v]
            loc, o = self.force_allocate_reg(v, forbidden_vars, selected_reg)
            ops += o
            ops.append(Load(v, prev_loc, loc))
        assert v in self.reg_bindings
        if self.longevity[v][1] > self.position:
            # we need to find a new place for variable x and
            # store result in the same place
            loc = self.reg_bindings[v]
            del self.reg_bindings[v]
            if v not in self.stack_bindings or v in self.dirty_stack:
                ops.append(self.move_variable_away(v, loc))
            self.reg_bindings[result_v] = loc
        else:
            self.reallocate_from_to(v, result_v)
            loc = self.reg_bindings[result_v]
        return loc, ops

    def consider_merge_point(self, op, ignored):
        # XXX we can sort out here by longevity if we need something
        # more optimal
        ops = [PerformDiscard(op, [])]
        locs = [None] * len(op.args)
        for i in range(len(op.args)):
            arg = op.args[i]
            assert not isinstance(arg, Const)
            reg = None
            loc = stack_pos(i)
            self.stack_bindings[arg] = loc
            if arg not in self.loop_consts:
                reg = self.try_allocate_reg(arg)
            if reg:
                locs[i] = reg
                # it's better to say here that we're always in dirty stack
                # than worry at the jump point
                self.dirty_stack[arg] = True
            else:
                locs[i] = loc
            # otherwise we have it saved on stack, so no worry
        op.arglocs = locs
        ops[-1].arglocs = op.arglocs
        op.stacklocs = [i for i in range(len(op.args))]
        # XXX be a bit smarter and completely ignore such vars
        self.eventually_free_vars(op.args)
        return ops

    def consider_catch(self, op, ignored):
        locs = []
        for arg in op.args:
            l = self.loc(arg)
            if isinstance(l, REG):
                self.dirty_stack[arg] = True
            locs.append(l)
            # possibly constants
        op.arglocs = locs
        op.stacklocs = [self.stack_loc(arg).position for arg in op.args]
        self.eventually_free_vars(op.args)
        return [PerformDiscard(op, [])]

    def _consider_guard(self, op, ignored):
        loc, ops = self.make_sure_var_in_reg(op.args[0], [])
        locs = self._locs_from_liveboxes(op)
        self.eventually_free_var(op.args[0])
        self.eventually_free_vars(op.liveboxes)
        return ops + [PerformDiscard(op, [loc] + locs)]

    consider_guard_true = _consider_guard
    consider_guard_false = _consider_guard

    def consider_guard_nonvirtualized(self, op, ignored):
        # XXX implement it
        locs = self._locs_from_liveboxes(op)
        self.eventually_free_var(op.args[0])
        self.eventually_free_vars(op.liveboxes)
        return []

    def consider_guard_no_exception(self, op, ignored):
        box = TempBox()
        loc, ops = self.force_allocate_reg(box, [])
        locs = self._locs_from_liveboxes(op)
        self.eventually_free_vars(op.liveboxes)
        self.eventually_free_var(box)
        return ops + [PerformDiscard(op, [loc] + locs)]

    def consider_guard_exception(self, op, ignored):
        loc, ops = self.make_sure_var_in_reg(op.args[0], [])
        box = TempBox()
        loc1, ops1 = self.force_allocate_reg(box, op.args)
        if op.result in self.longevity:
            # this means, is it ever used
            resloc, ops2 = self.force_allocate_reg(op.result,
                                                   op.args + [box])
        else:
            resloc, ops2 = None, []
        locs = self._locs_from_liveboxes(op)
        self.eventually_free_vars(op.liveboxes)
        self.eventually_free_vars(op.args)
        self.eventually_free_var(box)
        return ops + ops1 + ops2 + [Perform(op, [loc, loc1] + locs, resloc)]

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
            x, ops = self.make_sure_var_in_reg(op.args[0], [], imm_fine=False)
        else:
            ops = []
        y = self.loc(op.args[1])
        locs = self._locs_from_liveboxes(op)
        self.eventually_free_vars(op.liveboxes + op.args)
        return ops + [PerformDiscard(op, [x, y] + locs)]

    def consider_guard_class(self, op, ignored):
        x, ops = self.make_sure_var_in_reg(op.args[0], [], imm_fine=False)
        y = self.loc(op.args[1])
        locs = self._locs_from_liveboxes(op)
        self.eventually_free_vars(op.liveboxes + op.args)
        return ops + [PerformDiscard(op, [x, y] + locs)]

    def consider_return(self, op, ignored):
        if op.args:
            arglocs = [self.loc(op.args[0])]
            self.eventually_free_var(op.args[0])
        else:
            arglocs = []
        return [PerformDiscard(op, arglocs)]
    
    def _consider_binop_part(self, op, ignored):
        x = op.args[0]
        ops = []
        if isinstance(x, Const):
            res, ops = self.force_allocate_reg(op.result, [])
            argloc = self.loc(op.args[1])
            self.eventually_free_var(op.args[1])
            load_op = Load(x, self.loc(x), res)
            return res, argloc, ops + [load_op]
        loc, ops = self.force_result_in_reg(op.result, x, op.args)
        argloc = self.loc(op.args[1])
        self.eventually_free_var(op.args[1])
        return loc, argloc, ops

    def _consider_binop(self, op, ignored):
        loc, argloc, ops = self._consider_binop_part(op, ignored)
        return ops + [Perform(op, [loc, argloc], loc)]

    consider_int_add = _consider_binop
    consider_int_mul = _consider_binop
    consider_int_sub = _consider_binop
    consider_int_and = _consider_binop
    consider_int_or  = _consider_binop
    consider_int_xor = _consider_binop
    consider_uint_add = _consider_binop
    consider_uint_mul = _consider_binop
    consider_uint_sub = _consider_binop
    #consider_uint_and = _consider_binop
    
    def _consider_binop_ovf(self, op, guard_op):
        loc, argloc, ops = self._consider_binop_part(op, None)
        locs = self._locs_from_liveboxes(guard_op)
        self.position += 1
        self.eventually_free_vars(guard_op.liveboxes)
        return ops + [PerformWithGuard(op, guard_op, [loc, argloc] + locs, loc)]

    consider_int_mul_ovf = _consider_binop_ovf
    consider_int_sub_ovf = _consider_binop_ovf
    consider_int_add_ovf = _consider_binop_ovf
    # XXX ovf_neg op

    def consider_int_neg(self, op, ignored):
        res, ops = self.force_result_in_reg(op.result, op.args[0], [])
        return ops + [Perform(op, [res], res)]

    consider_bool_not = consider_int_neg

    def consider_int_rshift(self, op, ignored):
        tmpvar = TempBox()
        reg, ops = self.force_allocate_reg(tmpvar, [], ecx)
        y = self.loc(op.args[1])
        x, more_ops = self.force_result_in_reg(op.result, op.args[0],
                                               op.args + [tmpvar])
        self.eventually_free_vars(op.args + [tmpvar])
        return ops + more_ops + [Perform(op, [x, y, reg], x)]

    def consider_int_mod(self, op, ignored):
        l0, ops0 = self.make_sure_var_in_reg(op.args[0], [], eax)
        l1, ops1 = self.make_sure_var_in_reg(op.args[1], [], ecx)
        l2, ops2 = self.force_allocate_reg(op.result, [], edx)
        # eax is trashed after that operation
        tmpvar = TempBox()
        _, ops3 = self.force_allocate_reg(tmpvar, [], eax)
        assert (l0, l1, l2) == (eax, ecx, edx)
        self.eventually_free_vars(op.args + [tmpvar])
        return ops0 + ops1 + ops2 + ops3 + [Perform(op, [eax, ecx], edx)]

    def consider_int_mod_ovf(self, op, guard_op):
        l0, ops0 = self.make_sure_var_in_reg(op.args[0], [], eax)
        l1, ops1 = self.make_sure_var_in_reg(op.args[1], [], ecx)
        l2, ops2 = self.force_allocate_reg(op.result, [], edx)
        tmpvar = TempBox()
        _, ops3 = self.force_allocate_reg(tmpvar, [], eax)
        assert (l0, l1, l2) == (eax, ecx, edx)
        locs = self._locs_from_liveboxes(guard_op)
        self.eventually_free_vars(op.args + [tmpvar])
        self.position += 1
        self.eventually_free_vars(guard_op.liveboxes)
        return (ops0 + ops1 + ops2 + ops3 +
                [PerformWithGuard(op, guard_op, [eax, ecx] + locs, edx)])

    def consider_int_floordiv(self, op, ignored):
        tmpvar = TempBox()
        l0, ops0 = self.force_result_in_reg(op.result, op.args[0], [], eax)
        l1, ops1 = self.make_sure_var_in_reg(op.args[1], [], ecx)
        # we need to make sure edx is empty, since we're going to use it
        l2, ops2 = self.force_allocate_reg(tmpvar, [], edx)
        assert (l0, l1, l2) == (eax, ecx, edx)
        self.eventually_free_vars(op.args + [tmpvar])
        return ops0 + ops1 + ops2 + [Perform(op, [eax, ecx], eax)]

    def _consider_compop(self, op, guard_op):
        vx = op.args[0]
        vy = op.args[1]
        arglocs = [self.loc(vx), self.loc(vy)]
        if (vx in self.reg_bindings or vy in self.reg_bindings or
            isinstance(vx, Const) or isinstance(vy, Const)):
            ops0 = []
        else:
            arglocs[0], ops0 = self.force_allocate_reg(vx, [])
        self.eventually_free_var(vx)
        self.eventually_free_var(vy)
        if guard_op is None:
            loc, ops = self.force_allocate_reg(op.result, op.args)
            return ops0 + ops + [Perform(op, arglocs, loc)]
        else:
            locs = self._locs_from_liveboxes(guard_op)
            self.position += 1
            self.eventually_free_var(op.result)
            self.eventually_free_vars(guard_op.liveboxes)
            return ops0 + [PerformWithGuard(op, guard_op, arglocs + locs, None)]

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

    def sync_var(self, v):
        ops = []
        if v in self.dirty_stack or v not in self.stack_bindings:
            reg = self.reg_bindings[v]
            ops.append(Store(v, reg, self.stack_loc(v)))
            try:
                del self.dirty_stack[v]
            except KeyError:
                pass
        # otherwise it's clean
        return ops

    def sync_var_if_survives(self, v):
        if self.longevity[v][1] > self.position:
            return self.sync_var(v)
        return []

    def _call(self, op, arglocs, force_store=[]):
        ops = []
        # we need to store all variables which are now in registers
        for v, reg in self.reg_bindings.items():
            if self.longevity[v][1] > self.position or v in force_store:
                ops += self.sync_var(v)
        self.reg_bindings = newcheckdict()
        if op.result is not None:
            self.reg_bindings = {op.result: eax}
            self.free_regs = [reg for reg in REGS if reg is not eax]
            return ops + [Perform(op, arglocs, eax)]
        else:
            self.free_regs = REGS[:]
            return ops + [Perform(op, arglocs, eax)]

    def consider_call(self, op, ignored):
        from pypy.jit.backend.x86.runner import CPU386
        calldescr = op.descr
        numargs, size, _ = CPU386.unpack_calldescr(calldescr)
        assert numargs == len(op.args) - 1
        return self._call(op, [imm(size)] +
                          [self.loc(arg) for arg in op.args])

    consider_call_pure = consider_call

    def consider_new(self, op, ignored):
        return self._call(op, [imm(op.descr.v[0])])

    def consider_new_with_vtable(self, op, ignored):
        return self._call(op, [imm(op.descr.v[0]), self.loc(op.args[0])])

    def consider_newstr(self, op, ignored):
        ofs_items, _, ofs = symbolic.get_array_token(rstr.STR, self.translate_support_code)
        return self._malloc_varsize(0, ofs_items, ofs, 0, op.args[0],
                                    op.result)

    def _malloc_varsize(self, ofs, ofs_items, ofs_length, size, v, res_v):
        if isinstance(v, Box):
            loc, ops0 = self.make_sure_var_in_reg(v, [v])
            ops0 += self.sync_var(v)
            if size != 0:
                # XXX lshift?
                ops0.append(Perform(ResOperation(rop.INT_MUL, [], None),
                                [loc, imm(1 << size)], loc))
            ops0.append(Perform(ResOperation(rop.INT_ADD, [], None),
                                [loc, imm(ofs + ofs_items)], loc))
        else:
            ops0 = []
            loc = imm(ofs + ofs_items + (v.getint() << size))
        ops = self._call(ResOperation(rop.NEW, [v], res_v)
                         , [loc], [v])
        loc, ops1 = self.make_sure_var_in_reg(v, [res_v])
        assert self.loc(res_v) == eax
        # now we have to reload length to some reasonable place
        self.eventually_free_var(v)
        res = (ops0 + ops + ops1 +
               [PerformDiscard(ResOperation(rop.SETFIELD_GC, [], None),
                               [eax, imm(ofs + ofs_length), imm(WORD), loc])])
        return res

    def consider_new_array(self, op, ignored):
        size_of_field, basesize, _ = self._unpack_arraydescr(op.descr)
        return self._malloc_varsize(0, basesize, 0, size_of_field, op.args[0],
                                    op.result)

    def consider_oononnull(self, op, ignored):
        argloc = self.loc(op.args[0])
        self.eventually_free_var(op.args[0])
        reg = self.try_allocate_reg(op.result)
        assert reg
        return [Perform(op, [argloc], reg)]

    def _unpack_arraydescr(self, arraydescr):
        from pypy.jit.backend.x86.runner import CPU386
        return CPU386.unpack_arraydescr(arraydescr)

    def _unpack_fielddescr(self, fielddescr):
        from pypy.jit.backend.x86.runner import CPU386
        ofs, size, _ = CPU386.unpack_fielddescr(fielddescr)
        return imm(ofs), imm(size)

    def consider_setfield_gc(self, op, ignored):
        base_loc, ops0  = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc, size_loc = self._unpack_fielddescr(op.descr)
        value_loc, ops2 = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars(op.args)
        return (ops0 + ops2 +
                [PerformDiscard(op, [base_loc, ofs_loc, size_loc, value_loc])])

    def consider_strsetitem(self, op, ignored):
        base_loc, ops0  = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc, ops1 = self.make_sure_var_in_reg(op.args[1], op.args)
        value_loc, ops2 = self.make_sure_var_in_reg(op.args[2], op.args)
        self.eventually_free_vars([op.args[0], op.args[1], op.args[2]])
        return (ops0 + ops1 + ops2 +
                [PerformDiscard(op, [base_loc, ofs_loc, value_loc])])

    def consider_setarrayitem_gc(self, op, ignored):
        scale, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc, ops0  = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc, ops1 = self.make_sure_var_in_reg(op.args[1], op.args)
        value_loc, ops2 = self.make_sure_var_in_reg(op.args[2], op.args)
        self.eventually_free_vars(op.args)
        return (ops0 + ops2 + ops1 +
                [PerformDiscard(op, [base_loc, ofs_loc, value_loc,
                                     imm(scale), imm(ofs)])])

    def consider_getfield_gc(self, op, ignored):
        ofs_loc, size_loc = self._unpack_fielddescr(op.descr)
        base_loc, ops0 = self.make_sure_var_in_reg(op.args[0], op.args)
        self.eventually_free_vars(op.args)
        result_loc, more_ops = self.force_allocate_reg(op.result, [])
        return (ops0 + more_ops +
                [Perform(op, [base_loc, ofs_loc, size_loc], result_loc)])

    consider_getfield_gc_pure = consider_getfield_gc

    def consider_getarrayitem_gc(self, op, ignored):
        scale, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc, ops0  = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc, ops1 = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars(op.args)
        result_loc, more_ops = self.force_allocate_reg(op.result, [])
        return (ops0 + ops1 + more_ops +
                [Perform(op, [base_loc, ofs_loc, imm(scale), imm(ofs)],
                         result_loc)])

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

#     def consider_same_as(self, op, ignored):
#         x = op.args[0]
#         if isinstance(x, Const):
#             pos = self.allocate_new_loc(op.result)
#             return [Load(op.result, self.loc(x), pos)]
#         if self.longevity[x][1] > self.position or x not in self.reg_bindings:
#             if x in self.reg_bindings:
#                 res = self.allocate_new_loc(op.result)
#                 return [Load(op.result, self.loc(x), res)]
#             else:
#                 res, ops = self.force_allocate_reg(op.result, op.args)
#                 return ops + [Load(op.result, self.loc(x), res)]
#         else:
#             self.reallocate_from_to(x, op.result)
#             return []

#    consider_cast_int_to_char = consider_same_as
#    xxx_consider_cast_int_to_ptr  = consider_same_as

    def consider_int_is_true(self, op, ignored):
        argloc, ops = self.force_allocate_reg(op.args[0], [])
        self.eventually_free_var(op.args[0])
        resloc, more_ops = self.force_allocate_reg(op.result, [])
        return ops + more_ops + [Perform(op, [argloc], resloc)]

    def _consider_nullity(self, op, ignored):
        # doesn't need a register in arg
        argloc = self.loc(op.args[0])
        self.eventually_free_var(op.args[0])
        resloc, ops = self.force_allocate_reg(op.result, [])
        return ops + [Perform(op, [argloc], resloc)]
    
    consider_ooisnull = _consider_nullity
    consider_oononnull = _consider_nullity

    def consider_strlen(self, op, ignored):
        base_loc, ops0 = self.make_sure_var_in_reg(op.args[0], op.args)
        self.eventually_free_vars(op.args)
        result_loc, more_ops = self.force_allocate_reg(op.result, [])
        return ops0 + more_ops + [Perform(op, [base_loc], result_loc)]

    def consider_arraylen_gc(self, op, ignored):
        _, ofs, _ = self._unpack_arraydescr(op.descr)
        base_loc, ops0 = self.make_sure_var_in_reg(op.args[0], op.args)
        self.eventually_free_vars(op.args)
        result_loc, more_ops = self.force_allocate_reg(op.result, [])
        return ops0 + more_ops + [Perform(op, [base_loc, imm(ofs)],
                                          result_loc)]

    def consider_strgetitem(self, op, ignored):
        base_loc, ops0 = self.make_sure_var_in_reg(op.args[0], op.args)
        ofs_loc, ops1 = self.make_sure_var_in_reg(op.args[1], op.args)
        self.eventually_free_vars([op.args[0], op.args[1]])
        result_loc, more_ops = self.force_allocate_reg(op.result, [])
        return (ops0 + ops1 + more_ops +
                [Perform(op, [base_loc, ofs_loc], result_loc)])

    def consider_jump(self, op, ignored):
        ops = []
        laterops = []
        middle_ops = []
        reloaded = []
        middle_busy_regs = []
        for i in range(len(op.args)):
            arg = op.args[i]
            mp = op.jump_target
            res = mp.arglocs[i]
            if not (isinstance(arg, Const) or (arg in self.loop_consts
                                               and self.loop_consts[arg] == i)):
                assert mp.opnum == rop.MERGE_POINT
                if arg in self.reg_bindings:
                    if not isinstance(res, REG):
                        ops.append(Store(arg, self.loc(arg), self.stack_bindings[arg]))
                    elif res is self.reg_bindings[arg]:
                        middle_busy_regs.append(res)
                    else:
                        # register, but wrong
                        # we're going to need it (otherwise it'll be dead), so
                        # we spill it and reload
                        # if our register is free, easy
                        for v, reg in self.reg_bindings.items():
                            if reg is res:
                                ops.append(Store(arg, self.loc(arg), self.stack_loc(arg)))
                                laterops.append(Load(arg, self.stack_loc(arg), res))
                                break
                        else:
                            ops.append(Load(arg, self.loc(arg), res))
                else:
                    if arg not in self.stack_bindings:
                        # we can load it correctly, because we don't care
                        # any more about the previous var staying there
                        assert not isinstance(res, REG)
                        ops.append(Store(arg, self.loc(arg), res))
                    else:
                        assert arg not in self.dirty_stack
                        if isinstance(res, REG):
                            laterops.append(Load(arg, self.loc(arg), res))
                        else:
                            arg0 = self.loc(arg)
                            assert isinstance(arg0, MODRM)
                            assert isinstance(res, MODRM)
                            if arg0.position != res.position:
                                reloaded.append((arg, self.loc(arg), res))
            elif isinstance(arg, Const):
                laterops.append(Load(arg, self.loc(arg), res))
        if reloaded:
            self.eventually_free_vars(op.args)
            middleops = []
            # XXX performance
            free_reg = None
            last_middle_op = None
            for reg in REGS:
                if reg not in middle_busy_regs:
                    free_reg = reg
                    break
            if free_reg is None:
                # a very rare case
                v = self.reg_bindings.keys()[0]
                free_reg = self.reg_bindings[v]
                ops.append(Store(v, self.loc(v), self.stack_loc(v)))
                last_middle_op = Load(v, self.stack_loc(v), self.loc(v))
            for v, from_l, to_l in reloaded:
                middleops.append(Load(v, from_l, free_reg))
                middleops.append(Store(v, free_reg, to_l))
            if last_middle_op is not None:
                middleops.append(last_middle_op)
            return ops + middleops + laterops + [PerformDiscard(op, [])]
        self.eventually_free_vars(op.args)
        return ops + laterops + [PerformDiscard(op, [])]

    def not_implemented_op(self, op, ignored):
        print "[regalloc] Not implemented operation: %s" % op.getopname()
        raise NotImplementedError

oplist = [RegAlloc.not_implemented_op] * (RETURN + 1)

for name, value in RegAlloc.__dict__.iteritems():
    if name.startswith('consider_'):
        name = name[len('consider_'):]
        if name == 'return':
            num = RETURN
        else:
            num = getattr(rop, name.upper())
        oplist[num] = value

def arg_pos(i):
    res = mem(esp, FRAMESIZE + WORD * (i + 1))
    res.position = (i + 1) + FRAMESIZE // WORD
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

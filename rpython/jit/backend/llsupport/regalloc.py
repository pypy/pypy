import os
from rpython.jit.metainterp.history import Const, REF, JitCellToken
from rpython.rlib.objectmodel import we_are_translated, specialize
from rpython.jit.metainterp.resoperation import rop, AbstractValue
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.lltypesystem.lloperation import llop

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = dict # too bad

class TempVar(AbstractValue):
    def __init__(self):
        pass

    def __repr__(self):
        return "<TempVar at %s>" % (id(self),)

class NoVariableToSpill(Exception):
    pass

class Node(object):
    def __init__(self, val, next):
        self.val = val
        self.next = next

    def __repr__(self):
        return '<Node %d %r>' % (self.val, next)

class LinkedList(object):
    def __init__(self, fm, lst=None):
        # assume the list is sorted
        if lst is not None:
            node = None
            for i in range(len(lst) - 1, -1, -1):
                item = lst[i]
                node = Node(item, node)
            self.master_node = node
        else:
            self.master_node = None
        self.fm = fm

    def append(self, size, item):
        key = self.fm.get_loc_index(item)
        if size == 2:
            self._append(key)
            self._append(key + 1)
        else:
            assert size == 1
            self._append(key)

    def _append(self, key):
        if self.master_node is None or self.master_node.val > key:
            self.master_node = Node(key, self.master_node)
        else:
            node = self.master_node
            prev_node = self.master_node
            while node and node.val < key:
                prev_node = node
                node = node.next
            prev_node.next = Node(key, node)

    @specialize.arg(1)
    def foreach(self, function, arg):
        node = self.master_node
        while node is not None:
            function(arg, node.val)
            node = node.next

    def pop(self, size, tp, hint=-1):
        if size == 2:
            return self._pop_two(tp)   # 'hint' ignored for floats on 32-bit
        assert size == 1
        if not self.master_node:
            return None
        node = self.master_node
        #
        if hint >= 0:
            # Look for and remove the Node with the .val matching 'hint'.
            # If not found, fall back to removing the first Node.
            # Note that the loop below ignores the first Node, but
            # even if by chance it is the one with the correct .val,
            # it will be the one we remove at the end anyway.
            prev_node = node
            while prev_node.next:
                if prev_node.next.val == hint:
                    node = prev_node.next
                    prev_node.next = node.next
                    break
                prev_node = prev_node.next
            else:
                self.master_node = node.next
        else:
            self.master_node = node.next
        #
        return self.fm.frame_pos(node.val, tp)

    def _candidate(self, node):
        return (node.val & 1 == 0) and (node.val + 1 == node.next.val)

    def _pop_two(self, tp):
        node = self.master_node
        if node is None or node.next is None:
            return None
        if self._candidate(node):
            self.master_node = node.next.next
            return self.fm.frame_pos(node.val, tp)
        prev_node = node
        node = node.next
        while True:
            if node.next is None:
                return None
            if self._candidate(node):
                # pop two
                prev_node.next = node.next.next
                return self.fm.frame_pos(node.val, tp)
            node = node.next

    def len(self):
        node = self.master_node
        c = 0
        while node:
            node = node.next
            c += 1
        return c

    def __len__(self):
        """ For tests only
        """
        return self.len()

    def __repr__(self):
        if not self.master_node:
            return 'LinkedList(<empty>)'
        node = self.master_node
        l = []
        while node:
            l.append(str(node.val))
            node = node.next
        return 'LinkedList(%s)' % '->'.join(l)

class FrameManager(object):
    """ Manage frame positions

    start_free_depth is the start where we can allocate in whatever order
    we like.
    """
    def __init__(self, start_free_depth=0, freelist=None):
        self.bindings = {}
        self.current_frame_depth = start_free_depth
        self.hint_frame_pos = {}
        self.freelist = LinkedList(self, freelist)

    def get_frame_depth(self):
        return self.current_frame_depth

    def get(self, box):
        return self.bindings.get(box, None)

    def loc(self, box):
        """Return or create the frame location associated with 'box'."""
        # first check if it's already in the frame_manager
        try:
            return self.bindings[box]
        except KeyError:
            pass
        return self.get_new_loc(box)

    def get_new_loc(self, box):
        size = self.frame_size(box.type)
        hint = self.hint_frame_pos.get(box, -1)
        # frame_depth is rounded up to a multiple of 'size', assuming
        # that 'size' is a power of two.  The reason for doing so is to
        # avoid obscure issues in jump.py with stack locations that try
        # to move from position (6,7) to position (7,8).
        newloc = self.freelist.pop(size, box.type, hint)
        if newloc is None:
            #
            index = self.get_frame_depth()
            if index & 1 and size == 2:
                # we can't allocate it at odd position
                self.freelist._append(index)
                newloc = self.frame_pos(index + 1, box.type)
                self.current_frame_depth += 3
                index += 1 # for test
            else:
                newloc = self.frame_pos(index, box.type)
                self.current_frame_depth += size
            #
            if not we_are_translated():    # extra testing
                testindex = self.get_loc_index(newloc)
                assert testindex == index
            #

        self.bindings[box] = newloc
        if not we_are_translated():
            self._check_invariants()
        return newloc

    def bind(self, box, loc):
        pos = self.get_loc_index(loc)
        size = self.frame_size(box.type)
        self.current_frame_depth = max(pos + size, self.current_frame_depth)
        self.bindings[box] = loc

    def finish_binding(self):
        all = [0] * self.get_frame_depth()
        for b, loc in self.bindings.iteritems():
            size = self.frame_size(b.type)
            pos = self.get_loc_index(loc)
            for i in range(pos, pos + size):
                all[i] = 1
        self.freelist = LinkedList(self) # we don't care
        for elem in range(len(all)):
            if not all[elem]:
                self.freelist._append(elem)
        if not we_are_translated():
            self._check_invariants()

    def mark_as_free(self, box):
        try:
            loc = self.bindings[box]
        except KeyError:
            return    # already gone
        del self.bindings[box]
        size = self.frame_size(box.type)
        self.freelist.append(size, loc)
        if not we_are_translated():
            self._check_invariants()

    def _check_invariants(self):
        all = [0] * self.get_frame_depth()
        for b, loc in self.bindings.iteritems():
            size = self.frame_size(b)
            pos = self.get_loc_index(loc)
            for i in range(pos, pos + size):
                assert not all[i]
                all[i] = 1
        node = self.freelist.master_node
        while node is not None:
            assert not all[node.val]
            all[node.val] = 1
            node = node.next

    @staticmethod
    def _gather_gcroots(lst, var):
        lst.append(var)

    # abstract methods that need to be overwritten for specific assemblers

    def frame_pos(loc, type):
        raise NotImplementedError("Purely abstract")

    @staticmethod
    def frame_size(type):
        return 1

    @staticmethod
    def get_loc_index(loc):
        raise NotImplementedError("Purely abstract")

    @staticmethod
    def newloc(pos, size, tp):
        """ Reverse of get_loc_index
        """
        raise NotImplementedError("Purely abstract")

class RegisterManager(object):

    """ Class that keeps track of register allocations
    """
    box_types             = None       # or a list of acceptable types
    all_regs              = []
    no_lower_byte_regs    = []
    save_around_call_regs = []
    frame_reg             = None

    def __init__(self, longevity, frame_manager=None, assembler=None):
        self.free_regs = self.all_regs[:]
        self.free_regs.reverse()
        self.longevity = longevity
        self.temp_boxes = []
        if not we_are_translated():
            self.reg_bindings = OrderedDict()
        else:
            self.reg_bindings = {}
        self.bindings_to_frame_reg = {}
        self.position = -1
        self.frame_manager = frame_manager
        self.assembler = assembler

    def is_still_alive(self, v):
        # Check if 'v' is alive at the current position.
        # Return False if the last usage is strictly before.
        return self.longevity[v][1] >= self.position

    def stays_alive(self, v):
        # Check if 'v' stays alive after the current position.
        # Return False if the last usage is before or at position.
        return self.longevity[v][1] > self.position

    def next_instruction(self, incr=1):
        self.position += incr

    def _check_type(self, v):
        if not we_are_translated() and self.box_types is not None:
            assert isinstance(v, TempVar) or v.type in self.box_types

    def possibly_free_var(self, v):
        """ If v is stored in a register and v is not used beyond the
            current position, then free it.  Must be called at some
            point for all variables that might be in registers.
        """
        self._check_type(v)
        if isinstance(v, Const):
            return
        if v not in self.longevity or self.longevity[v][1] <= self.position:
            if v in self.reg_bindings:
                self.free_regs.append(self.reg_bindings[v])
                del self.reg_bindings[v]
            if self.frame_manager is not None:
                self.frame_manager.mark_as_free(v)

    def possibly_free_vars(self, vars):
        """ Same as 'possibly_free_var', but for all v in vars.
        """
        for v in vars:
            self.possibly_free_var(v)

    def possibly_free_vars_for_op(self, op):
        for i in range(op.numargs()):
            self.possibly_free_var(op.getarg(i))

    def free_temp_vars(self):
        self.possibly_free_vars(self.temp_boxes)
        self.temp_boxes = []

    def _check_invariants(self):
        if not we_are_translated():
            # make sure no duplicates
            assert len(dict.fromkeys(self.reg_bindings.values())) == len(self.reg_bindings)
            rev_regs = dict.fromkeys(self.reg_bindings.values())
            for reg in self.free_regs:
                assert reg not in rev_regs
            assert len(rev_regs) + len(self.free_regs) == len(self.all_regs)
        else:
            assert len(self.reg_bindings) + len(self.free_regs) == len(self.all_regs)
        assert len(self.temp_boxes) == 0
        if self.longevity:
            for v in self.reg_bindings:
                assert self.longevity[v][1] > self.position

    def try_allocate_reg(self, v, selected_reg=None, need_lower_byte=False):
        """ Try to allocate a register, if we have one free.
        need_lower_byte - if True, allocate one that has a lower byte reg
                          (e.g. eax has al)
        selected_reg    - if not None, force a specific register

        returns allocated register or None, if not possible.
        """
        self._check_type(v)
        assert not isinstance(v, Const)
        if selected_reg is not None:
            res = self.reg_bindings.get(v, None)
            if res is not None:
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
        if need_lower_byte:
            loc = self.reg_bindings.get(v, None)
            if loc is not None and loc not in self.no_lower_byte_regs:
                return loc
            for i in range(len(self.free_regs) - 1, -1, -1):
                reg = self.free_regs[i]
                if reg not in self.no_lower_byte_regs:
                    if loc is not None:
                        self.free_regs[i] = loc
                    else:
                        del self.free_regs[i]
                    self.reg_bindings[v] = reg
                    return reg
            return None
        try:
            return self.reg_bindings[v]
        except KeyError:
            if self.free_regs:
                loc = self.free_regs.pop()
                self.reg_bindings[v] = loc
                return loc

    def _spill_var(self, v, forbidden_vars, selected_reg,
                   need_lower_byte=False):
        v_to_spill = self._pick_variable_to_spill(v, forbidden_vars,
                               selected_reg, need_lower_byte=need_lower_byte)
        loc = self.reg_bindings[v_to_spill]
        del self.reg_bindings[v_to_spill]
        if self.frame_manager.get(v_to_spill) is None:
            newloc = self.frame_manager.loc(v_to_spill)
            self.assembler.regalloc_mov(loc, newloc)
        return loc

    def _pick_variable_to_spill(self, v, forbidden_vars, selected_reg=None,
                                need_lower_byte=False):
        """ Slightly less silly algorithm.
        """
        cur_max_age = -1
        candidate = None
        for next in self.reg_bindings:
            reg = self.reg_bindings[next]
            if next in forbidden_vars:
                continue
            if selected_reg is not None:
                if reg is selected_reg:
                    return next
                else:
                    continue
            if need_lower_byte and reg in self.no_lower_byte_regs:
                continue
            max_age = self.longevity[next][1]
            if cur_max_age < max_age:
                cur_max_age = max_age
                candidate = next
        if candidate is None:
            raise NoVariableToSpill
        return candidate

    def force_allocate_reg(self, v, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        """ Forcibly allocate a register for the new variable v.
        It must not be used so far.  If we don't have a free register,
        spill some other variable, according to algorithm described in
        '_pick_variable_to_spill'.

        Will not spill a variable from 'forbidden_vars'.
        """
        self._check_type(v)
        if isinstance(v, TempVar):
            self.longevity[v] = (self.position, self.position)
        loc = self.try_allocate_reg(v, selected_reg,
                                    need_lower_byte=need_lower_byte)
        if loc:
            return loc
        loc = self._spill_var(v, forbidden_vars, selected_reg,
                              need_lower_byte=need_lower_byte)
        prev_loc = self.reg_bindings.get(v, None)
        if prev_loc is not None:
            self.free_regs.append(prev_loc)
        self.reg_bindings[v] = loc
        return loc

    def force_allocate_frame_reg(self, v):
        """ Allocate the new variable v in the frame register."""
        self.bindings_to_frame_reg[v] = None

    def force_spill_var(self, var):
        self._sync_var(var)
        try:
            loc = self.reg_bindings[var]
            del self.reg_bindings[var]
            self.free_regs.append(loc)
        except KeyError:
            pass   # 'var' is already not in a register

    def loc(self, box, must_exist=False):
        """ Return the location of 'box'.
        """
        self._check_type(box)
        if isinstance(box, Const):
            return self.convert_to_imm(box)
        try:
            return self.reg_bindings[box]
        except KeyError:
            if box in self.bindings_to_frame_reg:
                return self.frame_reg
            if must_exist:
                return self.frame_manager.bindings[box]
            return self.frame_manager.loc(box)

    def return_constant(self, v, forbidden_vars=[], selected_reg=None):
        """ Return the location of the constant v.  If 'selected_reg' is
        not None, it will first load its value into this register.
        """
        self._check_type(v)
        assert isinstance(v, Const)
        immloc = self.convert_to_imm(v)
        if selected_reg:
            if selected_reg in self.free_regs:
                self.assembler.regalloc_mov(immloc, selected_reg)
                return selected_reg
            loc = self._spill_var(v, forbidden_vars, selected_reg)
            self.free_regs.append(loc)
            self.assembler.regalloc_mov(immloc, loc)
            return loc
        return immloc

    def make_sure_var_in_reg(self, v, forbidden_vars=[], selected_reg=None,
                             need_lower_byte=False):
        """ Make sure that an already-allocated variable v is in some
        register.  Return the register.  See 'force_allocate_reg' for
        the meaning of the optional arguments.
        """
        self._check_type(v)
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg)
        prev_loc = self.loc(v, must_exist=True)
        if prev_loc is self.frame_reg and selected_reg is None:
            return prev_loc
        loc = self.force_allocate_reg(v, forbidden_vars, selected_reg,
                                      need_lower_byte=need_lower_byte)
        if prev_loc is not loc:
            self.assembler.regalloc_mov(prev_loc, loc)
        return loc

    def _reallocate_from_to(self, from_v, to_v):
        reg = self.reg_bindings[from_v]
        del self.reg_bindings[from_v]
        self.reg_bindings[to_v] = reg

    def _move_variable_away(self, v, prev_loc):
        if self.free_regs:
            loc = self.free_regs.pop()
            self.reg_bindings[v] = loc
            self.assembler.regalloc_mov(prev_loc, loc)
        else:
            loc = self.frame_manager.loc(v)
            self.assembler.regalloc_mov(prev_loc, loc)

    def force_result_in_reg(self, result_v, v, forbidden_vars=[]):
        """ Make sure that result is in the same register as v.
        The variable v is copied away if it's further used.  The meaning
        of 'forbidden_vars' is the same as in 'force_allocate_reg'.
        """
        self._check_type(result_v)
        self._check_type(v)
        if isinstance(v, Const):
            if self.free_regs:
                loc = self.free_regs.pop()
            else:
                loc = self._spill_var(v, forbidden_vars, None)
            self.assembler.regalloc_mov(self.convert_to_imm(v), loc)
            self.reg_bindings[result_v] = loc
            return loc
        if v not in self.reg_bindings:
            prev_loc = self.frame_manager.loc(v)
            loc = self.force_allocate_reg(v, forbidden_vars)
            self.assembler.regalloc_mov(prev_loc, loc)
        assert v in self.reg_bindings
        if self.longevity[v][1] > self.position:
            # we need to find a new place for variable v and
            # store result in the same place
            loc = self.reg_bindings[v]
            del self.reg_bindings[v]
            if self.frame_manager.get(v) is None:
                self._move_variable_away(v, loc)
            self.reg_bindings[result_v] = loc
        else:
            self._reallocate_from_to(v, result_v)
            loc = self.reg_bindings[result_v]
        return loc

    def _sync_var(self, v):
        if not self.frame_manager.get(v):
            reg = self.reg_bindings[v]
            to = self.frame_manager.loc(v)
            self.assembler.regalloc_mov(reg, to)
        # otherwise it's clean

    def _bc_spill(self, v, new_free_regs):
        self._sync_var(v)
        new_free_regs.append(self.reg_bindings.pop(v))

    def before_call(self, force_store=[], save_all_regs=0):
        self.spill_or_move_registers_before_call(self.save_around_call_regs,
                                                 force_store, save_all_regs)

    def spill_or_move_registers_before_call(self, save_sublist,
                                            force_store=[], save_all_regs=0):
        """Spill or move some registers before a call.

        By default, this means: for every register in 'save_sublist',
        if there is a variable there and it survives longer than
        the current operation, then it is spilled/moved somewhere else.

        WARNING: this might do the equivalent of possibly_free_vars()
        on variables dying in the current operation.  It won't
        immediately overwrite registers that used to be occupied by
        these variables, though.  Use this function *after* you finished
        calling self.loc() or self.make_sure_var_in_reg(), i.e. when you
        know the location of all input arguments.  These locations stay
        valid, but only *if they are in self.save_around_call_regs,*
        not if they are callee-saved registers!

        'save_all_regs' can be 0 (default set of registers), 1 (do that
        for all registers), or 2 (default + gc ptrs).

        Overview of what we do (the implementation does it differently,
        for the same result):

        * we first check the set of registers that are free: call it F.

        * possibly_free_vars() is implied for all variables (except
          the ones listed in force_store): if they don't survive past
          the current operation, they are forgotten now.  (Their
          register remain not in F, because they are typically
          arguments to the call, so they should not be overwritten by
          the next step.)

        * then for every variable that needs to be spilled/moved: if
          there is an entry in F that is acceptable, pick it and emit a
          move.  Otherwise, emit a spill.  Start doing this with the
          variables that survive the shortest time, to give them a
          better change to remain in a register---similar algo as
          _pick_variable_to_spill().

        Note: when a register is moved, it often (but not always) means
        we could have been more clever and picked a better register in
        the first place, when we did so earlier.  It is done this way
        anyway, as a local hack in this function, because on x86 CPUs
        such register-register moves are almost free.
        """
        if not we_are_translated():
            # 'save_sublist' is either the whole
            # 'self.save_around_call_regs', or a sublist thereof, and
            # then only those registers are spilled/moved.  But when
            # we move them, we never move them to other registers in
            # 'self.save_around_call_regs', to avoid ping-pong effects
            # where the same value is constantly moved around.
            for reg in save_sublist:
                assert reg in self.save_around_call_regs

        new_free_regs = []
        move_or_spill = []

        for v, reg in self.reg_bindings.items():
            max_age = self.longevity[v][1]
            if v not in force_store and max_age <= self.position:
                # variable dies
                del self.reg_bindings[v]
                new_free_regs.append(reg)
                continue

            if save_all_regs == 1:
                # we need to spill all registers in this mode
                self._bc_spill(v, new_free_regs)
                #
            elif save_all_regs == 2 and v.type == REF:
                # we need to spill all GC ptrs in this mode
                self._bc_spill(v, new_free_regs)
                #
            elif reg not in save_sublist:
                continue  # in a register like ebx/rbx: it is fine where it is
                #
            else:
                # this is a register like eax/rax, which needs either
                # spilling or moving.
                move_or_spill.append((v, max_age))

        if len(move_or_spill) > 0:
            while len(self.free_regs) > 0:
                new_reg = self.free_regs.pop()
                if new_reg in self.save_around_call_regs:
                    new_free_regs.append(new_reg)    # not this register...
                    continue
                # This 'new_reg' is suitable for moving a candidate to.
                # Pick the one with the smallest max_age.  (This
                # is one step of a naive sorting algo, slow in theory,
                # but the list should always be very small so it
                # doesn't matter.)
                best_i = 0
                smallest_max_age = move_or_spill[0][1]
                for i in range(1, len(move_or_spill)):
                    max_age = move_or_spill[i][1]
                    if max_age < smallest_max_age:
                        best_i = i
                        smallest_max_age = max_age
                v, max_age = move_or_spill.pop(best_i)
                # move from 'reg' to 'new_reg'
                reg = self.reg_bindings[v]
                if not we_are_translated():
                    if move_or_spill:
                        assert max_age <= min([_a for _, _a in move_or_spill])
                    assert reg in save_sublist
                    assert reg in self.save_around_call_regs
                    assert new_reg not in self.save_around_call_regs
                self.assembler.regalloc_mov(reg, new_reg)
                self.reg_bindings[v] = new_reg    # change the binding
                new_free_regs.append(reg)
                #
                if len(move_or_spill) == 0:
                    break
            else:
                # no more free registers to move to, spill the rest
                for v, max_age in move_or_spill:
                    self._bc_spill(v, new_free_regs)

        # re-add registers in 'new_free_regs', but in reverse order,
        # so that the last ones (added just above, from
        # save_around_call_regs) are picked last by future '.pop()'
        while len(new_free_regs) > 0:
            self.free_regs.append(new_free_regs.pop())

    def after_call(self, v):
        """ Adjust registers according to the result of the call,
        which is in variable v.
        """
        self._check_type(v)
        r = self.call_result_location(v)
        if not we_are_translated():
            assert r not in self.reg_bindings.values()
        self.reg_bindings[v] = r
        self.free_regs = [fr for fr in self.free_regs if fr is not r]
        return r

    # abstract methods, override

    def convert_to_imm(self, c):
        """ Platform specific - convert a constant to imm
        """
        raise NotImplementedError("Abstract")

    def call_result_location(self, v):
        """ Platform specific - tell where the result of a call will
        be stored by the cpu, according to the variable type
        """
        raise NotImplementedError("Abstract")

    def get_scratch_reg(self, type, forbidden_vars=[], selected_reg=None):
        """ Platform specific - Allocates a temporary register """
        raise NotImplementedError("Abstract")

class BaseRegalloc(object):
    """ Base class on which all the backend regallocs should be based
    """
    def _set_initial_bindings(self, inputargs, looptoken):
        """ Set the bindings at the start of the loop
        """
        locs = []
        base_ofs = self.assembler.cpu.get_baseofs_of_frame_field()
        for box in inputargs:
            assert not isinstance(box, Const)
            loc = self.fm.get_new_loc(box)
            locs.append(loc.value - base_ofs)
        if looptoken.compiled_loop_token is not None:   # <- for tests
            looptoken.compiled_loop_token._ll_initial_locs = locs

    def next_op_can_accept_cc(self, operations, i):
        op = operations[i]
        next_op = operations[i + 1]
        opnum = next_op.getopnum()
        if (opnum != rop.GUARD_TRUE and opnum != rop.GUARD_FALSE
                                    and opnum != rop.COND_CALL):
            return False
        if next_op.getarg(0) is not op:
            return False
        if self.longevity[op][1] > i + 1:
            return False
        if opnum != rop.COND_CALL:
            if op in operations[i + 1].getfailargs():
                return False
        else:
            if op in operations[i + 1].getarglist()[1:]:
                return False
        return True

    def locs_for_call_assembler(self, op):
        descr = op.getdescr()
        assert isinstance(descr, JitCellToken)
        if op.numargs() == 2:
            self.rm._sync_var(op.getarg(1))
            return [self.loc(op.getarg(0)), self.fm.loc(op.getarg(1))]
        else:
            assert op.numargs() == 1
            return [self.loc(op.getarg(0))]


def compute_vars_longevity(inputargs, operations):
    # compute a dictionary that maps variables to index in
    # operations that is a "last-time-seen"

    # returns a pair longevity/useful. Non-useful variables are ones that
    # never appear in the assembler or it does not matter if they appear on
    # stack or in registers. Main example is loop arguments that go
    # only to guard operations or to jump or to finish
    last_used = {}
    last_real_usage = {}
    for i in range(len(operations)-1, -1, -1):
        op = operations[i]
        if op.type != 'v':
            if op not in last_used and rop.has_no_side_effect(op.opnum):
                continue
        opnum = op.getopnum()
        for j in range(op.numargs()):
            arg = op.getarg(j)
            if isinstance(arg, Const):
                continue
            if arg not in last_used:
                last_used[arg] = i
            if opnum != rop.JUMP and opnum != rop.LABEL:
                if arg not in last_real_usage:
                    last_real_usage[arg] = i
        if rop.is_guard(op.opnum):
            for arg in op.getfailargs():
                if arg is None: # hole
                    continue
                assert not isinstance(arg, Const)
                if arg not in last_used:
                    last_used[arg] = i
    #
    longevity = {}
    for i, arg in enumerate(operations):
        if arg.type != 'v' and arg in last_used:
            assert not isinstance(arg, Const)
            assert i < last_used[arg]
            longevity[arg] = (i, last_used[arg])
            del last_used[arg]
    for arg in inputargs:
        assert not isinstance(arg, Const)
        if arg not in last_used:
            longevity[arg] = (-1, -1)
        else:
            longevity[arg] = (0, last_used[arg])
            del last_used[arg]
    assert len(last_used) == 0

    if not we_are_translated():
        produced = {}
        for arg in inputargs:
            produced[arg] = None
        for op in operations:
            for arg in op.getarglist():
                if not isinstance(arg, Const):
                    assert arg in produced
            produced[op] = None
    
    return longevity, last_real_usage

def is_comparison_or_ovf_op(opnum):
    return rop.is_comparison(opnum) or rop.is_ovf(opnum)

def valid_addressing_size(size):
    return size == 1 or size == 2 or size == 4 or size == 8

def get_scale(size):
    assert valid_addressing_size(size)
    if size < 4:
        return size - 1         # 1, 2 => 0, 1
    else:
        return (size >> 2) + 1  # 4, 8 => 2, 3


def not_implemented(msg):
    msg = '[llsupport/regalloc] %s\n' % msg
    if we_are_translated():
        llop.debug_print(lltype.Void, msg)
    raise NotImplementedError(msg)

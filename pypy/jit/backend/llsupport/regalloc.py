
from pypy.jit.metainterp.history import Const, Box
from pypy.rlib.objectmodel import we_are_translated

class TempBox(Box):
    def __init__(self):
        pass

    def __repr__(self):
        return "<TempVar at %s>" % (id(self),)

class NoVariableToSpill(Exception):
    pass

class FrameManager(object):
    """ Manage frame positions
    """
    def __init__(self):
        self.frame_bindings = {}
        self.frame_depth    = 0

    def get(self, box):
        return self.frame_bindings.get(box, None)

    def loc(self, box, size):
        res = self.get(box)
        if res is not None:
            return res
        newloc = self.frame_pos(self.frame_depth, size)
        self.frame_bindings[box] = newloc
        self.frame_depth += size
        return newloc

    # abstract methods that need to be overwritten for specific assemblers
    @staticmethod
    def frame_pos(loc, size):
        raise NotImplementedError("Purely abstract")

class RegisterManager(object):
    """ Class that keeps track of register allocations
    """
    box_types             = None       # or a list of acceptable types
    all_regs              = []
    no_lower_byte_regs    = []
    save_around_call_regs = []
    reg_width             = 1 # in terms of stack space eaten
    
    def __init__(self, longevity, frame_manager=None, assembler=None):
        self.free_regs = self.all_regs[:]
        self.longevity = longevity
        self.reg_bindings = {}
        self.position = -1
        self.frame_manager = frame_manager
        self.assembler = assembler

    def stays_alive(self, v):
        return self.longevity[v][1] > self.position

    def next_instruction(self, incr=1):
        self.position += incr

    def _check_type(self, v):
        if not we_are_translated() and self.box_types is not None:
            assert isinstance(v, TempBox) or v.type in self.box_types

    def possibly_free_var(self, v):
        """ If v is stored in a register and v is not used beyond the
            current position, then free it.  Must be called at some
            point for all variables that might be in registers.
        """
        self._check_type(v)
        if isinstance(v, Const) or v not in self.reg_bindings:
            return
        if v not in self.longevity or self.longevity[v][1] <= self.position:
            self.free_regs.append(self.reg_bindings[v])
            del self.reg_bindings[v]

    def possibly_free_vars(self, vars):
        """ Same as 'possibly_free_var', but for all v in vars.
        """
        for v in vars:
            self.possibly_free_var(v)

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
            for i in range(len(self.free_regs)):
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
            newloc = self.frame_manager.loc(v_to_spill, self.reg_width)
            self.assembler.regalloc_mov(loc, newloc)
        return loc

    def _pick_variable_to_spill(self, v, forbidden_vars, selected_reg=None,
                                need_lower_byte=False):
        """ Silly algorithm.
        """
        candidates = []
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
            return next
        raise NoVariableToSpill

    def force_allocate_reg(self, v, forbidden_vars=[], selected_reg=None,
                           need_lower_byte=False):
        """ Forcibly allocate a register for the new variable v.
        It must not be used so far.  If we don't have a free register,
        spill some other variable, according to algorithm described in
        '_pick_variable_to_spill'.

        Will not spill a variable from 'forbidden_vars'.
        """
        self._check_type(v)
        if isinstance(v, TempBox):
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

    def loc(self, box):
        """ Return the location of 'box'.
        """
        self._check_type(box)
        if isinstance(box, Const):
            return self.convert_to_imm(box)
        try:
            return self.reg_bindings[box]
        except KeyError:
            return self.frame_manager.loc(box, self.reg_width)

    def return_constant(self, v, forbidden_vars=[], selected_reg=None,
                        imm_fine=True):
        """ Return the location of the constant v.  If 'imm_fine' is False,
        or if 'selected_reg' is not None, it will first load its value into
        a register.  See 'force_allocate_reg' for the meaning of 'selected_reg'
        and 'forbidden_vars'.
        """
        self._check_type(v)
        assert isinstance(v, Const)
        if selected_reg or not imm_fine:
            # this means we cannot have it in IMM, eh
            if selected_reg in self.free_regs:
                self.assembler.regalloc_mov(self.convert_to_imm(v), selected_reg)
                return selected_reg
            if selected_reg is None and self.free_regs:
                loc = self.free_regs[-1]
                self.assembler.regalloc_mov(self.convert_to_imm(v), loc)
                return loc
            loc = self._spill_var(v, forbidden_vars, selected_reg)
            self.free_regs.append(loc)
            self.assembler.regalloc_mov(self.convert_to_imm(v), loc)
            return loc
        return self.convert_to_imm(v)

    def make_sure_var_in_reg(self, v, forbidden_vars=[], selected_reg=None,
                             imm_fine=True, need_lower_byte=False):
        """ Make sure that an already-allocated variable v is in some
        register.  Return the register.  See 'return_constant' and
        'force_allocate_reg' for the meaning of the optional arguments.
        """
        self._check_type(v)
        if isinstance(v, Const):
            return self.return_constant(v, forbidden_vars, selected_reg,
                                        imm_fine)
        
        prev_loc = self.loc(v)
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
        reg = None
        if self.free_regs:
            loc = self.free_regs.pop()
            self.reg_bindings[v] = loc
            self.assembler.regalloc_mov(prev_loc, loc)
        else:
            loc = self.frame_manager.loc(v, self.reg_width)
            self.assembler.regalloc_mov(prev_loc, loc)

    def force_result_in_reg(self, result_v, v, forbidden_vars=[]):
        """ Make sure that result is in the same register as v.
        The variable v is copied away if it's further used.  The meaning
        of 'forbidden_vars' is the same as in 'force_allocate_reg'.
        """
        self._check_type(result_v)
        self._check_type(v)
        if isinstance(v, Const):
            loc = self.make_sure_var_in_reg(v, forbidden_vars,
                                            imm_fine=False)
            # note that calling make_sure_var_in_reg with imm_fine=False
            # will not allocate place in reg_bindings, we need to do it
            # on our own
            self.reg_bindings[result_v] = loc
            self.free_regs = [reg for reg in self.free_regs if reg is not loc]
            return loc
        if v not in self.reg_bindings:
            prev_loc = self.frame_manager.loc(v, self.reg_width)
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
            to = self.frame_manager.loc(v, self.reg_width)
            self.assembler.regalloc_mov(reg, to)
        # otherwise it's clean

    def before_call(self, force_store=[], save_all_regs=False):
        """ Spill registers before a call, as described by
        'self.save_around_call_regs'.  Registers are not spilled if
        they don't survive past the current operation, unless they
        are listed in 'force_store'.
        """
        for v, reg in self.reg_bindings.items():
            if v not in force_store and self.longevity[v][1] <= self.position:
                # variable dies
                del self.reg_bindings[v]
                self.free_regs.append(reg)
                continue
            if not save_all_regs and reg not in self.save_around_call_regs:
                # we don't have to
                continue
            self._sync_var(v)
            del self.reg_bindings[v]
            self.free_regs.append(reg)

    def after_call(self, v):
        """ Adjust registers according to the result of the call,
        which is in variable v.
        """
        self._check_type(v)
        r = self.call_result_location(v)
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

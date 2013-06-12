from rpython.rlib import debug
from prolog.interpreter.term import BindingVar, AttVar

from rpython.rlib import jit

INIT_TRAIL_VAR = []
INIT_TRAIL_BINDING = []

UNROLL_SIZE = 6

class Heap(object):
    def __init__(self, prev=None):
        self.trail_var = INIT_TRAIL_VAR
        debug.make_sure_not_resized(self.trail_var)
        self.trail_binding = INIT_TRAIL_BINDING
        debug.make_sure_not_resized(self.trail_binding)
        self.i = 0
        self.trail_attrs = None
        self.prev = prev
        self.discarded = False
        self.hook = None

    # _____________________________________________________
    # interface that term.py uses
    def _find_not_discarded(self):
        while self is not None and self.discarded:
            self = self.prev
        return self

    def add_trail_atts(self, attvar, attr_name):
        if self._is_created_in_self(attvar):
            return
        value, index = attvar.get_attribute(attr_name)
        self._add_entry_trail_attrs(attvar, index, value)

    def trail_new_attr(self, attvar, index, value):
        if self._is_created_in_self(attvar):
            return
        self._add_entry_trail_attrs(attvar, index, value)

    def _add_entry_trail_attrs(self, attvar, index, value):
        entry = (attvar, index, value)
        if self.trail_attrs is None:
            self.trail_attrs = [entry]
        else:
            self.trail_attrs.append(entry)

    def add_trail(self, var):
        """ Remember the current state of a variable to be able to backtrack it
        to that state. Usually called just before a variable changes. """
        # if the variable doesn't exist before the last choice point, don't
        # trail it (variable shunting)
        if self._is_created_in_self(var):
            return
        i = self.i
        if i >= len(self.trail_var):
            assert i == len(self.trail_var)
            self._double_size()
        self.trail_var[i] = var
        self.trail_binding[i] = var.binding
        self.i = i + 1

    def _is_created_in_self(self, var):
        created_in = var.created_after_choice_point
        if self is created_in: # fast path
            return True
        if created_in is not None and created_in.discarded:
            # unroll _find_not_discarded once for better jittability
            created_in = created_in.prev
            if created_in is not None and created_in.discarded:
                created_in = created_in._find_not_discarded()
            var.created_after_choice_point = created_in
        return self is created_in

    def _double_size(self):
        l = len(self.trail_var)
        if l == 0:
            self.trail_var = [None, None]
            self.trail_binding = [None, None]
        elif l == 1:
            assert 0, "cannot happen"
        else:
            self.trail_var = self.trail_var + [None] * l
            self.trail_binding = self.trail_binding + [None] * l

    def newvar(self):
        """ Make a new variable. Should return a Var instance, possibly with
        interesting attributes set that e.g. add_trail can inspect."""
        result = BindingVar()
        result.created_after_choice_point = self
        return result

    def new_attvar(self):
        result = AttVar()
        result.created_after_choice_point = self
        return result

    def newvar_in_term(self, parent, index):
        from prolog.interpreter.term import var_in_term_classes
        return self.newvar() # disabled for now
        result = var_in_term_classes[index](parent)
        result.created_after_choice_point = self
        return result

    # _____________________________________________________

    def branch(self):
        """ Branch of a heap for a choice point. The return value is the new
        heap that should be used from now on, self is the heap that can be
        backtracked to."""
        res = Heap(self)
        return res

    @jit.unroll_safe
    def revert_upto(self, heap, discard_choicepoint=False):
        """ Revert to the heap corresponding to a choice point. The return
        value is the new heap that should be used."""
        previous = self
        while self is not heap:
            if self is None:
                break
            self._revert()
            previous = self
            self = self.prev
        if discard_choicepoint:
            return heap
        return previous

    @jit.look_inside_iff(lambda self: self.i < UNROLL_SIZE)
    def _revert(self):
        i = jit.promote(self.i) - 1
        while i >= 0:
            v = self.trail_var[i]
            assert v is not None
            v.binding = self.trail_binding[i]
            self.trail_var[i] = None
            self.trail_binding[i] = None
            i -= 1
        self.i = 0

        if self.trail_attrs is not None:
            for attvar, index, value in self.trail_attrs:
                attvar.reset_field(index, value)

        self.trail_attrs = None
        self.hook = None

    def discard(self, current_heap):
        """ Remove a heap that is no longer needed (usually due to a cut) from
        a chain of frames. """
        self.discarded = True
        if current_heap.prev is self:
            current_heap._discard_try_remove_current_trail(self)
            if current_heap.trail_attrs is not None:
                current_heap._discard_try_remove_current_trail_attvars(self)

            # move the variable bindings from the discarded heap to the current
            # heap
            self._discard_move_bindings_to_current(current_heap)

            if self.trail_attrs is not None:
                if current_heap.trail_attrs is not None:
                    current_heap.trail_attrs.extend(self.trail_attrs)
                else:
                    current_heap.trail_attrs = self.trail_attrs

            current_heap.prev = self.prev
            self.trail_var = None
            self.trail_binding = None
            self.trail_attrs = None
            self.i = -1
            self.prev = current_heap
        else:
            return self
        return current_heap


    @jit.look_inside_iff(lambda self, discarded_heap:
            self.i < UNROLL_SIZE)
    def _discard_try_remove_current_trail(self, discarded_heap):
        targetpos = 0
        # check whether variables in the current heap no longer need to be
        # traced, because they originate in the discarded heap
        for i in range(jit.promote(self.i)):
            var = self.trail_var[i]
            binding = self.trail_binding[i]
            if var.created_after_choice_point is discarded_heap:
                var.created_after_choice_point = discarded_heap.prev
                self.trail_var[i] = None
                self.trail_binding[i] = None
            else:
                self.trail_var[targetpos] = var
                self.trail_binding[targetpos] = binding
                targetpos += 1
        self.i = targetpos

    def _discard_try_remove_current_trail_attvars(self, discarded_heap):
        trail_attrs = []
        targetpos = 0
        for var, attr, value in self.trail_attrs:
            if var.created_after_choice_point is discarded_heap:
                var.created_after_choice_point = discarded_heap.prev
            else:
                trail_attrs[targetpos] = (var, attr, value)
        if not trail_attrs:
            trail_attrs = None
        self.trail_attrs = trail_attrs


    @jit.look_inside_iff(lambda self, current_heap:
            self.i < UNROLL_SIZE)
    def _discard_move_bindings_to_current(self, current_heap):
        for i in range(jit.promote(self.i)):
            var = self.trail_var[i]
            currbinding = var.binding
            binding = self.trail_binding[i]

            var.binding = binding
            current_heap.add_trail(var)
            var.binding = currbinding

    def __repr__(self):
        return "<Heap %r trailed vars>" % (self.i, )

    def _dot(self, seen):
        if self in seen:
            return
        seen.add(self)
        yield '%s [label="%r", shape=octagon]' % (id(self), self)
        if self.prev:
            yield "%s -> %s [label=prev]" % (id(self), id(self.prev))
            for line in self.prev._dot(seen):
                yield line

    # methods to for the hook chain

    def add_hook(self, attvar):
        self.hook = HookCell(attvar, self.hook)


class HookCell(object):
    def __init__(self, attvar, next=None):
        self.attvar = attvar
        self.next = next

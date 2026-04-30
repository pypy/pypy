from pypy.conftest import option
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.pyframe import mark_stacks, MarkStacks
from pypy.interpreter.astcompiler.assemble import _encode_varint
from pypy.tool import stdlib_opcode as ops


class FakeCode(object):
    def __init__(self, co_code, co_exceptiontable=''):
        self.co_code = co_code
        self.co_exceptiontable = co_exceptiontable


def make_bytecode(*instrs):
    return ''.join(chr(op) + chr(arg) for op, arg in instrs)


def make_exceptiontable(*entries):
    result = []
    for start, length, target, depth, lasti in entries:
        _encode_varint(result, start)
        _encode_varint(result, length)
        _encode_varint(result, target)
        _encode_varint(result, (depth << 1) | lasti)
    return ''.join(result)


_ms = MarkStacks(0)   # instance used for constants and push() in helpers below

def stack(*kinds):
    """Build expected stack state, bottom-to-top order."""
    s = _ms.EMPTY
    for kind in kinds:
        s = _ms.push(s, kind)
    return s


# MarkStacks unit tests

def test_markstacks_constants():
    assert _ms.UNINITIALIZED == -2
    assert _ms.OVERFLOWED    == -1
    assert _ms.EMPTY         == 0
    assert _ms.BITS          == 3
    assert _ms.MASK          == 7

def test_markstacks_push_empty():
    assert _ms.push(_ms.EMPTY, _ms.OBJECT) == _ms.OBJECT

def test_markstacks_push_stacks():
    s = _ms.push(_ms.EMPTY, _ms.ITERATOR)
    s = _ms.push(s, _ms.OBJECT)
    # TOS is OBJECT (lowest bits), then ITERATOR
    assert s & _ms.MASK == _ms.OBJECT
    assert (s >> _ms.BITS) & _ms.MASK == _ms.ITERATOR

def test_markstacks_push_overflow():
    s = _ms.OVERFLOWED
    assert _ms.push(s, _ms.OBJECT) == _ms.OVERFLOWED
    s = _ms.UNINITIALIZED
    assert _ms.push(s, _ms.OBJECT) == _ms.OVERFLOWED

def test_markstacks_set_initializes():
    ms = MarkStacks(3)
    assert ms[1] == ms.UNINITIALIZED
    changed = ms.set(1, ms.EMPTY, False)
    assert changed
    assert ms[1] == ms.EMPTY

def test_markstacks_set_no_overwrite():
    ms = MarkStacks(3)
    ms.set(1, ms.OBJECT, False)
    changed = ms.set(1, ms.ITERATOR, False)
    assert not changed
    assert ms[1] == ms.OBJECT   # original value preserved

def test_markstacks_set_preserves_changed():
    ms = MarkStacks(3)
    ms.set(1, ms.OBJECT, False)
    # slot already set; changed=True should be passed through
    changed = ms.set(1, ms.ITERATOR, True)
    assert changed

def test_markstacks_len():
    ms = MarkStacks(5)
    assert len(ms) == 6   # n + 1 slots

def test_markstacks_compatible_empty_to_empty():
    assert _ms.compatible(_ms.EMPTY, _ms.EMPTY)

def test_markstacks_compatible_object_to_object():
    s = stack(_ms.OBJECT)
    assert _ms.compatible(s, s)

def test_markstacks_compatible_deeper_to_shallower():
    deep = stack(_ms.OBJECT, _ms.OBJECT)
    shallow = stack(_ms.OBJECT)
    assert _ms.compatible(deep, shallow)

def test_markstacks_compatible_shallower_to_deeper():
    deep = stack(_ms.OBJECT, _ms.OBJECT)
    shallow = stack(_ms.OBJECT)
    assert not _ms.compatible(shallow, deep)

def test_markstacks_compatible_object_accepts_iterator():
    # OBJECT slot accepts any non-empty kind (iterator, except, etc.)
    it = stack(_ms.ITERATOR)
    obj = stack(_ms.OBJECT)
    assert _ms.compatible(it, obj)

def test_markstacks_compatible_except_not_interchangeable():
    exc = stack(_ms.EXCEPT)
    it  = stack(_ms.ITERATOR)
    assert not _ms.compatible(exc, it)
    assert not _ms.compatible(it, exc)

def test_markstacks_compatible_negative():
    assert not _ms.compatible(_ms.UNINITIALIZED, _ms.EMPTY)
    assert not _ms.compatible(_ms.EMPTY, _ms.OVERFLOWED)

def test_markstacks_explain_incompatible_overflowed():
    assert "deep" in _ms.explain_incompatible(_ms.OVERFLOWED)

def test_markstacks_explain_incompatible_uninitialized():
    assert "unreachable" in _ms.explain_incompatible(_ms.UNINITIALIZED)

def test_markstacks_explain_incompatible_empty():
    assert "unreachable" in _ms.explain_incompatible(_ms.EMPTY)

def test_markstacks_explain_incompatible_except():
    assert "except" in _ms.explain_incompatible(stack(_ms.EXCEPT))

def test_markstacks_explain_incompatible_iterator():
    assert "for" in _ms.explain_incompatible(stack(_ms.ITERATOR))

def test_markstacks_pop_to_level():
    s = stack(_ms.OBJECT, _ms.ITERATOR, _ms.EXCEPT)
    assert _ms.pop_to_level(s, 1) == stack(_ms.OBJECT)
    assert _ms.pop_to_level(s, 0) == _ms.EMPTY


# mark_stacks unit tests

def test_mark_stacks_linear():
    # LOAD_CONST pushes an object; RETURN_VALUE is terminal.
    code = FakeCode(make_bytecode(
        (ops.LOAD_CONST, 0),
        (ops.RETURN_VALUE, 0),
    ))
    stacks = mark_stacks(code)
    assert stacks[0] == stacks.EMPTY
    assert stacks[1] == stack(stacks.OBJECT)
    assert stacks[2] == stacks.UNINITIALIZED   # terminal, no fall-through

def test_mark_stacks_jump_forward_unreachable():
    # JUMP_FORWARD skips the NOP; the NOP's slot stays uninitialized.
    code = FakeCode(make_bytecode(
        (ops.JUMP_FORWARD, 1),  # jump to instr 0+1+1 = 2
        (ops.NOP, 0),           # unreachable
        (ops.LOAD_CONST, 0),
        (ops.RETURN_VALUE, 0),
    ))
    stacks = mark_stacks(code)
    assert stacks[0] == stacks.EMPTY
    assert stacks[1] == stacks.UNINITIALIZED   # unreachable NOP
    assert stacks[2] == stacks.EMPTY           # jump target
    assert stacks[3] == stack(stacks.OBJECT)
    assert stacks[4] == stacks.UNINITIALIZED   # terminal

def test_mark_stacks_conditional_branch():
    # POP_JUMP_IF_TRUE pops the condition and branches to index 4 or falls
    # to index 2; both paths are reachable with an empty stack.
    code = FakeCode(make_bytecode(
        (ops.LOAD_CONST, 0),        # 0: push object
        (ops.POP_JUMP_IF_TRUE, 4),  # 1: pop, branch to 4 or fall to 2
        (ops.LOAD_CONST, 0),        # 2: false path
        (ops.RETURN_VALUE, 0),      # 3
        (ops.LOAD_CONST, 0),        # 4: true path
        (ops.RETURN_VALUE, 0),      # 5
    ))
    stacks = mark_stacks(code)
    assert stacks[0] == stacks.EMPTY
    assert stacks[1] == stack(stacks.OBJECT)
    assert stacks[2] == stacks.EMPTY           # fall-through, condition popped
    assert stacks[3] == stack(stacks.OBJECT)
    assert stacks[4] == stacks.EMPTY           # branch target, condition popped
    assert stacks[5] == stack(stacks.OBJECT)
    assert stacks[6] == stacks.UNINITIALIZED

def test_mark_stacks_for_iter_loop():
    # GET_ITER converts an object to an iterator; FOR_ITER pushes the loop
    # variable on the fall-through edge and pops the iterator on the
    # exhausted-jump edge.
    code = FakeCode(make_bytecode(
        (ops.LOAD_CONST, 0),    # 0: iterable
        (ops.GET_ITER, 0),      # 1: -> iterator
        (ops.FOR_ITER, 2),      # 2: loop var on fall, jump to 2+2+1=5 when done
        (ops.POP_TOP, 0),       # 3: discard loop var
        (ops.JUMP_ABSOLUTE, 2), # 4: back to FOR_ITER
        (ops.RETURN_VALUE, 0),  # 5: after loop
    ))
    stacks = mark_stacks(code)
    assert stacks[0] == stacks.EMPTY
    assert stacks[1] == stack(stacks.OBJECT)
    assert stacks[2] == stack(stacks.ITERATOR)
    assert stacks[3] == stack(stacks.ITERATOR, stacks.OBJECT)  # loop var on top
    assert stacks[4] == stack(stacks.ITERATOR)                 # after discarding loop var
    assert stacks[5] == stacks.EMPTY                           # iterator popped on exhaustion
    assert stacks[6] == stacks.UNINITIALIZED

def test_mark_stacks_push_exc_info_pop_except():
    # PUSH_EXC_INFO: pops exc (Object), pushes prev_exc (Except) + exc (Object).
    # POP_EXCEPT: pops the prev_exc (Except slot).
    code = FakeCode(make_bytecode(
        (ops.LOAD_CONST, 0),    # 0: exc object
        (ops.PUSH_EXC_INFO, 0), # 1
        (ops.POP_EXCEPT, 0),    # 2
        (ops.RETURN_VALUE, 0),  # 3
    ))
    stacks = mark_stacks(code)
    assert stacks[0] == stacks.EMPTY
    assert stacks[1] == stack(stacks.OBJECT)
    assert stacks[2] == stack(stacks.EXCEPT, stacks.OBJECT)
    assert stacks[3] == stack(stacks.EXCEPT)

def test_mark_stacks_exceptiontable_no_lasti():
    # Exception table entry with lasti=False seeds the handler with [EXCEPT].
    code = FakeCode(
        make_bytecode(
            (ops.LOAD_CONST, 0),    # 0: try body
            (ops.RETURN_VALUE, 0),  # 1: terminal
            (ops.PUSH_EXC_INFO, 0), # 2: handler entry point
            (ops.RETURN_VALUE, 0),  # 3
        ),
        make_exceptiontable((0, 1, 2, 0, 0)),  # start=0, len=1, target=2, depth=0, lasti=0
    )
    stacks = mark_stacks(code)
    assert stacks[2] == stack(stacks.EXCEPT)
    # PUSH_EXC_INFO at 2 pops EXCEPT, pushes EXCEPT + OBJECT
    assert stacks[3] == stack(stacks.EXCEPT, stacks.OBJECT)

def test_mark_stacks_exceptiontable_lasti():
    # Exception table entry with lasti=True seeds the handler with [LASTI, EXCEPT].
    code = FakeCode(
        make_bytecode(
            (ops.LOAD_CONST, 0),    # 0: try body
            (ops.RETURN_VALUE, 0),  # 1: terminal
            (ops.PUSH_EXC_INFO, 0), # 2: handler entry point
            (ops.RETURN_VALUE, 0),  # 3
        ),
        make_exceptiontable((0, 1, 2, 0, 1)),  # start=0, len=1, target=2, depth=0, lasti=1
    )
    stacks = mark_stacks(code)
    assert stacks[2] == stack(stacks.LASTI, stacks.EXCEPT)
    # PUSH_EXC_INFO at 2: pops EXCEPT (TOS), pushes EXCEPT + OBJECT
    assert stacks[3] == stack(stacks.LASTI, stacks.EXCEPT, stacks.OBJECT)

def check_no_w_locals(space, w_frame):
    return space.wrap(w_frame.getorcreatedebug().w_locals is None)

class AppTestPyFrame:

    def setup_class(cls):
        space = cls.space
        if not option.runappdirect:
            w_call_further = cls.space.appexec([], """():
                def call_further(f):
                    return f()
                return call_further
            """)
            assert not w_call_further.code.hidden_applevel
            w_call_further.code.hidden_applevel = True       # hack
            cls.w_call_further = w_call_further

            cls.w_check_no_w_locals = space.wrap(interp2app(check_no_w_locals))

    # test for the presence of the attributes, not functionality

    def test_set_lineno(self):
        import sys
        class JumpTracer:
            def __init__(self, function):
                self.function = function
                self.jumpFrom = function.jump[0]
                self.jumpTo = function.jump[1]
                self.done = False

            def trace(self, frame, event, arg):
                if not self.done and frame.f_code == self.function.__code__:
                    firstLine = frame.f_code.co_firstlineno
                    if event == 'line' and frame.f_lineno == firstLine + self.jumpFrom:
                        # Cope with non-integer self.jumpTo (because of
                        # no_jump_to_non_integers below).
                        try:
                            frame.f_lineno = firstLine + self.jumpTo
                        except TypeError:
                            frame.f_lineno = self.jumpTo
                        self.done = True
                return self.trace

        def run_test(func):
            tracer = JumpTracer(func)
            sys.settrace(tracer.trace)
            output = []
            func(output)
            sys.settrace(None)
            assert func.output == output

        # copied from cpython test suite
        def jump_out_of_block_forwards(output):
            for i in 1, 2:
                output.append(2)
                for j in [3]:  # Also tests jumping over a block
                    output.append(4)
            output.append(5)

        jump_out_of_block_forwards.jump = (3, 5)
        jump_out_of_block_forwards.output = [2, 5]
        run_test(jump_out_of_block_forwards)

        def jump_out_of_block_backwards(output):
            output.append(1)
            for i in [1]:
                output.append(3)
                for j in [2]:  # Also tests jumping over a block
                    output.append(5)
                output.append(6)
            output.append(7)

        jump_out_of_block_backwards.jump = (6, 1)
        jump_out_of_block_backwards.output = [1, 3, 5, 1, 3, 5, 6, 7]
        run_test(jump_out_of_block_backwards)


        def jump_to_codeless_line(output):
            output.append(1)
            # Jumping to this line should skip to the next one.
            output.append(3)
        jump_to_codeless_line.jump = (1, 2)
        jump_to_codeless_line.output = [3]
        run_test(jump_to_codeless_line)

        def jump_in_nested_finally(output):
            try:
                output.append(2)
            finally:
                output.append(4)
                try:
                    output.append(6)
                finally:
                    output.append(8)
                output.append(9)
        jump_in_nested_finally.jump = (4, 9)
        jump_in_nested_finally.output = [2, 9]
        run_test(jump_in_nested_finally)


    def test_f_back_hidden(self):
        if not hasattr(self, 'call_further'):
            skip("not for runappdirect testing")
        import sys
        def f():
            return (sys._getframe(0),
                    sys._getframe(1),
                    sys._getframe(0).f_back)
        def main():
            return self.call_further(f)
        f0, f1, f1bis = main()
        assert f0.f_code.co_name == 'f'
        assert f1.f_code.co_name == 'main'
        assert f1bis is f1
        assert f0.f_back is f1

    def test_fast2locals_called_lazily(self):
        import sys
        class FrameHolder:
            pass
        fh = FrameHolder()
        def trace(frame, what, arg):
            # trivial trace function, does not access f_locals
            fh.frame = frame
            return trace
        def f(x):
            x += 1
            return x
        sys.settrace(trace)
        res = f(1)
        sys.settrace(None)
        assert res == 2
        if hasattr(self, "check_no_w_locals"): # not appdirect
            assert self.check_no_w_locals(fh.frame)

    def test_del_cell_locals_bug(self):
        """
        def f():
            x = object()

            def foo():
                print(x)

            locals()
            del x
            assert "x" not in locals()
        f()
        """

    def test_repr(self):
        import sys
        def a_name(a, b, c):
            a + b + c
            return sys._getframe()
        frame = a_name(5, 6, 4)
        r = repr(frame)
        assert "a_name" in r

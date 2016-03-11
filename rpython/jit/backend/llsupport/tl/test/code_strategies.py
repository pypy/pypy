from hypothesis import strategies as st
from hypothesis.control import assume
from hypothesis.strategies import composite
from rpython.jit.backend.llsupport.tl import code, interp, stack
from hypothesis.searchstrategy.collections import TupleStrategy, ListStrategy
import hypothesis.internal.conjecture.utils as cu

def get_strategy_for(typ):
    if typ == code.INT_TYP:
        return st.integers(min_value=-2**31, max_value=2**31-1)
    elif typ == code.IDX_TYP:
        return st.integers(min_value=-2**31, max_value=2**31-1)
    elif typ == code.SHORT_TYP:
        return st.integers(min_value=-2**15, max_value=2**15-1)
    elif typ == code.BYTE_TYP:
        return st.integers(min_value=-2**7, max_value=2**7-1)
    elif typ == code.COND_TYP:
        return st.integers(min_value=0, max_value=4)
    elif typ == code.STR_TYP:
        return st.text().filter(lambda x: x is not None)
    elif typ == code.LIST_TYP:
        # TODO recursive
        result = st.lists(elements=st.one_of(get_strategy_for('i')))
        return result.filter(lambda x: x is not None)
    else:
        raise NotImplementedError("type: " + str(typ))

STD_SPACE = interp.Space()

def stack_entry(types=code.all_types):
    return st.one_of(*[get_strategy_for(t) for t in types])

def runtime_stack(min_size=0, average_size=5, max_size=4096, types=code.all_types):
    if max_size == 0:
        return st.just(stack.Stack(0))
    stack_entries = st.lists(stack_entry(all_types), min_size=min_size,
                             average_size=average_size,
                             max_size=max_size)
    return stack_entries.map(lambda elems: \
                                stack.Stack.from_items(STD_SPACE, elems))

def get_byte_code_class(num):
    return code.BC_NUM_TO_CLASS[num]

def find_next(stack, type, off=0):
    i = off
    while i < stack.size():
        if stack.peek(i).is_of_type(type):
            break
        i += 1
    else:
        return None
    return stack.peek(i)

class BasicBlockStrategy(ListStrategy):
    """ Generates a list of values, but does not throw away elements.
        See XXX """

    def do_draw(self, data):
        if self.max_size == self.min_size:
            return [
                data.draw(self.element_strategy)
                for _ in range(self.min_size)
            ]

        stopping_value = 1 - 1.0 / (1 + self.average_length)
        result = []
        while True:
            data.start_example()
            more = cu.biased_coin(data, stopping_value)
            value = data.draw(self.element_strategy)
            data.stop_example()
            if not more:
                if len(result) < self.min_size:
                    # XXX if not appended the resulting list will have
                    # a bigger stack but a missing op code
                    result.append(value)
                    continue
                else:
                    break
            result.append(value)
        if self.max_size < float('inf'):
            result = result[:self.max_size]
        return result

    def __repr__(self):
        return (
            'BasicBlockStrategy(%r, min_size=%r, average_size=%r, max_size=%r)'
        ) % (
            self.element_strategy, self.min_size, self.average_length,
            self.max_size
        )

@st.defines_strategy
def basic_block(strategy, min_size=1, average_size=8, max_size=128):
    return BasicBlockStrategy([strategy], min_size=min_size,
                              average_length=average_size,
                              max_size=max_size)

@st.defines_strategy
def bytecode_class(stack):
    # get a byte code class, only allow what is valid for the run_stack
    return st.sampled_from(code.BC_CLASSES).filter(lambda clazz: clazz.filter_bytecode(stack))


@composite
def bytecode(draw, max_stack_size=4096):
    # get a stack that is the same for one test run
    run_stack = draw(st.shared(st.just(stack.Stack(0)), 'stack2'))

    # get a byte code class, only allow what is valid for the run_stack
    clazz = draw(st.sampled_from(code.BC_CLASSES).filter(lambda clazz: clazz.filter_bytecode(run_stack)))

    # create an instance of the chosen class
    pt = getattr(clazz.__init__, '_param_types', [])
    args = [draw(get_strategy_for(t)) for t in pt]
    inst = clazz(*args)

    # propagate the changes to the stack
    bytecode, consts = code.Context().transform([inst])
    interp.dispatch_once(STD_SPACE, 0, bytecode, consts, run_stack)

    return inst


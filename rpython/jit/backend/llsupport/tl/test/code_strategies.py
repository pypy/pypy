from hypothesis import strategies as st
from hypothesis.control import assume
from hypothesis.strategies import composite
from rpython.jit.backend.llsupport.tl import code, interp, stack
from rpython.jit.backend.llsupport.tl.stack import Stack
from hypothesis.searchstrategy.collections import TupleStrategy, ListStrategy
from hypothesis.searchstrategy.strategies import SearchStrategy, one_of_strategies
import hypothesis.internal.conjecture.utils as cu
from collections import namedtuple

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
        return st.just(Stack(0))
    stack_entries = st.lists(stack_entry(all_types), min_size=min_size,
                             average_size=average_size,
                             max_size=max_size)
    return stack_entries.map(lambda elems: \
                                Stack.from_items(STD_SPACE, elems))

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
    assert max_size >= 1
    if average_size < max_size:
        average_size = max_size//2
    return BasicBlockStrategy([strategy], min_size=min_size,
                              average_length=average_size,
                              max_size=int(max_size))

@st.defines_strategy
def bytecode_class(stack):
    # get a byte code class, only allow what is valid for the run_stack
    clazzes = filter(lambda clazz: clazz.filter_bytecode(stack), code.BC_CLASSES)
    return st.sampled_from(clazzes)


@composite
def bytecode(draw, run_stack=None):
    # get a stack that is the same for one test run
    if run_stack is None:
        run_stack = draw(st.shared(st.just(Stack(0)), 'stack'))

    # get a byte code class, only allow what is valid for the run_stack
    clazzes = filter(lambda clazz: clazz.filter_bytecode(run_stack), code.BC_CLASSES)
    clazz = draw(st.sampled_from(clazzes))

    # create an instance of the chosen class
    pt = getattr(clazz.__init__, '_param_types', [])
    args = [draw(get_strategy_for(t)) for t in pt]
    inst = clazz(*args)

    # propagate the changes to the stack
    bytecode, consts = code.Context().transform([inst])
    interp.dispatch_once(STD_SPACE, 0, bytecode, consts, run_stack)

    return inst

class DeterministicControlFlowSearchStrategy(SearchStrategy):
    """ This is flow graph search space is limited to deterministic
        control flow. This means the execution of this program MUST
        terminate in at most `max_steps`.

        max/min_steps: one step is one execution in the interpreter loop
        max_byte_codes: the amount of bytecodes the final program has
    """

    def __init__(self, stack, min_steps=1, max_steps=2**16, max_byte_codes=4000):
        SearchStrategy.__init__(self)

        self.stack = stack
        self.max_steps = float(max_steps)
        self.min_steps = min_steps
        self.average_steps = (self.max_steps - self.min_steps) / 2.0
        self.max_byte_codes = max_byte_codes

    def validate(self):
        pass
        #self.element_strategy.validate()

    def draw_from(self, stack, bccf):
        left = int(self.max_steps - bccf.interp_steps())
        if left <= 0:
            return st.just(None)
        if left > 32:
            left = 32
        # either draw a normal basic block
        strats = [basic_block(bytecode(stack), max_size=left)]
        # or draw a loop
        #strats.append(deterministic_loop(bytecode(stack)))
        # or draw a conditional
        #strats.append(conditional(bytecode(stack)))
        return one_of_strategies(strats)

    def do_draw(self, data):
        bccf = code.ByteCodeControlFlow()
        last_block = None
        stopping_value = 1 - 1.0 / (1 + self.average_steps)
        while True:
            data.start_example()
            block = bccf.generate_block(data, last_block, self)
            data.stop_example()
            if block is None:
                break # enough is enough!
            more = cu.biased_coin(data, stopping_value)
            if not more:
                break
        return bccf

@st.defines_strategy
def control_flow_graph(stack=None):
    if stack is None:
        # get a stack that is the same for one test run
        stack = Stack(0)
    return DeterministicControlFlowSearchStrategy(stack)


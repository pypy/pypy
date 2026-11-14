import opcode

from rpython.flowspace.bytecode import HostCode


def decode(func):
    code = HostCode._from_code(func.__code__)
    result = []
    offset = 0
    while offset < len(code.co_code):
        next_offset, opname, oparg = code.read(offset)
        assert next_offset > offset
        result.append((offset, opname, oparg))
        offset = next_offset
    assert offset == len(code.co_code)
    return code, result


JUMPS = set(opcode.opname[i] for i in opcode.hasjrel + opcode.hasjabs)


def test_read_whole_function():
    def f(x, y):
        total = 0
        for i in range(x):
            if i > y:
                total += i
            elif i == 3:
                continue
            while total > 100:
                total -= y
        return total

    code, instructions = decode(f)
    starts = set(offset for offset, _, _ in instructions)
    names = [opname for _, opname, _ in instructions]
    assert 'MISSING_OPCODE' not in names
    assert 'EXTENDED_ARG' not in names
    assert 'FOR_ITER' in names
    assert names[-1] == 'RETURN_VALUE'
    targets = [oparg for _, opname, oparg in instructions if opname in JUMPS]
    assert targets
    for target in targets:
        assert target in starts


def test_read_backward_jump():
    def f(n):
        while n:
            n -= 1

    code, instructions = decode(f)
    backward = [oparg for offset, opname, oparg in instructions
                if opname in JUMPS and oparg <= offset]
    assert backward


def test_read_large_argument():
    numbers = range(1000, 1400)
    source = 'def f():\n    return [%s]\n' % ', '.join(map(str, numbers))
    namespace = {}
    exec(source, namespace)

    code, instructions = decode(namespace['f'])
    loaded = [code.consts[oparg] for _, opname, oparg in instructions
              if opname == 'LOAD_CONST']
    if loaded == [tuple(numbers)]:
        return     # the host compiler folded the list display
    assert loaded == list(numbers)

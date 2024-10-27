import dis
import io
import pytest

def compare_lines(t1, t2):
    for l1, l2 in zip(t1.split('\n'), t2.split('\n')):
        if 'LOAD_CONST' in l1:
            # some small variation is OK
            assert 'LOAD_CONST' in l2
        else:
            assert l1.strip() == l2.strip()


@pytest.mark.skip("PyPy does not really try to be compatible")
def test_asyncFor():
    co = compile('''
async def f():
    class Iterable:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration


    async for i in Iterable():
        pass
    else:
        print('ok')
    ''', '<str>', 'exec')
    # Python does not resursively call dis._disassemble, but we want
    # the dis of the "async for", which we can only access inside a "async def"
    result = io.StringIO()
    dis.dis(co.co_consts[0].co_code, file=result)
    cpython310 = """0 GEN_START                1
          2 LOAD_BUILD_CLASS
          4 LOAD_CONST               1 (1)
          6 LOAD_CONST               2 (2)
          8 MAKE_FUNCTION            0
         10 LOAD_CONST               2 (2)
         12 CALL_FUNCTION            2
         14 STORE_FAST               0 (0)
         16 LOAD_FAST                0 (0)
         18 CALL_FUNCTION            0
         20 GET_AITER
    >>   22 SETUP_FINALLY            6 (to 36)
         24 GET_ANEXT
         26 LOAD_CONST               0 (0)
         28 YIELD_FROM
         30 POP_BLOCK
         32 STORE_FAST               1 (1)
         34 JUMP_ABSOLUTE           11 (to 22)
    >>   36 END_ASYNC_FOR
         38 LOAD_GLOBAL              0 (0)
         40 LOAD_CONST               3 (3)
         42 CALL_FUNCTION            1
         44 POP_TOP
         46 LOAD_CONST               0 (0)
         48 RETURN_VALUE
"""

    compare_lines(cpython310, result.getvalue()) 

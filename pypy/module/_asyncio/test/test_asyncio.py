class AppTestAsyncIO(object):
    """These tests are based on the async-await syntax of Python 3.5."""
    
    spaceconfig = dict(usemodules=["select","_socket","thread","signal",
                                   "struct","_multiprocessing","array",
                                   "_posixsubprocess","fcntl",
                                   "unicodedata"])
    
    def test_gil_issue(self):
        # the problem occured at await asyncio.open_connection
        # after calling run_until_complete
        """
import encodings.idna
import asyncio

async def f():
    reader, writer = await asyncio.open_connection('example.com', 80)
    writer.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(f())
print("done with async loop")
        """
    
    def test_async_for(self):
        # temporary test from
        # http://blog.idego.pl/2015/12/05/back-to-the-future-with-async-and-await-in-python-3-5/
        """
import asyncio
import logging
import sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(asctime)s: %(message)s")

class AsyncIter:
    def __init__(self):
        self._data = list(range(10))
        self._index = 0
    
    async def __aiter__(self):
        return self
    
    async def __anext__(self):
        while self._index < 10:
            await asyncio.sleep(1)
            self._index += 1
            return self._data[self._index-1]
        raise StopAsyncIteration

async def do_loop():
    async for x in AsyncIter():
        logging.info(x)

loop = asyncio.get_event_loop()
futures = [asyncio.ensure_future(do_loop()), asyncio.ensure_future(do_loop())]
loop.run_until_complete(asyncio.wait(futures))
        """
    
    def test_asynchronous_context_managers(self):
        # it is important that "releasing lock A" happens before "holding lock B"
        # or the other way around, but it is not allowed that both coroutines
        # hold the lock at the same time
        """
import encodings.idna
import asyncio

class Corotest(object):
    def __init__(self):
        self.res = "-"
    
    async def coro(self, name, lock):
        self.res += ' coro {}: waiting for lock -'.format(name)
        async with lock:
            self.res += ' coro {}: holding the lock -'.format(name)
            await asyncio.sleep(1)
            self.res += ' coro {}: releasing the lock -'.format(name)

cor = Corotest()
loop = asyncio.get_event_loop()
lock = asyncio.Lock()
coros = asyncio.gather(cor.coro(1, lock), cor.coro(2, lock))
try:
    loop.run_until_complete(coros)
finally:
    loop.close()

assert "coro 1: waiting for lock" in cor.res
assert "coro 1: holding the lock" in cor.res
assert "coro 1: releasing the lock" in cor.res
assert "coro 2: waiting for lock" in cor.res
assert "coro 2: holding the lock" in cor.res
assert "coro 2: releasing the lock" in cor.res
assert cor.res.find("coro 1: releasing the lock") < cor.res.find("coro 2: holding the lock") or \
cor.res.find("coro 2: releasing the lock") < cor.res.find("coro 1: holding the lock")
        """

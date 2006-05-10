from stackless import coroutine

__all__ = 'run getcurrent getmain schedule tasklet channel'.split()

main_tasklet = None
next_tasklet = None
scheduler = None

coro_reg = {}

def __init():
    global maintasklet
    mt = tasklet()
    mt._coro = c = coroutine.getcurrent()
    maintasklet = mt
    coro_reg[c] = mt

def run():
    schedule()

def getcurrent():
    c = coroutine.getcurrent()
    return coro_reg[c]

def getmain():
    return main_tasklet

def schedule():
    scheduler.schedule()

class tasklet(object):
    def __init__(self,func=None):
        self._func = func

    def __call__(self,*argl,**argd):
        self._coro = c = coroutine()
        c.bind(self._func,*argl,**argd)
        coro_reg[c] = self
        self.insert()
        return self

    def awake(self):pass

    def sleep(self):pass

    def run(self):
        scheduler.setnexttask(self)
        schedule()

    def insert(self):
        scheduler.insert(self)

    def remove(self):
        scheduler.remove(self)

    def kill(self):pass

class channel(object):
    def __init__(self):
        self.balance = 0
        self._readq = []
        self._writeq = []

    def send(self, msg):
        ct = getcurrent()
        scheduler.remove(ct)
        self._writeq.append((ct,msg))
        self.balance += 1
        if self._readq:
            nt, self._readq = self._readq[0], self._readq[1:]
            scheduler.priorityinsert(nt)
        schedule()

    def receive(self):
        ct = getcurrent()
        if self._writeq:
            (wt,retval), self._writeq = self._writeq[0], self._writeq[1:]
            scheduler.priorityinsert(wt)
            self.balance -= 1
            return retval
        else:
            self._readq.append(ct)
            scheduler.remove(ct)
            schedule()
            return self.receive()

class Scheduler(object):
    def __init__(self):
        self.tasklist = []
        self.nexttask = None 

    def empty(self):
        return not self.tasklist

    def __str__(self):
        return repr(self.tasklist) + '/%s' % self.nexttask

    def insert(self,task):
        if (task not in self.tasklist) and task is not maintasklet:
            self.tasklist.append(task)
        if self.nexttask is None:
            self.nexttask = 0

    def priorityinsert(self,task):
        if task in self.tasklist:
            self.tasklist.remove(task)
        if task is maintasklet:
            return
        if self.nexttask:
            self.tasklist.insert(self.nexttask,task)
        else:
            self.tasklist.insert(0,task)
            self.nexttask = 0

    def remove(self,task):
        try:
            i = self.tasklist.index(task)
            del(self.tasklist[i])
            if self.nexttask > i:
                self.nexttask -= 1
            if len(self.tasklist) == 0:
                self.nexttask = None
        except ValueError:pass

    def next(self):
        if self.nexttask is not None:
            task = self.tasklist[self.nexttask]
            self.nexttask += 1
            if self.nexttask == len(self.tasklist):
                self.nexttask = 0
            return task
        else:
            return maintasklet

    def setnexttask(self,task):
        if task not in self.tasklist:
            self.tasklist.insert(task)
        try:
            i = self.tasklist.index(task)
            self.nexttask = i
        except IndexError:pass

    def schedule(self):
        n = self.next()
        n._coro.switch()

scheduler = Scheduler()
__init()

"""Minimal reader for the profiles written by src/shared."""

import struct

MARKER_STACKTRACE = '\x01'
MARKER_VIRTUAL_IP = '\x02'
MARKER_TRAILER = '\x03'
MARKER_HEADER = '\x05'
MARKER_TIME_N_ZONE = '\x06'
MARKER_META = '\x07'
MARKER_NATIVE_SYMBOLS = '\x08'

VERSION_THREAD_ID = 1
VERSION_MEMORY = 3
VERSION_MODE_AWARE = 4
VERSION_DURATION = 5
VERSION_TIMESTAMP = 6
VERSION_SAMPLE_TIME = 7

PROFILE_MEMORY = 1
PROFILE_LINES = 2
PROFILE_NATIVE = 4
PROFILE_RPYTHON = 8
PROFILE_REAL_TIME = 16

VMPROF_CODE_TAG = 1
VMPROF_JITTED_TAG = 3
VMPROF_ASSEMBLER_TAG = 6
VMPROF_NATIVE_TAG = 7

# a sample may stand for at most this many seconds of lost timer signals,
# so that a process stopped in a debugger does not attribute minutes to one
# frame; the excess is reported as Profile.lost_time
DEFAULT_MAX_SAMPLE_GAP = 1.0

TIME_N_ZONE_SIZE = 24    # two 64 bit words plus an 8 byte zone name


class AssemblerCode(int):
    pass

class JittedCode(int):
    pass

class NativeCode(int):
    pass

def wrap_kind(kind, pc):
    if kind == VMPROF_ASSEMBLER_TAG:
        return AssemblerCode(pc)
    elif kind == VMPROF_JITTED_TAG:
        return JittedCode(pc)
    elif kind == VMPROF_NATIVE_TAG:
        return NativeCode(pc)
    assert kind == VMPROF_CODE_TAG, 'unknown stack entry kind %d' % kind
    return pc


class Node(object):

    def __init__(self, addr, name, count=0):
        self.addr = addr
        self.name = name
        self.count = count
        self.children = {}
        self.lines = {}

    def add_child(self, addr, name, count):
        try:
            child = self.children[addr]
            child.count += count
        except KeyError:
            child = self.children[addr] = Node(addr, name, count)
        return child

    def walk(self, callback):
        callback(self)
        for child in self.children.values():
            child.walk(callback)

    def __repr__(self):
        return '<Node %s count=%s>' % (self.name, self.count)


class Profile(object):
    """The parts of vmprof.stats.Stats that the rvmprof tests use."""

    def __init__(self):
        self.version = 0
        self.interp_name = None
        self.period = 0          # microseconds
        self.profile_memory = False
        self.profile_lines = False
        self.profile_rpython = False
        self.profile_real_time = False
        self.meta = {}
        self.names = {}
        self.profiles = []       # (trace, weight, thread_id, mem_in_kb)
        self.lost_time = 0.0

    @property
    def n_samples(self):
        return len(self.profiles)

    @property
    def expected_samples(self):
        """The number of timer periods the samples stand for."""
        return sum([p[1] for p in self.profiles])

    def get_lost_fraction(self):
        if not self.expected_samples:
            return 0.0
        return 1.0 - float(self.n_samples) / self.expected_samples

    def get_name(self, addr):
        return self.names.get(addr, '<unknown code>')

    def get_tree(self):
        for trace, _, _, _ in self.profiles:
            if trace:
                break
        else:
            raise ValueError('no stack samples in the profile')
        top = Node(trace[0], self.get_name(trace[0]), self.expected_samples)
        for trace, weight, _, _ in self.profiles:
            cur = top
            last_addr = top.addr
            for addr in trace:
                if isinstance(addr, AssemblerCode):
                    continue
                if addr <= 0:
                    cur.lines[-addr] = cur.lines.get(-addr, 0) + weight
                elif addr != last_addr:
                    last_addr = addr
                    cur = cur.add_child(addr, self.get_name(addr), weight)
        return _filter_top(top)


def _filter_top(top):
    """Descend to the first interesting node, like vmprof's Stats does."""
    first_top = top
    while top.children:
        if top.name.startswith('py:<module>'):
            return top
        if len(top.children) > 1:
            top = max(top.children.values(), key=lambda node: node.count)
        else:
            top = top.children.values()[0]
    return first_top


class _Reader(object):

    def __init__(self, data):
        self.data = data
        self.pos = 0
        # the static header starts with the words 0 and 3, so the position
        # of the 3 gives the word size
        if data[4] == '\x03':
            self.word_size = 4
        elif data[8] == '\x03':
            self.word_size = 8
        else:
            raise ValueError('cannot tell the word size of the profile')

    def read(self, count):
        end = self.pos + count
        assert end <= len(self.data), 'truncated profile'
        res = self.data[self.pos:end]
        self.pos = end
        return res

    def skip(self, count):
        self.read(count)

    def at_end(self):
        return self.pos >= len(self.data)

    def word(self):
        if self.word_size == 8:
            return struct.unpack('<q', self.read(8))[0]
        return struct.unpack('<l', self.read(4))[0]

    def s64(self):
        return struct.unpack('<q', self.read(8))[0]

    def string(self):
        return self.read(self.word())

    def addresses(self, count):
        res = []
        for i in range(count):
            addr = self.word()
            if addr > 0 and addr & 1 == 1:
                addr = NativeCode(addr)
            res.append(addr)
        return res


class _Parser(object):

    def __init__(self, data, max_sample_gap):
        self.reader = _Reader(data)
        self.max_sample_gap = max_sample_gap
        self.prof = Profile()
        self.last_sample_time = {}

    def parse(self):
        r = self.reader
        prof = self.prof
        assert r.word() == 0, 'bad static header'
        assert r.word() == 3, 'bad static header'
        assert r.word() == 0, 'bad static header'
        prof.period = r.word()
        assert r.word() in (0, 1), 'bad static header'
        while not r.at_end():
            marker = r.read(1)
            if marker == MARKER_HEADER:
                self.read_header()
            elif marker == MARKER_META:
                key = r.string()
                prof.meta[key] = r.string()
            elif marker == MARKER_TIME_N_ZONE:
                r.skip(TIME_N_ZONE_SIZE)
            elif marker == MARKER_STACKTRACE:
                self.read_stacktrace()
            elif marker in (MARKER_VIRTUAL_IP, MARKER_NATIVE_SYMBOLS):
                addr = r.word()
                prof.names[addr] = r.string()
            elif marker == MARKER_TRAILER:
                if prof.version >= VERSION_DURATION:
                    r.skip(TIME_N_ZONE_SIZE)
                break
            else:
                raise ValueError('unknown marker %r at %d' % (marker, r.pos))
        return prof

    def read_header(self):
        r = self.reader
        prof = self.prof
        assert not prof.version, 'multiple headers'
        prof.version, = struct.unpack('!h', r.read(2))
        if prof.version > VERSION_SAMPLE_TIME:
            raise ValueError('profile version %d is newer than this reader'
                             % prof.version)
        if prof.version >= VERSION_MODE_AWARE:
            mode = ord(r.read(1))
            prof.profile_memory = (mode & PROFILE_MEMORY) != 0
            prof.profile_lines = (mode & PROFILE_LINES) != 0
            prof.profile_rpython = (mode & PROFILE_RPYTHON) != 0
            prof.profile_real_time = (mode & PROFILE_REAL_TIME) != 0
        else:
            prof.profile_memory = prof.version == VERSION_MEMORY
        prof.interp_name = r.read(ord(r.read(1)))
        if prof.interp_name == 'pypy':
            prof.profile_rpython = True

    def read_stacktrace(self):
        r = self.reader
        prof = self.prof
        count = r.word()
        assert count == 1, 'sample count %d is not supported' % count
        depth = r.word()
        assert depth <= 2 ** 16, 'stack trace depth too high'
        if prof.profile_rpython:
            assert depth & 1 == 0, 'rpython traces come in (kind, pc) pairs'
            kinds_and_pcs = r.addresses(depth)
            trace = [wrap_kind(kinds_and_pcs[i], kinds_and_pcs[i + 1])
                     for i in range(0, depth, 2)]
        else:
            trace = r.addresses(depth)
            if prof.profile_lines:
                for i in range(0, len(trace), 2):
                    trace[i] = -trace[i]
        thread_id = 0
        mem_in_kb = 0
        sample_time = None
        if prof.version >= VERSION_THREAD_ID:
            thread_id = r.word()
        if prof.profile_memory:
            mem_in_kb = r.word()
        if prof.version >= VERSION_SAMPLE_TIME:
            sample_time = r.s64()
        trace.reverse()
        weight = self.sample_weight(thread_id, sample_time)
        prof.profiles.append((trace, weight, thread_id, mem_in_kb))

    def sample_weight(self, thread_id, sample_time):
        """How many timer periods this sample stands for.

        A pending timer signal is a single bit, so every expiry while the
        process is off the cpu is dropped. Weighting a sample by the time
        since the previous one on the same clock accounts for those. In real
        time mode each thread gets its own signal, so track the previous
        sample per thread; in cpu time mode there is one process wide timer
        and the timestamps are process cpu time.
        """
        prof = self.prof
        if sample_time is None or prof.period <= 0:
            return 1
        key = thread_id if prof.profile_real_time else None
        prev = self.last_sample_time.get(key)
        if prev is None or sample_time > prev:
            self.last_sample_time[key] = sample_time
        if prev is None:
            return 1.0
        gap = sample_time - prev
        max_gap = self.max_sample_gap * 10 ** 9
        if gap > max_gap:
            prof.lost_time += (gap - max_gap) / 10.0 ** 9
            gap = max_gap
        return max(gap / (prof.period * 1000.0), 1.0)


def read_profile(filename, max_sample_gap=DEFAULT_MAX_SAMPLE_GAP):
    with open(str(filename), 'rb') as fobj:
        data = fobj.read()
    return _Parser(data, max_sample_gap).parse()

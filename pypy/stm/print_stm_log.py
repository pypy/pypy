#!/usr/bin/env pypy
import sys, os
import struct, re, linecache

# ____________________________________________________________

STM_TRANSACTION_START   = 0
STM_TRANSACTION_COMMIT  = 1
STM_TRANSACTION_ABORT   = 2

# sometimes there is a DETACH w/o REATTACH and the other way around.
# This happens because the JIT does not emit DETACH/REATTACH events
# to the log (XXX).
STM_TRANSACTION_DETACH = 3
STM_TRANSACTION_REATTACH = 4

# inevitable contention: all threads that try to become inevitable
# have a STM_BECOME_INEVITABLE event with a position marker.  Then,
# if it waits it gets a STM_WAIT_OTHER_INEVITABLE.  It is possible
# that a thread gets STM_BECOME_INEVITABLE followed by
# STM_TRANSACTION_ABORT if it fails to become inevitable.
STM_BECOME_INEVITABLE      = 5

# write-read contention: a "marker" is included in the PYPYSTM file
# saying where the write was done.  Followed by STM_TRANSACTION_ABORT.
STM_CONTENTION_WRITE_READ  = 6

# always one STM_WAIT_xxx followed later by STM_WAIT_DONE or
# possibly STM_TRANSACTION_ABORT
STM_WAIT_FREE_SEGMENT      = 7
STM_WAIT_SYNCING           = 8
STM_WAIT_SYNC_PAUSE        = 9
STM_WAIT_OTHER_INEVITABLE  = 10
STM_WAIT_DONE              = 11

# start and end of GC cycles
STM_GC_MINOR_START  = 12
STM_GC_MINOR_DONE   = 13
STM_GC_MAJOR_START  = 14
STM_GC_MAJOR_DONE   = 15

_STM_EVENT_N  = 16

PAUSE_AFTER_ABORT   = 0.000001      # usleep(1) after every abort


event_name = {}
for _key, _value in globals().items():
    if _key.startswith('STM_'):
        event_name[_value] = _key

# ____________________________________________________________


class LogEntry(object):
    def __init__(self, timestamp, threadnum, event, marker, frac):
        self.timestamp = timestamp
        self.threadnum = threadnum
        self.event = event
        self.marker = marker
        self.frac = frac

    def __str__(self):
        s = '[%.3f][%s]\t%s' % (
            self.timestamp, self.threadnum, event_name[self.event])
        if self.marker:
            s += ':\n%s' % print_marker(self.marker)
        return s


def parse_log(filename):
    f = open(filename, 'rb')
    try:
        header = f.read(16)
        if header != "STMGC-C8-PROF01\n":
            raise ValueError("wrong format in file %r" % (filename,))
        f.seek(0, 2)
        frac = 1.0 / f.tell()
        f.seek(16, 0)
        result = []
        prev_time = -1.0
        while True:
            packet = f.read(14)
            if len(packet) < 14: break
            sec, nsec, threadnum, event, markerlen = \
                  struct.unpack("IIIBB", packet)
            if event >= _STM_EVENT_N:
                raise ValueError("the file %r appears corrupted" % (filename,))
            timestamp = sec + 0.000000001 * nsec
            if timestamp < prev_time:
                raise ValueError("decreasing timestamps: %.9f -> %.9f" % (
                    prev_time, timestamp))
            prev_time = timestamp
            marker = f.read(markerlen)
            yield LogEntry(timestamp, threadnum, event, marker,
                           f.tell() * frac)
    finally:
        f.close()


class ThreadState(object):
    def __init__(self, threadnum):
        self.threadnum = threadnum
        self.cpu_time_committed = 0.0
        self.cpu_time_aborted = 0.0
        self.cpu_time_paused = 0.0
        self.cpu_time_gc_minor = 0.0
        self.cpu_time_gc_major = 0.0
        self.count_committed = 0
        self.count_aborted = 0
        self._prev = (0.0, "stop")
        self._in_major_coll = None
        self.reset_counters()

    def reset_counters(self):
        self._transaction_cpu_time = 0.0
        self._transaction_pause_time = 0.0
        self._transaction_aborting = False
        self._transaction_inev = None
        self._transaction_detached_time = 0.0
        self._in_minor_coll = None
        assert self._prev[1] == "stop"

    def transaction_start(self, entry):
        self.reset_counters()
        self.progress(entry.timestamp, "run")

    def progress(self, now, new_state):
        prev_time, prev_state = self._prev
        add_time = now - prev_time
        assert add_time >= 0.0
        if prev_state == "run":
            self._transaction_cpu_time += add_time
        elif prev_state == "pause":
            self._transaction_pause_time += add_time
        elif prev_state == "detached":
            self._transaction_detached_time += add_time
        self._prev = now, new_state

    def make_sure_not_detached(self, entry):
        # since some DETACH events are not followed by a REATTACH
        # (because the JIT does not emit them), approximate by
        # calling this method where we are sure that we shouldn't
        # be detached.
        if self._prev[1] == "detached":
            self.progress(entry.timestamp, "run")

    def transaction_detach(self, entry):
        self.progress(entry.timestamp, "detached")

    def transaction_reattach(self, entry):
        self.progress(entry.timestamp, "run")

    def transaction_commit(self, entry):
        assert not self._transaction_aborting
        self.progress(entry.timestamp, "stop")
        self.cpu_time_committed += self._transaction_cpu_time
        self.cpu_time_paused += self._transaction_pause_time
        self.count_committed += 1

    def transaction_abort(self, entry):
        self.progress(entry.timestamp, "stop")
        self.cpu_time_aborted += self._transaction_cpu_time
        self.cpu_time_paused += self._transaction_pause_time
        self.count_aborted += 1

    def become_inevitable(self, entry):
        self.progress(entry.timestamp, "run")
        if self._transaction_inev is None:
            self._transaction_inev = [entry, None]

    def transaction_pause(self, entry):
        self.progress(entry.timestamp, "pause")
        if (entry.event == STM_WAIT_OTHER_INEVITABLE and
                self._transaction_inev is not None):
            self._transaction_inev[1] = entry.timestamp

    def transaction_unpause(self, entry, out_conflicts):
        self.progress(entry.timestamp, "run")
        if self._transaction_inev and self._transaction_inev[1] is not None:
            wait_time = entry.timestamp - self._transaction_inev[1]
            self.wait_for_other_inev(wait_time, out_conflicts)
            self._transaction_inev[1] = None

    def get_conflict(self, entry, out_conflicts):
        summary = (entry.event, entry.marker)
        c = out_conflicts.get(summary)
        if c is None:
            c = out_conflicts[summary] = ConflictSummary(*summary)
        c.num_events += 1
        c.timestamps.append(entry.timestamp)
        return c

    def contention_write_read(self, entry, out_conflicts):
        # This thread is aborted because it has read an object, but
        # another thread already committed a change to that object.
        # The marker is pointing inside the other thread's write.
        if self._transaction_aborting:
            print >> sys.stderr, "note: double STM_CONTENTION_WRITE_READ"
            return
        self._transaction_aborting = True
        c = self.get_conflict(entry, out_conflicts)
        self.progress(entry.timestamp, "run")
        c.aborted_time += self._transaction_cpu_time
        c.paused_time += self._transaction_pause_time

    def wait_for_other_inev(self, wait_time, out_conflicts):
        c = self.get_conflict(self._transaction_inev[0], out_conflicts)
        assert wait_time >= 0.0
        c.paused_time += wait_time

    def gc_minor_start(self, event):
        self.make_sure_not_detached(event)
        self._in_minor_coll = event.timestamp

    def gc_minor_done(self, event):
        if self._in_minor_coll is not None:
            gc_time = event.timestamp - self._in_minor_coll
            assert gc_time >= 0.0
            self.cpu_time_gc_minor += gc_time
            self._in_minor_coll = None

    def gc_major_start(self, event):
        self._in_major_coll = event.timestamp

    def gc_major_done(self, event):
        if self._in_major_coll is not None:
            gc_time = event.timestamp - self._in_major_coll
            assert gc_time >= 0.0
            self.cpu_time_gc_major += gc_time
            self._in_major_coll = None


class ConflictSummary(object):
    def __init__(self, event, marker):
        self.event = event
        self.marker = marker
        self.aborted_time = 0.0
        self.paused_time = 0.0
        self.num_events = 0
        self.timestamps = []

    def sortkey(self):
        return self.aborted_time + self.paused_time

    def get_event_name(self):
        return event_name[self.event]

    def get_marker(self):
        return print_marker(self.marker)

    def __str__(self):
        s = '%.3fs lost in aborts, %.3fs paused (%dx %s)\n' % (
            self.aborted_time, self.paused_time, self.num_events,
            self.get_event_name())
        s += print_marker(self.marker)
        return s



r_marker = re.compile(r'File "(.+)", line (\d+)')

def print_marker(marker):
    s = '  %s' % marker
    match = r_marker.search(marker)
    if match:
        filename = match.group(1)
        if not (filename.endswith('.pyc') or filename.endswith('.pyo')):
            line = linecache.getline(filename, int(match.group(2)))
            line = line.strip()
            if line:
                s += '\n    %s' % line
    return s

def percent(fraction, total):
    r = '%.1f' % (fraction * 100.0 / total)
    if len(r) > 3:
        r = r.split('.')[0]
    return r + '%'

def summarize_log_entries(logentries, stmlog):
    threads = {}
    conflicts = {}
    cnt = 0
    for entry in logentries:
        if (cnt & 0x7ffff) == 0:
            if cnt == 0:
                start_time = entry.timestamp
            else:
                print >> sys.stderr, '%.0f%%' % (entry.frac * 100.0,),
        cnt += 1
        #
        #print entry
        t = threads.get(entry.threadnum)
        if t is None:
            t = threads[entry.threadnum] = ThreadState(entry.threadnum)
        #
        if entry.event == STM_TRANSACTION_START:
            t.transaction_start(entry)
        elif entry.event == STM_TRANSACTION_DETACH:
            t.transaction_detach(entry)
        elif entry.event == STM_TRANSACTION_REATTACH:
            t.transaction_reattach(entry)
            t.become_inevitable(entry)
        elif entry.event == STM_TRANSACTION_COMMIT:
            t.transaction_commit(entry)
        elif entry.event == STM_TRANSACTION_ABORT:
            t.transaction_abort(entry)
        elif entry.event == STM_BECOME_INEVITABLE:
            t.become_inevitable(entry)
        elif entry.event == STM_CONTENTION_WRITE_READ:
            t.contention_write_read(entry, conflicts)
        elif entry.event in (STM_WAIT_FREE_SEGMENT,
                             STM_WAIT_SYNCING,
                             STM_WAIT_SYNC_PAUSE,
                             STM_WAIT_OTHER_INEVITABLE):
            t.transaction_pause(entry)
        elif entry.event == STM_WAIT_DONE:
            t.transaction_unpause(entry, conflicts)
        elif entry.event == STM_GC_MINOR_START:
            t.gc_minor_start(entry)
        elif entry.event == STM_GC_MINOR_DONE:
            t.gc_minor_done(entry)
        elif entry.event == STM_GC_MAJOR_START:
            t.gc_major_start(entry)
        elif entry.event == STM_GC_MAJOR_DONE:
            t.gc_major_done(entry)
    #
    if cnt == 0:
        raise Exception("empty file")
    print >> sys.stderr
    stop_time = entry.timestamp
    stmlog.start_time = start_time
    stmlog.total_time = stop_time - start_time
    stmlog.threads = threads
    stmlog.conflicts = conflicts

def dump_summary(stmlog, maxcount=15):
    start_time = stmlog.start_time
    total_time = stmlog.total_time
    print
    print 'Total real time:     %9.3fs' % (total_time,)
    #
    total_cpu_time_committed = stmlog.get_total_cpu_time_committed()
    total_cpu_time_aborted = stmlog.get_total_cpu_time_aborted()
    total_cpu_time_paused = stmlog.get_total_cpu_time_paused()
    total_cpu_time_total = (total_cpu_time_committed +
                            total_cpu_time_aborted +
                            total_cpu_time_paused)
    total_cpu_time_gc_minor = stmlog.get_total_cpu_time_gc_minor()
    total_cpu_time_gc_major = stmlog.get_total_cpu_time_gc_major()
    print 'CPU time in STM mode:%9.3fs (%4s) committed' % (
        total_cpu_time_committed, percent(total_cpu_time_committed, total_time))
    print '                     %9.3fs (%4s) aborted' % (
        total_cpu_time_aborted,   percent(total_cpu_time_aborted,   total_time))
    print '                     %9.3fs (%4s) paused' % (
        total_cpu_time_paused,    percent(total_cpu_time_paused,    total_time))
    print '                     %9.3fs (%4s) TOTAL' % (
        total_cpu_time_total,     percent(total_cpu_time_total,     total_time))
    print '           including %9.3fs (%4s) minor GC collections' % (
        total_cpu_time_gc_minor,  percent(total_cpu_time_gc_minor,  total_time))
    print '                 and %9.3fs (%4s) major GC collections' % (
        total_cpu_time_gc_major,  percent(total_cpu_time_gc_major,  total_time))
    total_committed, total_aborted = stmlog.get_transaction_statistics()
    total_transactions = total_committed + total_aborted
    transactions_per_second = total_transactions / total_cpu_time_total
    print 'Total number of transactions: %6.f committed: %4s aborted: %4s' % (
        total_transactions, percent(total_committed, total_transactions),
        percent(total_aborted, total_transactions))
    print '     transactions per second: %6.f' % (
        transactions_per_second)
    print
    #
    values = stmlog.get_conflicts()
    for c in values[:maxcount]:
        intervals = 60
        timeline = [0] * intervals
        for t in c.timestamps:
            idx = int((t - start_time) / total_time * intervals)
            timeline[idx] += 1

        print str(c)
        max_events = float(max(timeline))+0.1
        print "time line:", "|"+"".join(['_xX'[int(i / max_events * 3)]
                                     if i else ' ' for i in timeline])+"|"
        print


class StmLog(object):
    def __init__(self, filename):
        summarize_log_entries(parse_log(filename), self)

    def get_transaction_statistics(self):
        aborted = sum([v.count_aborted for v in self.threads.values()])
        committed = sum([v.count_committed for v in self.threads.values()])
        return (committed, aborted)

    def get_total_cpu_time_committed(self):
        return sum([v.cpu_time_committed for v in self.threads.values()])

    def get_total_cpu_time_aborted(self):
        return sum([v.cpu_time_aborted for v in self.threads.values()])

    def get_total_cpu_time_paused(self):
        return sum([v.cpu_time_paused for v in self.threads.values()])

    def get_total_cpu_time_gc_minor(self):
        return sum([v.cpu_time_gc_minor for v in self.threads.values()])

    def get_total_cpu_time_gc_major(self):
        return sum([v.cpu_time_gc_major for v in self.threads.values()])

    def get_conflicts(self):
        values = self.conflicts.values()
        values.sort(key=ConflictSummary.sortkey)
        values.reverse()
        return values

    def get_total_aborts_and_pauses(self):
        total = 0
        for c in self.conflicts.values():
            total += c.num_events
        return total

    def dump(self, maxcount=15):
        dump_summary(self, maxcount)


def main(argv):
    assert len(argv) >= 1, "expected a filename argument"
    if len(argv) > 1:
        maxcount = int(argv[1])
    else:
        maxcount = 5
    StmLog(argv[0]).dump(maxcount)
    return 0

if __name__ == '__main__':
    if sys.stdout.isatty():
        sys.stdout = os.popen("less --quit-if-one-screen --no-init", "w")
    try:
        sys.exit(main(sys.argv[1:]))
    finally:
        sys.stdout.close()

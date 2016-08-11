import sys, os, struct, socket, errno, subprocess
import linecache
from rpython.translator.revdb import ancillary
from rpython.translator.revdb.message import *


class Breakpoint(Exception):
    def __init__(self, time):
        self.time = time   # time of the previous stop_point
        self.nums = []     # list of breakpoint numbers that occurred, in order

    def record_num(self, num):
        self.nums.append(num)

    def regular_breakpoint_nums(self):
        for num in self.nums:
            if num != -1 and num != -2:
                yield num

    def __repr__(self):
        return 'Breakpoint(%d, %r)' % (self.time, self.nums)
    __str__ = __repr__


class AllBreakpoints(object):

    def __init__(self):
        self.num2break = {}    # {small number: encoded break/watchpoint}
        self.sources = {}      # {small number: src text}
        self.watchvalues = {}  # {small number: resulting text}
        self.watchuids = {}    # {small number: [uid...]}
        self.stack_id = 0      # breaks when leaving/entering a frame from/to
                               # the frame identified by 'stack_id'

    def __repr__(self):
        return 'AllBreakpoints(%r, %r, %r, %r)' % (
            self.num2break, self.watchvalues, self.watchuids,
            self.stack_id)

    def compare(self, other):
        if (self.num2break == other.num2break and
            self.stack_id == other.stack_id):
            if self.watchvalues == other.watchvalues:
                return 2     # completely equal
            else:
                return 1     # equal, but watchvalues out-of-date
        else:
            return 0     # different

    def is_empty(self):
        return len(self.num2break) == 0 and self.stack_id == 0

    def duplicate(self):
        a = AllBreakpoints()
        a.num2break.update(self.num2break)
        a.stack_id = self.stack_id
        return a


class RecreateSubprocess(Exception):
    pass


class ReplayProcess(object):
    """Represent one replaying subprocess.

    It can be either the one started with --revdb-replay, or a fork.
    """

    def __init__(self, pid, control_socket,
                 breakpoints_cache=AllBreakpoints(),
                 printed_objects=frozenset(),
                 linecacheoutput=None):
        self.pid = pid
        self.control_socket = control_socket
        self.tainted = False
        self.breakpoints_cache = breakpoints_cache    # don't mutate this
        self.printed_objects = printed_objects        # don't mutate this
        # ^^^ frozenset containing the uids of the objects that are
        #     either already discovered in this child
        #     (if uid < currently_created_objects), or that will
        #     automatically be discovered when we move forward
        self.linecacheoutput = linecacheoutput or linecache.getline

    def _recv_all(self, size):
        pieces = []
        while size > 0:
            data = self.control_socket.recv(size)
            if not data:
                raise EOFError
            size -= len(data)
            pieces.append(data)
        return ''.join(pieces)

    def send(self, msg):
        #print 'SENT:', self.pid, msg
        binary = struct.pack("iIqqq", msg.cmd, len(msg.extra),
                             msg.arg1, msg.arg2, msg.arg3)
        self.control_socket.sendall(binary + msg.extra)

    def recv(self):
        binary = self._recv_all(struct.calcsize("iIqqq"))
        cmd, size, arg1, arg2, arg3 = struct.unpack("iIqqq", binary)
        extra = self._recv_all(size)
        msg = Message(cmd, arg1, arg2, arg3, extra)
        #print 'RECV:', self.pid, msg
        return msg

    def expect(self, cmd, arg1=0, arg2=0, arg3=0, extra=""):
        msg = self.recv()
        assert msg.cmd == cmd, msg
        if arg1 is not Ellipsis:
            assert msg.arg1 == arg1, msg
        if arg2 is not Ellipsis:
            assert msg.arg2 == arg2, msg
        if arg3 is not Ellipsis:
            assert msg.arg3 == arg3, msg
        if extra is not Ellipsis:
            assert msg.extra == extra, msg
        return msg

    def expect_ready(self):
        msg = self.expect(ANSWER_READY, Ellipsis, Ellipsis)
        self.update_times(msg)

    def update_times(self, msg):
        self.current_time = msg.arg1
        self.currently_created_objects = msg.arg2

    def clone(self):
        """Fork this subprocess.  Returns a new ReplayProcess() that is
        an identical copy.
        """
        self.send(Message(CMD_FORK))
        s1, s2 = socket.socketpair()
        ancillary.send_fds(self.control_socket.fileno(), [s2.fileno()])
        s2.close()
        msg = self.expect(ANSWER_FORKED, Ellipsis)
        child_pid = msg.arg1
        self.expect_ready()
        other = ReplayProcess(child_pid, s1,
                              breakpoints_cache=self.breakpoints_cache,
                              printed_objects=self.printed_objects,
                              linecacheoutput=self.linecacheoutput)
        other.expect_ready()
        #print >> sys.stderr, 'CLONED', self.current_time
        return other

    def close(self):
        """Close this subprocess."""
        try:
            self.send(Message(CMD_QUIT))
        except socket.error:
            pass

    def forward(self, steps, breakpoint_mode):
        """Move this subprocess forward in time.
        Returns the Breakpoint or None.
        """
        assert not self.tainted

        # <DEBUGGING ONLY>
        currents = self.current_time, self.currently_created_objects
        self.send(Message(CMD_PING))
        self.expect_ready()
        assert currents == (self.current_time, self.currently_created_objects)
        # </DEBUGGING ONLY>

        self.send(Message(CMD_FORWARD, steps, ord(breakpoint_mode)))
        #
        # record all breakpoints that occur together during the *last* step
        bkpt = None
        while True:
            msg = self.recv()
            if msg.cmd != ANSWER_BREAKPOINT:
                break
            if bkpt is None or bkpt.time != msg.arg1:
                bkpt = Breakpoint(msg.arg1)
            bkpt.record_num(msg.arg3)
        assert msg.cmd == ANSWER_READY, msg
        self.update_times(msg)
        return bkpt

    def print_text_answer(self, pgroup=None):
        while True:
            msg = self.recv()
            if msg.cmd == ANSWER_TEXT:
                sys.stdout.write(msg.extra)
                sys.stdout.flush()
            elif msg.cmd == ANSWER_READY:
                self.update_times(msg)
                break
            elif msg.cmd == ANSWER_LINECACHE:
                line = self.linecacheoutput(msg.extra, msg.arg1)
                if line == '':
                    line = '?'
                if msg.arg2:    # strip?
                    line = line.strip()
                else:
                    line = line.rstrip('\r\n')
                sys.stdout.write(line + '\n')
                sys.stdout.flush()
            elif msg.cmd == ANSWER_NEXTNID and pgroup is not None:
                uid = msg.arg1
                if uid < pgroup.initial_uid:
                    continue     # created before the first stop point, ignore
                self.printed_objects = self.printed_objects.union([uid])
                new_nid = len(pgroup.all_printed_objects_lst)
                nid = pgroup.all_printed_objects.setdefault(uid, new_nid)
                if nid == new_nid:
                    pgroup.all_printed_objects_lst.append(uid)
                sys.stdout.write('$%d = ' % nid)
                sys.stdout.flush()
            elif msg.cmd == ANSWER_ATTEMPT_IO:
                raise RecreateSubprocess
            else:
                print >> sys.stderr, "unexpected %r" % (msg,)


class ReplayProcessGroup(object):
    """Handle a family of subprocesses.
    """
    MAX_SUBPROCESSES = 31       # maximum number of subprocesses
    STEP_RATIO = 0.25           # subprocess n is between subprocess n-1
                                #   and the end, at this fraction of interval

    def __init__(self, executable, revdb_log_filename, linecacheoutput=None):
        s1, s2 = socket.socketpair()
        initial_subproc = subprocess.Popen(
            [executable, '--revdb-replay', revdb_log_filename,
             str(s2.fileno())], preexec_fn=s1.close)
        s2.close()
        child = ReplayProcess(initial_subproc.pid, s1,
                              linecacheoutput=linecacheoutput)
        msg = child.expect(ANSWER_INIT, INIT_VERSION_NUMBER, Ellipsis)
        self.total_stop_points = msg.arg2
        if self.total_stop_points == 0:
            raise ValueError("%r does not contain any stop point" %
                             (revdb_log_filename,))
        child.expect_ready()
        self.initial_uid = child.currently_created_objects

        self.active = child
        self.paused = {1: child.clone()}     # {time: subprocess}
        self.all_breakpoints = AllBreakpoints()
        self.all_printed_objects = {}
        self.all_printed_objects_lst = []

    def get_current_time(self):
        return self.active.current_time

    def get_currently_created_objects(self):
        return self.active.currently_created_objects

    def _check_current_time(self, time):
        assert self.get_current_time() == time
        self.active.send(Message(CMD_FORWARD, 0))
        return self.active.expect(ANSWER_READY, time, Ellipsis)

    def get_max_time(self):
        return self.total_stop_points

    def get_next_clone_time(self):
        # if 'active' has more printed_objects than the next process
        # already in 'paused', then we re-clone 'active'.
        cur_time = self.get_current_time()
        future = [time for time in self.paused if time > cur_time]
        if future:
            for futime in sorted(future):
                if (self.paused[futime].printed_objects !=
                        frozenset(self.all_printed_objects_lst)):
                    # 'futime' is the time of the first "future" childs
                    # with an incomplete 'printed_objects'.  This will
                    # be re-cloned.
                    return futime
        #
        if len(self.paused) >= self.MAX_SUBPROCESSES:
            next_time = self.total_stop_points + 1
        else:
            latest_done = max(self.paused)
            range_not_done = self.total_stop_points - latest_done
            next_time = latest_done + int(self.STEP_RATIO * range_not_done) + 1
        return next_time

    def is_tainted(self):
        return self.active.tainted

    def go_forward(self, steps, breakpoint_mode='b'):
        """Go forward, for the given number of 'steps' of time.

        If needed, it will leave clones at intermediate times.
        Does not close the active subprocess.  Note that
        is_tainted() must return false in order to use this.

        breakpoint_mode:
          'b' = regular mode where hitting a breakpoint stops
          'i' = ignore breakpoints
          'r' = record the occurrence of a breakpoint but continue
        """
        assert steps >= 0
        if breakpoint_mode != 'i':
            self.update_breakpoints()
        latest_bkpt = None
        while True:
            cur_time = self.get_current_time()
            if cur_time + steps > self.total_stop_points:
                steps = self.total_stop_points - cur_time
            next_clone = self.get_next_clone_time()
            rel_next_clone = next_clone - cur_time
            if rel_next_clone > steps:
                break
            assert rel_next_clone >= 0
            if rel_next_clone > 0:
                bkpt = self.active.forward(rel_next_clone, breakpoint_mode)
                if breakpoint_mode == 'r':
                    latest_bkpt = bkpt or latest_bkpt
                elif bkpt:
                    raise bkpt
                steps -= rel_next_clone
            if self.active.current_time in self.paused:
                self.paused[self.active.current_time].close()
            clone = self.active.clone()
            self.paused[clone.current_time] = clone
        bkpt = self.active.forward(steps, breakpoint_mode)
        if breakpoint_mode == 'r':
            bkpt = bkpt or latest_bkpt
        if bkpt:
            raise bkpt

    def go_backward(self, steps, ignore_breakpoints=False):
        """Go backward, for the given number of 'steps' of time.

        Closes the active process.  Implemented as jump_in_time()
        and then forward-searching for breakpoint locations (if any).
        """
        assert steps >= 0
        initial_time = self.get_current_time()
        if self.all_breakpoints.is_empty() or ignore_breakpoints:
            self.jump_in_time(initial_time - steps)
        else:
            if self.all_breakpoints.watchvalues:
                first_steps = 97    # use smaller steps, because that's costly
            else:
                first_steps = 957
            self._backward_search_forward(
                search_start_time       = initial_time - first_steps,
                search_stop_time        = initial_time,
                search_go_on_until_time = initial_time - steps)

    def _backward_search_forward(self, search_start_time, search_stop_time,
                                 search_go_on_until_time=1):
        while True:
            self.jump_in_time(max(search_start_time, search_go_on_until_time))
            search_start_time = self.get_current_time()
            time_range_to_search = search_stop_time - search_start_time
            if time_range_to_search <= 0:
                print "[search end]"
                return
            print "[searching %d..%d]" % (search_start_time,
                                          search_stop_time)
            self.go_forward(time_range_to_search, breakpoint_mode='r')
            # If at least one breakpoint was found, the Breakpoint
            # exception is raised with the *last* such breakpoint.
            # Otherwise, we continue here.  Search farther along a
            # 3-times-bigger range.
            search_stop_time = search_start_time
            search_start_time -= time_range_to_search * 3

    def _update_watchpoints_uids(self):
        if self.all_breakpoints.watchuids:
            uids = set()
            uids.update(*self.all_breakpoints.watchuids.values())
            #print self.all_breakpoints
            #print '\t===>', uids
            self.attach_printed_objects(uids, watch_env=True)

    def update_breakpoints(self):
        self._update_watchpoints_uids()
        cmp = self.all_breakpoints.compare(self.active.breakpoints_cache)
        #print 'compare:', cmp, self.all_breakpoints.watchvalues
        if cmp == 2:
            return      # up-to-date

        # update the breakpoints/watchpoints
        self.active.breakpoints_cache = None
        num2break = self.all_breakpoints.num2break
        N = (max(num2break) + 1) if num2break else 0
        if cmp == 0:
            flat = [num2break.get(n, '\x00') for n in range(N)]
            arg1 = self.all_breakpoints.stack_id
            extra = ''.join(flat)
            self.active.send(Message(CMD_BREAKPOINTS, arg1, extra=extra))
            self.active.expect_ready()
        else:
            assert cmp == 1

        # update the watchpoint values
        if any(name.startswith('W') for name in num2break.values()):
            watchvalues = self.all_breakpoints.watchvalues
            flat = []
            for n in range(N):
                text = ''
                name = num2break.get(n, '')
                if name.startswith('W'):
                    text = watchvalues[n]
                flat.append(text)
            extra = '\x00'.join(flat)
            self.active.send(Message(CMD_WATCHVALUES, extra=extra))
            self.active.expect_ready()

        self.active.breakpoints_cache = self.all_breakpoints.duplicate()

    def update_watch_values(self):
        try:
            self._update_watchpoints_uids()
        except socket.error as e:
            print >> sys.stderr, "socket.error: %s" % (e,)
            print >> sys.stderr, "restarting at position 1"
            self.jump_in_time(1)
            self._update_watchpoints_uids()
        seen = set()
        for num, name in self.all_breakpoints.num2break.items():
            if name.startswith('W'):
                _, text = self.check_watchpoint_expr(name[4:])
                if text != self.all_breakpoints.watchvalues[num]:
                    #print self.active.pid
                    print 'updating watchpoint value: %s => %s' % (
                        self.all_breakpoints.sources[num], text)
                    self.all_breakpoints.watchvalues[num] = text
                seen.add(num)
        assert set(self.all_breakpoints.watchvalues) == seen

    def compile_watchpoint_expr(self, expr):
        self.active.send(Message(CMD_COMPILEWATCH, extra=expr))
        msg = self.active.expect(ANSWER_WATCH, Ellipsis, extra=Ellipsis)
        self.active.expect_ready()
        return msg.arg1, msg.extra

    def check_watchpoint_expr(self, compiled_code, nids=None):
        if nids:
            uids = self.nids_to_uids(nids)
            self.attach_printed_objects(uids, watch_env=True)
        self.active.send(Message(CMD_CHECKWATCH, extra=compiled_code))
        msg = self.active.expect(ANSWER_WATCH, Ellipsis, extra=Ellipsis)
        self.active.expect_ready()
        return msg.arg1, msg.extra

    def _resume(self, from_time):
        clone_me = self.paused[from_time]
        if self.active is not None:
            self.active.close()
        self.active = clone_me.clone()

    def jump_in_time(self, target_time):
        """Jump in time at the given 'target_time'.

        This function always closes the active subprocess.
        """
        if target_time < 1:
            target_time = 1
        if target_time > self.total_stop_points:
            target_time = self.total_stop_points
        uids = set()
        uids.update(*self.all_breakpoints.watchuids.values())
        self.ensure_printed_objects(uids, forced_time = target_time)

    def close(self):
        """Close all subprocesses.
        """
        for subp in [self.active] + self.paused.values():
            subp.close()

    def ensure_printed_objects(self, uids, forced_time=None):
        """Ensure that all the given unique_ids are loaded in the active
        child, if necessary by forking another child from earlier.
        """
        if forced_time is None:
            initial_time = self.get_current_time()
            child = self.active
        else:
            initial_time = forced_time
            stop_time = max(time for time in self.paused
                                 if time <= initial_time)
            child = self.paused[stop_time]

        while True:
            uid_limit = child.currently_created_objects
            missing_uids = [uid for uid in uids
                                if uid < uid_limit
                                   and uid not in child.printed_objects]
            if not missing_uids:
                break
            # pick the earlier fork
            start_time = child.current_time
            stop_time = max(time for time in self.paused if time < start_time)
            child = self.paused[stop_time]

        # No missing_uids left: all uids are either already in
        # self.active.printed_objects, or in the future.
        future_uids = [uid for uid in uids if uid >= uid_limit]
        if child is self.active:
            assert not future_uids
        else:
            self._resume(stop_time)
            if future_uids:
                future_uids.sort()
                pack_uids = [struct.pack('q', uid) for uid in future_uids]
                pack_uids = ''.join(pack_uids)
                #print '%d: from %d: CMD_FUTUREIDS %r' % (
                #    self.active.pid,
                #    self.active.current_time,
                #    future_uids)
                self.active.send(Message(CMD_FUTUREIDS, extra=pack_uids))
                self.active.expect_ready()
                self.active.printed_objects = (
                    self.active.printed_objects.union(future_uids))
            self.go_forward(initial_time - self.get_current_time(),
                            breakpoint_mode='i')
        assert self.active.printed_objects.issuperset(uids)

    def nids_to_uids(self, nids, skip_futures=False):
        uids = []
        for nid in set(nids):
            try:
                uid = self.all_printed_objects_lst[nid]
            except IndexError:
                continue
            if skip_futures and uid >= self.get_currently_created_objects():
                #print >> sys.stderr, (
                #    "note: '$%d' refers to an object that is "
                #    "only created later in time" % nid)
                continue
            uids.append(uid)
        return uids

    def attach_printed_objects(self, uids, watch_env):
        for uid in uids:
            nid = self.all_printed_objects[uid]
            #print '%d: %s => %s (watch_env=%d)' % (self.active.pid, nid, uid,
            #                                       watch_env)
            self.active.send(Message(CMD_ATTACHID, nid, uid, int(watch_env)))
            self.active.expect_ready()

    def recreate_subprocess(self):
        # recreate a subprocess at the current time
        time = self.get_current_time()
        self.active = None
        self.jump_in_time(time)

    def print_cmd(self, expression, nids=[]):
        """Print an expression.
        """
        uids = []
        if nids:
            uids = self.nids_to_uids(nids, skip_futures=True)
            self.ensure_printed_objects(uids)
        #
        self.active.tainted = True
        self.attach_printed_objects(uids, watch_env=False)
        self.active.send(Message(CMD_PRINT, extra=expression))
        try:
            self.active.print_text_answer(pgroup=self)
        except RecreateSubprocess:
            self.recreate_subprocess()

    def show_backtrace(self, complete=1):
        """Show the backtrace.
        """
        if complete:
            self.active.tainted = True
        self.active.send(Message(CMD_BACKTRACE, complete))
        try:
            self.active.print_text_answer()
        except RecreateSubprocess:
            self.recreate_subprocess()

    def show_locals(self):
        """Show the locals.
        """
        self.active.tainted = True
        self.active.send(Message(CMD_LOCALS))
        try:
            self.active.print_text_answer()
        except RecreateSubprocess:
            self.recreate_subprocess()

    def edit_breakpoints(self):
        return self.all_breakpoints

    def _stack_id(self, is_parent=0):
        self.active.send(Message(CMD_STACKID, is_parent))
        msg = self.active.expect(ANSWER_STACKID, Ellipsis, Ellipsis)
        self.active.expect_ready()
        return msg

    def get_stack_id(self, is_parent):
        return self._stack_id(is_parent).arg1

    def get_hiddenpos_level(self):
        return self._stack_id().arg2

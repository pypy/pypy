import sys, os, re
import subprocess, socket
import traceback
from contextlib import contextmanager

from rpython.translator.revdb.process import ReplayProcessGroup, maxint64
from rpython.translator.revdb.process import Breakpoint

r_cmdline = re.compile(r"(\S+)\s*(.*)")
r_dollar_num = re.compile(r"\$(\d+)\b")


class RevDebugControl(object):

    def __init__(self, revdb_log_filename, executable=None):
        with open(revdb_log_filename, 'rb') as f:
            header = f.readline()
        assert header.endswith('\n')
        fields = header[:-1].split('\t')
        if len(fields) < 2 or fields[0] != 'RevDB:':
            raise ValueError("file %r is not a RevDB log" % (
                revdb_log_filename,))
        if executable is None:
            executable = fields[1]
        if not os.path.isfile(executable):
            raise ValueError("executable %r not found" % (executable,))
        self.pgroup = ReplayProcessGroup(executable, revdb_log_filename)
        self.print_extra_pending_info = None

    def interact(self):
        last_command = 'help'
        previous_time = None
        while True:
            last_time = self.pgroup.get_current_time()
            if last_time != previous_time:
                print
                self.pgroup.update_watch_values()
            if self.print_extra_pending_info:
                print self.print_extra_pending_info
                self.print_extra_pending_info = None
            if last_time != previous_time:
                self.pgroup.show_backtrace(complete=0)
                previous_time = last_time
            prompt = '(%d)$ ' % last_time
            sys.stdout.write(prompt)
            sys.stdout.flush()
            try:
                cmdline = raw_input().strip()
            except EOFError:
                print
                cmdline = 'quit'
            if not cmdline:
                cmdline = last_command
            match = r_cmdline.match(cmdline)
            if not match:
                continue
            last_command = cmdline
            command, argument = match.groups()
            try:
                runner = getattr(self, 'command_' + command)
            except AttributeError:
                print >> sys.stderr, "no command '%s', try 'help'" % (command,)
            else:
                try:
                    runner(argument)
                except Exception as e:
                    traceback.print_exc()

    def command_help(self, argument):
        """Display commands summary"""
        print 'Available commands:'
        lst = dir(self)
        commands = [(name[len('command_'):], getattr(self, name))
                    for name in lst
                        if name.startswith('command_')]
        seen = {}
        for name, func in commands:
            seen.setdefault(func, []).append(name)
        for _, func in commands:
            if func in seen:
                names = seen.pop(func)
                names.sort(key=len, reverse=True)
                docstring = func.__doc__ or 'undocumented'
                print '\t%-16s %s' % (', '.join(names), docstring)

    def command_quit(self, argument):
        """Exit the debugger"""
        self.pgroup.close()
        sys.exit(0)
    command_q = command_quit

    def command_go(self, argument):
        """Jump to time ARG"""
        arg = int(argument or self.pgroup.get_current_time())
        self.pgroup.jump_in_time(arg)

    def command_info(self, argument):
        """Display various info ('info help' for more)"""
        display = getattr(self, 'cmd_info_' + argument, self.cmd_info_help)
        return display()

    def cmd_info_help(self):
        """Display info topics summary"""
        print 'Available info topics:'
        for name in dir(self):
            if name.startswith('cmd_info_'):
                command = name[len('cmd_info_'):]
                docstring = getattr(self, name).__doc__ or 'undocumented'
                print '\tinfo %-12s %s' % (command, docstring)

    def cmd_info_paused(self):
        """List current paused subprocesses"""
        lst = [str(n) for n in sorted(self.pgroup.paused)]
        print ', '.join(lst)

    def _bp_kind(self, name):
        if name[0] == 'B':
            return 'breakpoint'
        elif name[0] == 'W':
            return 'watchpoint'
        else:
            return '?????point'

    def _bp_new(self, break_at, nids=None):
        b = self.pgroup.edit_breakpoints()
        new = 1
        while new in b.num2name:
            new += 1
        b.num2name[new] = break_at
        if break_at.startswith('W'):
            b.watchvalues[new] = ''
            if nids:
                b.watchuids[new] = self.pgroup.nids_to_uids(nids)
        print "%s %d added" % (self._bp_kind(break_at).capitalize(), new)

    def cmd_info_breakpoints(self):
        """List current breakpoints and watchpoints"""
        lst = self.pgroup.all_breakpoints.num2name.items()
        if lst:
            for num, name in sorted(lst):
                print '\t%s %d: %s' % (self._bp_kind(name), num, name[1:])
        else:
            print 'no breakpoints.'
    cmd_info_watchpoints = cmd_info_breakpoints

    def move_forward(self, steps):
        self.remove_tainting()
        try:
            self.pgroup.go_forward(steps)
            return True
        except Breakpoint as b:
            self.hit_breakpoint(b)
            return False

    def move_backward(self, steps):
        try:
            self.pgroup.go_backward(steps, ignore_breakpoints=(steps==1))
            return True
        except Breakpoint as b:
            self.hit_breakpoint(b, backward=True)
            return False

    def hit_breakpoint(self, b, backward=False):
        if b.num != -1:
            name = self.pgroup.all_breakpoints.num2name.get(b.num, '??')
            kind = self._bp_kind(name)
            self.print_extra_pending_info = 'Hit %s %d: %s' % (kind, b.num,
                                                               name[1:])
        elif backward:
            b.time -= 1
        if self.pgroup.get_current_time() != b.time:
            self.pgroup.jump_in_time(b.time)

    def remove_tainting(self):
        if self.pgroup.is_tainted():
            self.pgroup.jump_in_time(self.pgroup.get_current_time())
            assert not self.pgroup.is_tainted()

    def command_step(self, argument):
        """Run forward ARG steps (default 1)"""
        arg = int(argument or '1')
        self.move_forward(arg)
    command_s = command_step

    def command_bstep(self, argument):
        """Run backward ARG steps (default 1)"""
        arg = int(argument or '1')
        self.move_backward(arg)
    command_bs = command_bstep

    @contextmanager
    def _stack_depth_break(self, range_stop):
        # add temporarily a breakpoint for "stack_depth < range_stop"
        b = self.pgroup.edit_breakpoints()
        b.stack_depth = range_stop
        try:
            yield
        finally:
            b.stack_depth = 0

    def command_next(self, argument):
        """Run forward for one step, skipping calls"""
        depth1 = self.pgroup.get_stack_depth()
        if self.move_forward(1):
            depth2 = self.pgroup.get_stack_depth()
            if depth2 > depth1:
                # If, after running one step, the stack depth is greater
                # than before, then continue until it is back to what it was.
                # Can't do it more directly because the "breakpoint" of
                # stack_depth is only checked for on function enters and
                # returns (which simplifies and speeds up things for the
                # RPython code).
                with self._stack_depth_break(depth1 + 1):
                    self.command_continue('')
    command_n = command_next

    def command_bnext(self, argument):
        """Run backward for one step, skipping calls"""
        depth1 = self.pgroup.get_stack_depth()
        if self.move_backward(1):
            depth2 = self.pgroup.get_stack_depth()
            if depth2 > depth1:
                # If, after running one bstep, the stack depth is greater
                # than before, then bcontinue until it is back to what it was.
                with self._stack_depth_break(depth1 + 1):
                    self.command_bcontinue('')
    command_bn = command_bnext

    def command_finish(self, argument):
        """Run forward until the current function finishes"""
        with self._stack_depth_break(self.pgroup.get_stack_depth()):
            self.command_continue('')

    def command_bfinish(self, argument):
        """Run backward until the current function is called"""
        with self._stack_depth_break(self.pgroup.get_stack_depth()):
            self.command_bcontinue('')

    def command_continue(self, argument):
        """Run forward"""
        self.move_forward(self.pgroup.get_max_time() -
                          self.pgroup.get_current_time())
    command_c = command_continue

    def command_bcontinue(self, argument):
        """Run backward"""
        self.move_backward(self.pgroup.get_current_time() - 1)
    command_bc = command_bcontinue

    def command_print(self, argument):
        """Print an expression"""
        # locate which $NUM appear used in the expression
        nids = map(int, r_dollar_num.findall(argument))
        self.pgroup.print_cmd(argument, nids=nids)
    command_p = command_print

    def command_backtrace(self, argument):
        """Show the backtrace"""
        self.pgroup.show_backtrace(complete=1)
    command_bt = command_backtrace

    def command_locals(self, argument):
        """Show the locals"""
        self.pgroup.show_locals()

    def command_break(self, argument):
        """Add a breakpoint"""
        if not argument:
            print "Break where?"
            return
        self._bp_new('B' + argument)
    command_b = command_break

    def command_delete(self, argument):
        """Delete a breakpoint/watchpoint"""
        arg = int(argument)
        b = self.pgroup.edit_breakpoints()
        if arg not in b.num2name:
            print "No breakpoint/watchpoint number %d" % (arg,)
        else:
            name = b.num2name.pop(arg)
            b.watchvalues.pop(arg, '')
            b.watchuids.pop(arg, '')
            kind = self._bp_kind(name)
            print "%s %d deleted: %s" % (kind.capitalize(), arg, name[1:])

    def command_watch(self, argument):
        """Add a watchpoint (use $NUM in the expression to watch)"""
        if not argument:
            print "Watch what?"
            return
        nids = map(int, r_dollar_num.findall(argument))
        ok_flag, text = self.pgroup.check_watchpoint_expr(argument, nids)
        if not ok_flag:
            print text
            print 'Watchpoint not added'
        else:
            self._bp_new('W' + argument, nids=nids)
            self.pgroup.update_watch_values()

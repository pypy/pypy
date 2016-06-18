import sys, re
import subprocess, socket
import traceback
from rpython.translator.revdb.message import *

r_cmdline = re.compile(r"(\S+)\s*(.*)")


class RevDebugControl(object):

    def __init__(self, revdb_log_filename, executable=None):
        with open(revdb_log_filename, 'rb') as f:
            header = f.readline()
        fields = header.split('\t')
        if len(fields) < 2 or fields[0] != 'RevDB:':
            raise ValueError("file %r is not a RevDB log" % (
                revdb_log_filename,))
        if executable is None:
            executable = fields[1]
        #
        s1, s2 = socket.socketpair()
        subproc = subprocess.Popen(
            [executable, '--revdb-replay', revdb_log_filename,
             str(s2.fileno())])
        s2.close()
        self.subproc = subproc
        child = ReplayProcess(subproc.pid, s1)
        msg = child.expect(ANSWER_INIT, INIT_VERSION_NUMBER, Ellipsis)
        self.total_stop_points = msg.arg2
        child.expect(ANSWER_STD, 1, Ellipsis)
        self.active_child = child
        self.paused_children = {}

    def interact(self):
        last_command = ''
        while True:
            prompt = '(%d)$ ' % self.active_child.current_time()
            try:
                cmdline = raw_input(prompt).strip()
            except EOFError:
                print
                cmdline = 'quit'
            if not cmdline:
                cmdline = last_command
            match = r_cmdline.match(cmdline)
            if not match:
                continue
            command, argument = match.groups()
            try:
                runner = getattr(self, 'command_' + command)
            except AttributeError:
                print >> sys.stderr, "no command '%s', try 'help'" % (command,)
            else:
                try:
                    runner(argument)
                except Exception as e:
                    for line in traceback.format_exception_only(type(e), e):
                        sys.stderr.write(line)
                last_command = cmdline

    def command_help(self, argument):
        """Display commands summary"""
        print 'Available commands:'
        for name in dir(self):
            if name.startswith('command_'):
                command = name[len('command_'):]
                docstring = getattr(self, name).__doc__ or 'undocumented'
                print '\t%s\t%s' % (command, docstring)

    def command_quit(self, argument):
        """Exit the reverse debugger"""
        sys.exit(0)

    def command_go(self, argument):
        """Go to time ARG"""
        target_time = int(argument)

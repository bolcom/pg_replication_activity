"""
pg__replication_activity
author: Sebastiaan Mannem <sebas@mannem.nl>
license: PostgreSQL License

Copyright (c) 2012 - 2018, S. Mannem

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose, without fee, and without a written
agreement is hereby granted, provided that the above copyright notice
and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL SEBASTIAAN MANNEM BE LIABLE TO ANY PARTY FOR
DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST
PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION,
EVEN IF SEBASTIAAN MANNEM HAS BEEN ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.

SEBASTIAAN MANNEM SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING,
BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS"
BASIS, AND SEBASTIAAN MANNEM HAS NO OBLIGATIONS TO PROVIDE
MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

from __future__ import print_function

import curses
import time
import sys
import re
from datetime import timedelta
from getpass import getpass
from pgreplicationactivity.Data import Data

# Define some color pairs
C_BLACK_GREEN = 1
C_CYAN = 2
C_RED = 3
C_GREEN = 4
C_YELLOW = 5
C_MAGENTA = 6
C_WHITE = 7
C_BLACK_CYAN = 8
C_RED_BLACK = 9
C_GRAY = 10

# Columns
PGTOP_FLAG_UPSTREAM = 1
PGTOP_FLAG_LAGS = 2
PGTOP_FLAG_ROLE = 4
PGTOP_FLAG_LAGB = 8
PGTOP_FLAG_NONE = None

# Display query mode
PGTOP_TRUNCATE = 1
PGTOP_WRAP_NOINDENT = 2
PGTOP_WRAP = 3

# Maximum number of column
PGTOP_MAX_NCOL = 14

PGTOP_COLS = {
    'lag': {
        'host': {
            'n':  1,
            'name': 'HOST',
            'template_h': '%-25s ',
            'flag': PGTOP_FLAG_NONE,
            'mandatory': True
        },
        'role': {
            'n':  2,
            'name': 'ROLE',
            'template_h': '%-8s ',
            'flag': PGTOP_FLAG_ROLE,
            'mandatory': False
        },
        'upstream': {
            'n':  3,
            'name': 'UPSTREAM',
            'template_h': '%-25s ',
            'flag': PGTOP_FLAG_UPSTREAM,
            'mandatory': False
        },
        'lag_sec': {
            'n':  4,
            'name': 'LAG(s)',
            'template_h': '%10s ',
            'flag': PGTOP_FLAG_LAGS,
            'mandatory': False
        },
        'lag_bytes': {
            'n':  5,
            'name': 'LAG(B)',
            'template_h': '%10s ',
            'flag': PGTOP_FLAG_LAGB,
            'mandatory': False
        }
    }
}

SORT_KEYS = {'u': 'upstream', 'r': 'role', 'm': 'lag_sec', 'w': 'lag_bytes'}


def bytes2human(num):
    """
    Convert a size into a human readable format.
    """
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = {}
    nume = ''
    if num < 0:
        num = num * -1
        nume = '-'
    for pos, sym in enumerate(symbols):
        prefix[sym] = 1 << (pos+1)*10
    for sym in reversed(symbols):
        if num >= prefix[sym]:
            value = "%.2f" % float(float(num) / float(prefix[sym]))
            return "%s%s%s" % (nume, value, sym)
    return "%s%.2fB" % (nume, num)


class UI:
    """
    UI class
    """
    def __init__(self, version):
        """
        Constructor.
        """
        self.version = version
        self.win = None
        self.sys_color = True
        self.lineno = 0
        self.lines = []
        # Maximum number of columns
        self.max_ncol = 13
        # Default
        self.verbose_mode = PGTOP_WRAP_NOINDENT
        # Max IOPS
        self.max_iops = 0
        # Sort
        self.sort = 'u'
        # Color
        self.color = True
        # Default mode : activites, waiting, blocking
        self.mode = 'lag'
        # Does pg_activity is connected to a local PG server ?
        self.is_local = True
        # Start line
        self.start_line = 5
        # Window's size
        self.maxy = 0
        self.maxx = 0
        # Init uibuffer
        self.uibuffer = None
        # Refresh time
        self.refresh_time = 2
        # Maximum DATABASE columns header length
        self.max_db_length = 16
        # Array containing pid of processes to yank
        self.pid_yank = []
        self.pid = []
        # Data collector
        self.data = Data()
        # Maximum number of column
        self.max_ncol = PGTOP_MAX_NCOL
        # Default filesystem blocksize
        self.fs_blocksize = 4096
        # Init curses
        # self.__init_curses()

    def set_is_local(self, is_local):
        """
        Set self.is_local
        """
        self.is_local = is_local

    def get_is_local(self,):
        """
        Get self.is_local
        """
        return self.is_local

    def get_mode(self,):
        """
        Get self.mode
        """
        return self.mode

    def set_start_line(self, start_line):
        """
        Set self.start_line
        """
        self.start_line = start_line

    def set_buffer(self, uibuffer):
        """
        Set self.uibuffer
        """
        self.uibuffer = uibuffer

    def set_blocksize(self, blocksize):
        """
        Set blocksize
        """
        if not isinstance(blocksize, int):
            raise Exception('Unvalid blocksize value.')
        if blocksize != 0 and not (blocksize & (blocksize - 1)) == 0:
            raise Exception('Unvalid blocksize value.')
        if not blocksize > 0:
            raise Exception('Unvalid blocksize value.')
        self.fs_blocksize = int(blocksize)

    def init_curses(self,):
        """
        Initialize curses environment and colors.
        """
        self.__init_curses()
        # Columns colors definition
        self.line_colors = {
            'host': {
                'default': self.__get_color(C_CYAN),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'upstream': {
                'default': curses.A_BOLD | self.__get_color(C_GRAY),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'role': {
                'default': curses.A_BOLD | self.__get_color(C_GRAY),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'lag_sec': {
                'default': self.__get_color(C_CYAN),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'lag_bytes': {
                'default': self.__get_color(0),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'role_yellow': {
                'default': self.__get_color(C_YELLOW),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'role_green': {
                'default': self.__get_color(C_GREEN),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'role_red': {
                'default': self.__get_color(C_RED),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
            'role_default': {
                'default': self.__get_color(0),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            },
        }

    def __init_curses(self,):
        """
        Initialize curses environment.
        """
        curses.setupterm()
        self.win = curses.initscr()
        self.win.keypad(1)
        curses.noecho()
        try:
            # deactivate cursor
            curses.curs_set(0)
            # use colors
            curses.start_color()
            curses.use_default_colors()
        except Exception:
            # Terminal doesn't support curs_set() and colors
            self.sys_color = False
        curses.cbreak()
        curses.endwin()
        self.win.scrollok(0)
        (self.maxy, self.maxx) = self.win.getmaxyx()

    def get_flag_from_options(self, options):
        """
        Returns the flag depending on the options.
        """
        flag = PGTOP_FLAG_UPSTREAM | PGTOP_FLAG_ROLE | PGTOP_FLAG_LAGS | PGTOP_FLAG_LAGB
        if options.nodb is True:
            flag -= PGTOP_FLAG_UPSTREAM
        if options.nouser is True:
            flag -= PGTOP_FLAG_ROLE
        if options.nocpu is True:
            flag -= PGTOP_FLAG_LAGB
        if options.noclient is True:
            flag -= PGTOP_FLAG_LAGS
        return flag

    def __get_color(self, color):
        """
        Wrapper around curses.color_pair()
        """
        if self.sys_color:
            return curses.color_pair(color)
        return 0

    def at_exit_curses(self,):
        """
        Called at exit time.
        Rollback to default values.
        """
        try:
            self.win.keypad(0)
            self.win.move(0, 0)
            self.win.erase()
        except KeyboardInterrupt:
            pass
        except AttributeError:
            # Curses not initialized yet
            return
        curses.nocbreak()
        curses.echo()
        try:
            curses.curs_set(1)
        except Exception:
            pass
        curses.endwin()

    def signal_handler(self, signal, frame):
        """
        Function called on a process kill.
        """
        self.at_exit_curses()
        print("FATAL: Killed with signal %s ." % (str(signal),))
        print("%s" % (str(frame),))
        sys.exit(1)

    def set_nocolor(self,):
        """
        Replace colors by white.
        """
        if not self.sys_color:
            return
        self.color = False
        curses.init_pair(C_BLACK_GREEN, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(C_CYAN, curses.COLOR_WHITE, -1)
        curses.init_pair(C_RED, curses.COLOR_WHITE, -1)
        curses.init_pair(C_RED_BLACK, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(C_GREEN, curses.COLOR_WHITE, -1)
        curses.init_pair(C_YELLOW, curses.COLOR_WHITE, -1)
        curses.init_pair(C_MAGENTA, curses.COLOR_WHITE, -1)
        curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(C_BLACK_CYAN, curses.COLOR_WHITE, -1)
        curses.init_pair(C_GRAY, curses.COLOR_WHITE, -1)

    def set_color(self,):
        """
        Set colors.
        """
        if not self.sys_color:
            return
        self.color = True
        curses.init_pair(C_BLACK_GREEN, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(C_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(C_RED, curses.COLOR_RED, -1)
        curses.init_pair(C_RED_BLACK, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(C_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(C_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(C_MAGENTA, curses.COLOR_MAGENTA, -1)
        curses.init_pair(C_WHITE, curses.COLOR_WHITE, -1)
        curses.init_pair(C_BLACK_CYAN, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(C_GRAY, 0, -1)

    def check_window_size(self,):
        """
        Update window's size
        """
        (self.maxy, self.maxx) = self.win.getmaxyx()
        return

    def __get_pause_msg(self,):
        """
        Returns PAUSE message, depending of the line size
        """
        msg = "PAUSE"
        line = ""
        line += " " * (int(self.maxx/2) - len(msg))
        line += msg
        line += " " * (self.maxx - len(line) - 0)
        return line

    def __pause(self,):
        """
        PAUSE mode
        """
        self.__print_string(
            self.start_line,
            0,
            self.__get_pause_msg(),
            self.__get_color(C_RED_BLACK) | curses.A_REVERSE | curses.A_BOLD)
        while 1:
            try:
                k = self.win.getch()
            except KeyboardInterrupt as err:
                raise err
            if k == ord('q'):
                curses.endwin()
                exit()
            if k == ord(' '):
                curses.flushinp()
                return 0

            if k == curses.KEY_RESIZE:
                if self.uibuffer is not None and 'procs' in self.uibuffer:
                    self.check_window_size()
                    self.refresh_window(
                        self.uibuffer['procs'],
                        self.uibuffer['extras'],
                        self.uibuffer['flag'],
                        self.uibuffer['indent'],
                        self.uibuffer['io'],
                        self.uibuffer['tps'],
                        self.uibuffer['active_connections'],
                        self.uibuffer['size_ev'],
                        self.uibuffer['total_size'])
                    self.__print_string(self.start_line, 0,
                                        self.__get_pause_msg(),
                                        self.__get_color(C_RED_BLACK) |
                                        curses.A_REVERSE | curses.A_BOLD)
            curses.flushinp()

    def __current_position(self,):
        """
        Display current mode
        """
        if self.mode == 'lag':
            msg = "REPLICATION LAG"
        color = self.__get_color(C_GREEN)
        line = ""
        line += " " * (int(self.maxx/2) - len(msg))
        line += msg
        line += " " * (self.maxx - len(line) - 0)
        self.__print_string(self.start_line, 0, line, color | curses.A_BOLD)

    def __help_key_interactive(self,):
        """
        Display interactive mode menu bar
        """
        colno = self.__print_string(
            (self.maxy - 1),
            0,
            "c",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Cancel current query     ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "k",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Terminate the backend    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Space",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Tag/untag the process    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Other",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Back to activity    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "q",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Quit    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            self.__add_blank(" "),
            self.__get_color(C_CYAN) | curses.A_REVERSE)

    def __change_mode_interactive(self,):
        """
        Display change mode menu bar
        """
        colno = self.__print_string(
            (self.maxy - 1),
            0,
            "F1/1",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Running queries    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "F2/2",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Waiting queries    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "F3/3",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Blocking queries ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Space",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Pause    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "q",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Quit    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "h",
            self.__get_color(0))
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            "Help    ",
            self.__get_color(C_CYAN) | curses.A_REVERSE)
        colno += self.__print_string(
            (self.maxy - 1),
            colno,
            self.__add_blank(" "),
            self.__get_color(C_CYAN) | curses.A_REVERSE)

    def __interactive(self, process, flag, indent,):
        """
        Interactive mode trigged on KEY_UP or KEY_DOWN key press
        If no key hit during 3 seconds, exit this mode
        """
        # Force truncated display
        old_verbose_mode = self.verbose_mode
        self.verbose_mode = PGTOP_TRUNCATE

        # Refresh lines with this verbose mode
        self.__scroll_window(process, flag, indent, 0)

        self.__help_key_interactive()

        current_pos = 0
        offset = 0
        self.__refresh_line(process[current_pos], flag, indent, 'cursor',
                            self.lines[current_pos] - offset)
        self.win.timeout(int(1000))
        nb_nk = 0

        while 1:
            known = False
            try:
                k = self.win.getch()
            except KeyboardInterrupt as err:
                raise err
            if k == -1:
                nb_nk += 1
            # quit
            if k == ord('q'):
                curses.endwin()
                exit()
            # Move cursor
            if k == curses.KEY_DOWN or k == curses.KEY_UP:
                nb_nk = 0
                known = True
                if k == curses.KEY_UP and current_pos > 0:
                    if (self.lines[current_pos] - offset) < \
                      (self.start_line + 3):
                        offset -= 1
                        self.__scroll_window(process, flag, indent, offset)
                        self.__help_key_interactive()

                    if current_pos < len(process):
                        self.__refresh_line(
                            process[current_pos],
                            flag,
                            indent,
                            'default',
                            self.lines[current_pos] - offset)
                    current_pos -= 1
                if k == curses.KEY_DOWN and current_pos < (len(process) - 1):
                    if (self.lines[current_pos] - offset) >= (self.maxy - 2):
                        offset += 1
                        self.__scroll_window(process, flag, indent, offset)
                        self.__help_key_interactive()

                    if current_pos >= 0:
                        self.__refresh_line(
                            process[current_pos],
                            flag,
                            indent,
                            'default',
                            self.lines[current_pos] - offset)
                    current_pos += 1
                self.__refresh_line(
                    process[current_pos],
                    flag,
                    indent,
                    'cursor',
                    self.lines[current_pos] - offset)
                curses.flushinp()
                continue
            if k == ord(' '):
                known = True

                self.__refresh_line(
                    process[current_pos],
                    flag,
                    indent,
                    'default',
                    self.lines[current_pos] - offset)

                if current_pos < (len(process) - 1):
                    current_pos += 1
                    if (self.lines[current_pos] - offset) >= (self.maxy - 1):
                        offset += 1
                        self.__scroll_window(process, flag, indent, offset)
                        self.__help_key_interactive()
                self.__refresh_line(
                    process[current_pos],
                    flag,
                    indent,
                    'cursor',
                    self.lines[current_pos] - offset)
            # Quit interactive mode
            if (k != -1 and not known) or k == curses.KEY_RESIZE:
                self.verbose_mode = old_verbose_mode
                curses.flushinp()
                return 0
            curses.flushinp()
            if nb_nk > 3:
                self.verbose_mode = old_verbose_mode
                return 0

    def poll(self, interval, flag, indent, process=None, disp_proc=None):
        """
        Poll activities.
        """
        # Keyboard interactions
        self.win.timeout(int(1000 * self.refresh_time * interval))
        t_start = time.time()
        known = False
        do_refresh = False
        try:
            key = self.win.getch()
        except KeyboardInterrupt as err:
            raise err
        if key == ord('q'):
            curses.endwin()
            exit()
        # PAUSE mode
        if key == ord(' '):
            self.__pause()
            do_refresh = True
        # interactive mode
        if (key == curses.KEY_DOWN or key == curses.KEY_UP) and disp_proc:
            self.__interactive(disp_proc, flag, indent)
            known = False
            do_refresh = True
        # change verbosity
        if key == ord('v'):
            self.verbose_mode += 1
            if self.verbose_mode > 3:
                self.verbose_mode = 1
            do_refresh = True
        # turn off/on colors
        if key == ord('C'):
            if self.color is True:
                self.set_nocolor()
            else:
                self.set_color()
            do_refresh = True
        # sorts
        if key == ord('c') and (flag & PGTOP_FLAG_LAGB) and self.sort != 'c':
            self.sort = 'c'
            known = True
        if key == ord('u') and self.sort != 'u':
            self.sort = 'u'
            known = True
        if key == ord('+') and self.refresh_time < 3:
            self.refresh_time += 1
            do_refresh = True
        if key == ord('-') and self.refresh_time > 1:
            self.refresh_time -= 1
            do_refresh = True
        # Refresh
        if key == ord('R'):
            known = True

        if key == ord('h'):
            self.__help_window()
            do_refresh = True

        if key == curses.KEY_RESIZE and \
           self.uibuffer is not None and 'procs' in self.uibuffer:
            do_refresh = True

        if do_refresh is True and self.uibuffer is not None and \
           isinstance(self.uibuffer, dict) and 'procs' in self.uibuffer:
            self.check_window_size()
            self.refresh_window(
                self.uibuffer['procs'],
                self.uibuffer['extras'],
                self.uibuffer['flag'],
                self.uibuffer['indent'],
                self.uibuffer['io'],
                self.uibuffer['tps'],
                self.uibuffer['active_connections'],
                self.uibuffer['size_ev'],
                self.uibuffer['total_size'])

        curses.flushinp()
        t_end = time.time()
        if key > -1 and not known and (t_end - t_start) < \
                                      (self.refresh_time * interval):
            return self.poll(
                ((self.refresh_time * interval) -
                 (t_end - t_start))/self.refresh_time,
                flag,
                indent,
                process,
                disp_proc)

        # poll postgresql activity
        lag_info = self.data.pg_get_lag_info()

        # return processes sorted by query duration
        try:
            sort_key = SORT_KEYS[self.sort]
        except KeyError:
            sort_key = 'host'

        lag_info = sorted(lag_info, key=lambda p: p[sort_key])

        return (lag_info, None)

    def __print_string(self, lineno, colno, word, color=0):
        """
        Print a string at position (lineno, colno) and returns its length.
        """
        try:
            self.win.addstr(lineno, colno, word, color)
        except curses.error:
            pass
        return len(word)

    def __add_blank(self, line, offset=0):
        """
        Complete string with white spaces from end of string to end of line.
        """
        line += " " * (self.maxx - (len(line) + offset))
        return line

    def get_indent(self, flag):
        """
        Returns identation for Query column.
        """
        indent = ''
        cols = [{}] * self.max_ncol
        for _, mode in PGTOP_COLS[self.mode].items():
            if mode['mandatory'] or (mode['flag'] & flag):
                cols[int(mode['n'])] = mode
        for col in cols:
            try:
                if col['name'] != 'Query':
                    indent += col['template_h'] % ' '
            except KeyError:
                pass
        return indent

    def __print_cols_header(self, flag):
        """
        Print columns headers
        """
        line = ''
        disp = ''
        xpos = 0
        res = [{}] * self.max_ncol
        color = self.__get_color(C_GREEN)
        for _, val in PGTOP_COLS[self.mode].items():
            if val['mandatory'] or (val['flag'] & flag):
                res[int(val['n'])] = val
        for val in res:
            if 'name' in val:
                disp = val['template_h'] % val['name']
                if self.sort == val['name'][0].lower() and val['name'] in \
                   ["CPU%", "MEM%", "READ/s", "WRITE/s", "TIME+"]:
                    color_highlight = self.__get_color(C_CYAN)
                else:
                    color_highlight = color
                if val['name'] == "Query":
                    disp += " " * (self.maxx - (len(line) + len(disp)))
                line += disp
                self.__print_string(
                    self.lineno,
                    xpos,
                    disp,
                    color_highlight | curses.A_REVERSE)
                xpos += len(disp)
        self.lineno += 1

    def __print_header(self, pg_version, hostname, user, host, port, database,
                       ios, tps, active_connections, size_ev, total_size):
        """
        Print window header
        """
        self.lineno = 0
        colno = 0
        version = " %s" % (pg_version)
        colno = self.__print_string(self.lineno, colno, version)
        colno += self.__print_string(self.lineno, colno, " - ")
        colno += self.__print_string(self.lineno, colno, hostname,
                                     curses.A_BOLD)
        colno += self.__print_string(self.lineno, colno, " - ")
        colno += self.__print_string(self.lineno, colno, user,
                                     self.__get_color(C_CYAN))
        colno += self.__print_string(self.lineno, colno, "@")
        colno += self.__print_string(self.lineno, colno, host,
                                     self.__get_color(C_CYAN))
        colno += self.__print_string(self.lineno, colno, ":")
        colno += self.__print_string(self.lineno, colno, port,
                                     self.__get_color(C_CYAN))
        colno += self.__print_string(self.lineno, colno, "/")
        colno += self.__print_string(self.lineno, colno, database,
                                     self.__get_color(C_CYAN))
        colno += self.__print_string(self.lineno, colno,
                                     " - Ref.: %ss" % (self.refresh_time,))
        colno = 0
        self.lineno += 1
        colno += self.__print_string(self.lineno, colno, "  Size: ")
        colno += self.__print_string(self.lineno, colno,
                                     "%8s" % (bytes2human(total_size),),)
        colno += self.__print_string(self.lineno, colno,
                                     " - %9s/s" % (bytes2human(size_ev),),)
        colno += self.__print_string(self.lineno, colno, "        | TPS: ")
        colno += self.__print_string(self.lineno, colno, "%11s" % (tps,),
                                     self.__get_color(C_GREEN) | curses.A_BOLD)
        colno += self.__print_string(self.lineno, colno,
                                     "        | Active Connections: ")
        colno += self.__print_string(self.lineno, colno,
                                     "%11s" % (active_connections,),
                                     self.__get_color(C_GREEN) | curses.A_BOLD)

        # If not local connection, don't get and display system informations
        if not self.is_local:
            return

        self.lineno += 1
        line = "  Mem.: %6s0%% - %9s/%-8s" % \
            (100, bytes2human(14), bytes2human(180))
        colno_io = self.__print_string(self.lineno, 0, line)

        if (int(ios['read_count'])+int(ios['write_count'])) > self.max_iops:
            self.max_iops = (int(ios['read_count'])+int(ios['write_count']))

        line_io = " | IO Max: %8s/s" % (self.max_iops,)
        colno = self.__print_string(self.lineno, colno_io, line_io)

        # swap usage
        line = "  Swap: %6s0%% - %9s/%-8s" % \
            (1000, bytes2human(100), bytes2human(2000))
        self.lineno += 1
        colno = self.__print_string(self.lineno, 0, line)
        line_io = " | Read : %10s/s - %6s/s" % \
            (bytes2human(ios['read_bytes']), int(ios['read_count']),)
        colno = self.__print_string(self.lineno, colno_io, line_io)

        # load average, uptime
        line = "  Load:    %.2f %.2f %.2f" % (1, 2, 3)
        self.lineno += 1
        colno = self.__print_string(self.lineno, 0, line)
        line_io = " | Write: %10s/s - %6s/s" % \
            (bytes2human(ios['write_bytes']), int(ios['write_count']),)
        colno = self.__print_string(self.lineno, colno_io, line_io)

    def __help_window(self,):
        """
        Display help window
        """
        self.win.erase()
        self.lineno = 0
        text = "pg_activity %s - (c) 2018 Sebastiaan Mannem" % \
            (self.version)
        self.__print_string(self.lineno, 0, text,
                            self.__get_color(C_GREEN) | curses.A_BOLD)
        self.lineno += 1
        text = "Released under PostgreSQL License."
        self.__print_string(self.lineno, 0, text)
        self.lineno += 2
        self.__display_help_key(self.lineno, 0, "Up/Down",
                                "scroll process list")
        self.__display_help_key(self.lineno, 45, "      C",
                                "activate/deactivate colors")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "  Space", "pause")
        self.__display_help_key(self.lineno, 45, "      r",
                                "sort by READ/s desc. (activities)")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "      v",
                                "change display mode")
        self.__display_help_key(self.lineno, 45, "      w",
                                "sort by WRITE/s desc. (activities)")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "      q", "quit")
        self.__display_help_key(self.lineno, 45, "      c",
                                "sort by CPU% desc. (activities)")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "      +",
                                "increase refresh time (max:3)")
        self.__display_help_key(self.lineno, 45, "      m",
                                "sort by MEM% desc. (activities)")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "      -",
                                "decrease refresh time (min:1)")
        self.__display_help_key(self.lineno, 45, "      u",
                                "sort by UPSTREAM desc. (activities)")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "      R", "force refresh")
        self.lineno += 1
        self.__print_string(self.lineno, 0, "Mode")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "   F1/1", "running queries")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "   F2/2", "waiting queries")
        self.lineno += 1
        self.__display_help_key(self.lineno, 0, "   F3/3", "blocking queries")

        self.lineno += 2
        self.__print_string(self.lineno, 0, "Press any key to exit.")
        self.win.timeout(-1)
        try:
            self.win.getch()
        except KeyboardInterrupt as err:
            raise err

    def __display_help_key(self, lineno, colno, key, help_msg):
        """
        Display help key
        """
        pos1 = self.__print_string(lineno, colno, key,
                                   self.__get_color(C_CYAN) | curses.A_BOLD)
        pos2 = self.__print_string(lineno, colno + pos1, ": %s" % (help_msg,))
        return colno + pos1 + pos2

    def refresh_window(self, procs, extras, flag, indent, ios, tps,
                       active_connections, size_ev, total_size):
        """
        Refresh the window
        """

        self.lines = []
        (pg_version, hostname, user, host, port, dbname) = extras
        self.win.erase()
        self.__print_header(
            pg_version,
            hostname,
            user,
            host,
            port,
            dbname,
            ios,
            tps,
            active_connections,
            size_ev,
            total_size)
        self.lineno += 2
        line_trunc = self.lineno
        self.__current_position()
        self.__print_cols_header(flag)
        for proc in procs:
            try:
                self.__refresh_line(proc, flag, indent, 'default')
                line_trunc += 1
                self.lines.append(line_trunc)
            except curses.error:
                break
        for line in range(self.lineno, (self.maxy-1)):
            self.__print_string(line, 0, self.__add_blank(" "))
        self.__change_mode_interactive()

    def __scroll_window(self, procs, flag, indent, offset=0):
        """
        Scroll the window
        """
        self.lineno = (self.start_line + 2)
        pos = 0
        for proc in procs:
            if pos >= offset and self.lineno < (self.maxy - 1):
                self.__refresh_line(proc, flag, indent, 'default')
            pos += 1
        for line in range(self.lineno, (self.maxy-1)):
            self.__print_string(line, 0, self.__add_blank(" "))

    def __refresh_line(self, process, flag, indent, typecolor='default',
                       line=None):
        """
        Refresh a line for activities mode
        """
        if line is not None:
            l_lineno = line
        else:
            l_lineno = self.lineno

        colno = 0
        word = PGTOP_COLS[self.mode]['host']['template_h'] % (process['host'],)
        colno += self.__print_string(l_lineno, colno, word,
                                     self.line_colors['host'][typecolor])
        cols = []
        if self.mode == 'lag':
            if flag & PGTOP_FLAG_ROLE:
                if process['role'] == 'master':
                    color_role = 'role_green'
                elif process['role'] == 'standby':
                    color_role = 'role_yellow'
                else:
                    color_role = 'role_default'

                word = PGTOP_COLS[self.mode]['role']['template_h'] % \
                    process['role']
                color = self.line_colors[color_role][typecolor]
                colno += self.__print_string(l_lineno, colno, word, color)
            if flag & PGTOP_FLAG_UPSTREAM:
                cols.append('upstream')
            if flag & PGTOP_FLAG_LAGS:
                cols.append('lag_sec')
            if flag & PGTOP_FLAG_LAGB:
                cols.append('lag_bytes')
            for col in cols:
                word = PGTOP_COLS[self.mode][col]['template_h'] % \
                       (str(process[col])[:16],)
                color = self.line_colors[col][typecolor]
                colno += self.__print_string(l_lineno, colno, word, color)
        self.lineno += 1


def ask_password():
    """
    Ask for PostgreSQL user password
    """
    password = getpass()
    return password


def clean_str(string):
    """
    Strip and replace some special characters.
    """
    msg = str(string)
    msg = msg.replace("\n", " ")
    msg = re.sub(r"\s+", r" ", msg)
    msg = msg.replace("FATAL:", "")
    msg = re.sub(r"^\s", r"", msg)
    msg = re.sub(r"\s$", r"", msg)
    return msg

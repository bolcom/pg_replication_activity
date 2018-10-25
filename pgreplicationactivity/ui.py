"""
This module handles all ui functionality.

module: pgreplicationactivity
submodule: ui
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

import curses
import time
import sys
import re
from getpass import getpass
import yaml

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

# Maximum number of column
PGTOP_MAX_NCOL = 14

PGTOP_COLS = yaml.load(open('pgreplicationactivity/cols.yaml'))
PGTOP_FLAGS = yaml.load(open('pgreplicationactivity/flags.yaml'))


def get_coldef_by_name(chapter, name):
    """Get the definition of a column by its name."""
    for coldef in PGTOP_COLS[chapter]:
        if coldef['name'] == name:
            return coldef
    return None


SORT_KEYS = {'u': 'upstream', 's': 'slot', 'r': 'role', 'm': 'lag_sec',
             'w': 'lag_mb', 'l': 'lsn'}


def bytes2human(num):
    """Convert a size into a human readable format."""
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
    """UI class for handling all UI operations."""

    def __init__(self):
        """Constructor."""
        self.win = None
        self.sys_color = True
        self.lineno = 0
        self.lines = []
        self.line_colors = None
        # Sort
        self.sort = 'u'
        # Color
        self.color = True
        # Default mode : activites, waiting, blocking
        self.mode = 'lag'
        # Start line
        self.start_line = 5
        # Window's size
        self.maxy = 0
        self.maxx = 0
        # Init uibuffer
        self.uibuffer = None
        # Refresh time
        self.refresh_time = 2
        # Data collector
        self.data = None
        # Maximum number of column
        self.max_ncol = PGTOP_MAX_NCOL
        # Init curses
        # self.__init_curses()

    def get_mode(self,):
        """Get self.mode."""
        return self.mode

    def set_start_line(self, start_line):
        """Set self.start_line."""
        self.start_line = start_line

    def set_buffer(self, uibuffer):
        """Set self.uibuffer."""
        self.uibuffer = uibuffer

    def init_curses(self,):
        """Initialize curses environment and colors."""
        self.__init_curses()
        # Columns colors definition

        self.line_colors = {}
        for coldef in PGTOP_COLS['lag']:
            self.line_colors[coldef['name']] = {
                'default': self.__get_color(C_CYAN),
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            }
        for colname in ['yellow', 'green', 'red', 'default']:
            self.line_colors['role_'+colname] = {
                'cursor':  self.__get_color(C_CYAN) | curses.A_REVERSE,
                'yellow':  self.__get_color(C_YELLOW) | curses.A_BOLD
            }
        self.line_colors['role_yellow']['default'] = self.__get_color(C_YELLOW)
        self.line_colors['role_green']['default'] = self.__get_color(C_GREEN)
        self.line_colors['role_red']['default'] = self.__get_color(C_RED)
        self.line_colors['role_default']['default'] = self.__get_color(0)

    def __init_curses(self,):
        """Initialize curses environment."""
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
        except curses.error:
            # Terminal doesn't support curs_set() and colors
            self.sys_color = False
        curses.cbreak()
        curses.endwin()
        self.win.scrollok(0)
        (self.maxy, self.maxx) = self.win.getmaxyx()

    def __get_color(self, color):
        """
        Get the collor info of a specific collor.

        This is merely a wrapper around curses.color_pair().
        """
        if self.sys_color:
            return curses.color_pair(color)
        return 0

    def at_exit_curses(self,):
        """
        Cleanup at exit of curses.

        This is called at exit time.
        This method will rollback to default values.
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
        except curses.error:
            pass
        curses.endwin()

    def signal_handler(self, signal, frame):
        """
        Process a received signal.

        This function is called on a process kill.
        """
        self.at_exit_curses()
        print("FATAL: Killed with signal %s ." % (str(signal),))
        print("%s" % (str(frame),))
        sys.exit(1)

    def set_nocolor(self,):
        """Replace colors by white."""
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
        """Set colors."""
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
        """Update window's size."""
        (self.maxy, self.maxx) = self.win.getmaxyx()

    def __get_pause_msg(self,):
        """Return PAUSE message, depending of the line size."""
        msg = "PAUSE"
        line = ""
        line += " " * (int(self.maxx/2) - len(msg))
        line += msg
        line += " " * (self.maxx - len(line) - 0)
        return line

    def __pause(self,):
        """Pause the UI refresh."""
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
                    self.refresh_window()
                    self.__print_string(self.start_line, 0,
                                        self.__get_pause_msg(),
                                        self.__get_color(C_RED_BLACK) |
                                        curses.A_REVERSE | curses.A_BOLD)
            curses.flushinp()

    def __current_position(self,):
        """Display current mode."""
        if self.mode == 'lag':
            msg = "REPLICATION LAG"
        color = self.__get_color(C_GREEN)
        line = ""
        line += " " * (int(self.maxx/2) - len(msg))
        line += msg
        line += " " * (self.maxx - len(line) - 0)
        self.__print_string(self.start_line, 0, line, color | curses.A_BOLD)

    def __help_key_interactive(self):
        """Display interactive mode menu bar."""
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

    def __change_mode_interactive(self):
        """Display change mode menu bar."""
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

    def __interactive(self, process, flag):
        """
        Switch o interactive mode.

        Interactive mode is trigged on KEY_UP or KEY_DOWN key press
        If no key hit during 3 seconds, exit this mode
        """
        # Refresh lines with this verbose mode
        self.__scroll_window(process, flag, 0)

        self.__help_key_interactive()

        current_pos = 0
        offset = 0
        self.__refresh_line(process[current_pos], flag, 'cursor',
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
            if k in (curses.KEY_DOWN, curses.KEY_UP):
                nb_nk = 0
                known = True
                if k == curses.KEY_UP and current_pos > 0:
                    if (self.lines[current_pos] - offset) < \
                      (self.start_line + 3):
                        offset -= 1
                        self.__scroll_window(process, flag, offset)
                        self.__help_key_interactive()

                    if current_pos < len(process):
                        self.__refresh_line(
                            process[current_pos],
                            flag,
                            'default',
                            self.lines[current_pos] - offset)
                    current_pos -= 1
                if k == curses.KEY_DOWN and current_pos < (len(process) - 1):
                    if (self.lines[current_pos] - offset) >= (self.maxy - 2):
                        offset += 1
                        self.__scroll_window(process, flag, offset)
                        self.__help_key_interactive()

                    if current_pos >= 0:
                        self.__refresh_line(
                            process[current_pos],
                            flag,
                            'default',
                            self.lines[current_pos] - offset)
                    current_pos += 1
                self.__refresh_line(
                    process[current_pos],
                    flag,
                    'cursor',
                    self.lines[current_pos] - offset)
                curses.flushinp()
                continue
            if k == ord(' '):
                known = True

                self.__refresh_line(
                    process[current_pos],
                    flag,
                    'default',
                    self.lines[current_pos] - offset)

                if current_pos < (len(process) - 1):
                    current_pos += 1
                    if (self.lines[current_pos] - offset) >= (self.maxy - 1):
                        offset += 1
                        self.__scroll_window(process, flag, offset)
                        self.__help_key_interactive()
                self.__refresh_line(
                    process[current_pos],
                    flag,
                    'cursor',
                    self.lines[current_pos] - offset)
            # Quit interactive mode
            if (k != -1 and not known) or k == curses.KEY_RESIZE:
                curses.flushinp()
                return 0
            curses.flushinp()
            if nb_nk > 3:
                return 0

    def poll(self, interval, flag, indent, process=None, disp_proc=None):
        """Poll activities."""
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
        if key in (curses.KEY_DOWN, curses.KEY_UP) and disp_proc:
            self.__interactive(disp_proc, flag)
            known = False
            do_refresh = True
        # turn off/on colors
        if key == ord('C'):
            if self.color is True:
                self.set_nocolor()
            else:
                self.set_color()
            do_refresh = True
        # sorts
        if key == ord('c') and (flag & PGTOP_FLAGS['LAGB']) and self.sort != 'c':
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
            self.refresh_window()

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
        lag_info = self.data.get_standby_info()

        # return processes sorted by query duration
        try:
            sort_key = SORT_KEYS[self.sort]
        except KeyError:
            sort_key = 'host'

        lag_info = sorted(lag_info, key=lambda p: p[sort_key])

        return (lag_info, None)

    def __print_string(self, lineno, colno, word, color=0):
        """Print a string at position (lineno, colno) and returns its length."""
        try:
            self.win.addstr(lineno, colno, word, color)
        except curses.error:
            pass
        return len(word)

    def __add_blank(self, line, offset=0):
        """Complete string with white spaces from end of string to end of line."""
        line += " " * (self.maxx - (len(line) + offset))
        return line

    def get_indent(self, flag):
        """Return identation for Query column."""
        indent = ''
        cols = [{}] * self.max_ncol
        for num in range(len(PGTOP_COLS[self.mode])):
            mode = PGTOP_COLS[self.mode][num]
            if mode['mandatory'] or (PGTOP_FLAGS[mode['flag']] & flag):
                cols[num] = mode
        for col in cols:
            try:
                indent += col['template_h'] % ' '
            except KeyError:
                pass
        return indent

    def __print_cols_header(self, flag):
        """Print columns headers."""
        line = ''
        disp = ''
        xpos = 0
        cols = [{}] * self.max_ncol
        color = self.__get_color(C_GREEN)
        for num in range(len(PGTOP_COLS[self.mode])):
            mode = PGTOP_COLS[self.mode][num]
            if mode['mandatory'] or (PGTOP_FLAGS[mode['flag']] & flag):
                cols[num] = mode
        for val in cols:
            if 'title' in val:
                disp = val['template_h'] % val['title']
                if self.sort == val['title'][0].lower() and val['title'] in \
                   ["CPU%", "MEM%", "READ/s", "WRITE/s", "TIME+"]:
                    color_highlight = self.__get_color(C_CYAN)
                else:
                    color_highlight = color
                line += disp
                self.__print_string(
                    self.lineno,
                    xpos,
                    disp,
                    color_highlight | curses.A_REVERSE)
                xpos += len(disp)
        self.lineno += 1

    def __print_header(self, pg_version, conn_string, tps,
                       active_connections, size_ev, total_size):
        """Print window header."""
        self.lineno = 0
        colno = 0
        line = "%s - '%s' - Ref.: %ss" % (pg_version, conn_string, self.refresh_time)
        colno = self.__print_string(self.lineno, colno, line)
        return
        # pylint: disable=W0101
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

    def __help_window(self):
        """Display help window."""
        self.win.erase()
        self.lineno = 0
        pgreplicationactivity = __import__('pgreplicationactivity')
        text = "pg_activity %s - (c) 2018 Sebastiaan Mannem" % \
            (pgreplicationactivity.__version__)
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
        self.__display_help_key(self.lineno, 45, "      l",
                                "sort by LSN desc. (lsn)")
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
        """Display help key."""
        pos1 = self.__print_string(lineno, colno, key,
                                   self.__get_color(C_CYAN) | curses.A_BOLD)
        pos2 = self.__print_string(lineno, colno + pos1, ": %s" % (help_msg,))
        return colno + pos1 + pos2

    def refresh_window(self):
        """Refresh the window."""
        procs = self.uibuffer['procs']
        pg_version = self.uibuffer['pg_version']
        conn_string = self.uibuffer['conn_string']
        flag = self.uibuffer['flag']
        tps = self.uibuffer['tps']
        active_connections = self.uibuffer['active_connections']
        size_ev = self.uibuffer['size_ev']
        total_size = self.uibuffer['total_size']

        self.lines = []
        self.win.erase()
        self.__print_header(
            pg_version,
            conn_string,
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
                self.__refresh_line(proc, flag, 'default')
                line_trunc += 1
                self.lines.append(line_trunc)
            except curses.error:
                break
        for line in range(self.lineno, (self.maxy-1)):
            self.__print_string(line, 0, self.__add_blank(" "))
        self.__change_mode_interactive()

    def __scroll_window(self, procs, flag, offset=0):
        """Scroll the window."""
        self.lineno = (self.start_line + 2)
        pos = 0
        for proc in procs:
            if pos >= offset and self.lineno < (self.maxy - 1):
                self.__refresh_line(proc, flag, 'default')
            pos += 1
        for line in range(self.lineno, (self.maxy-1)):
            self.__print_string(line, 0, self.__add_blank(" "))

    def __refresh_line(self, process, flag, typecolor='default',
                       line=None):
        """Refresh a line for activities mode."""
        if line is not None:
            l_lineno = line
        else:
            l_lineno = self.lineno

        colno = 0
        coldef = get_coldef_by_name(self.mode, 'host')
        word = coldef['template_h'] % (process['host'],)
        colno += self.__print_string(l_lineno, colno, word,
                                     self.line_colors['host'][typecolor])
        cols = []
        if self.mode == 'lag':
            if flag & PGTOP_FLAGS['ROLE']:
                if process['role'] == 'master':
                    color_role = 'role_green'
                elif process['role'] == 'standby':
                    color_role = 'role_yellow'
                else:
                    color_role = 'role_default'

                coldef = get_coldef_by_name(self.mode, 'role')
                word = coldef['template_h'] % process['role']
                color = self.line_colors[color_role][typecolor]
                colno += self.__print_string(l_lineno, colno, word, color)
            if flag & PGTOP_FLAGS['UPSTREAM']:
                cols.append('upstream')
            if flag & PGTOP_FLAGS['LSN']:
                cols.append('lsn')
            if flag & PGTOP_FLAGS['RECCONF']:
                cols.append('recovery_conf')
            if flag & PGTOP_FLAGS['STBYMODE']:
                cols.append('standby_mode')
            if flag & PGTOP_FLAGS['LAGS']:
                cols.append('lag_sec')
            if flag & PGTOP_FLAGS['LAGB']:
                cols.append('lag_mb')
            if flag & PGTOP_FLAGS['WALS']:
                cols.append('wal_sec')
            for col in cols:
                coldef = get_coldef_by_name(self.mode, col)
                word = coldef['template_h'] % (str(process[col[:35]]),)
                color = self.line_colors[col][typecolor]
                colno += self.__print_string(l_lineno, colno, word, color)
        self.lineno += 1


def ask_password():
    """Ask for PostgreSQL user password."""
    password = getpass()
    return password


def clean_str(string):
    """Strip and replace some special characters."""
    msg = str(string)
    msg = msg.replace("\n", " ")
    msg = re.sub(r"\s+", r" ", msg)
    msg = msg.replace("FATAL:", "")
    msg = re.sub(r"^\s", r"", msg)
    msg = re.sub(r"\s$", r"", msg)
    return msg


def get_flag_from_options():
    """Return the flag depending on the options."""
    flag = 0
    for _, val in PGTOP_FLAGS.items():
        flag = flag | val
    return flag

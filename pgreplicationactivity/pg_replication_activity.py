#!/usr/bin/env python
"""
This module is the starting point for pg_replication_activity.

module: pg_replication_activity
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


import os
import sys
import signal
import argparse
import logging
import psycopg2
from psycopg2 import errorcodes

from pgreplicationactivity import UI, pgconnection

if os.name != 'posix':
    sys.exit("FATAL: Platform not supported.")

# Create the UI
PGAUI = UI.UI()


def get_arguments():
    """Run argparse and return arguments."""
    try:
        # Use argparse to handle devices as arguments
        description = 'htop like application for PostgreSQL replication ' + \
                      'activity monitoring.'
        parser = argparse.ArgumentParser(description=description)

        # -c / --connectstring
        parser.add_argument(
            '-c',
            '--connectstring',
            dest='connstr',
            default='',
            help='Connectstring (default: "").',
            metavar='CONNECTSTRING')
        # -r / --role
        parser.add_argument(
            '-r',
            '--role',
            dest='role',
            default=None,
            help='Role (default: "").',
            metavar='ROLE')
        # -C / --no-color
        parser.add_argument(
            '-C',
            '--no-color',
            dest='nocolor',
            action='store_true',
            help="Disable color usage.",)
        # --debug
        parser.add_argument(
            '-x',
            '--debug',
            dest='debug',
            action='store_true',
            help="Enable debug mode for traceback tracking.")
        args = parser.parse_args()
    except (argparse.ArgumentError, argparse.ArgumentTypeError) as err:
        print('pg_activity: error: %s' % str(err))
        print('Try "pg_activity --help" for more information.')
        sys.exit(1)
    return args


def main():
    """Run the main entrypoint."""
    signal.signal(signal.SIGTERM, PGAUI.signal_handler)
    args = get_arguments()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    try:
        connstr = try_connecting(args)
        # top part
        interval = 0
        if PGAUI.get_mode() == 'lag':
            lag_info = PGAUI.data.get_standby_info()
        # draw the flag
        flag = UI.get_flag_from_options()
        # main loop
        disp_procs = None
        # indentation
        indent = PGAUI.get_indent(flag)
        # Init curses
        PGAUI.init_curses()
        # color ?
        if args.nocolor is True:
            PGAUI.set_nocolor()
        else:
            PGAUI.set_color()
        while 1:
            PGAUI.check_window_size()
            old_pgtop_mode = PGAUI.get_mode()
            # poll process
            (disp_procs, new_lag_info) = PGAUI.poll(interval, flag, indent,
                                                    lag_info, disp_procs)
            if PGAUI.get_mode() != old_pgtop_mode:
                indent = PGAUI.get_indent(flag)
            lag_info = new_lag_info
            # get active connections
            PGAUI.set_buffer({
                'procs': disp_procs,
                'conn_string': connstr,
                'pg_version': PGAUI.data.get_pg_version(),
                'flag': flag,
                'indent': indent,
                'tps': 9,
                'active_connections': 10,
                'size_ev': 100,
                'total_size': 1000
            })
            # refresh
            PGAUI.refresh_window()
            interval = 1

    except KeyboardInterrupt as err:
        PGAUI.at_exit_curses()
        sys.exit(1)
    except Exception as err:
        PGAUI.at_exit_curses()
        # DEBUG
        if args.debug:
            logging.exception("FATAL: %s", str(err))
        sys.exit("FATAL: %s" % (str(err)))


def check_for_password_error(err):
    """Check if an error is a password error."""
    msg = str(err).strip()
    if msg.startswith("FATAL:  password authentication failed "
                      "for user"):
        return True
    if err.pgcode == errorcodes.INVALID_PASSWORD:
        return True
    if msg == "fe_sendauth: no password supplied":
        return True
    return False


def try_connecting(args):
    """Try connecting and retry with password if needed."""
    password = os.environ.get('PGPASSWORD')
    nb_try = 0
    while nb_try < 2:
        try:
            dsn = pgconnection.connstr_to_dsn(args.connstr)
            if password and nb_try > 0:
                dsn['password'] = password
            PGAUI.data = pgconnection.PGMultiConnection(dsn, args.role)
            PGAUI.data.connect()
            break
        except psycopg2.OperationalError as err:
            is_password_error = check_for_password_error(err)
            if is_password_error and nb_try < 1:
                nb_try += 1
                password = UI.ask_password()
            else:
                if args.debug:
                    logging.exception(str(err).strip())
                sys.exit("pg_activity: FATAL: %s" %
                         (UI.clean_str(str(err),)))

    return pgconnection.dsn_to_connstr({k: v for k, v in dsn.items() if k != 'password'})

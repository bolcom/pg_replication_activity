"""
pg_activity
author: Julien Tachoires <julmon@gmail.com>
license: PostgreSQL License

Copyright (c) 2012 - 2016, Julien Tachoires

Permission to use, copy, modify, and distribute this software and its
documentation for any purpose, without fee, and without a written
agreement is hereby granted, provided that the above copyright notice
and this paragraph and the following two paragraphs appear in all copies.

IN NO EVENT SHALL JULIEN TACHOIRES BE LIABLE TO ANY PARTY FOR DIRECT,
INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST
PROFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION,
EVEN IF JULIEN TACHOIRES HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

JULIEN TACHOIRES SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT
NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE. THE SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS"
BASIS, AND JULIEN TACHOIRES HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE,
SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
"""

import re
import psycopg2
from psycopg2.extras import DictConnection


def clean_str(string):
    """
    Strip and replace some special characters.
    """
    msg = str(string)
    msg = msg.replace("\n", " ")
    msg = re.sub(r"\s+", r" ", msg)
    msg = re.sub(r"^\s", r"", msg)
    msg = re.sub(r"\s$", r"", msg)
    return msg


class Data:
    """
    Data class
    """
    pg_conn = None
    pg_version = None
    pg_num_version = None
    io_counters = None
    prev_io_counters = None
    read_bytes_delta = 0
    write_bytes_delta = 0
    read_count_delta = 0
    write_count_delta = 0

    def __init__(self,):
        """
        Constructor.
        """
        self.pg_conn = None
        self.pg_version = None
        self.pg_num_version = None
        self.io_counters = None
        self.prev_io_counters = None
        self.read_bytes_delta = 0
        self.write_bytes_delta = 0
        self.read_count_delta = 0
        self.write_count_delta = 0

    def get_pg_version(self,):
        """
        Get self.pg_version
        """
        return self.pg_version

    def pg_connect(self, host=None, port=5432, user='postgres', password=None,
                   database='postgres', rds_mode=False):
        """
        Connect to a PostgreSQL server and return
        cursor & connector.
        """
        self.pg_conn = pg_conn = None
        if host is None or host == 'localhost':
            # try to connect using UNIX socket
            try:
                pg_conn = psycopg2.connect(database=database, user=user,
                                           port=port, password=password,
                                           connection_factory=DictConnection)
            except psycopg2.Error as psy_err:
                if host is None:
                    raise psy_err
        if pg_conn is None:  # fallback on TCP/IP connection
            pg_conn = psycopg2.connect(database=database, host=host, port=port,
                                       user=user, password=password,
                                       connection_factory=DictConnection)
        self.pg_conn = pg_conn
        pg_conn.set_isolation_level(0)
        if not rds_mode:  # Make sure we are using superuser if not on RDS
            cur = pg_conn.cursor()
            cur.execute("SELECT current_setting('is_superuser')")
            ret = cur.fetchone()
            if ret[0] != "on":
                raise Exception("Must be run with database superuser privileges.")

    def pg_get_version(self,):
        """
        Get PostgreSQL server version.
        """
        query = "SELECT version() AS pg_version"
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        return ret['pg_version']

    def pg_get_num_version(self, text_version):
        """
        Get PostgreSQL short & numeric version from
        a string (SELECT version()).
        """
        res = re.match(
            r"^(PostgreSQL|EnterpriseDB) ([0-9]+)\.([0-9]+)(?:\.([0-9]+))?",
            text_version)
        if res is not None:
            rmatch = res.group(2)
            if int(res.group(3)) < 10:
                rmatch += '0'
            rmatch += res.group(3)
            if res.group(4) is not None:
                if int(res.group(4)) < 10:
                    rmatch += '0'
                rmatch += res.group(4)
            else:
                rmatch += '00'
            self.pg_version = str(res.group(0))
            self.pg_num_version = int(rmatch)
            return
        self.pg_get_num_dev_version(text_version)

    def pg_get_num_dev_version(self, text_version):
        """
        Get PostgreSQL short & numeric devel. or beta version
        from a string (SELECT version()).
        """
        res = re.match(
            r"^(PostgreSQL|EnterpriseDB) ([0-9]+)(?:\.([0-9]+))?(devel|beta[0-9]+|rc[0-9]+)",
            text_version)
        if res is not None:
            rmatch = res.group(2)
            if res.group(3) is not None:
                if int(res.group(3)) < 10:
                    rmatch += '0'
                rmatch += res.group(3)
            else:
                rmatch += '00'
            rmatch += '00'
            self.pg_version = str(res.group(0))
            self.pg_num_version = int(rmatch)
            return
        raise Exception('Undefined PostgreSQL version.')

    def pg_is_local(self,):
        """
        Is pg_activity connected localy ?
        """
        query = """
        SELECT inet_server_addr() AS inet_server_addr, inet_client_addr() AS inet_client_addr
        """
        cur = self.pg_conn.cursor()
        cur.execute(query)
        ret = cur.fetchone()
        if ret['inet_server_addr'] == ret['inet_client_addr']:
            return True
        return False

    def pg_get_lag_info(self):
        '''
        Get a list of all instances
        '''
        ret = []
        ret.append({'host': '127.0.0.1:5435', 'role': 'master',
                    'lag_sec': 0, 'lag_bytes': 0, 'upstream': ''})
        ret.append({'host': '127.0.0.1:5436', 'role': 'standby',
                    'lag_sec': 10, 'lag_bytes': 10002, 'upstream': 'db01'})

        return ret

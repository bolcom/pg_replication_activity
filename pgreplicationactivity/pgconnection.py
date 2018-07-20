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

import os
from copy import copy
import logging
import re
import psycopg2
# from psycopg2 import sql

RE_QUOTE=re.compile('''['"]''')

LOGGER = logging.getLogger('pgconnection')

class PGConnectionException(Exception):
    '''
    This exception is raised when invalid data is fed to a PGConnectionException
    '''
    pass


class PGConnection():
    '''
    This class is used to connect to a postgres cluster and to run logical functionality
    through methods of this class, like dropdb, createdb, etc.
    '''
    def __init__(self, dsn_params=None):
        '''
        Sets some defaults on a new initted PGConnection class.
        '''
        if not isinstance(dsn_params, dict) or not dsn_params:
            raise PGConnectionException('Init PGConnection class with a dict of '
                                        'connection parameters')
        self.__dsn_params = dsn_params
        self.__conn = {}
        self.pg_version = None
        self.pg_num_version = None
        self.__recoveryconf = None

    def dsn(self, dsn_params=None):
        '''
        This method returns the DSN that is used for the current connection.
        '''
        if not dsn_params:
            dsn_params = copy(self.__dsn_params)
            for key in ['password', 'dbname']:
                try:
                    del dsn_params[key]
                except KeyError:
                    pass
        return dsn_to_connstr(dsn_params)

    def connect(self, database: str = 'postgres'):
        '''
        Connect to a pg cluster. You can specify the connectstring, or use the one
        thats already set during init, or a previous connect.
        If a succesful connection is already there, connect will be skipped.
        '''
        try:
            if not self.__conn[database].closed:
                return
        except (KeyError, AttributeError):
            pass
        # Split 'host=127.0.0.1 dbname=postgres' in {'host': '127.0.0.1', 'dbname': 'postgres'}
        dsn_params = copy(self.__dsn_params)
        dsn_params['dbname'] = database

        # Join {'host': '127.0.0.1', 'dbname': 'postgres'} into 'host=127.0.0.1 dbname=postgres'
        dsn = self.dsn(dsn_params)
        self.__conn[database] = conn = psycopg2.connect(dsn)
        conn.autocommit = True

    def disconnect(self, database: str = ''):
        '''
        Disconnect a DB connection from a pg cluster.
        If no DB connection is named, all connections are closed.
        '''
        if database:
            databases = [database]
        else:
            databases = [db for db in  self.__conn.keys()]
        for database_name in databases:
            try:
                del self.__conn[database_name]
            except Exception:
                pass

    def connection_dsn(self, database: str = 'postgres'):
        '''
        return get_dsn_parameters() from the connection.
        Even if you use only service= in your dsn, you can deduct all connection details from this dict.
        '''
        self.connect(database)
        return self.__conn[database].get_dsn_parameters()

    def run_sql(self, query, parameters=None, database: str = 'postgres'):
        '''
        Run a query. If the query returns results, the results are returned by this function
        as a list of dictionaries, e.a.:
          [{'name': 'postgres', 'oid': 12345}, {'name': 'template1', 'oid': 12346}]).
        '''
        self.connect(database=database)
        cur = self.__conn[database].cursor()
        try:
            LOGGER.debug('query: %s', query)
            cur.execute(query, parameters)
        except Exception as error:
            if LOGGER.getEffectiveLevel() <= logging.DEBUG:
                LOGGER.exception(str(error))
            raise
        try:
            columns = [i[0] for i in cur.description]
        except TypeError:
            return None
        ret = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return ret

    def connected(self):
        '''
        This simple helper function tries to conenct adn detects if a valid pg conenction is made.
        '''
        try:
            result = self.run_sql('SELECT pg_is_in_recovery() AS recovery')
            return True
        except psycopg2.OperationalError:
            return False

    def is_standby(self):
        '''
        This simple helper function detects if this instance is an standby.
        '''
        result = self.run_sql('SELECT pg_is_in_recovery() AS recovery')
        return result[0]['recovery']

    def port(self):
        '''
        This method will return the port that the postgres instance is running on.
        It will try to read it from Postgres.
        If it cannot connect it will read it from the dsn params.
        If it cannot read it from dsn, it will use default (5432).
        '''
        try:
            result = self.run_sql("select inet_server_port() as port")
            return result[0]['port']
        except psycopg2.OperationalError:
            pass
        # Read it from DSN, if its not there from PGPORT env var, if not there default to 5432
        return self.__dsn_params.get('port', os.environ.get('PGPORT', '5432'))

    def ip(self):
        '''
        This method will return the address that the postgres instance is running on.
        It will try to read it from Postgres.
        If it cannot connect it will read it from the dsn params.
        If it cannot read it from dsn, it will return None.
        '''
        try:
            result = self.run_sql("select inet_server_addr() as ip")
            return result[0]['ip']
        except psycopg2.OperationalError:
            pass
        ip = self.__dsn_params.get('host', os.environ.get('PGHOST'))
        if ',' in ip:
            # Multiple connections in dsn, so this is not one of the specific connections
            # Could not connect, so this non-specific connection did not connect
            # pg_replication_activity will not work without any connection.
            # But let pg_replication_activity break rather than this method.
            return None
        else:
            return ip

    def hostid(self):
        '''
        This method returns the ID as the server experiences it.
        It is constructed from the ip and port that the Postgres server is
        attached to inet_server_addr, and inet_server_port.
        '''
        ip, port = self.ip(), self.port()
        if ip:
            return '{0}:{1}'.format(ip, port)
        elif 'service' in self.__dsn_params:
            return 'service={0}'.format(self.__dsn_params['service'])
        else:
            return None

    def get_upstream(self):
        '''
        This method calculates the upstream server for a standby.
        '''
        try:
            conninfo = self.run_sql('select conninfo from pg_stat_wal_receiver')
            conninfo = conninfo[0]['conninfo']
            dsn = connstr_to_dsn(conninfo)
            return '{0}:{1}'.format(dsn['host'], dsn['port'])
        except IndexError:
            return ''

    def current_time_lag_lsn(self):
        '''
        This method resturns the local time, the lag (compared to local time)
        and the latest received lsn. We can use this info to display time drift.
        '''
        # This works on a standby
        if not self.connected():
            return {'now': None, 'lsn': None, 'lag_sec': None}
        result = self.run_sql('select now() as now, latest_end_lsn as lsn, '
                              'extract( epoch from now() - '
                              'pg_last_xact_replay_timestamp()) as lag_sec '
                              'from pg_stat_wal_receiver')
        if result:
            return result[0]
        if self.get_num_version() >= 100000:
            # This works on a master. For PG10, we cannot use pg_current_xlog_location(),
            # but should use pg_current_wal_lsn() instead
            result = self.run_sql('select now() as now, pg_current_wal_lsn() as lsn, '
                                  '0 as lag_sec')
        else:
            # This works on a master. with a version lower than  PG10
            result = self.run_sql('select now() as now, pg_current_xlog_location() as lsn, '
                                  '0 as lag_sec from pg_stat_wal_receiver')
        if result:
            return result[0]
        raise PGConnectionException('Cannot determine current_time_lag_lsn')

    def get_standby_info(self):
        '''
        This method returns the replication info of all connected servers.
        '''
        ret = {}
        ret['host'] = self.hostid()
        try:
            if self.is_standby():
                ret['role'] = 'standby'
                ret['upstream'] = self.get_upstream()
            else:
                ret['role'] = 'master'
                ret['upstream'] = ''
        except psycopg2.OperationalError:
            ret['role'] = 'Down'
            ret['upstream'] = ''
        try:
            recoveryconf = self.recoveryconf()
            ret['recovery_conf'] = True
            ret['standby_mode'] = confbool_to_bool(recoveryconf.get('standby_mode'))
        except (AttributeError, psycopg2.OperationalError):
            ret['recovery_conf'] = False
            ret['standby_mode'] = None
        return ret

    def get_pg_version(self,):
        """
        Get self.pg_version
        """
        if not self.pg_version:
            self.get_num_version()
        return self.pg_version

    def get_num_version(self):
        """
        Get PostgreSQL short & numeric version from
        a string (SELECT version()).
        """
        if self.pg_num_version:
            return self.pg_num_version
        try:
            pg_version = self.run_sql("SELECT version() AS pg_version")
        except psycopg2.OperationalError:
            return None
        text_version = pg_version[0]['pg_version']
        # First try as normal version number
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
            return self.pg_num_version

        # Okay, then try with devel version number
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
            return self.pg_num_version

        # Seems we cannot deduce version number.
        raise Exception('Undefined PostgreSQL version.')

    def recoveryconf(self):
        if self.__recoveryconf or self.__recoveryconf is False:
            return self.__recoveryconf
        try:
            result = self.run_sql("select pg_read_file('recovery.conf') as recoveryconf")
            self.__recoveryconf = ret = {}
            for line in result[0]['recoveryconf'].split('\n'):
                line=line.strip()
                if not '=' in line:
                    continue
                k,v = line.split('=', 1)
                k, v = k.strip(), v.strip()
                ret[k] = v
        except psycopg2.OperationalError:
            self.__recoveryconf = ret = False
        return ret


class PGMultiConnection():
    '''
    This class is used to connect multiple to postgres cluster (like all
    clusters in a a replicated cluster) and to run logical functionality
    through methods of this class on all of them.
    '''
    def __init__(self, dsn_params=None):
        '''
        Sets some defaults on a new initted PGConnection class.
        '''
        if not isinstance(dsn_params, dict) or not dsn_params:
            raise PGConnectionException('Init PGConnection class with a dict of '
                                        'connection parameters')
        self.__dsn_params = dsn_params
        self.__conn = {}

    def dsn(self, dsn_params=None):
        '''
        This method returns the DSN that is used for the current connection.
        '''
        if not dsn_params:
            dsn_params = copy(self.__dsn_params)
            for key in ['password', 'dbname']:
                try:
                    del dsn_params[key]
                except KeyError:
                    pass
        return " ".join(["=".join((k, str(v))) for k, v in dsn_params.items()])

    def connect(self, database: str = 'postgres'):
        '''
        Connect to multiple instances. You can specify the connectstring,
        or use the one thats already set during init, or a previous connect.
        Contrary to PGConnection.connect(), in this case for multiple
        hosts (host=host1,host2) a connection is made to very host (and not
        just one as default libpq functionality would do).
        '''
        try:
            if not self.__conn[database].closed:
                return
        except (KeyError, AttributeError):
            pass
        # Split 'host=127.0.0.1 dbname=postgres' in {'host': '127.0.0.1', 'dbname': 'postgres'}
        dsn_params = copy(self.__dsn_params)
        dsn_params['dbname'] = database
        ports = dsn_params.get('port', os.environ.get('PGPORT', '5432')).split(',')
        hosts = dsn_params.get('host', os.environ.get('PGHOST'))
        if hosts:
            hosts = hosts.split(',')
            if len(hosts) > 1 and len(ports) == 1:
                ports = ports * len(hosts)
            if len(hosts) != len(ports):
                raise PGConnectionException('you cannot specify less or more ports than hosts')
            for i, _ in enumerate(hosts):
                dsn_params = copy(dsn_params)
                dsn_params['host'] = hosts[i]
                dsn_params['port'] = ports[i]
                try:
                    new_con = PGConnection(dsn_params)
                    hostid = new_con.hostid()
                except psycopg2.OperationalError:
                    hostid = '{0}:{1}'.format(dsn_params['host'], dsn_params['port'])
                if hostid in self.__conn:
                    new_con.disconnect()
                else:
                    self.__conn[hostid] = new_con
            return
        else:
            # No hosts configured. Maybe service configured. Or default /tmp/.s.PGSQL.5432 might work.
            # Let libpq figure it out and use connection_dsn() to find hosts and ports config.
            new_con = PGConnection(dsn_params)
            hostid = new_con.hostid()
            self.__conn[hostid] = new_con
        if not 'service' in dsn_params and not 'PGSERVICEFILE' in os.environ:
            return
        if not len(self.__conn) == 1:
            return
        # A service was used, no host was set, and only one connection was made, 
        # so maybe multiple hosts where defined in the service
        # In that case libpq would only connect to one master.
        # But we can easilly deduct hosts from the one connection and reconnect to all of them seperately.

        # But first find the one connection. To bypass an error like
        # TypeError: 'dict_keys' object does not support indexing
        # I convert to a real list first
        con_keys = [key for key in self.__conn.keys()]
        one_and_only_con_key = con_keys[0]
        one_and_only_con = self.__conn[one_and_only_con_key]

        con_dsn = one_and_only_con.connection_dsn()
        if ',' in con_dsn['host']:
            # A service was used, and there are multiple hosts in config below.
            # Change one conenction to any host into a connection for every host.
            # But first cleanup the default connection
            one_and_only_con.disconnect()
            del self.__conn[one_and_only_con_key]
            # Set dsn host to a comma seperated list of all hosts read from default connection
            self.__dsn_params['host'] = con_dsn['host']
            # And set port to list of all portss read from default connection
            self.__dsn_params['port'] = con_dsn['port']
            # Now rerun myself to create a seperate connection to every host
            self.connect(database)

    def get_standby_info(self):
        '''
        This method returns the replication info of all connected servers.
        '''
        ret = []
        for key, connection in self.__conn.items():
            lag_info = connection.get_standby_info()
            lag_info['host'] = key
            ret.append(lag_info)
        # To keep time distance between these queries as short as possible
        # These queries are run in a seperate run.
        for lag_info in ret:
            hostid = lag_info['host']
            connection = self.__conn[hostid]
            lag_info.update(connection.current_time_lag_lsn())
        # We now detect the latest LSN and now from all servers.
        # This will act as reference for drift and lag_bytes.
        max_now = max([li['now'] for li in ret if li['now']])
        max_lsn = max([lsn_to_xlogbyte(li['lsn']) for li in ret if li['lsn']])
        # Now just calculate drift and lag_bytes
        for lag_info in ret:
            if lag_info['now']:
                lag_info['drift'] = max_now - lag_info['now']
            else:
                lag_info['drift'] = None
            if lag_info['lsn']:
                lag_info['lag_bytes'] = max_lsn - lsn_to_xlogbyte(lag_info['lsn'])
            else:
                lag_info['lag_bytes'] = None
        return ret

    def get_pg_version(self,):
        """
        Get self.pg_version
        """
        pg_versions = set([connection.get_pg_version() for _, connection in self.__conn.items() if connection.get_pg_version()])
        if len(pg_versions) == 1:
            return pg_versions.pop()
        raise PGConnectionException('More than one pg_version was detected in this multicluster', pg_versions)


def dsn_to_connstr(dsn_params=None):
    '''
    This function converts a dict with dsn params to a connstring.
    '''
    return " ".join(["=".join((k, str(v))) for k, v in dsn_params.items()])


def connstr_to_dsn(connstring=''):
    '''
    This function converts a dict with dsn params to a connstring.
    '''
    connstring = connstring.strip()
    if not connstring:
        return {}
    return dict([kv.split('=', 1) for kv in connstring.split(' ')])


def lsn_to_xlogbyte(lsn):
    '''
    This function converts a LSN to a integer, which points to an exact byte
    in the wal stream.
    '''
    # Split by '/' character
    xlogid, xrecoff = lsn.split('/')

    # Convert both from hex to int
    xlogid = int(xlogid, 16)
    xrecoff = int(xrecoff, 16)

    # multiply wal file nr to offset by multiplying with 2**32, and add offset
    # in file to come to absolute int position of lsn and return result
    return xlogid * 2**32 + xrecoff

def confbool_to_bool(confbool):
    '''
    This function is used to convert a boolean from postgres config to a python boolean (True or False)
    '''
    confbool = RE_QUOTE.sub('', confbool.lower())
    if confbool.lower() in ['on', 'true', 'yes', '1', 1]:
        return True
    elif confbool.lower() in ['off', 'false', 'no', '0', 0]:
        return False
    return None

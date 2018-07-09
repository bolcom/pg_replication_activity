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
import psycopg2
# from psycopg2 import sql


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
            raise PGConnectionException('Init PGConnection class with a dict of connection \
                                         parameters')
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
        for key in ['sslkey', 'sslcert', 'sslrootcert']:
            if key in dsn_params:
                dsn_params[key] = os.path.realpath(os.path.expanduser(dsn_params[key]))
        return " ".join(["=".join((k, str(v))) for k, v in dsn_params.items()])

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
            databases = self.__conn.keys()
        for database_name in databases:
            try:
                del self.__conn[database_name]
            except Exception:
                pass

    def run_sql(self, query, parameters=None, database: str = 'postgres'):
        '''
        Run a query. If the query returns results, the results are returned by this function
        as a list of dictionaries, e.a.:
          [{'name': 'postgres', 'oid': 12345}, {'name': 'template1', 'oid': 12346}]).
        '''
        self.connect(database=database)
        cur = self.__conn[database].cursor()
        try:
            logging.debug('query: %s', query)
            cur.execute(query, parameters)
        except Exception as error:
            logging.exception(str(error))
            raise
        try:
            columns = [i[0] for i in cur.description]
        except TypeError:
            return None
        ret = [dict(zip(columns, row)) for row in cur.fetchall()]
        cur.close()
        return ret

    def is_standby(self):
        '''
        This simple helper function detects if this instance is an standby.
        '''
        result = self.run_sql('SELECT pg_is_in_recovery() AS recovery')
        return result[0]['recovery']

    def hostid(self):
        '''
        This method returns the ID as the server experiences it.
        It is constructed from the ip and port that the Postgres server is
        attached to inet_server_addr, and inet_server_port.
        '''
        result = self.run_sql('select inet_server_addr() as ip, '
                              'inet_server_port() as port')
        return '{0}:{1}'.format(result[0]['ip'], result[0]['port'])


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
            raise PGConnectionException('Init PGConnection class with a dict of connection \
                                         parameters')
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
        for key in ['sslkey', 'sslcert', 'sslrootcert']:
            if key in dsn_params:
                dsn_params[key] = os.path.realpath(os.path.expanduser(dsn_params[key]))
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
        ports = dsn_params.get('port', '5432').split(',')
        hosts = dsn_params.get('host')
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

                new_con = PGConnection(dsn_params)
                hostid = new_con.hostid()
                if hostid in self.__conn:
                    new_con.disconnect()
                else:
                    self.__conn[hostid] = new_con

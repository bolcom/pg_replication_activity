#!/usr/bin/env python3
'''
This module holds all unit tests for the pgconnection module
'''
import os
import tempfile
import logging
import unittest
import unittest.mock
from unittest.mock import patch
from psycopg2.sql import Composed, SQL, Identifier
from pgreplicationactivity.pgconnection import PGConnection, PGConnectionException


logging.disable(logging.CRITICAL)


class PGConnectionTest(unittest.TestCase):
    """
    Test the PGConnection Class.
    """
    def test_mocked_pg_connection_init(self):
        '''
        Test PGConnection.init for normal functionality
        '''
        with unittest.mock.patch('psycopg2.connect') as mock_connect:
            mock_con = mock_connect.return_value
            mock_con.closed = False
            pgconn = PGConnection(dsn_params={'server': ['server1', 'server2']})
            pgconn.connect()
            pgconn.connect()
            self.assertIsInstance(pgconn, PGConnection)
        expected_msg = 'Init PGConnection class with a dict of connection parameters'
        with self.assertRaises(PGConnectionException, msg=expected_msg):
            pgconn = PGConnection(dsn_params='')
        with self.assertRaises(PGConnectionException, msg=expected_msg):
            pgconn = PGConnection(dsn_params={})
        with self.assertRaises(PGConnectionException, msg=expected_msg):
            pgconn = PGConnection()

    def test_mocked_runsql(self):
        '''
        Test PGConnection.run_sql for normal functionality
        '''
        test_qry = "select datname, datdba from pg_database where datname in " \
                   "('postgres', 'template0')"
        query_header = [("datname",), ("datdba",)]
        query_faulty_header = [0, 1]
        query_result = [("template0", 10), ("postgres", 11)]
        expected_result = [{'datname': 'template0', 'datdba': 10},
                           {'datname': 'postgres', 'datdba': 11}]
        expected_connstr = 'server=server1 dbname=postgres'
        with unittest.mock.patch('psycopg2.connect') as mock_connect:
            mock_con = mock_connect.return_value
            mock_cur = mock_con.cursor.return_value
            mock_cur.description = query_header
            mock_cur.fetchall.return_value = query_result
            result = PGConnection(dsn_params={'server': 'server1'}, role='myrole').run_sql(test_qry)
            mock_connect.assert_called_with(expected_connstr)
            mock_cur.execute.assert_called_with(test_qry, None)
            self.assertEqual(result, expected_result)
            mock_cur.description = query_faulty_header
            result = PGConnection(dsn_params={'server': 'server1'}).run_sql(test_qry)
            self.assertIsNone(result)

        with unittest.mock.patch('psycopg2.connect') as mock_connect:
            mock_con = mock_connect.return_value
            mock_cur = mock_con.cursor.return_value
            mock_cur.execute.side_effect = PGConnectionException
            with self.assertRaises(PGConnectionException):
                result = PGConnection(dsn_params={'server': 'server1'}).run_sql(test_qry)

    def test_mocked_is_standby(self):
        '''
        Test PGConnection.is_standby for normal functionality
        '''
        query_header = [("recovery",)]
        with unittest.mock.patch('psycopg2.connect') as mock_connect:
            mock_con = mock_connect.return_value
            mock_cur = mock_con.cursor.return_value
            mock_cur.description = query_header
            for expected_result in [True, False]:
                mock_cur.fetchall.return_value = [(expected_result,)]
                result = PGConnection(dsn_params={'server': 'server1'}).is_standby()
                self.assertEqual(result, expected_result)


if __name__ == '__main__':
    unittest.main()

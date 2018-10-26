
"""
This is the init class of pgreplicationactivity/config/.

This module is only there, so that config files are copied over.
"""
COLS = {'lag': [{'name': 'host', 'title': 'HOST', 'template_h': '%-25s ',
                 'flag': 'NONE', 'mandatory': True},
                {'name': 'role', 'title': 'ROLE', 'template_h': '%-8s ',
                 'flag': 'ROLE', 'mandatory': False},
                {'name': 'upstream', 'title': 'UPSTREAM', 'template_h': '%-40s ',
                 'flag': 'UPSTREAM', 'mandatory': False},
                {'name': 'lsn', 'title': 'LSN', 'template_h': '%-13s ',
                 'flag': 'LSN', 'mandatory': False},
                {'name': 'recovery_conf', 'title': 'REC_CONF',
                 'template_h': '%-10s ', 'flag': 'RECCONF', 'mandatory': False},
                {'name': 'standby_mode', 'title': 'STBY_MODE',
                 'template_h': '%-10s ', 'flag': 'STBYMODE', 'mandatory': False},
                {'name': 'replication_slot', 'title': 'SLOT',
                 'template_h': '%-10s ', 'flag': 'SLOT', 'mandatory': False},
                {'name': 'lag_sec', 'title': 'LAG(s)', 'template_h': '%10s ',
                 'flag': 'LAGS', 'mandatory': False},
                {'name': 'lag_mb', 'title': 'LAG(MB)', 'template_h': '%10s ',
                 'flag': 'LAGB', 'mandatory': False},
                {'name': 'wal_sec', 'title': 'WAL MB/s', 'template_h': '%10s ',
                 'flag': 'WALS', 'mandatory': False}]}
FLAGS = {}
FLAGS['NONE'] = 0
VALUE = 1
for flag in ['UPSTREAM', 'LSN', 'RECCONF', 'STBYMODE', 'SLOT', 'LAGS', 'ROLE',
             'LAGB', 'WALS']:
    FLAGS[flag] = VALUE
    VALUE *= 2
del VALUE

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
MAX_NCOL = 14

SORT_KEYS = {'u': 'upstream', 's': 'slot', 'r': 'role', 'm': 'lag_sec',
             'w': 'lag_mb', 'l': 'lsn'}

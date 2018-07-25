This is an attempt to create something like pg_top, pg_view or pg_activity, but not for Postgres processes, bt rather Postgres Replication info.
It started out as a fork of https://github.com/julmon/pg_activity/commit/ec96aa7f8e0b85a21956a3bd75a8ad26c7d6f5be.
After that a lot of changes have been done to upgrade code quality, update to newer standards and change from proces details to replication details.

==rpm for centos7==
* Requires python34-psycopg2 package, which you must build yourselve

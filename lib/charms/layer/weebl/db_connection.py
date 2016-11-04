#!/usr/bin/env python3

import psycopg2
from subprocess import check_call


def save_database_dump(weebl_data, output_file):
    check_call(
        "PGPASSWORD={password} pg_dump -h {host} -U {user} -p {port} -x -F "
        "t {database} -f {out}".format(**weebl_data, out=output_file))
    return True


class DatabaseConnection():

    def __init__(self, name, user, password, host, port, owner='postgres',
                 dbname='postgres', isolation_lvl=0):
        self.name = name
        self.user = user
        self.host = host
        self.port = port
        self.pwd = password
        self.owner = owner
        self.dbname = dbname
        self.isolation_lvl = isolation_lvl

    def database_connection(self, sql, dbname=None, user=None, pwd=None):
        con = psycopg2.connect(
            dbname=self.name if dbname is None else dbname,
            user=self.user if user is None else user,
            host=self.host,
            port=self.port,
            password=self.pwd if pwd is None else pwd)
        con.set_isolation_level(self.isolation_lvl)
        cursor = con.cursor()
        try:
            cursor.execute(sql)
            response = cursor.fetchall()
        except psycopg2.ProgrammingError as e:
            response = e
            cursor.close()
            con.close()
        return response

    def check_if_user_exists(self, user):
        sql_check_user = "SELECT 1 FROM pg_roles WHERE rolname='{}'"
        sql = sql_check_user.format(user)
        try:
            output = self.database_connection(sql)
            return True if output[0][0] else False
        except:
            return False

    def check_if_database_exists(self, database):
        sql = "SELECT * from pg_database where datname='{}'".format(database)
        out = self.database_connection(sql)
        exists = False
        for element in out:
            if database in element:
                exists = True
        return exists

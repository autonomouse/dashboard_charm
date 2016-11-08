#!/usr/bin/env python3

import psycopg2
from subprocess import check_call


def remote_db_cli_interaction(app, weebl_data, custom=''):
    check_call(
        "PGPASSWORD={password} {app} -h {host} -U {user} -p {port} {custom}"
        .format(**weebl_data, app=app, custom=custom), shell=True)
    return True

def save_database_dump(weebl_data, output_file):
    custom = "-f {} --no-owner --no-acl -x -F t -d {}".format(
        output_file, weebl_data['database'])
    remote_db_cli_interaction("pg_dump", weebl_data, custom)


def drop_database(database, weebl_data):
    remote_db_cli_interaction("dropdb", weebl_data, database)


def create_empty_database(database, weebl_data, postgres_user="postgres"):
    create_cmds = "{} -O {}".format(database, postgres_user)
    remote_db_cli_interaction("createdb", weebl_data, create_cmds)


def upload_database_dump(weebl_data, dump_file):
    restore_cmds = "-d {} --clean --exit-on-error {}".format(
        weebl_data['database'], dump_file)
    remote_db_cli_interaction("pg_restore", weebl_data, restore_cmds)


class DatabaseConnection():

    def __init__(self, name, user, password, host, port, isolation_lvl=0):
        self.name = name
        self.user = user
        self.host = host
        self.port = port
        self.pwd = password
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
        finally:
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

#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, os.path.join(os.environ['CHARM_DIR'], 'lib'))
import yaml
import psycopg2
from charms.layer.weebl import utils


def save_database_dump(weebl_data, output_file):
    db_dump_saved = False
    try:
        cmd = ("PGPASSWORD={password} pg_dump -h {host} -U {user} -p {port} -x"
               " -F t {database} -f {out}".format(
                    **weebl_data, out=output_file))
        utils.run_cli(cmd, shell=True)
        db_dump_saved = True
    except Exception as e:
        hookenv.log(e)
    finally:
        return db_dump_saved


def database_connection(sql, pwd, dbname='postgres', user='postgres',
                    host='localhost', isolation_lvl=0):
    con = psycopg2.connect(dbname=dbname, user=user, host=host, password=pwd)
    con.set_isolation_level(isolation_lvl)
    cursor = con.cursor()
    try:
        cursor.execute(sql)
        response = cursor.fetchall()
    except psycopg2.ProgrammingError as e:
        response = e
        cursor.close()
        con.close()
    return response


def check_if_user_exists(user, pwd):
    sql_check_user = "SELECT 1 FROM pg_roles WHERE rolname='{}'"
    sql = sql_check_user.format(user)
    try:
        return True if database_connection(sql, pwd)[0][0] else False
    except:
        return False


def check_if_database_exists(database, pwd):
    sql = "SELECT * from pg_database where datname='{}'".format(database)
    out = database_connection(sql, pwd)
    exists = False
    for element in out:
        if database in element:
            exists = True
    return exists

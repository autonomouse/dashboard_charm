#!/usr/bin/env python3

import os
import sys
import shutil
import shlex
import argparse
import subprocess


CHARMSTORE_LOC = "cs:~oil-charms/weebl"


class Uploader():

    def main(self):
        self.exit_if_repo_not_clean()
        self.working_dir = os.getcwd()
        self.get_args()
        self.print_username_or_exit_if_logged_out()
        try:
            self.process_charm()
        finally:
            self.tidy_up()


    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('release', default=False, nargs='?',
                            help='Release as stable, candidate, beta, or edge.'
                            ' e.g.: "./upload.py stable"')
        return vars(parser.parse_args())


    def get_args(self):
        args = self.parse_args()
        self.release = args['release']


    def exit_if_repo_not_clean(self):
        output = self.cmd('bzr status')
        if not output:
            return
        else:
            print("Repo not clean - commit changes and try again.")
            sys.exit()


    def print_username_or_exit_if_logged_out(self):
        output = self.cmd('charm whoami')
        user = [line.split(' ')[1] for line in output.split('\n')
                if 'user' in line.lower()]
        if not user:
            print(output)
            sys.exit()
        print("Logged in as {}".format(user[0]))


    def tidy_up(self):
        os.chdir(self.working_dir)
        self.rmdir(os.path.join(self.working_dir, 'builds'))
        self.rmdir(os.path.join(self.working_dir, 'deps'))


    def rmdir(self, path):
        try:
            shutil.rmtree(path)
            print("{} removed.".format(path))
        except FileNotFoundError:
            pass


    def cmd(self, command):
        return subprocess.check_output(command, shell=True).strip().decode()


    def process_charm(self):
        self.build_charm()
        self.release_charm()


    def build_charm(self):
        self.cmd('charm build -o {}'.format(self.working_dir))
        build_dir = os.path.join(self.working_dir, "builds/weebl/")
        print(self.cmd('charm proof {}'.format(build_dir)))
        output = self.cmd('charm push {} {}'.format(build_dir, CHARMSTORE_LOC))
        self.charm = output.split('\n')[0].split(' ')[1]
        print("The {} charm has been built and is temporarily in {}".format(
            self.charm, build_dir))


    def release_charm(self):
        if not self.release:
            print("This charm has not been released.")
            return
        output = self.cmd('charm release {} --channel {}'.format(
            self.charm, self.release))
        self.channel = output.split(' ')[2]
        self.cmd('charm grant {} --channel {} everyone'.format(
            self.charm, self.release))
        print("This charm has been released to {}.".format(self.channel))


def main():
    Uploader().main()


if __name__ == "__main__":
    sys.exit(main())

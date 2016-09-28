#!/usr/bin/env python3

import os
import sys
import shutil
import shlex
import argparse
import subprocess


CHARMSTORE_LOC = "cs:~oil-charms/weebl"
BUILT_CHARM_REPOS = {
    'stable': "lp:~oil-ci/oil-ci/charm-weebl-BUILT", }


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
        parser.add_argument('publish', default=False)
        return vars(parser.parse_args())


    def get_args(self):
        args = self.parse_args()
        self.publish = args['publish']


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
        self.publish_charm()
        self.update_built_charm()


    def build_charm(self):
        self.cmd('charm build -o {}'.format(self.working_dir))
        build_dir = os.path.join(self.working_dir, "builds/weebl/")
        output = self.cmd('charm push {} {}'.format(build_dir, CHARMSTORE_LOC))
        self.charm = output.split('\n')[0].split(' ')[1]
        print("The {} charm has been built and is temporarily in {}".format(
            self.charm, build_dir))


    def publish_charm(self):
        if not self.publish:
            print("This charm has not been published.")
            return
        output = self.cmd('charm publish {} --channel {}'.format(
            self.charm, self.publish))
        self.channel = output.split(' ')[2]
        print("This charm has been published to {}.".format(self.channel))


    def update_built_charm(self):
        built_charm_repo = BUILT_CHARM_REPOS.get(self.publish)
        if not built_charm_repo:
            return
        weebl_dir = os.path.join(self.working_dir, "builds/weebl/")
        built_dir = os.path.join(self.working_dir, "builds/weebl-built/")
        self.cmd('bzr checkout {} {}'.format(built_charm_repo, built_dir))
        shutil.copytree('builds/weebl-built/.bzr', weebl_dir)
        shutil.rmtree(os.path.join(built_dir, "builds"))
        log = self.cmd('bzr log -r-1 --line')
        os.chdir(weebl_dir)
        self.cmd('bzr add')
        # This repo has a post-commit hook that automatically pushes to trunk:
        self.cmd('bzr commit -m "{}"'.format(log))


def main():
    Uploader().main()


if __name__ == "__main__":
    sys.exit(main())

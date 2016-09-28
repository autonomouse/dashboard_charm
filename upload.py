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
        args = self.parse_args()
        self.publish = args['publish']
        self.print_username_or_exit_if_logged_out()
        try:
            self.charm_build()
        finally:
            self.tidy_up()


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
        print("Logged in as {}.".format(user[0]))


    def tidy_up(self):
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


    def charm_build(self):
        self.cmd('charm build -o {}'.format(self.working_dir))
        build_dir = os.path.join(self.working_dir, "builds/weebl/")
        output = self.cmd('charm push {} {}'.format(build_dir, CHARMSTORE_LOC))
        self.charm = output.split('\n')[0].split(' ')[1]
        if self.publish:
            self.channel = self.publish_charm(self.charm)
            print("This charm has been published to {}.".format(self.channel))
        else:
            print("This charm has not been published.")
        self.update_built_charm()


    def publish_charm(self, charm):
        output = self.cmd('charm publish {} --channel {}'.format(
            charm, self.publish))
        channel = output.split(' ')[2]
        return channel

    def update_built_charm(self):
        built_charm_repo = BUILT_CHARM_REPOS.get(self.publish)
        import ipdb; ipdb.set_trace()
        '''if not built_charm_repo:
            return
        output = self.cmd('bzr checkout $builtcharmrepo builds/weebl-built')
        cp -R builds/weebl-built/.bzr builds/weebl/
        rm -fr builds/weebl-built/builds
        log=$(bzr log -r-1 --line)
        cd builds/weebl
        bzr add
        bzr commit -m "$log"'''







    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('publish', nargs='?', default=False)
        return vars(parser.parse_args())

def main():
    output = Uploader().main()
    if output:
        pprint(output)


if __name__ == "__main__":
    sys.exit(main())

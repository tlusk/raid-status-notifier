#!/usr/bin/env python3

import sys
import re
import os
import pickle

from argparse import ArgumentParser
from subprocess import check_output
from pushover import init, Client
from configparser import ConfigParser


class RaidStatusChecker(object):
    def __init__(self, config):
        init(config.get("settings", "pushover_api_token"))
        self.client = Client(config.get("settings", "pushover_user_key"))
        self.btrfs_mount_points = [path for key, path in config.items("btrfs_mount_points")]

    def check_btrfs_stats(self):
        for mount_point in self.btrfs_mount_points:
            stats_filename = "data/btrfs-stats_%s.p" % mount_point[1:].replace("/", "-")

            device_stats = {}
            if os.path.exists(stats_filename):
                device_stats = pickle.load(open(stats_filename, "rb"))

            status = check_output(["sudo", "btrfs", "device", "stats", mount_point]).decode("utf-8").strip()
            new_errors = False
            regex = re.compile('\[/dev/(.*)\]\.(\S*)\s*(\d*)')

            for line in status.split('\n'):
                match = regex.match(line)
                if match is not None:
                    if match.group(1) not in device_stats:
                        device_stats[match.group(1)] = {}
                    previous_stats = device_stats[match.group(1)].get(match.group(2), 0)
                    if int(match.group(3)) > previous_stats:
                        device_stats[match.group(1)][match.group(2)] = int(match.group(3))
                        new_errors = True

            if not os.path.exists("data"):
                os.mkdir("data")

            pickle.dump(device_stats, open(stats_filename, "wb"))

            if new_errors is not False:
                self.client.send_message(status, title="BTRFS Errors: %s" % mount_point)

    def check_btrfs_drives(self):
        status = check_output(["sudo", "btrfs", "fi", "show", "-d"]).decode("utf-8").strip()

        regex = re.compile('(missing|warning)')
        if regex.match(status) is not None:
            self.client.send_message(status, title="BTRFS Array Error")

    def check_zfs_drives(self):
        status = check_output(["sudo", "zpool", "status", "-x"])
        if status != "all pools are healthy":
            self.client.send_message(status, title="ZFS Array Error")

    def run(self):
        self.check_zfs_drives()
        self.check_btrfs_stats()
        self.check_btrfs_drives()


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    parser = ArgumentParser()
    parser.add_argument("-c", "--config", action="store", help="Configuration File", metavar="CONFIGFILE")
    parser.set_defaults(config="settings.cfg")

    options = parser.parse_args(argv)

    config = ConfigParser()
    config.read(options.config)

    RaidStatusChecker(config).run()

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3

import sys
import re
import os
import pickle
import time

from argparse import ArgumentParser
from subprocess import check_output
from pushover import init, Client
from configparser import ConfigParser
from functools import wraps


def suppression_window(function):
    @wraps(function)
    def wrapper(inst, *args, **kwargs):
        last_checked_filename = "%s/last-checked_%s.p" % (inst.data_dir, function.__name__)

        last_checked_time = 0
        if os.path.exists(last_checked_filename):
            last_checked_time = pickle.load(open(last_checked_filename, "rb"))

        current_time = int(time.time())
        if current_time >= last_checked_time + inst.suppression_window:
            function(inst, *args, **kwargs)

            if not os.path.exists(inst.data_dir):
                os.mkdir(inst.data_dir)

            pickle.dump(current_time, open(last_checked_filename, "wb"))

    return wrapper


class RaidStatusChecker(object):
    def __init__(self, config):
        init(config.get("settings", "pushover_api_token"))
        self.client = Client(config.get("settings", "pushover_user_key"))
        self.btrfs_mount_points = [path for key, path in config.items("btrfs_mount_points")]
        self.data_dir = config.get("settings", "data_directory")
        self.suppression_window = int(config.get("settings", "suppression_window"))

    @suppression_window
    def check_btrfs_stats(self):
        for mount_point in self.btrfs_mount_points:
            stats_filename = "%s/btrfs-stats_%s.p" % (self.data_dir, mount_point[1:].replace("/", "-"))

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

            if not os.path.exists(self.data_dir):
                os.mkdir(self.data_dir)

            pickle.dump(device_stats, open(stats_filename, "wb"))

            if new_errors is not False:
                self.client.send_message(status, title="BTRFS Errors: %s" % mount_point)

    @suppression_window
    def check_btrfs_drives(self):
        status = check_output(["sudo", "btrfs", "fi", "show", "-d"]).decode("utf-8").strip()

        regex = re.compile('(missing|warning)')
        if regex.match(status) is not None:
            self.client.send_message(status, title="BTRFS Array Error")

    @suppression_window
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
    parser.add_argument("-c", "--config", action="store", help="Configuration File", metavar="CONFIG_FILE")
    parser.set_defaults(config="settings.cfg")

    options = parser.parse_args(argv)

    config = ConfigParser()
    config.read(options.config)

    RaidStatusChecker(config).run()

if __name__ == "__main__":
    sys.exit(main())

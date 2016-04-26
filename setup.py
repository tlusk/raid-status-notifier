#!/usr/bin/env python3

from setuptools import setup

reqs = ['python-pushover>=0.2']

setup(
    name='raid-status-notifier',
    version="1.0",
    url='https://github.com/tlusk/raid-status-notifier',
    author='Timothy Lusk',
    author_email='darkcube@gmail.com',
    description='BTRFS/ZFS Raid Status Notifier',
    license='MIT',
    packages=['raid_status_notifier'],
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={'console_scripts': [
        'raid-status-notifier = raid_status_notifier.main:main'
    ]},
    install_requires=reqs,
    zip_safe=False,
    test_suite='unittest2.collector',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ],
)
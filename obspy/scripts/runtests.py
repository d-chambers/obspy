#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A command-line program that runs all ObsPy tests.

All tests in ObsPy are located in the tests directory of each specific
module.

A few important command line arguments:
    --help : Print help message an exit.
    --no-report, --report : Do not ask and automatically (not) submit report
            to ObsPys' report server.
    --cov : Calculate and display test coverage.
    --network : Only run network tests (requires an internet connection).
    --all : Run both network and non-network tests.
    --keep-images : Store all images generated by tests in obspy's directory.

Also note, the test runner uses pytest under the hood so any pytest command
line argument is also accepted.

.. rubric:: Examples

(1) Run all local tests (ignoring tests requiring a network connection) on
    command line::
        $ obspy-runtests
(2) Run all tests on command line (including network tests)::
        $ obspy-runtests --all
(3) Run tests of module :mod:`obspy.io.mseed`::
        $ obspy-runtests io/mseed
(4) Run tests of multiple modules, e.g. :mod:`obspy.io.wav` and
    :mod:`obspy.io.sac`::
        $ obspy-runtests io/wav obspy/io/sac
(5) Run a specific test case::
        $ obspy-runtests core/tests/test_stats.py::TestStats::test_init
(6) Run tests and print a coverage report to screen including missed lines:
        $ obspy-runtests --cov obspy --cov-report term-missing
(7) Save the image outputs of the testsuite, called 'obspy_image_tests':
        $ obspy-runtests --keep-images
(8) Run the test suite, drop into a pdb debugging session for each failure:
        $ obspy-runtests --pdb

:copyright:
    The ObsPy Development Team (devs@obspy.org)
:license:
    GNU Lesser General Public License, Version 3
    (https://www.gnu.org/copyleft/lesser.html)
"""
import os
import re
import sys
from pathlib import Path

import pkg_resources
import requests

import obspy
from obspy.core.util.requirements import PYTEST_REQUIRES


# URL to upload json report
REPORT_URL = "tests.obspy.org"


def _ensure_tests_requirements_installed():
    """
    Ensure all the tests requirements are installed or raise exception.

    This function is intended to help less experienced users run the tests.
    """
    delimiters = (" ", "=", "<", ">", "!")
    patterns = '|'.join(map(re.escape, delimiters))
    msg = (f"\nNot all ObsPy's test requirements are installed. You need to "
           f"install them before using obspy-runtest. Example with pip: \n"
           f"\t$ pip install {' '.join(PYTEST_REQUIRES)}")
    for package_req in PYTEST_REQUIRES:
        # strip off any requirements, just get pkg_name
        pkg_name = re.split(patterns, package_req, maxsplit=1)[0]
        try:
            pkg_resources.get_distribution(pkg_name).version
        except pkg_resources.DistributionNotFound:
            raise ImportError(msg)


def main():
    """
    Entry point for setup.py.
    Wrapper for a profiler if requested otherwise just call run() directly.
    If profiling is enabled we disable interactivity as it would wait for user
    input and influence the statistics. However the -r option still works.
    """
    _ensure_tests_requirements_installed()

    import pytest
    from pytest_jsonreport.plugin import JSONReport

    report = (True if '--report' in sys.argv else
              False if '--no-report' in sys.argv else None)
    if '-h' in sys.argv or '--help' in sys.argv:
        print(__doc__)
        sys.exit(0)
    elif all(['--json-report-file' not in arg for arg in sys.argv]):
        sys.argv.append('--json-report-file=none')
    # Use default traceback for nicer report display
    sys.argv.append("--tb=native")

    here = Path().cwd()
    base_obspy_path = Path(obspy.__file__).parent
    plugin = JSONReport()
    os.chdir(base_obspy_path)
    try:
        status = pytest.main(plugins=[plugin])
    finally:
        os.chdir(here)
    upload_json_report(report=report, data=plugin.report)
    sys.exit(status)


def upload_json_report(report=None, data=None):
    """Upload the json report to ObsPy test server."""
    if report is None:
        msg = f"Do you want to report this to {REPORT_URL} ? [n]: "
        answer = input(msg).lower()
        report = 'y' in answer
    if report:
        # only include unique warnings.
        data['warnings'] = [
            dict(t) for t in {tuple(d.items()) for d in data['warnings']}
        ]
        response = requests.post(f"https://{REPORT_URL}/post/v2/", json=data)
        # get the response
        if response.status_code == 200:
            report_url = response.json().get('url', REPORT_URL)
            print('Your test results have been reported and are available at: '
                  '{}\nThank you!'.format(report_url))
        # handle errors
        else:
            print(f"Error: Could not sent a test report to {REPORT_URL}.")
            print(response.reason)


if __name__ == "__main__":
    main()

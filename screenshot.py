#!/usr/bin/env python
# encoding: utf8
""" Take a screenshot using ImageMagick's `import', and X window selection. """
from __future__ import unicode_literals, print_function, absolute_import

import os
import re
import sys
import argparse
import subprocess
from datetime import datetime

# TODO: Rewrite using PythonMagick or Wand?


class Setting(object):
    """ A setting descriptor with a default value. """

    def __init__(self, name, default=None, validator=None):
        """ Initialize with a default value, and a set of value limits. """
        self.name = name
        self.default = default
        self.value = None
        self.validator = validator

    def validate(self, value):
        """ Validate value. """
        if self.validator is not None and not self.validator(value):
            raise ValueError(
                "Setting '{!s}' - value {!r} does not pass validation".format(
                    self.name, value))

    def __get__(self, instance, owner_class=None):
        """ Getter, returns area as float. """
        if instance is None:
            return self
        if self.value is None:
            return self.default
        return self.value

    def __set__(self, instance, value):
        """ Setter, this makes the class a descriptor. """
        self.validate(value)
        self.value = value

    def __delete__(self, instance):
        """ Clear the descriptor. """
        if instance is not None:
            self.value = None


class FileName(object):
    """ Settings container object. """

    folder = Setting('folder', '/tmp', validator=os.path.isdir)
    prefix = Setting('prefix', '')
    imgtype = Setting('format', 'png',
                      validator=lambda x: x in set(('png', 'jpg', 'gif')))
    datefmt = Setting('datefmt', '%Y-%m-%d_%H-%M')
    padding = Setting('padding', 4)

    def suggest_filename(self):
        """ Suggest a filename based on settings. """
        maxint = 0
        max_int_pattern = re.compile(r"^%s([0-9]+)_.*" % self.prefix)
        path = os.path.abspath(self.folder)
        for f in os.listdir(path):
            match = max_int_pattern.match(f)
            if os.path.isfile(os.path.join(path, f)) and match:
                if int(match.group(1)) > maxint:
                    maxint = int(match.group(1))

        filename_fmt = '{{!s}}{{:0{:d}d}}_{{!s}}.{{!s}}'.format(self.padding)
        filename = filename_fmt.format(self.prefix,
                                       maxint + 1,
                                       datetime.now().strftime(self.datefmt),
                                       self.imgtype)

        return os.path.join(path, filename)

    def parse_filename(self, path):
        """ Set settings and return a filename based on filename. """
        folder, rest = os.path.split(path)
        if folder:
            self.folder = folder

        filename, ext = os.path.splitext(rest)
        if ext:
            self.imgtype = ext[1:].lower()

        return os.path.join(
            os.path.abspath(self.folder),
            '{!s}{!s}.{!s}'.format(self.prefix, filename, self.imgtype))

    def __call__(self, filename=None):
        """ Calculate the file name for the next screenshot. """
        if filename:
            filename = self.parse_filename(filename)
        else:
            filename = self.suggest_filename()
        if os.path.exists(filename):
            raise ValueError("File exists: %s" % filename)
        return filename

    def __str__(self):
        """ Print string version. """
        return ', '.join(
            ("%s=[%s]" % (key, getattr(self, key)) for
             key in ('folder', 'prefix', 'format', 'datefmt')))


def fetch_window():
    """ Wait for the user to select an X window. """
    process = subprocess.Popen(["xwininfo", ], stdout=subprocess.PIPE)
    out, _ = process.communicate()

    if process.returncode != 0:
        raise Exception("Exit code was %d" % process.returncode)

    result = re.search(r'^xwininfo: Window id: (?P<window>0x[0-9A-Za-z]+) .*',
                       out, re.MULTILINE)
    if not result:
        raise Exception("Error fetching window.")
    return result.group('window')


def take_screenshot(dest, window=None, frame=True):
    """ Take a screenshot with `import'. """
    args = ['import', ]

    if window is not None:
        args.extend(['-window', str(window), ])
        if frame:
            args.append('-frame')

    args.append(dest)

    process = subprocess.Popen(args,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)

    out, err = process.communicate()
    ret = process.returncode

    if (ret != 0) or err:
        raise Exception("Exit code was %d: %s" % (ret, err))


def excepthook(exc, val, tb):
    """ Print type and value, raise SystemExit. """
    raise SystemExit("%s: %s" % (exc.__name__, str(val)))


def main(args=None):
    """ Script invoke. """
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument(
        '-w', '--window',
        dest='window',
        default=False,
        action='store_true',
        help='Screenshot of a full window')
    parser.add_argument(
        '-b', '--border',
        dest='border',
        default=False,
        action='store_true',
        help='Include window manager decorations in windowed screenshot')
    parser.add_argument(
        '-d', '--dir',
        dest='folder',
        metavar='<dir>',
        help='Store screenshot(s) in <dir>')
    parser.add_argument(
        '-p', '--file-prefix',
        dest='prefix',
        metavar='<str>',
        help='Prefix screenshot file with <str>')
    parser.add_argument(
        '-t', '--type',
        dest='format',
        metavar='<format>',
        default='png',
        help='Set the screenshot file type to <format>')
    parser.add_argument(
        '-f', '--file',
        dest='file',
        metavar='<file>',
        help='Ignore all other options and write directly to <file>')

    args = parser.parse_args(args)
    sys.excepthook = excepthook
    filename = window = None

    f = FileName()
    for s in ('folder', 'prefix', 'format'):
        if getattr(args, s):
            setattr(f, s, getattr(args, s))
    filename = f(args.file)

    if args.window:
        window = fetch_window()

    print('Taking screenshot with settings: {!s}'.format(f))
    take_screenshot(filename, window=window, frame=args.border)
    print('Took screenshot: {!s}'.format(filename))


if __name__ == '__main__':
    main()

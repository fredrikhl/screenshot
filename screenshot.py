#!/usr/bin/env python
# encoding: utf8
""" Take a screenshot using ImageMagick's `import', and X window selection. """
from __future__ import unicode_literals, print_function, absolute_import

import argparse
import datetime
import logging
import os
import re
import subprocess
import io
import select

logger = logging.getLogger('screenshot')


class Setting(object):
    """ A setting descriptor with a default value. """

    def __init__(self, name, default=None):
        """ Initialize with a default value, and a set of value limits. """
        self.name = name
        self.default = default

    def __repr__(self):
        return ('{cls.__name__}({obj.name!r}, default={obj.default!r})'
                ).format(cls=type(self), obj=self)

    @property
    def attr(self):
        return '_{cls.__name__}__{obj.name}_value_0x{_id:02x}'.format(
            cls=type(self),
            obj=self,
            _id=id(self))

    def __get__(self, obj, cls=None):
        if obj is None:
            return self
        return getattr(obj, self.attr, self.default)

    def __set__(self, obj, value):
        setattr(obj, self.attr, value)

    def __delete__(self, obj):
        if hasattr(obj, self.attr):
            delattr(obj, self.attr)


class FileNamer(object):
    """ Settings container object. """

    directory = Setting('directory', default='')
    namefmt = Setting('namefmt', default='screenshot_{number}_{datetime}')
    datefmt = Setting('datefmt', default='%Y-%m-%d_%H-%M')
    ext = Setting('ext', default='png')
    digits = Setting('digits', default=4)

    def __init__(self, **kwargs):
        cls = type(self)
        for key in kwargs:
            if hasattr(cls, key) and isinstance(getattr(cls, key), Setting):
                setattr(self, key, kwargs[key])

    def __iter__(self):
        def settings_generator():
            cls = type(self)
            for name in dir(cls):
                if isinstance(getattr(cls, name), Setting):
                    yield name
        return settings_generator()

    def __repr__(self):
        data = dict((name, getattr(self, name))
                    for name in self)
        args = ', '.join('{name}={value!r}'.format(name=name, value=data[name])
                         for name in data)
        return '{cls.__name__}({attr})'.format(cls=type(self), attr=args)

    def format_datetime(self, d):
        return d.strftime(self.datefmt)

    def format_number(self, i):
        return '{number:0{padding:d}d}'.format(number=i, padding=self.digits)

    def format_basename(self, datetime, number):
        data = {
            'datetime': datetime,
            'number': number,
        }
        return self.namefmt.format(**data)

    def _find_max(self):
        path = os.path.abspath(self.directory)
        max_int_pattern = re.compile(
            '^' + self.format_basename('.*', '(?P<number>[0-9]+)') +
            '\\' + os.path.extsep + '.*$')
        logger.debug('pattern: %s', max_int_pattern.pattern)

        def _iter_matches():
            yield 0
            for f in os.listdir(path):
                match = max_int_pattern.match(f)
                if os.path.isfile(os.path.join(path, f)) and match:
                    yield int(match.group('number'))

        return max(_iter_matches())

    def suggest_filename(self):
        """ Suggest a filename based on settings. """
        basename = self.format_basename(
            self.format_datetime(datetime.datetime.now()),
            self.format_number(self._find_max() + 1))
        filename = os.path.extsep.join((basename, self.ext))
        logger.debug('filename: %r', filename)
        return os.path.join(self.directory, filename)

    def __call__(self, filename=None):
        """ Calculate the file name for the next screenshot. """
        filename = self.suggest_filename()
        if os.path.exists(filename):
            raise ValueError("File exists: %s" % filename)
        return filename


def run_command(*cmd):
    logger.debug('running %r', cmd)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding='utf-8',
    )

    stdout = io.StringIO()
    stderr = io.StringIO()
    # process output
    log_io = {
        proc.stdout: (
            (lambda line: logger.debug('[%d] stdout: %s',
                                       proc.pid, line.rstrip())),
            (lambda line: stdout.write(line)),
        ),
        proc.stderr: (
            (lambda line: logger.warning('[%d] stderr: %s',
                                         proc.pid, line.rstrip())),
            (lambda line: stderr.write(line)),
        ),
    }

    while log_io:
        ready, _, _ = select.select(log_io.keys(), [], [])
        for fd in ready:
            handlers = log_io[fd]
            line = fd.readline()
            if line:
                for fn in handlers:
                    fn(line)
            else:
                fd.close()
                del log_io[fd]

    # handle exit
    status = proc.wait()
    level = logging.DEBUG
    etype = 'exit'
    err = False

    if status != 0:
        level = logging.ERROR
        err = True
        if os.WIFSIGNALED(status):
            status = os.WTERMSIG(status)
            etype = 'signal'
        else:
            status = os.WSTOPSIG(status)

    logger.log(level, 'process pid=%r %s=%r', proc.pid, etype, status)
    if err:
        raise RuntimeError('command %r failed' % (cmd,))
    return stdout.getvalue(), stderr.getvalue()


def _fetch_window(*args):
    """ Wait for the user to select an X window. """
    out, _ = run_command('xwininfo', *args)

    result = re.search(r'^xwininfo: Window id: (?P<window>0x[0-9A-Za-z]+) .*',
                       out, re.MULTILINE)
    if not result:
        logger.error("xwininfo - no window id in output")
        raise RuntimeError("unable to fetch window")

    return result.group('window')


def fetch_window():
    return _fetch_window()


def verify_window_root():
    return _fetch_window('-root')


def verify_window_id(window_id):
    return _fetch_window('-id', '0x' + format(window_id, 'x'))


def verify_window_name(window_name):
    return _fetch_window('-name', str(window_name))


def take_screenshot(dest, window=None, frame=True):
    """ Take a screenshot with `import'. """
    cmd = ['import', ]

    if window is not None:
        cmd.extend(['-window', str(window), ])
        if frame:
            cmd.append('-frame')

    cmd.append(dest)

    out, _ = run_command(*cmd)


def excepthook(exc, val, tb):
    """ Print type and value, raise SystemExit. """
    raise SystemExit("%s: %s" % (exc.__name__, str(val)))


def window_type(value):
    """ validate and convert a hex/oct/dec string -> int """
    value = value.strip().lower()
    if value.startswith('0x'):
        value = int(value[2:], 16)
    elif value.startswith('0o'):
        value = int(value[2:], 8)
    else:
        value = int(value, 10)
    return value


def writable_dir(value):
    if not os.path.exists(value):
        raise ValueError("%r does not exist" % (value, ))
    if not os.path.isdir(value):
        raise ValueError("%r is not a directory" % (value, ))
    if not os.access(value, os.R_OK | os.X_OK):
        raise ValueError("%r is not writable" % (value, ))
    return value


def datetime_format(s):
    # Just make sure it works
    res = datetime.datetime.now().strftime(s)
    if len(res) < 1:
        raise ValueError("datetime format %r results in empty string" % (s, ))
    base = datetime.datetime.fromtimestamp(0).strftime(s)
    if res == base:
        raise ValueError("datetime format %r has no date or time components" %
                         (s, ))
    return s


DEFAULT_DIRECTORY = '/tmp'
DEFAULT_NAMEFMT = '{number}_{datetime}'
DEFAULT_DATEFMT = '%Y-%m-%d_%H-%M'
DEFAULT_EXT = 'png'
VALID_EXT = set(('png', 'gif', 'jpg'))


def main(args=None):
    """ Script invoke. """
    parser = argparse.ArgumentParser(description=__doc__)

    what_args = parser.add_argument_group('selection')
    window_args = what_args.add_mutually_exclusive_group()

    window_args.add_argument(
        '-w', '--window',
        dest='window_select',
        action='store_true',
        default=False,
        help='select a window to screenshot')
    window_args.add_argument(
        '-W', '--window-id',
        dest='window_id',
        type=window_type,
        help='take screenshot of window with ID %(metavar)s',
        metavar='<id>')
    window_args.add_argument(
        '-r', '--window-root',
        dest='window_root',
        action='store_true',
        default=False,
        help='take screenshot of the root window',
    )
    window_args.add_argument(
        '--window-name',
        dest='window_name',
        help='take screenshot of window with ID %(metavar)s',
        metavar='<name>',
    )

    what_args.add_argument(
        '-b', '--border',
        dest='border',
        action='store_true',
        default=False,
        help='include window manager decorations in windowed screenshot')

    output_args = parser.add_argument_group('output')
    output_args.add_argument(
        '-d', '--dir',
        dest='directory',
        type=writable_dir,
        default=DEFAULT_DIRECTORY,
        help='Store screenshot(s) in %(metavar)s (%(default)s)',
        metavar='<dir>',
    )
    output_args.add_argument(
        '--date-format',
        dest='datefmt',
        type=datetime_format,
        default=DEFAULT_DATEFMT,
        help='use format %(metavar)s for datetime (%(default)s)',
        metavar='<format>',
    )
    output_args.add_argument(
        '--format',
        dest='namefmt',
        default=DEFAULT_NAMEFMT,
        help='use format %(metavar)s for the filename (%(default)s)',
        metavar='<format>',
    )
    output_args.add_argument(
        '-t', '--type',
        dest='ext',
        choices=VALID_EXT,
        default=DEFAULT_EXT,
        help='Set the screenshot file type to %(metavar)s (%(default)s)',
        metavar='<ext>',
    )
    output_args.add_argument(
        '-f', '--file',
        dest='filename',
        help='ignore all other options and write directly to %(metavar)s',
        metavar='<file>',
    )

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(levelName)s - %(name) - %(message)',
    )

    args = parser.parse_args(args)
    # sys.excepthook = excepthook

    namer = FileNamer(
        directory=args.directory,
        namefmt=args.namefmt,
        datefmt=args.datefmt,
        ext=args.ext
    )

    if args.filename:
        filename = args.filename
    else:
        filename = namer()

    if args.window_select:
        window = fetch_window()
    elif args.window_id:
        window = verify_window_id(args.window_id)
    elif args.window_name:
        window = verify_window_name(args.window_name)
    elif args.window_root:
        window = verify_window_root()
    else:
        window = None

    logger.debug('taking screenshot with settings: %r', namer)
    take_screenshot(filename, window=window, frame=args.border)
    logger.info('screenshot written to %r', filename)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s")
    main()

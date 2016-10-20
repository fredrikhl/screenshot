# screenshot

This scripts takes screenshots, and places them in a configured folder with a
pre-defined name syntax.

When invoked, the user will be prompted to select a desktop area or a window.


## Usage

```bash
$ python screenshot.py -h
usage: screenshot.py [-h] [-w] [-b] [-d <dir>] [-p <str>] [-t <format>]
                     [-f <file>]

Take a screenshot using ImageMagick's `import', and X window selection.

optional arguments:
  -h, --help            show this help message and exit
  -w, --window          Screenshot of a full window
  -b, --border          Include window manager decorations in windowed
                        screenshot
  -d <dir>, --dir <dir>
                        Store screenshot(s) in <dir>
  -p <str>, --file-prefix <str>
                        Prefix screenshot file with <str>
  -t <format>, --type <format>
                        Set the screenshot file type to <format>
  -f <file>, --file <file>
                        Ignore all other options and write directly to <file>
```


## Examples

Take a windowed screenshot with window manager decorations:

```bash
$ python screenshot.py --window --border --file 'somewindow.png'
```

Take a screenshot of a desktop area, and place it in a folder

```bash
$ python screenshot.py --file-prefix area --type jpg --dir /tmp/
```


## Requirements

This script uses [[ImageMagick]] (`import`) to take screenshots, and [[X.Org]]
`xwininfo` to select windows.


## TODO

Replace `import` and `xwininfo` subprocess calls with bindings to libraries.


  [ImageMagick]: http://www.imagemagick.org/
  [X.Org]: https://www.x.org/

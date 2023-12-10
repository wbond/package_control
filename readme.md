# Package Control

The [Sublime Text](http://www.sublimetext.com) package manager. 
It allows users to find, install and keep packages up to date.

## Installation

To install:

 - Open the command palette and type "Install Package Control"
 - or, use the menu *Tools > Install Package Control*

Until Package Control 4.0 is available via packagecontrol.io, call the following command from Sublime Text's console.

```py
from urllib.request import urlretrieve;urlretrieve(url="https://github.com/wbond/package_control/releases/latest/download/Package.Control.sublime-package", filename=sublime.installed_packages_path() + '/Package Control.sublime-package')
```

## Usage

All of the primary features of Package Control are exposed through the command palette.

To install a package:

 - Open the command palette
 - Type "Install Package"
 - Select a package from the list

For more features, see https://packagecontrol.io/docs/usage.

## Documentation

The documentation for Package Control can be found at https://packagecontrol.io/docs.

## Bug Reports

If you find a bug with Package Control, please follow the directions at https://packagecontrol.io/docs/issues to submit an issue.

## License

Package Control is licensed under the MIT license.

```
Copyright (c) 2011-2023 Will Bond <will@wbond.net>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

# Package Control

The [Sublime Text](http://www.sublimetext.com) package manager. Visit
[packagecontrol.io](https://packagecontrol.io) for
[installation instructions](https://packagecontrol.io/installation), a list of
[available packages](https://packagecontrol.io/browse) and detailed
[documentation](https://packagecontrol.io/docs).

## License

Package Control is licensed under the MIT license.

All of the source code (except for `package_control/semver.py` and
`package_control/http/x509.py`), is under the license:

```
Copyright (c) 2011-2015 Will Bond <will@wbond.net>

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

`package_control/semver.py` is under the license:

```
Copyright (c) 2013 Zachary King, FichteFoll

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

`package_control/http/x509.py` is under the license:

```
Copyright (c) 2007 the Python-ASN1 authors, 2014-2015 Will Bond <will@wbond.net>

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

## How to report an issue

The following information must be submitted to speed up the bug review process:

### Summary 
Fill in a short, one sentence description of the problem. For example, "Saving file in .tiff format causes program to exit."

### Details 
This is your long version of the issue. Be as specific as possible. Make sure to give a rational, complete depiction of the problem; saying "The print button is broken" does not describe the problem enough.

### Reproducibility 
This is a very important field. Does this happen every time you follow some procedure? Does it only happen on Tuesdays? Was it only once?

### Steps to Reproduce 
As discussed earlier, provide the steps you followed to reach the bug. If the problem cannot be reproduced, say so in "Reproducibility" and give the steps to the best of your memory.

### Software Version 
Your current version can be viewed by accessing the Preferences > Package Settings > Package Control > Settings – Default under the user_agent parameter

### Operating System 
There are many ways to determine the operating system you are running, but running uname -sr in a terminal is one way to do it.

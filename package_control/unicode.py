import sublime
import os
import locale


def unicode_from_os(e):
    """
    This is needed as some exceptions coming from the OS are
    already encoded and so just calling unicode(e) will result
    in an UnicodeDecodeError as the string isn't in ascii form.

    :param e:
        The exception to get the value of

    :return:
        The unicode version of the exception message
    """

    fallback_encodings = ['utf-8', 'cp1252']

    # Sublime Text on OS X does not seem to report the correct encoding
    # so we hard-code that to UTF-8
    encoding = 'UTF-8' if os.name == 'darwin' else locale.getpreferredencoding()

    if int(sublime.version()) > 3000:
        return str(e)

    try:
        if isinstance(e, Exception):
            e = e.message

        if isinstance(e, unicode):
            return e

        if isinstance(e, int):
            e = str(e)

        return unicode(e, encoding)

    # If the "correct" encoding did not work, try some defaults, and then just
    # obliterate characters that we can't seen to decode properly
    except UnicodeDecodeError:
        for encoding in fallback_encodings:
            try:
                return unicode(e, encoding, errors='strict')
            except:
                pass
    return unicode(e, errors='replace')

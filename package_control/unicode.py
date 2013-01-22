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

    try:
        # Sublime Text on OS X does not seem to report the correct encoding
        # so we hard-code that to UTF-8
        encoding = 'UTF-8' if os.name == 'darwin' else locale.getpreferredencoding()
        return unicode(str(e), encoding)

    # If the "correct" encoding did not work, try some defaults, and then just
    # obliterate characters that we can't seen to decode properly
    except UnicodeDecodeError:
        encodings = ['utf-8', 'cp1252']
        for encoding in encodings:
            try:
                return unicode(str(e), encoding, errors='strict')
            except:
                pass
    return unicode(str(e), errors='replace')

from textwrap import dedent
import re


def format(string, params=None, strip=True, indent=None):
    """
    Takes a multi-line string and does the following:

     - dedents
     - removes a single leading newline if the second character is not a newline also
     - converts newlines with text before and after into a single line
     - removes a single trailing newline if the second-to-laster character is not a newline also

    :param string:
        The string to format

    :param params:
        Params to interpolate into the string

    :param strip:
        If the last newline in the string should be removed

    :param indent:
        If all lines should be indented by a set indent after being dedented

    :return:
        The formatted string
    """

    output = string

    # Only dedent if not a single-line string. This allows for
    # single-line-formatted string to be printed that include intentional
    # whitespace.
    if output.find(u'\n') != -1:
        output = dedent(output)

    # If the string starts with just a newline, we want to trim it because
    # it is a side-effect of the code formatting, but if there are two newlines
    # then that means we intended there to be newlines at the beginning
    if output[0] == u'\n' and output[1] != u'\n':
        output = output[1:]

    # Unwrap lines, taking into account bulleted lists, ordered lists and
    # underlines consisting of = signs
    if output.find(u'\n') != -1:
        output = re.sub(u'(?<=\\S)\n(?=[^ \n\t\d\*\-=])', u' ', output)

    # By default we want to trim a single trailing newline from a string since
    # that is likely from the code formatting, but that trimming is prevented
    # if strip == False, or if there are two trailing newlines, which means we
    # actually wanted whitespace at the end
    if output[-1] == u'\n' and strip and output[-2] != u'\n':
        output = output[0:-1]

    if params is not None:
        output = output % params

    if indent is not None:
        output = indent + output.replace(u'\n', u'\n' + indent)

    return output

import time
import threading
import unittest
import re

import sublime



LAST_COMMIT_TIMESTAMP = '2014-11-28 20:54:15'
LAST_COMMIT_VERSION = re.sub('[ :\-]', '.', LAST_COMMIT_TIMESTAMP)

CLIENT_ID = ''
CLIENT_SECRET = ''


class StringQueue():
    def __init__(self):
        self.lock = threading.Lock()
        self.queue = ''

    def write(self, data):
        self.lock.acquire()
        self.queue += data
        self.lock.release()

    def get(self):
        self.lock.acquire()
        output = self.queue
        self.queue = ''
        self.lock.release()
        return output

    def flush(self):
        pass


def runner(window, test_classes):
    """
    Runs tests in a thread and outputs the results to an output panel

    :param window:
        A sublime.Window object to use to display the results

    :param test_classes:
        A unittest.TestCase class, or list of classes
    """

    output = StringQueue()

    panel = window.get_output_panel('package_control_tests')
    panel.settings().set('word_wrap', True)

    window.run_command('show_panel', {'panel': 'output.package_control_tests'})

    threading.Thread(target=show_results, args=(panel, output)).start()
    threading.Thread(target=do_run, args=(test_classes, output)).start()


def do_run(test_classes, output):
    if not isinstance(test_classes, list) and not isinstance(test_classes, tuple):
        test_classes = [test_classes]

    suite = unittest.TestSuite()

    loader = unittest.TestLoader()
    for test_class in test_classes:
        suite.addTest(loader.loadTestsFromTestCase(test_class))

    result = unittest.TextTestRunner(stream=output, verbosity=1).run(suite)
    output.write("\x04")


def show_results(panel, output):
    def write_to_panel(chars):
        sublime.set_timeout(lambda: panel.run_command('package_control_insert', {'string': chars}), 10)

    write_to_panel(u'Running Package Control Tests\n\n')

    while True:
        chars = output.get()

        if chars == '':
            time.sleep(0.1)
            continue

        if chars[-1] == "\x04":
            chars = chars[0:-1]
            write_to_panel(chars)
            break

        write_to_panel(chars)

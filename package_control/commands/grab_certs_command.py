import os
import re
import socket
import threading

try:
    # Python 3
    from urllib.parse import urlparse
except (ImportError):
    # Python 2
    from urlparse import urlparse

import sublime
import sublime_plugin

from ..show_error import show_error
from ..open_compat import open_compat
from ..ca_certs import find_root_ca_cert
from ..thread_progress import ThreadProgress
from ..package_manager import PackageManager


class GrabCertsCommand(sublime_plugin.WindowCommand):
    """
    A command that extracts the CA certs for a domain name, allowing a user to
    fetch packages from sources other than those used by the default channel
    """

    def run(self):
        panel = self.window.show_input_panel('Domain Name', 'example.com', self.on_done,
            None, None)
        panel.sel().add(sublime.Region(0, panel.size()))

    def on_done(self, domain):
        """
        Input panel handler - grabs the CA certs for the domain name presented

        :param domain:
            A string of the domain name
        """

        domain = domain.strip()

        # Make sure the user enters something
        if domain == '':
            show_error(u"Please enter a domain name, or press cancel")
            self.run()
            return

        # If the user inputs a URL, extract the domain name
        if domain.find('/') != -1:
            parts = urlparse(domain)
            if parts.hostname:
                domain = parts.hostname

        # Allow _ even though it technically isn't valid, this is really
        # just to try and prevent people from typing in gibberish
        if re.match('^(?:[a-zA-Z0-9]+(?:[\-_]*[a-zA-Z0-9]+)*\.)+[a-zA-Z]{2,6}$', domain, re.I) == None:
            show_error(u"Unable to get the CA certs for \"%s\" since it does not appear to be a validly formed domain name" % domain)
            return

        # Make sure it is a real domain
        try:
            socket.gethostbyname(domain)
        except (socket.gaierror) as e:
            error = unicode_from_os(e)
            show_error(u"Error trying to lookup \"%s\":\n\n%s" % (domain, error))
            return

        manager = PackageManager()

        thread = GrabCertsThread(manager.settings, domain)
        thread.start()
        ThreadProgress(thread, 'Grabbing CA certs for %s' % domain,
            'CA certs for %s added to settings' % domain)


class GrabCertsThread(threading.Thread):
    """
    A thread to run openssl so that the Sublime Text UI does not become frozen
    """

    def __init__(self, settings, domain):
        self.settings = settings
        self.domain = domain
        threading.Thread.__init__(self)

    def run(self):
        cert, cert_hash = find_root_ca_cert(self.settings, self.domain)

        certs_dir = os.path.join(sublime.packages_path(), 'User',
            'Package Control.ca-certs')
        if not os.path.exists(certs_dir):
            os.mkdir(certs_dir)

        cert_path = os.path.join(certs_dir, self.domain + '-ca.crt')
        with open_compat(cert_path, 'w') as f:
            f.write(cert)

        def save_certs():
            settings = sublime.load_settings('Package Control.sublime-settings')
            certs = settings.get('certs', {})
            if not certs:
                certs = {}
            certs[self.domain] = [cert_hash, cert_path]
            settings.set('certs', certs)
            sublime.save_settings('Package Control.sublime-settings')

        sublime.set_timeout(save_certs, 10)

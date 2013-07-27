import os
import hashlib

from .cmd import Cli


class CaCertExtractor(Cli):

    def fetch(self, domain):
        name = 'openssl'
        if os.name == 'nt':
            name += '.exe'

        binary = self.find_binary(name)
        if binary and os.path.isdir(binary):
            full_path = os.path.join(binary, name)
            if os.path.exists(full_path):
                binary = full_path

        if not binary:
            show_error((u'Unable to find %s. Please set the openssl_binary ' +
                u'setting by accessing the Preferences > Package Settings > ' +
                u'Package Control > Settings \u2013 User menu entry. The ' +
                u'Settings \u2013 Default entry can be used for reference, ' +
                u'but changes to that will be overwritten upon next upgrade.') % name)
            return False

        args = [binary, 's_client', '-showcerts', '-connect', domain + ':443']
        result = self.execute(args, os.path.dirname(binary))

        certs = []
        temp = []

        in_block = False
        for line in result.splitlines():
            if line.find('BEGIN CERTIFICATE') != -1:
                in_block = True
            if in_block:
                temp.append(line)
            if line.find('END CERTIFICATE') != -1:
                in_block = False
                certs.append(u"\n".join(temp))
                temp = []

        # Remove the cert for the domain itself, just leaving the
        # chain cert and the CA cert
        certs.pop(0)

        lines = []
        for cert in certs:
            args = [binary, 'x509', '-inform', 'PEM', '-text']
            result = self.execute(args, os.path.dirname(binary), cert)
            lines.append(result)

        cert = u"\n".join(lines)
        cert_hash = hashlib.md5(cert.encode('utf-8')).hexdigest()

        return [cert, cert_hash]

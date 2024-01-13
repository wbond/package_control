import os.path
import sys

try:
    from .oscrypto import use_ctypes, use_openssl

    use_ctypes()

    # On Linux we need to use the version of OpenSSL included with Sublime Text
    # to prevent conflicts between two different versions of OpenSSL being
    # dynamically linked. On ST3, we can't use oscrypto for OpenSSL stuff since
    # it has OpenSSL statically linked, and we can't dlopen() that.
    # ST 4081 broke sys.executable to return "sublime_text", but other 4xxx builds
    # will contain "plugin_host".
    if sys.version_info[:2] == (3, 8) and sys.platform == 'linux' and (
            'sublime_text' in sys.executable or
            'plugin_host' in sys.executable):
        install_dir = os.path.dirname(sys.executable)
        try:
            use_openssl(
                os.path.join(install_dir, 'libcrypto.so.1.1'),
                os.path.join(install_dir, 'libssl.so.1.1')
            )
        except RuntimeError:
            pass  # runtime error may be raised, when reloading modules.

except ImportError:
    pass

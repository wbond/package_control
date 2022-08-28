# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import re

from .. import _backend_config
from .._errors import pretty_message
from .._ffi import get_library, register_ffi
from ..errors import LibraryNotFoundError

from cffi import FFI


__all__ = [
    'is_libressl',
    'libcrypto',
    'libressl_version',
    'libressl_version_info',
    'version',
    'version_info',
]

libcrypto_path = _backend_config().get('libcrypto_path')
if libcrypto_path is None:
    libcrypto_path = get_library('crypto', 'libcrypto.dylib', '42')
if not libcrypto_path:
    raise LibraryNotFoundError('The library libcrypto could not be found')

try:
    vffi = FFI()
    vffi.cdef("const char *SSLeay_version(int type);")
    version_string = vffi.string(vffi.dlopen(libcrypto_path).SSLeay_version(0)).decode('utf-8')
except (AttributeError):
    vffi = FFI()
    vffi.cdef("const char *OpenSSL_version(int type);")
    version_string = vffi.string(vffi.dlopen(libcrypto_path).OpenSSL_version(0)).decode('utf-8')

is_libressl = 'LibreSSL' in version_string

version_match = re.search('\\b(\\d\\.\\d\\.\\d[a-z]*)\\b', version_string)
if not version_match:
    version_match = re.search('(?<=LibreSSL )(\\d\\.\\d(\\.\\d)?)\\b', version_string)
if not version_match:
    raise LibraryNotFoundError('Error detecting the version of libcrypto')
version = version_match.group(1)
version_parts = re.sub('(\\d)([a-z]+)', '\\1.\\2', version).split('.')
version_info = tuple(int(part) if part.isdigit() else part for part in version_parts)

# LibreSSL is compatible with libcrypto from OpenSSL 1.0.1
libressl_version = ''
libressl_version_info = tuple()
if is_libressl:
    libressl_version = version
    libressl_version_info = version_info
    version = '1.0.1'
    version_info = (1, 0, 1)

ffi = FFI()

libcrypto = ffi.dlopen(libcrypto_path)
register_ffi(libcrypto, ffi)

if version_info < (0, 9, 8):
    raise LibraryNotFoundError(pretty_message(
        '''
        OpenSSL versions older than 0.9.8 are not supported - found version %s
        ''',
        version
    ))

if version_info < (1, 1):
    ffi.cdef("""
        void ERR_load_crypto_strings(void);
        void ERR_free_strings(void);
    """)


if version_info >= (3, ):
    ffi.cdef("""
        typedef ... OSSL_LIB_CTX;
        typedef ... OSSL_PROVIDER;

        int OSSL_PROVIDER_available(OSSL_LIB_CTX *libctx, const char *name);
        OSSL_PROVIDER *OSSL_PROVIDER_load(OSSL_LIB_CTX *libctx, const char *name);
    """)

# The typedef uintptr_t lines here allow us to check for a NULL pointer,
# without having to redefine the structs in our code. This is kind of a hack,
# but it should cause problems since we treat these as opaque.
ffi.cdef("""
    typedef ... EVP_MD;
    typedef uintptr_t EVP_CIPHER_CTX;
    typedef ... EVP_CIPHER;
    typedef ... ENGINE;
    typedef uintptr_t EVP_PKEY;
    typedef uintptr_t X509;
    typedef uintptr_t DH;
    typedef uintptr_t RSA;
    typedef uintptr_t DSA;
    typedef uintptr_t EC_KEY;
    typedef ... EVP_MD_CTX;
    typedef ... EVP_PKEY_CTX;
    typedef ... BN_GENCB;
    typedef ... BIGNUM;

    unsigned long ERR_get_error(void);
    char *ERR_error_string(unsigned long e, char *buf);
    unsigned long ERR_peek_error(void);

    void OPENSSL_config(const char *config_name);

    EVP_CIPHER_CTX *EVP_CIPHER_CTX_new(void);
    void EVP_CIPHER_CTX_free(EVP_CIPHER_CTX *ctx);

    int EVP_CIPHER_CTX_set_key_length(EVP_CIPHER_CTX *x, int keylen);
    int EVP_CIPHER_CTX_set_padding(EVP_CIPHER_CTX *x, int padding);
    int EVP_CIPHER_CTX_ctrl(EVP_CIPHER_CTX *ctx, int type, int arg, void *ptr);

    const EVP_CIPHER *EVP_aes_128_cbc(void);
    const EVP_CIPHER *EVP_aes_192_cbc(void);
    const EVP_CIPHER *EVP_aes_256_cbc(void);
    const EVP_CIPHER *EVP_des_cbc(void);
    const EVP_CIPHER *EVP_des_ede_cbc(void);
    const EVP_CIPHER *EVP_des_ede3_cbc(void);
    const EVP_CIPHER *EVP_rc4(void);
    const EVP_CIPHER *EVP_rc2_cbc(void);

    int EVP_EncryptInit_ex(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                    ENGINE *impl, const char *key,
                    const char *iv);
    int EVP_EncryptUpdate(EVP_CIPHER_CTX *ctx, char *out, int *outl,
                    const char *in, int inl);
    int EVP_EncryptFinal_ex(EVP_CIPHER_CTX *ctx, char *out, int *outl);

    int EVP_DecryptInit_ex(EVP_CIPHER_CTX *ctx, const EVP_CIPHER *cipher,
                    ENGINE *impl, const char *key,
                    const char *iv);
    int EVP_DecryptUpdate(EVP_CIPHER_CTX *ctx, char *out, int *outl,
                    const char *in, int inl);
    int EVP_DecryptFinal_ex(EVP_CIPHER_CTX *ctx, char *out, int *outl);

    EVP_PKEY *d2i_AutoPrivateKey(EVP_PKEY **a, const char **pp,
                    long length);
    EVP_PKEY *d2i_PUBKEY(EVP_PKEY **a, const char **pp, long length);
    int i2d_PUBKEY(EVP_PKEY *a, char **pp);
    void EVP_PKEY_free(EVP_PKEY *key);

    X509 *d2i_X509(X509 **px, const char **in, int len);
    int i2d_X509(X509 *x, char **out);
    EVP_PKEY *X509_get_pubkey(X509 *x);
    void X509_free(X509 *a);

    RSA *EVP_PKEY_get1_RSA(EVP_PKEY *pkey);
    void RSA_free(RSA *r);

    int RSA_public_encrypt(int flen, const char *from,
                    char *to, RSA *rsa, int padding);
    int RSA_private_encrypt(int flen, const char *from,
                    char *to, RSA *rsa, int padding);
    int RSA_public_decrypt(int flen, const char *from,
                    char *to, RSA *rsa, int padding);
    int RSA_private_decrypt(int flen, const char *from,
                    char *to, RSA *rsa, int padding);

    int EVP_DigestUpdate(EVP_MD_CTX *ctx, const void *d, unsigned int cnt);

    const EVP_MD *EVP_md5(void);
    const EVP_MD *EVP_sha1(void);
    const EVP_MD *EVP_sha224(void);
    const EVP_MD *EVP_sha256(void);
    const EVP_MD *EVP_sha384(void);
    const EVP_MD *EVP_sha512(void);

    int PKCS12_key_gen_uni(char *pass, int passlen, char *salt,
                    int saltlen, int id, int iter, int n,
                    char *out, const EVP_MD *md_type);

    void BN_free(BIGNUM *a);
    int BN_dec2bn(BIGNUM **a, const char *str);

    DH *DH_new(void);
    int DH_generate_parameters_ex(DH *dh, int prime_len, int generator, BN_GENCB *cb);
    int i2d_DHparams(const DH *a, char **pp);
    void DH_free(DH *dh);

    RSA *RSA_new(void);
    int RSA_generate_key_ex(RSA *rsa, int bits, BIGNUM *e, BN_GENCB *cb);
    int i2d_RSAPublicKey(RSA *a, char **pp);
    int i2d_RSAPrivateKey(RSA *a, char **pp);

    DSA *DSA_new(void);
    int DSA_generate_parameters_ex(DSA *dsa, int bits,
                    const char *seed, int seed_len, int *counter_ret,
                    unsigned long *h_ret, BN_GENCB *cb);
    int DSA_generate_key(DSA *a);
    int i2d_DSA_PUBKEY(const DSA *a, char **pp);
    int i2d_DSAPrivateKey(const DSA *a, char **pp);
    void DSA_free(DSA *dsa);

    EC_KEY *EC_KEY_new_by_curve_name(int nid);
    int EC_KEY_generate_key(EC_KEY *key);
    void EC_KEY_set_asn1_flag(EC_KEY *, int);
    int i2d_ECPrivateKey(EC_KEY *key, char **out);
    int i2o_ECPublicKey(EC_KEY *key, char **out);
    void EC_KEY_free(EC_KEY *key);
""")

if version_info < (3, ):
    ffi.cdef("""
        int EVP_PKEY_size(EVP_PKEY *pkey);
    """)
else:
    ffi.cdef("""
        int EVP_PKEY_get_size(EVP_PKEY *pkey);
    """)

if version_info < (1, 1):
    ffi.cdef("""
        EVP_MD_CTX *EVP_MD_CTX_create(void);
        void EVP_MD_CTX_destroy(EVP_MD_CTX *ctx);
    """)
else:
    ffi.cdef("""
        EVP_MD_CTX *EVP_MD_CTX_new(void);
        void EVP_MD_CTX_free(EVP_MD_CTX *ctx);
    """)

if version_info < (1,):
    ffi.cdef("""
        typedef ... *DSA_SIG;
        typedef ... *ECDSA_SIG;

        DSA_SIG *DSA_do_sign(const char *dgst, int dlen, DSA *dsa);
        ECDSA_SIG *ECDSA_do_sign(const char *dgst, int dgst_len, EC_KEY *eckey);

        DSA_SIG *d2i_DSA_SIG(DSA_SIG **v, const char **pp, long length);
        ECDSA_SIG *d2i_ECDSA_SIG(ECDSA_SIG **v, const char **pp, long len);

        int i2d_DSA_SIG(const DSA_SIG *a, char **pp);
        int i2d_ECDSA_SIG(const ECDSA_SIG *a, char **pp);

        int DSA_do_verify(const char *dgst, int dgst_len, DSA_SIG *sig, DSA *dsa);
        int ECDSA_do_verify(const char *dgst, int dgst_len, const ECDSA_SIG *sig, EC_KEY *eckey);

        void DSA_SIG_free(DSA_SIG *a);
        void ECDSA_SIG_free(ECDSA_SIG *a);

        DSA *EVP_PKEY_get1_DSA(EVP_PKEY *pkey);
        EC_KEY *EVP_PKEY_get1_EC_KEY(EVP_PKEY *pkey);

        int RSA_verify_PKCS1_PSS(RSA *rsa, const char *mHash,
                        const EVP_MD *Hash, const char *EM,
                        int sLen);
        int RSA_padding_add_PKCS1_PSS(RSA *rsa, char *EM,
                        const char *mHash, const EVP_MD *Hash,
                        int sLen);

        int EVP_DigestInit_ex(EVP_MD_CTX *ctx, const EVP_MD *type, ENGINE *impl);
        int EVP_SignFinal(EVP_MD_CTX *ctx, char *sig, unsigned int *s, EVP_PKEY *pkey);
        int EVP_VerifyFinal(EVP_MD_CTX *ctx, char *sigbuf, unsigned int siglen, EVP_PKEY *pkey);

        void EVP_MD_CTX_set_flags(EVP_MD_CTX *ctx, int flags);
    """)
else:
    ffi.cdef("""
        int PKCS5_PBKDF2_HMAC(const char *pass, int passlen,
                        const char *salt, int saltlen, int iter,
                        const EVP_MD *digest,
                        int keylen, char *out);

        int EVP_DigestSignInit(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx, const EVP_MD *type, ENGINE *e, EVP_PKEY *pkey);
        int EVP_DigestSignFinal(EVP_MD_CTX *ctx, char *sig, size_t *siglen);

        int EVP_DigestVerifyInit(EVP_MD_CTX *ctx, EVP_PKEY_CTX **pctx, const EVP_MD *type, ENGINE *e, EVP_PKEY *pkey);
        int EVP_DigestVerifyFinal(EVP_MD_CTX *ctx, const char *sig, size_t siglen);

        int EVP_PKEY_CTX_ctrl(EVP_PKEY_CTX *ctx, int keytype, int optype, int cmd, int p1, void *p2);
    """)

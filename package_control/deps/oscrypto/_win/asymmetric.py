# coding: utf-8
from __future__ import unicode_literals, division, absolute_import, print_function

import os
import sys
import hashlib
import random

from .._asn1 import (
    Certificate as Asn1Certificate,
    DHParameters,
    DSAParams,
    DSASignature,
    ECDomainParameters,
    ECPrivateKey,
    Integer,
    int_from_bytes,
    int_to_bytes,
    PrivateKeyAlgorithm,
    PrivateKeyInfo,
    PublicKeyAlgorithm,
    PublicKeyInfo,
    RSAPrivateKey,
    RSAPublicKey,
)
from .._asymmetric import (
    _CertificateBase,
    _fingerprint,
    _parse_pkcs12,
    _PrivateKeyBase,
    _PublicKeyBase,
    _unwrap_private_key_info,
    parse_certificate,
    parse_private,
    parse_public,
)
from .._errors import pretty_message
from .._ffi import (
    buffer_from_bytes,
    buffer_from_unicode,
    byte_array,
    bytes_from_buffer,
    cast,
    deref,
    native,
    new,
    null,
    pointer_set,
    sizeof,
    struct,
    struct_bytes,
    struct_from_buffer,
    unwrap,
    write_to_buffer,
)
from .. import backend
from .._int import fill_width
from ..errors import AsymmetricKeyError, IncompleteAsymmetricKeyError, SignatureError
from .._types import type_name, str_cls, byte_cls, int_types
from .._pkcs1 import (
    add_pkcs1v15_signature_padding,
    add_pss_padding,
    raw_rsa_private_crypt,
    raw_rsa_public_crypt,
    remove_pkcs1v15_signature_padding,
    verify_pss_padding,
)
from ..util import constant_compare

_gwv = sys.getwindowsversion()
_win_version_info = (_gwv[0], _gwv[1])
_backend = backend()

if _backend == 'winlegacy':
    from ._advapi32 import advapi32, Advapi32Const, handle_error, open_context_handle, close_context_handle
    from .._ecdsa import (
        ec_generate_pair as _pure_python_ec_generate_pair,
        ec_compute_public_key_point as _pure_python_ec_compute_public_key_point,
        ec_public_key_info,
        ecdsa_sign as _pure_python_ecdsa_sign,
        ecdsa_verify as _pure_python_ecdsa_verify,
    )
else:
    from ._cng import bcrypt, BcryptConst, handle_error, open_alg_handle, close_alg_handle


__all__ = [
    'Certificate',
    'dsa_sign',
    'dsa_verify',
    'ecdsa_sign',
    'ecdsa_verify',
    'generate_pair',
    'load_certificate',
    'load_pkcs12',
    'load_private_key',
    'load_public_key',
    'parse_pkcs12',
    'PrivateKey',
    'PublicKey',
    'rsa_oaep_decrypt',
    'rsa_oaep_encrypt',
    'rsa_pkcs1v15_decrypt',
    'rsa_pkcs1v15_encrypt',
    'rsa_pkcs1v15_sign',
    'rsa_pkcs1v15_verify',
    'rsa_pss_sign',
    'rsa_pss_verify',
]


# A list of primes from OpenSSL's bn_prime.h to use when testing primality of a
# large integer
_SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19,
    23, 29, 31, 37, 41, 43, 47, 53,
    59, 61, 67, 71, 73, 79, 83, 89,
    97, 101, 103, 107, 109, 113, 127, 131,
    137, 139, 149, 151, 157, 163, 167, 173,
    179, 181, 191, 193, 197, 199, 211, 223,
    227, 229, 233, 239, 241, 251, 257, 263,
    269, 271, 277, 281, 283, 293, 307, 311,
    313, 317, 331, 337, 347, 349, 353, 359,
    367, 373, 379, 383, 389, 397, 401, 409,
    419, 421, 431, 433, 439, 443, 449, 457,
    461, 463, 467, 479, 487, 491, 499, 503,
    509, 521, 523, 541, 547, 557, 563, 569,
    571, 577, 587, 593, 599, 601, 607, 613,
    617, 619, 631, 641, 643, 647, 653, 659,
    661, 673, 677, 683, 691, 701, 709, 719,
    727, 733, 739, 743, 751, 757, 761, 769,
    773, 787, 797, 809, 811, 821, 823, 827,
    829, 839, 853, 857, 859, 863, 877, 881,
    883, 887, 907, 911, 919, 929, 937, 941,
    947, 953, 967, 971, 977, 983, 991, 997,
    1009, 1013, 1019, 1021, 1031, 1033, 1039, 1049,
    1051, 1061, 1063, 1069, 1087, 1091, 1093, 1097,
    1103, 1109, 1117, 1123, 1129, 1151, 1153, 1163,
    1171, 1181, 1187, 1193, 1201, 1213, 1217, 1223,
    1229, 1231, 1237, 1249, 1259, 1277, 1279, 1283,
    1289, 1291, 1297, 1301, 1303, 1307, 1319, 1321,
    1327, 1361, 1367, 1373, 1381, 1399, 1409, 1423,
    1427, 1429, 1433, 1439, 1447, 1451, 1453, 1459,
    1471, 1481, 1483, 1487, 1489, 1493, 1499, 1511,
    1523, 1531, 1543, 1549, 1553, 1559, 1567, 1571,
    1579, 1583, 1597, 1601, 1607, 1609, 1613, 1619,
    1621, 1627, 1637, 1657, 1663, 1667, 1669, 1693,
    1697, 1699, 1709, 1721, 1723, 1733, 1741, 1747,
    1753, 1759, 1777, 1783, 1787, 1789, 1801, 1811,
    1823, 1831, 1847, 1861, 1867, 1871, 1873, 1877,
    1879, 1889, 1901, 1907, 1913, 1931, 1933, 1949,
    1951, 1973, 1979, 1987, 1993, 1997, 1999, 2003,
    2011, 2017, 2027, 2029, 2039, 2053, 2063, 2069,
    2081, 2083, 2087, 2089, 2099, 2111, 2113, 2129,
    2131, 2137, 2141, 2143, 2153, 2161, 2179, 2203,
    2207, 2213, 2221, 2237, 2239, 2243, 2251, 2267,
    2269, 2273, 2281, 2287, 2293, 2297, 2309, 2311,
    2333, 2339, 2341, 2347, 2351, 2357, 2371, 2377,
    2381, 2383, 2389, 2393, 2399, 2411, 2417, 2423,
    2437, 2441, 2447, 2459, 2467, 2473, 2477, 2503,
    2521, 2531, 2539, 2543, 2549, 2551, 2557, 2579,
    2591, 2593, 2609, 2617, 2621, 2633, 2647, 2657,
    2659, 2663, 2671, 2677, 2683, 2687, 2689, 2693,
    2699, 2707, 2711, 2713, 2719, 2729, 2731, 2741,
    2749, 2753, 2767, 2777, 2789, 2791, 2797, 2801,
    2803, 2819, 2833, 2837, 2843, 2851, 2857, 2861,
    2879, 2887, 2897, 2903, 2909, 2917, 2927, 2939,
    2953, 2957, 2963, 2969, 2971, 2999, 3001, 3011,
    3019, 3023, 3037, 3041, 3049, 3061, 3067, 3079,
    3083, 3089, 3109, 3119, 3121, 3137, 3163, 3167,
    3169, 3181, 3187, 3191, 3203, 3209, 3217, 3221,
    3229, 3251, 3253, 3257, 3259, 3271, 3299, 3301,
    3307, 3313, 3319, 3323, 3329, 3331, 3343, 3347,
    3359, 3361, 3371, 3373, 3389, 3391, 3407, 3413,
    3433, 3449, 3457, 3461, 3463, 3467, 3469, 3491,
    3499, 3511, 3517, 3527, 3529, 3533, 3539, 3541,
    3547, 3557, 3559, 3571, 3581, 3583, 3593, 3607,
    3613, 3617, 3623, 3631, 3637, 3643, 3659, 3671,
    3673, 3677, 3691, 3697, 3701, 3709, 3719, 3727,
    3733, 3739, 3761, 3767, 3769, 3779, 3793, 3797,
    3803, 3821, 3823, 3833, 3847, 3851, 3853, 3863,
    3877, 3881, 3889, 3907, 3911, 3917, 3919, 3923,
    3929, 3931, 3943, 3947, 3967, 3989, 4001, 4003,
    4007, 4013, 4019, 4021, 4027, 4049, 4051, 4057,
    4073, 4079, 4091, 4093, 4099, 4111, 4127, 4129,
    4133, 4139, 4153, 4157, 4159, 4177, 4201, 4211,
    4217, 4219, 4229, 4231, 4241, 4243, 4253, 4259,
    4261, 4271, 4273, 4283, 4289, 4297, 4327, 4337,
    4339, 4349, 4357, 4363, 4373, 4391, 4397, 4409,
    4421, 4423, 4441, 4447, 4451, 4457, 4463, 4481,
    4483, 4493, 4507, 4513, 4517, 4519, 4523, 4547,
    4549, 4561, 4567, 4583, 4591, 4597, 4603, 4621,
    4637, 4639, 4643, 4649, 4651, 4657, 4663, 4673,
    4679, 4691, 4703, 4721, 4723, 4729, 4733, 4751,
    4759, 4783, 4787, 4789, 4793, 4799, 4801, 4813,
    4817, 4831, 4861, 4871, 4877, 4889, 4903, 4909,
    4919, 4931, 4933, 4937, 4943, 4951, 4957, 4967,
    4969, 4973, 4987, 4993, 4999, 5003, 5009, 5011,
    5021, 5023, 5039, 5051, 5059, 5077, 5081, 5087,
    5099, 5101, 5107, 5113, 5119, 5147, 5153, 5167,
    5171, 5179, 5189, 5197, 5209, 5227, 5231, 5233,
    5237, 5261, 5273, 5279, 5281, 5297, 5303, 5309,
    5323, 5333, 5347, 5351, 5381, 5387, 5393, 5399,
    5407, 5413, 5417, 5419, 5431, 5437, 5441, 5443,
    5449, 5471, 5477, 5479, 5483, 5501, 5503, 5507,
    5519, 5521, 5527, 5531, 5557, 5563, 5569, 5573,
    5581, 5591, 5623, 5639, 5641, 5647, 5651, 5653,
    5657, 5659, 5669, 5683, 5689, 5693, 5701, 5711,
    5717, 5737, 5741, 5743, 5749, 5779, 5783, 5791,
    5801, 5807, 5813, 5821, 5827, 5839, 5843, 5849,
    5851, 5857, 5861, 5867, 5869, 5879, 5881, 5897,
    5903, 5923, 5927, 5939, 5953, 5981, 5987, 6007,
    6011, 6029, 6037, 6043, 6047, 6053, 6067, 6073,
    6079, 6089, 6091, 6101, 6113, 6121, 6131, 6133,
    6143, 6151, 6163, 6173, 6197, 6199, 6203, 6211,
    6217, 6221, 6229, 6247, 6257, 6263, 6269, 6271,
    6277, 6287, 6299, 6301, 6311, 6317, 6323, 6329,
    6337, 6343, 6353, 6359, 6361, 6367, 6373, 6379,
    6389, 6397, 6421, 6427, 6449, 6451, 6469, 6473,
    6481, 6491, 6521, 6529, 6547, 6551, 6553, 6563,
    6569, 6571, 6577, 6581, 6599, 6607, 6619, 6637,
    6653, 6659, 6661, 6673, 6679, 6689, 6691, 6701,
    6703, 6709, 6719, 6733, 6737, 6761, 6763, 6779,
    6781, 6791, 6793, 6803, 6823, 6827, 6829, 6833,
    6841, 6857, 6863, 6869, 6871, 6883, 6899, 6907,
    6911, 6917, 6947, 6949, 6959, 6961, 6967, 6971,
    6977, 6983, 6991, 6997, 7001, 7013, 7019, 7027,
    7039, 7043, 7057, 7069, 7079, 7103, 7109, 7121,
    7127, 7129, 7151, 7159, 7177, 7187, 7193, 7207,
    7211, 7213, 7219, 7229, 7237, 7243, 7247, 7253,
    7283, 7297, 7307, 7309, 7321, 7331, 7333, 7349,
    7351, 7369, 7393, 7411, 7417, 7433, 7451, 7457,
    7459, 7477, 7481, 7487, 7489, 7499, 7507, 7517,
    7523, 7529, 7537, 7541, 7547, 7549, 7559, 7561,
    7573, 7577, 7583, 7589, 7591, 7603, 7607, 7621,
    7639, 7643, 7649, 7669, 7673, 7681, 7687, 7691,
    7699, 7703, 7717, 7723, 7727, 7741, 7753, 7757,
    7759, 7789, 7793, 7817, 7823, 7829, 7841, 7853,
    7867, 7873, 7877, 7879, 7883, 7901, 7907, 7919,
    7927, 7933, 7937, 7949, 7951, 7963, 7993, 8009,
    8011, 8017, 8039, 8053, 8059, 8069, 8081, 8087,
    8089, 8093, 8101, 8111, 8117, 8123, 8147, 8161,
    8167, 8171, 8179, 8191, 8209, 8219, 8221, 8231,
    8233, 8237, 8243, 8263, 8269, 8273, 8287, 8291,
    8293, 8297, 8311, 8317, 8329, 8353, 8363, 8369,
    8377, 8387, 8389, 8419, 8423, 8429, 8431, 8443,
    8447, 8461, 8467, 8501, 8513, 8521, 8527, 8537,
    8539, 8543, 8563, 8573, 8581, 8597, 8599, 8609,
    8623, 8627, 8629, 8641, 8647, 8663, 8669, 8677,
    8681, 8689, 8693, 8699, 8707, 8713, 8719, 8731,
    8737, 8741, 8747, 8753, 8761, 8779, 8783, 8803,
    8807, 8819, 8821, 8831, 8837, 8839, 8849, 8861,
    8863, 8867, 8887, 8893, 8923, 8929, 8933, 8941,
    8951, 8963, 8969, 8971, 8999, 9001, 9007, 9011,
    9013, 9029, 9041, 9043, 9049, 9059, 9067, 9091,
    9103, 9109, 9127, 9133, 9137, 9151, 9157, 9161,
    9173, 9181, 9187, 9199, 9203, 9209, 9221, 9227,
    9239, 9241, 9257, 9277, 9281, 9283, 9293, 9311,
    9319, 9323, 9337, 9341, 9343, 9349, 9371, 9377,
    9391, 9397, 9403, 9413, 9419, 9421, 9431, 9433,
    9437, 9439, 9461, 9463, 9467, 9473, 9479, 9491,
    9497, 9511, 9521, 9533, 9539, 9547, 9551, 9587,
    9601, 9613, 9619, 9623, 9629, 9631, 9643, 9649,
    9661, 9677, 9679, 9689, 9697, 9719, 9721, 9733,
    9739, 9743, 9749, 9767, 9769, 9781, 9787, 9791,
    9803, 9811, 9817, 9829, 9833, 9839, 9851, 9857,
    9859, 9871, 9883, 9887, 9901, 9907, 9923, 9929,
    9931, 9941, 9949, 9967, 9973, 10007, 10009, 10037,
    10039, 10061, 10067, 10069, 10079, 10091, 10093, 10099,
    10103, 10111, 10133, 10139, 10141, 10151, 10159, 10163,
    10169, 10177, 10181, 10193, 10211, 10223, 10243, 10247,
    10253, 10259, 10267, 10271, 10273, 10289, 10301, 10303,
    10313, 10321, 10331, 10333, 10337, 10343, 10357, 10369,
    10391, 10399, 10427, 10429, 10433, 10453, 10457, 10459,
    10463, 10477, 10487, 10499, 10501, 10513, 10529, 10531,
    10559, 10567, 10589, 10597, 10601, 10607, 10613, 10627,
    10631, 10639, 10651, 10657, 10663, 10667, 10687, 10691,
    10709, 10711, 10723, 10729, 10733, 10739, 10753, 10771,
    10781, 10789, 10799, 10831, 10837, 10847, 10853, 10859,
    10861, 10867, 10883, 10889, 10891, 10903, 10909, 10937,
    10939, 10949, 10957, 10973, 10979, 10987, 10993, 11003,
    11027, 11047, 11057, 11059, 11069, 11071, 11083, 11087,
    11093, 11113, 11117, 11119, 11131, 11149, 11159, 11161,
    11171, 11173, 11177, 11197, 11213, 11239, 11243, 11251,
    11257, 11261, 11273, 11279, 11287, 11299, 11311, 11317,
    11321, 11329, 11351, 11353, 11369, 11383, 11393, 11399,
    11411, 11423, 11437, 11443, 11447, 11467, 11471, 11483,
    11489, 11491, 11497, 11503, 11519, 11527, 11549, 11551,
    11579, 11587, 11593, 11597, 11617, 11621, 11633, 11657,
    11677, 11681, 11689, 11699, 11701, 11717, 11719, 11731,
    11743, 11777, 11779, 11783, 11789, 11801, 11807, 11813,
    11821, 11827, 11831, 11833, 11839, 11863, 11867, 11887,
    11897, 11903, 11909, 11923, 11927, 11933, 11939, 11941,
    11953, 11959, 11969, 11971, 11981, 11987, 12007, 12011,
    12037, 12041, 12043, 12049, 12071, 12073, 12097, 12101,
    12107, 12109, 12113, 12119, 12143, 12149, 12157, 12161,
    12163, 12197, 12203, 12211, 12227, 12239, 12241, 12251,
    12253, 12263, 12269, 12277, 12281, 12289, 12301, 12323,
    12329, 12343, 12347, 12373, 12377, 12379, 12391, 12401,
    12409, 12413, 12421, 12433, 12437, 12451, 12457, 12473,
    12479, 12487, 12491, 12497, 12503, 12511, 12517, 12527,
    12539, 12541, 12547, 12553, 12569, 12577, 12583, 12589,
    12601, 12611, 12613, 12619, 12637, 12641, 12647, 12653,
    12659, 12671, 12689, 12697, 12703, 12713, 12721, 12739,
    12743, 12757, 12763, 12781, 12791, 12799, 12809, 12821,
    12823, 12829, 12841, 12853, 12889, 12893, 12899, 12907,
    12911, 12917, 12919, 12923, 12941, 12953, 12959, 12967,
    12973, 12979, 12983, 13001, 13003, 13007, 13009, 13033,
    13037, 13043, 13049, 13063, 13093, 13099, 13103, 13109,
    13121, 13127, 13147, 13151, 13159, 13163, 13171, 13177,
    13183, 13187, 13217, 13219, 13229, 13241, 13249, 13259,
    13267, 13291, 13297, 13309, 13313, 13327, 13331, 13337,
    13339, 13367, 13381, 13397, 13399, 13411, 13417, 13421,
    13441, 13451, 13457, 13463, 13469, 13477, 13487, 13499,
    13513, 13523, 13537, 13553, 13567, 13577, 13591, 13597,
    13613, 13619, 13627, 13633, 13649, 13669, 13679, 13681,
    13687, 13691, 13693, 13697, 13709, 13711, 13721, 13723,
    13729, 13751, 13757, 13759, 13763, 13781, 13789, 13799,
    13807, 13829, 13831, 13841, 13859, 13873, 13877, 13879,
    13883, 13901, 13903, 13907, 13913, 13921, 13931, 13933,
    13963, 13967, 13997, 13999, 14009, 14011, 14029, 14033,
    14051, 14057, 14071, 14081, 14083, 14087, 14107, 14143,
    14149, 14153, 14159, 14173, 14177, 14197, 14207, 14221,
    14243, 14249, 14251, 14281, 14293, 14303, 14321, 14323,
    14327, 14341, 14347, 14369, 14387, 14389, 14401, 14407,
    14411, 14419, 14423, 14431, 14437, 14447, 14449, 14461,
    14479, 14489, 14503, 14519, 14533, 14537, 14543, 14549,
    14551, 14557, 14561, 14563, 14591, 14593, 14621, 14627,
    14629, 14633, 14639, 14653, 14657, 14669, 14683, 14699,
    14713, 14717, 14723, 14731, 14737, 14741, 14747, 14753,
    14759, 14767, 14771, 14779, 14783, 14797, 14813, 14821,
    14827, 14831, 14843, 14851, 14867, 14869, 14879, 14887,
    14891, 14897, 14923, 14929, 14939, 14947, 14951, 14957,
    14969, 14983, 15013, 15017, 15031, 15053, 15061, 15073,
    15077, 15083, 15091, 15101, 15107, 15121, 15131, 15137,
    15139, 15149, 15161, 15173, 15187, 15193, 15199, 15217,
    15227, 15233, 15241, 15259, 15263, 15269, 15271, 15277,
    15287, 15289, 15299, 15307, 15313, 15319, 15329, 15331,
    15349, 15359, 15361, 15373, 15377, 15383, 15391, 15401,
    15413, 15427, 15439, 15443, 15451, 15461, 15467, 15473,
    15493, 15497, 15511, 15527, 15541, 15551, 15559, 15569,
    15581, 15583, 15601, 15607, 15619, 15629, 15641, 15643,
    15647, 15649, 15661, 15667, 15671, 15679, 15683, 15727,
    15731, 15733, 15737, 15739, 15749, 15761, 15767, 15773,
    15787, 15791, 15797, 15803, 15809, 15817, 15823, 15859,
    15877, 15881, 15887, 15889, 15901, 15907, 15913, 15919,
    15923, 15937, 15959, 15971, 15973, 15991, 16001, 16007,
    16033, 16057, 16061, 16063, 16067, 16069, 16073, 16087,
    16091, 16097, 16103, 16111, 16127, 16139, 16141, 16183,
    16187, 16189, 16193, 16217, 16223, 16229, 16231, 16249,
    16253, 16267, 16273, 16301, 16319, 16333, 16339, 16349,
    16361, 16363, 16369, 16381, 16411, 16417, 16421, 16427,
    16433, 16447, 16451, 16453, 16477, 16481, 16487, 16493,
    16519, 16529, 16547, 16553, 16561, 16567, 16573, 16603,
    16607, 16619, 16631, 16633, 16649, 16651, 16657, 16661,
    16673, 16691, 16693, 16699, 16703, 16729, 16741, 16747,
    16759, 16763, 16787, 16811, 16823, 16829, 16831, 16843,
    16871, 16879, 16883, 16889, 16901, 16903, 16921, 16927,
    16931, 16937, 16943, 16963, 16979, 16981, 16987, 16993,
    17011, 17021, 17027, 17029, 17033, 17041, 17047, 17053,
    17077, 17093, 17099, 17107, 17117, 17123, 17137, 17159,
    17167, 17183, 17189, 17191, 17203, 17207, 17209, 17231,
    17239, 17257, 17291, 17293, 17299, 17317, 17321, 17327,
    17333, 17341, 17351, 17359, 17377, 17383, 17387, 17389,
    17393, 17401, 17417, 17419, 17431, 17443, 17449, 17467,
    17471, 17477, 17483, 17489, 17491, 17497, 17509, 17519,
    17539, 17551, 17569, 17573, 17579, 17581, 17597, 17599,
    17609, 17623, 17627, 17657, 17659, 17669, 17681, 17683,
    17707, 17713, 17729, 17737, 17747, 17749, 17761, 17783,
    17789, 17791, 17807, 17827, 17837, 17839, 17851, 17863,
]


class _WinKey():

    # A CNG BCRYPT_KEY_HANDLE on Vista and newer, an HCRYPTKEY on XP and 2003
    key_handle = None
    # On XP and 2003, we have to carry around more info
    context_handle = None
    ex_key_handle = None

    # A reference to the library used in the destructor to make sure it hasn't
    # been garbage collected by the time this object is garbage collected
    _lib = None

    def __init__(self, key_handle, asn1):
        """
        :param key_handle:
            A CNG BCRYPT_KEY_HANDLE value (Vista and newer) or an HCRYPTKEY
            (XP and 2003) from loading/importing the key

        :param asn1:
            An asn1crypto object for the concrete type
        """

        self.key_handle = key_handle
        self.asn1 = asn1

        if _backend == 'winlegacy':
            self._lib = advapi32
        else:
            self._lib = bcrypt

    def __del__(self):
        if self.key_handle:
            if _backend == 'winlegacy':
                res = self._lib.CryptDestroyKey(self.key_handle)
            else:
                res = self._lib.BCryptDestroyKey(self.key_handle)
            handle_error(res)
            self.key_handle = None
        if self.context_handle and _backend == 'winlegacy':
            close_context_handle(self.context_handle)
            self.context_handle = None
        self._lib = None


class PrivateKey(_WinKey, _PrivateKeyBase):
    """
    Container for the OS crypto library representation of a private key
    """

    _public_key = None

    def __init__(self, key_handle, asn1):
        """
        :param key_handle:
            A CNG BCRYPT_KEY_HANDLE value (Vista and newer) or an HCRYPTKEY
            (XP and 2003) from loading/importing the key

        :param asn1:
            An asn1crypto.keys.PrivateKeyInfo object
        """

        _WinKey.__init__(self, key_handle, asn1)

    @property
    def public_key(self):
        """
        :return:
            A PublicKey object corresponding to this private key.
        """

        if _backend == 'winlegacy':
            if self.algorithm == 'ec':
                pub_point = _pure_python_ec_compute_public_key_point(self.asn1)
                self._public_key = PublicKey(None, ec_public_key_info(pub_point, self.curve))
            elif self.algorithm == 'dsa':
                # The DSA provider won't allow exporting the private key with
                # CryptoImportKey flags set to 0 and won't allow flags to be set
                # to CRYPT_EXPORTABLE, so we manually recreated the public key
                # ASN.1
                params = self.asn1['private_key_algorithm']['parameters']
                pub_asn1 = PublicKeyInfo({
                    'algorithm': PublicKeyAlgorithm({
                        'algorithm': 'dsa',
                        'parameters': params
                    }),
                    'public_key': Integer(pow(
                        params['g'].native,
                        self.asn1['private_key'].parsed.native,
                        params['p'].native
                    ))
                })
                self._public_key = load_public_key(pub_asn1)
            else:
                # This suffers from similar problems as above, although not
                # as insurmountable. This is just a simpler/faster solution
                # since the private key has all of the data we need anyway
                parsed = self.asn1['private_key'].parsed
                pub_asn1 = PublicKeyInfo({
                    'algorithm': PublicKeyAlgorithm({
                        'algorithm': 'rsa'
                    }),
                    'public_key': RSAPublicKey({
                        'modulus': parsed['modulus'],
                        'public_exponent': parsed['public_exponent']
                    })
                })
                self._public_key = load_public_key(pub_asn1)
        else:
            pub_asn1, _ = _bcrypt_key_handle_to_asn1(self.algorithm, self.bit_size, self.key_handle)
            self._public_key = load_public_key(pub_asn1)
        return self._public_key

    @property
    def fingerprint(self):
        """
        Creates a fingerprint that can be compared with a public key to see if
        the two form a pair.

        This fingerprint is not compatible with fingerprints generated by any
        other software.

        :return:
            A byte string that is a sha256 hash of selected components (based
            on the key type)
        """

        if self._fingerprint is None:
            self._fingerprint = _fingerprint(self.asn1, load_private_key)
        return self._fingerprint


class PublicKey(_WinKey, _PublicKeyBase):
    """
    Container for the OS crypto library representation of a public key
    """

    def __init__(self, key_handle, asn1):
        """
        :param key_handle:
            A CNG BCRYPT_KEY_HANDLE value (Vista and newer) or an HCRYPTKEY
            (XP and 2003) from loading/importing the key

        :param asn1:
            An asn1crypto.keys.PublicKeyInfo object
        """

        _WinKey.__init__(self, key_handle, asn1)


class Certificate(_WinKey, _CertificateBase):
    """
    Container for the OS crypto library representation of a certificate
    """

    _public_key = None
    _self_signed = None

    def __init__(self, key_handle, asn1):
        """
        :param key_handle:
            A CNG BCRYPT_KEY_HANDLE value (Vista and newer) or an HCRYPTKEY
            (XP and 2003) from loading/importing the certificate

        :param asn1:
            An asn1crypto.x509.Certificate object
        """

        _WinKey.__init__(self, key_handle, asn1)

    @property
    def public_key(self):
        """
        :return:
            The PublicKey object for the public key this certificate contains
        """

        if self._public_key is None:
            self._public_key = load_public_key(self.asn1['tbs_certificate']['subject_public_key_info'])
        return self._public_key

    @property
    def self_signed(self):
        """
        :return:
            A boolean - if the certificate is self-signed
        """

        if self._self_signed is None:
            self._self_signed = False
            if self.asn1.self_signed in set(['yes', 'maybe']):

                signature_algo = self.asn1['signature_algorithm'].signature_algo
                hash_algo = self.asn1['signature_algorithm'].hash_algo

                if signature_algo == 'rsassa_pkcs1v15':
                    verify_func = rsa_pkcs1v15_verify
                elif signature_algo == 'rsassa_pss':
                    verify_func = rsa_pss_verify
                elif signature_algo == 'dsa':
                    verify_func = dsa_verify
                elif signature_algo == 'ecdsa':
                    verify_func = ecdsa_verify
                else:
                    raise OSError(pretty_message(
                        '''
                        Unable to verify the signature of the certificate since
                        it uses the unsupported algorithm %s
                        ''',
                        signature_algo
                    ))

                try:
                    verify_func(
                        self,
                        self.asn1['signature_value'].native,
                        self.asn1['tbs_certificate'].dump(),
                        hash_algo
                    )
                    self._self_signed = True
                except (SignatureError):
                    pass

        return self._self_signed


def generate_pair(algorithm, bit_size=None, curve=None):
    """
    Generates a public/private key pair

    :param algorithm:
        The key algorithm - "rsa", "dsa" or "ec"

    :param bit_size:
        An integer - used for "rsa" and "dsa". For "rsa" the value maye be 1024,
        2048, 3072 or 4096. For "dsa" the value may be 1024, plus 2048 or 3072
        if on Windows 8 or newer.

    :param curve:
        A unicode string - used for "ec" keys. Valid values include "secp256r1",
        "secp384r1" and "secp521r1".

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A 2-element tuple of (PublicKey, PrivateKey). The contents of each key
        may be saved by calling .asn1.dump().
    """

    if algorithm not in set(['rsa', 'dsa', 'ec']):
        raise ValueError(pretty_message(
            '''
            algorithm must be one of "rsa", "dsa", "ec", not %s
            ''',
            repr(algorithm)
        ))

    if algorithm == 'rsa':
        if bit_size not in set([1024, 2048, 3072, 4096]):
            raise ValueError(pretty_message(
                '''
                bit_size must be one of 1024, 2048, 3072, 4096, not %s
                ''',
                repr(bit_size)
            ))

    elif algorithm == 'dsa':
        # Windows Vista and 7 only support SHA1-based DSA keys
        if _win_version_info < (6, 2) or _backend == 'winlegacy':
            if bit_size != 1024:
                raise ValueError(pretty_message(
                    '''
                    bit_size must be 1024, not %s
                    ''',
                    repr(bit_size)
                ))
        else:
            if bit_size not in set([1024, 2048, 3072]):
                raise ValueError(pretty_message(
                    '''
                    bit_size must be one of 1024, 2048, 3072, not %s
                    ''',
                    repr(bit_size)
                ))

    elif algorithm == 'ec':
        if curve not in set(['secp256r1', 'secp384r1', 'secp521r1']):
            raise ValueError(pretty_message(
                '''
                curve must be one of "secp256r1", "secp384r1", "secp521r1", not %s
                ''',
                repr(curve)
            ))

    if _backend == 'winlegacy':
        if algorithm == 'ec':
            pub_info, priv_info = _pure_python_ec_generate_pair(curve)
            return (PublicKey(None, pub_info), PrivateKey(None, priv_info))
        return _advapi32_generate_pair(algorithm, bit_size)
    else:
        return _bcrypt_generate_pair(algorithm, bit_size, curve)


def _advapi32_key_handle_to_asn1(algorithm, bit_size, key_handle):
    """
    Accepts an key handle and exports it to ASN.1

    :param algorithm:
        The key algorithm - "rsa" or "dsa"

    :param bit_size:
        An integer - only used when algorithm is "rsa"

    :param key_handle:
        The handle to export

    :return:
        A 2-element tuple of asn1crypto.keys.PrivateKeyInfo and
        asn1crypto.keys.PublicKeyInfo
    """

    if algorithm == 'rsa':
        struct_type = 'RSABLOBHEADER'
    else:
        struct_type = 'DSSBLOBHEADER'

    out_len = new(advapi32, 'DWORD *')
    res = advapi32.CryptExportKey(
        key_handle,
        null(),
        Advapi32Const.PRIVATEKEYBLOB,
        0,
        null(),
        out_len
    )
    handle_error(res)

    buffer_length = deref(out_len)
    buffer_ = buffer_from_bytes(buffer_length)
    res = advapi32.CryptExportKey(
        key_handle,
        null(),
        Advapi32Const.PRIVATEKEYBLOB,
        0,
        buffer_,
        out_len
    )
    handle_error(res)

    blob_struct_pointer = struct_from_buffer(advapi32, struct_type, buffer_)
    blob_struct = unwrap(blob_struct_pointer)
    struct_size = sizeof(advapi32, blob_struct)

    private_blob = bytes_from_buffer(buffer_, buffer_length)[struct_size:]

    if algorithm == 'rsa':
        public_info, private_info = _advapi32_interpret_rsa_key_blob(bit_size, blob_struct, private_blob)

    else:
        # The public key for a DSA key is not available in from the private
        # key blob, so we have to separately export the public key
        public_out_len = new(advapi32, 'DWORD *')
        res = advapi32.CryptExportKey(
            key_handle,
            null(),
            Advapi32Const.PUBLICKEYBLOB,
            0,
            null(),
            public_out_len
        )
        handle_error(res)

        public_buffer_length = deref(public_out_len)
        public_buffer = buffer_from_bytes(public_buffer_length)
        res = advapi32.CryptExportKey(
            key_handle,
            null(),
            Advapi32Const.PUBLICKEYBLOB,
            0,
            public_buffer,
            public_out_len
        )
        handle_error(res)

        public_blob = bytes_from_buffer(public_buffer, public_buffer_length)[struct_size:]

        public_info, private_info = _advapi32_interpret_dsa_key_blob(bit_size, public_blob, private_blob)

    return (public_info, private_info)


def _advapi32_generate_pair(algorithm, bit_size=None):
    """
    Generates a public/private key pair using CryptoAPI

    :param algorithm:
        The key algorithm - "rsa" or "dsa"

    :param bit_size:
        An integer - used for "rsa" and "dsa". For "rsa" the value maye be 1024,
        2048, 3072 or 4096. For "dsa" the value may be 1024.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A 2-element tuple of (PublicKey, PrivateKey). The contents of each key
        may be saved by calling .asn1.dump().
    """

    if algorithm == 'rsa':
        provider = Advapi32Const.MS_ENH_RSA_AES_PROV
        algorithm_id = Advapi32Const.CALG_RSA_SIGN
    else:
        provider = Advapi32Const.MS_ENH_DSS_DH_PROV
        algorithm_id = Advapi32Const.CALG_DSS_SIGN

    context_handle = None
    key_handle = None

    try:
        context_handle = open_context_handle(provider, verify_only=False)

        key_handle_pointer = new(advapi32, 'HCRYPTKEY *')
        flags = (bit_size << 16) | Advapi32Const.CRYPT_EXPORTABLE
        res = advapi32.CryptGenKey(context_handle, algorithm_id, flags, key_handle_pointer)
        handle_error(res)

        key_handle = unwrap(key_handle_pointer)

        public_info, private_info = _advapi32_key_handle_to_asn1(algorithm, bit_size, key_handle)

        return (load_public_key(public_info), load_private_key(private_info))

    finally:
        if context_handle:
            close_context_handle(context_handle)
        if key_handle:
            advapi32.CryptDestroyKey(key_handle)


def _bcrypt_key_handle_to_asn1(algorithm, bit_size, key_handle):
    """
    Accepts an key handle and exports it to ASN.1

    :param algorithm:
        The key algorithm - "rsa", "dsa" or "ec"

    :param bit_size:
        An integer - only used when algorithm is "dsa"

    :param key_handle:
        The handle to export

    :return:
        A 2-element tuple of asn1crypto.keys.PrivateKeyInfo and
        asn1crypto.keys.PublicKeyInfo
    """

    if algorithm == 'rsa':
        struct_type = 'BCRYPT_RSAKEY_BLOB'
        private_blob_type = BcryptConst.BCRYPT_RSAFULLPRIVATE_BLOB
        public_blob_type = BcryptConst.BCRYPT_RSAPUBLIC_BLOB

    elif algorithm == 'dsa':
        if bit_size > 1024:
            struct_type = 'BCRYPT_DSA_KEY_BLOB_V2'
        else:
            struct_type = 'BCRYPT_DSA_KEY_BLOB'
        private_blob_type = BcryptConst.BCRYPT_DSA_PRIVATE_BLOB
        public_blob_type = BcryptConst.BCRYPT_DSA_PUBLIC_BLOB

    else:
        struct_type = 'BCRYPT_ECCKEY_BLOB'
        private_blob_type = BcryptConst.BCRYPT_ECCPRIVATE_BLOB
        public_blob_type = BcryptConst.BCRYPT_ECCPUBLIC_BLOB

    private_out_len = new(bcrypt, 'ULONG *')
    res = bcrypt.BCryptExportKey(key_handle, null(), private_blob_type, null(), 0, private_out_len, 0)
    handle_error(res)

    private_buffer_length = deref(private_out_len)
    private_buffer = buffer_from_bytes(private_buffer_length)
    res = bcrypt.BCryptExportKey(
        key_handle,
        null(),
        private_blob_type,
        private_buffer,
        private_buffer_length,
        private_out_len,
        0
    )
    handle_error(res)
    private_blob_struct_pointer = struct_from_buffer(bcrypt, struct_type, private_buffer)
    private_blob_struct = unwrap(private_blob_struct_pointer)
    struct_size = sizeof(bcrypt, private_blob_struct)
    private_blob = bytes_from_buffer(private_buffer, private_buffer_length)[struct_size:]

    if algorithm == 'rsa':
        private_key = _bcrypt_interpret_rsa_key_blob('private', private_blob_struct, private_blob)
    elif algorithm == 'dsa':
        if bit_size > 1024:
            private_key = _bcrypt_interpret_dsa_key_blob('private', 2, private_blob_struct, private_blob)
        else:
            private_key = _bcrypt_interpret_dsa_key_blob('private', 1, private_blob_struct, private_blob)
    else:
        private_key = _bcrypt_interpret_ec_key_blob('private', private_blob_struct, private_blob)

    public_out_len = new(bcrypt, 'ULONG *')
    res = bcrypt.BCryptExportKey(key_handle, null(), public_blob_type, null(), 0, public_out_len, 0)
    handle_error(res)

    public_buffer_length = deref(public_out_len)
    public_buffer = buffer_from_bytes(public_buffer_length)
    res = bcrypt.BCryptExportKey(
        key_handle,
        null(),
        public_blob_type,
        public_buffer,
        public_buffer_length,
        public_out_len,
        0
    )
    handle_error(res)
    public_blob_struct_pointer = struct_from_buffer(bcrypt, struct_type, public_buffer)
    public_blob_struct = unwrap(public_blob_struct_pointer)
    struct_size = sizeof(bcrypt, public_blob_struct)
    public_blob = bytes_from_buffer(public_buffer, public_buffer_length)[struct_size:]

    if algorithm == 'rsa':
        public_key = _bcrypt_interpret_rsa_key_blob('public', public_blob_struct, public_blob)
    elif algorithm == 'dsa':
        if bit_size > 1024:
            public_key = _bcrypt_interpret_dsa_key_blob('public', 2, public_blob_struct, public_blob)
        else:
            public_key = _bcrypt_interpret_dsa_key_blob('public', 1, public_blob_struct, public_blob)
    else:
        public_key = _bcrypt_interpret_ec_key_blob('public', public_blob_struct, public_blob)

    return (public_key, private_key)


def _bcrypt_generate_pair(algorithm, bit_size=None, curve=None):
    """
    Generates a public/private key pair using CNG

    :param algorithm:
        The key algorithm - "rsa", "dsa" or "ec"

    :param bit_size:
        An integer - used for "rsa" and "dsa". For "rsa" the value maye be 1024,
        2048, 3072 or 4096. For "dsa" the value may be 1024, plus 2048 or 3072
        if on Windows 8 or newer.

    :param curve:
        A unicode string - used for "ec" keys. Valid values include "secp256r1",
        "secp384r1" and "secp521r1".

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A 2-element tuple of (PublicKey, PrivateKey). The contents of each key
        may be saved by calling .asn1.dump().
    """

    if algorithm == 'rsa':
        alg_constant = BcryptConst.BCRYPT_RSA_ALGORITHM

    elif algorithm == 'dsa':
        alg_constant = BcryptConst.BCRYPT_DSA_ALGORITHM

    else:
        alg_constant = {
            'secp256r1': BcryptConst.BCRYPT_ECDSA_P256_ALGORITHM,
            'secp384r1': BcryptConst.BCRYPT_ECDSA_P384_ALGORITHM,
            'secp521r1': BcryptConst.BCRYPT_ECDSA_P521_ALGORITHM,
        }[curve]
        bit_size = {
            'secp256r1': 256,
            'secp384r1': 384,
            'secp521r1': 521,
        }[curve]

    key_handle = None
    try:
        alg_handle = open_alg_handle(alg_constant)
        key_handle_pointer = new(bcrypt, 'BCRYPT_KEY_HANDLE *')
        res = bcrypt.BCryptGenerateKeyPair(alg_handle, key_handle_pointer, bit_size, 0)
        handle_error(res)
        key_handle = unwrap(key_handle_pointer)

        res = bcrypt.BCryptFinalizeKeyPair(key_handle, 0)
        handle_error(res)

        public_key, private_key = _bcrypt_key_handle_to_asn1(algorithm, bit_size, key_handle)

    finally:
        if key_handle:
            bcrypt.BCryptDestroyKey(key_handle)

    return (load_public_key(public_key), load_private_key(private_key))


def generate_dh_parameters(bit_size):
    """
    Generates DH parameters for use with Diffie-Hellman key exchange. Returns
    a structure in the format of DHParameter defined in PKCS#3, which is also
    used by the OpenSSL dhparam tool.

    THIS CAN BE VERY TIME CONSUMING!

    :param bit_size:
        The integer bit size of the parameters to generate. Must be between 512
        and 4096, and divisible by 64. Recommended secure value as of early 2016
        is 2048, with an absolute minimum of 1024.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        An asn1crypto.algos.DHParameters object. Use
        oscrypto.asymmetric.dump_dh_parameters() to save to disk for usage with
        web servers.
    """

    if not isinstance(bit_size, int_types):
        raise TypeError(pretty_message(
            '''
            bit_size must be an integer, not %s
            ''',
            type_name(bit_size)
        ))

    if bit_size < 512:
        raise ValueError('bit_size must be greater than or equal to 512')

    if bit_size > 4096:
        raise ValueError('bit_size must be less than or equal to 4096')

    if bit_size % 64 != 0:
        raise ValueError('bit_size must be a multiple of 64')

    alg_handle = None

    # The following algorithm has elements taken from OpenSSL. In short, it
    # generates random numbers and then ensures that they are valid for the
    # hardcoded generator of 2, and then ensures the number is a "safe" prime
    # by ensuring p//2 is prime also.

    # OpenSSL allows use of generator 2 or 5, but we hardcode 2 since it is
    # the default, and what is used by Security.framework on OS X also.
    g = 2

    try:
        byte_size = bit_size // 8
        if _backend == 'win':
            alg_handle = open_alg_handle(BcryptConst.BCRYPT_RNG_ALGORITHM)
            buffer = buffer_from_bytes(byte_size)

        while True:
            if _backend == 'winlegacy':
                rb = os.urandom(byte_size)
            else:
                res = bcrypt.BCryptGenRandom(alg_handle, buffer, byte_size, 0)
                handle_error(res)
                rb = bytes_from_buffer(buffer)

            p = int_from_bytes(rb)

            # If a number is even, it can't be prime
            if p % 2 == 0:
                continue

            # Perform the generator checks outlined in OpenSSL's
            # dh_builtin_genparams() located in dh_gen.c
            if g == 2:
                if p % 24 != 11:
                    continue
            elif g == 5:
                rem = p % 10
                if rem != 3 and rem != 7:
                    continue

            divisible = False
            for prime in _SMALL_PRIMES:
                if p % prime == 0:
                    divisible = True
                    break

            # If the number is not divisible by any of the small primes, then
            # move on to the full Miller-Rabin test.
            if not divisible and _is_prime(bit_size, p):
                q = p // 2
                if _is_prime(bit_size, q):
                    return DHParameters({'p': p, 'g': g})

    finally:
        if alg_handle:
            close_alg_handle(alg_handle)


def _is_prime(bit_size, n):
    """
    An implementation of Miller–Rabin for checking if a number is prime.

    :param bit_size:
        An integer of the number of bits in the prime number

    :param n:
        An integer, the prime number

    :return:
        A boolean
    """

    r = 0
    s = n - 1
    while s % 2 == 0:
        r += 1
        s //= 2

    if bit_size >= 1300:
        k = 2
    elif bit_size >= 850:
        k = 3
    elif bit_size >= 650:
        k = 4
    elif bit_size >= 550:
        k = 5
    elif bit_size >= 450:
        k = 6

    for _ in range(k):
        a = random.randrange(2, n - 1)
        x = pow(a, s, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False

    return True


def _advapi32_interpret_rsa_key_blob(bit_size, blob_struct, blob):
    """
    Takes a CryptoAPI RSA private key blob and converts it into the ASN.1
    structures for the public and private keys

    :param bit_size:
        The integer bit size of the key

    :param blob_struct:
        An instance of the advapi32.RSAPUBKEY struct

    :param blob:
        A byte string of the binary data after the header

    :return:
        A 2-element tuple of (asn1crypto.keys.PublicKeyInfo,
        asn1crypto.keys.PrivateKeyInfo)
    """

    len1 = bit_size // 8
    len2 = bit_size // 16

    prime1_offset = len1
    prime2_offset = prime1_offset + len2
    exponent1_offset = prime2_offset + len2
    exponent2_offset = exponent1_offset + len2
    coefficient_offset = exponent2_offset + len2
    private_exponent_offset = coefficient_offset + len2

    public_exponent = blob_struct.rsapubkey.pubexp
    modulus = int_from_bytes(blob[0:prime1_offset][::-1])
    prime1 = int_from_bytes(blob[prime1_offset:prime2_offset][::-1])
    prime2 = int_from_bytes(blob[prime2_offset:exponent1_offset][::-1])
    exponent1 = int_from_bytes(blob[exponent1_offset:exponent2_offset][::-1])
    exponent2 = int_from_bytes(blob[exponent2_offset:coefficient_offset][::-1])
    coefficient = int_from_bytes(blob[coefficient_offset:private_exponent_offset][::-1])
    private_exponent = int_from_bytes(blob[private_exponent_offset:private_exponent_offset + len1][::-1])

    public_key_info = PublicKeyInfo({
        'algorithm': PublicKeyAlgorithm({
            'algorithm': 'rsa',
        }),
        'public_key': RSAPublicKey({
            'modulus': modulus,
            'public_exponent': public_exponent,
        }),
    })

    rsa_private_key = RSAPrivateKey({
        'version': 'two-prime',
        'modulus': modulus,
        'public_exponent': public_exponent,
        'private_exponent': private_exponent,
        'prime1': prime1,
        'prime2': prime2,
        'exponent1': exponent1,
        'exponent2': exponent2,
        'coefficient': coefficient,
    })

    private_key_info = PrivateKeyInfo({
        'version': 0,
        'private_key_algorithm': PrivateKeyAlgorithm({
            'algorithm': 'rsa',
        }),
        'private_key': rsa_private_key,
    })

    return (public_key_info, private_key_info)


def _advapi32_interpret_dsa_key_blob(bit_size, public_blob, private_blob):
    """
    Takes a CryptoAPI DSS private key blob and converts it into the ASN.1
    structures for the public and private keys

    :param bit_size:
        The integer bit size of the key

    :param public_blob:
        A byte string of the binary data after the public key header

    :param private_blob:
        A byte string of the binary data after the private key header

    :return:
        A 2-element tuple of (asn1crypto.keys.PublicKeyInfo,
        asn1crypto.keys.PrivateKeyInfo)
    """

    len1 = 20
    len2 = bit_size // 8

    q_offset = len2
    g_offset = q_offset + len1
    x_offset = g_offset + len2
    y_offset = x_offset

    p = int_from_bytes(private_blob[0:q_offset][::-1])
    q = int_from_bytes(private_blob[q_offset:g_offset][::-1])
    g = int_from_bytes(private_blob[g_offset:x_offset][::-1])
    x = int_from_bytes(private_blob[x_offset:x_offset + len1][::-1])
    y = int_from_bytes(public_blob[y_offset:y_offset + len2][::-1])

    public_key_info = PublicKeyInfo({
        'algorithm': PublicKeyAlgorithm({
            'algorithm': 'dsa',
            'parameters': DSAParams({
                'p': p,
                'q': q,
                'g': g,
            })
        }),
        'public_key': Integer(y),
    })

    private_key_info = PrivateKeyInfo({
        'version': 0,
        'private_key_algorithm': PrivateKeyAlgorithm({
            'algorithm': 'dsa',
            'parameters': DSAParams({
                'p': p,
                'q': q,
                'g': g,
            })
        }),
        'private_key': Integer(x),
    })

    return (public_key_info, private_key_info)


def _bcrypt_interpret_rsa_key_blob(key_type, blob_struct, blob):
    """
    Take a CNG BCRYPT_RSAFULLPRIVATE_BLOB and converts it into an ASN.1
    structure

    :param key_type:
        A unicode string of "private" or "public"

    :param blob_struct:
        An instance of BCRYPT_RSAKEY_BLOB

    :param blob:
        A byte string of the binary data contained after the struct

    :return:
        An asn1crypto.keys.PrivateKeyInfo or asn1crypto.keys.PublicKeyInfo
        object, based on the key_type param
    """

    public_exponent_byte_length = native(int, blob_struct.cbPublicExp)
    modulus_byte_length = native(int, blob_struct.cbModulus)

    modulus_offset = public_exponent_byte_length

    public_exponent = int_from_bytes(blob[0:modulus_offset])
    modulus = int_from_bytes(blob[modulus_offset:modulus_offset + modulus_byte_length])

    if key_type == 'public':
        return PublicKeyInfo({
            'algorithm': PublicKeyAlgorithm({
                'algorithm': 'rsa',
            }),
            'public_key': RSAPublicKey({
                'modulus': modulus,
                'public_exponent': public_exponent,
            }),
        })

    elif key_type == 'private':
        prime1_byte_length = native(int, blob_struct.cbPrime1)
        prime2_byte_length = native(int, blob_struct.cbPrime2)

        prime1_offset = modulus_offset + modulus_byte_length
        prime2_offset = prime1_offset + prime1_byte_length
        exponent1_offset = prime2_offset + prime2_byte_length
        exponent2_offset = exponent1_offset + prime2_byte_length
        coefficient_offset = exponent2_offset + prime2_byte_length
        private_exponent_offset = coefficient_offset + prime1_byte_length

        prime1 = int_from_bytes(blob[prime1_offset:prime2_offset])
        prime2 = int_from_bytes(blob[prime2_offset:exponent1_offset])
        exponent1 = int_from_bytes(blob[exponent1_offset:exponent2_offset])
        exponent2 = int_from_bytes(blob[exponent2_offset:coefficient_offset])
        coefficient = int_from_bytes(blob[coefficient_offset:private_exponent_offset])
        private_exponent = int_from_bytes(blob[private_exponent_offset:private_exponent_offset + modulus_byte_length])

        rsa_private_key = RSAPrivateKey({
            'version': 'two-prime',
            'modulus': modulus,
            'public_exponent': public_exponent,
            'private_exponent': private_exponent,
            'prime1': prime1,
            'prime2': prime2,
            'exponent1': exponent1,
            'exponent2': exponent2,
            'coefficient': coefficient,
        })

        return PrivateKeyInfo({
            'version': 0,
            'private_key_algorithm': PrivateKeyAlgorithm({
                'algorithm': 'rsa',
            }),
            'private_key': rsa_private_key,
        })

    else:
        raise ValueError(pretty_message(
            '''
            key_type must be one of "public", "private", not %s
            ''',
            repr(key_type)
        ))


def _bcrypt_interpret_dsa_key_blob(key_type, version, blob_struct, blob):
    """
    Take a CNG BCRYPT_DSA_KEY_BLOB or BCRYPT_DSA_KEY_BLOB_V2 and converts it
    into an ASN.1 structure

    :param key_type:
        A unicode string of "private" or "public"

    :param version:
        An integer - 1 or 2, indicating the blob is BCRYPT_DSA_KEY_BLOB or
        BCRYPT_DSA_KEY_BLOB_V2

    :param blob_struct:
        An instance of BCRYPT_DSA_KEY_BLOB or BCRYPT_DSA_KEY_BLOB_V2

    :param blob:
        A byte string of the binary data contained after the struct

    :return:
        An asn1crypto.keys.PrivateKeyInfo or asn1crypto.keys.PublicKeyInfo
        object, based on the key_type param
    """

    key_byte_length = native(int, blob_struct.cbKey)

    if version == 1:
        q = int_from_bytes(native(byte_cls, blob_struct.q))

        g_offset = key_byte_length
        public_offset = g_offset + key_byte_length
        private_offset = public_offset + key_byte_length

        p = int_from_bytes(blob[0:g_offset])
        g = int_from_bytes(blob[g_offset:public_offset])

    elif version == 2:
        seed_byte_length = native(int, blob_struct.cbSeedLength)
        group_byte_length = native(int, blob_struct.cbGroupSize)

        q_offset = seed_byte_length
        p_offset = q_offset + group_byte_length
        g_offset = p_offset + key_byte_length
        public_offset = g_offset + key_byte_length
        private_offset = public_offset + key_byte_length

        # The seed is skipped since it is not part of the ASN.1 structure
        q = int_from_bytes(blob[q_offset:p_offset])
        p = int_from_bytes(blob[p_offset:g_offset])
        g = int_from_bytes(blob[g_offset:public_offset])

    else:
        raise ValueError('version must be 1 or 2, not %s' % repr(version))

    if key_type == 'public':
        public = int_from_bytes(blob[public_offset:private_offset])
        return PublicKeyInfo({
            'algorithm': PublicKeyAlgorithm({
                'algorithm': 'dsa',
                'parameters': DSAParams({
                    'p': p,
                    'q': q,
                    'g': g,
                })
            }),
            'public_key': Integer(public),
        })

    elif key_type == 'private':
        private = int_from_bytes(blob[private_offset:private_offset + key_byte_length])
        return PrivateKeyInfo({
            'version': 0,
            'private_key_algorithm': PrivateKeyAlgorithm({
                'algorithm': 'dsa',
                'parameters': DSAParams({
                    'p': p,
                    'q': q,
                    'g': g,
                })
            }),
            'private_key': Integer(private),
        })

    else:
        raise ValueError(pretty_message(
            '''
            key_type must be one of "public", "private", not %s
            ''',
            repr(key_type)
        ))


def _bcrypt_interpret_ec_key_blob(key_type, blob_struct, blob):
    """
    Take a CNG BCRYPT_ECCKEY_BLOB and converts it into an ASN.1 structure

    :param key_type:
        A unicode string of "private" or "public"

    :param blob_struct:
        An instance of BCRYPT_ECCKEY_BLOB

    :param blob:
        A byte string of the binary data contained after the struct

    :return:
        An asn1crypto.keys.PrivateKeyInfo or asn1crypto.keys.PublicKeyInfo
        object, based on the key_type param
    """

    magic = native(int, blob_struct.dwMagic)
    key_byte_length = native(int, blob_struct.cbKey)

    curve = {
        BcryptConst.BCRYPT_ECDSA_PRIVATE_P256_MAGIC: 'secp256r1',
        BcryptConst.BCRYPT_ECDSA_PRIVATE_P384_MAGIC: 'secp384r1',
        BcryptConst.BCRYPT_ECDSA_PRIVATE_P521_MAGIC: 'secp521r1',
        BcryptConst.BCRYPT_ECDSA_PUBLIC_P256_MAGIC: 'secp256r1',
        BcryptConst.BCRYPT_ECDSA_PUBLIC_P384_MAGIC: 'secp384r1',
        BcryptConst.BCRYPT_ECDSA_PUBLIC_P521_MAGIC: 'secp521r1',
    }[magic]

    public = b'\x04' + blob[0:key_byte_length * 2]

    if key_type == 'public':
        return PublicKeyInfo({
            'algorithm': PublicKeyAlgorithm({
                'algorithm': 'ec',
                'parameters': ECDomainParameters(
                    name='named',
                    value=curve
                )
            }),
            'public_key': public,
        })

    elif key_type == 'private':
        private = int_from_bytes(blob[key_byte_length * 2:key_byte_length * 3])
        return PrivateKeyInfo({
            'version': 0,
            'private_key_algorithm': PrivateKeyAlgorithm({
                'algorithm': 'ec',
                'parameters': ECDomainParameters(
                    name='named',
                    value=curve
                )
            }),
            'private_key': ECPrivateKey({
                'version': 'ecPrivkeyVer1',
                'private_key': private,
                'public_key': public,
            }),
        })

    else:
        raise ValueError(pretty_message(
            '''
            key_type must be one of "public", "private", not %s
            ''',
            repr(key_type)
        ))


def load_certificate(source):
    """
    Loads an x509 certificate into a Certificate object

    :param source:
        A byte string of file contents or a unicode string filename

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A Certificate object
    """

    if isinstance(source, Asn1Certificate):
        certificate = source

    elif isinstance(source, byte_cls):
        certificate = parse_certificate(source)

    elif isinstance(source, str_cls):
        with open(source, 'rb') as f:
            certificate = parse_certificate(f.read())

    else:
        raise TypeError(pretty_message(
            '''
            source must be a byte string, unicode string or
            asn1crypto.x509.Certificate object, not %s
            ''',
            type_name(source)
        ))

    return _load_key(certificate, Certificate)


def _load_key(key_object, container):
    """
    Loads a certificate, public key or private key into a Certificate,
    PublicKey or PrivateKey object

    :param key_object:
        An asn1crypto.x509.Certificate, asn1crypto.keys.PublicKeyInfo or
        asn1crypto.keys.PrivateKeyInfo object

    :param container:
        The class of the object to hold the key_handle

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PrivateKey, PublicKey or Certificate object, based on container
    """

    key_info = key_object
    if isinstance(key_object, Asn1Certificate):
        key_info = key_object['tbs_certificate']['subject_public_key_info']

    algo = key_info.algorithm
    curve_name = None

    if algo == 'ec':
        curve_type, curve_name = key_info.curve
        if curve_type != 'named':
            raise AsymmetricKeyError(pretty_message(
                '''
                Windows only supports EC keys using named curves
                '''
            ))
        if curve_name not in set(['secp256r1', 'secp384r1', 'secp521r1']):
            raise AsymmetricKeyError(pretty_message(
                '''
                Windows only supports EC keys using the named curves
                secp256r1, secp384r1 and secp521r1
                '''
            ))

    elif algo == 'dsa':
        if key_info.hash_algo is None:
            raise IncompleteAsymmetricKeyError(pretty_message(
                '''
                The DSA key does not contain the necessary p, q and g
                parameters and can not be used
                '''
            ))
        elif key_info.bit_size > 1024 and (_win_version_info < (6, 2) or _backend == 'winlegacy'):
            raise AsymmetricKeyError(pretty_message(
                '''
                Windows XP, 2003, Vista, 7 and Server 2008 only support DSA
                keys based on SHA1 (1024 bits or less) - this key is based
                on %s and is %s bits
                ''',
                key_info.hash_algo.upper(),
                key_info.bit_size
            ))
        elif key_info.bit_size == 2048 and key_info.hash_algo == 'sha1':
            raise AsymmetricKeyError(pretty_message(
                '''
                Windows only supports 2048 bit DSA keys based on SHA2 - this
                key is 2048 bits and based on SHA1, a non-standard
                combination that is usually generated by old versions
                of OpenSSL
                '''
            ))

    if _backend == 'winlegacy':
        if algo == 'ec':
            return container(None, key_object)
        return _advapi32_load_key(key_object, key_info, container)
    return _bcrypt_load_key(key_object, key_info, container, curve_name)


def _advapi32_load_key(key_object, key_info, container):
    """
    Loads a certificate, public key or private key into a Certificate,
    PublicKey or PrivateKey object via CryptoAPI

    :param key_object:
        An asn1crypto.x509.Certificate, asn1crypto.keys.PublicKeyInfo or
        asn1crypto.keys.PrivateKeyInfo object

    :param key_info:
        An asn1crypto.keys.PublicKeyInfo or asn1crypto.keys.PrivateKeyInfo
        object

    :param container:
        The class of the object to hold the key_handle

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PrivateKey, PublicKey or Certificate object, based on container
    """

    key_type = 'public' if isinstance(key_info, PublicKeyInfo) else 'private'
    algo = key_info.algorithm
    if algo == 'rsassa_pss':
        algo = 'rsa'

    if algo == 'rsa' or algo == 'rsassa_pss':
        provider = Advapi32Const.MS_ENH_RSA_AES_PROV
    else:
        provider = Advapi32Const.MS_ENH_DSS_DH_PROV

    context_handle = None
    key_handle = None

    try:
        context_handle = open_context_handle(provider, verify_only=key_type == 'public')

        blob = _advapi32_create_blob(key_info, key_type, algo)
        buffer_ = buffer_from_bytes(blob)

        key_handle_pointer = new(advapi32, 'HCRYPTKEY *')
        res = advapi32.CryptImportKey(
            context_handle,
            buffer_,
            len(blob),
            null(),
            0,
            key_handle_pointer
        )
        handle_error(res)

        key_handle = unwrap(key_handle_pointer)
        output = container(key_handle, key_object)
        output.context_handle = context_handle

        if algo == 'rsa':
            ex_blob = _advapi32_create_blob(key_info, key_type, algo, signing=False)
            ex_buffer = buffer_from_bytes(ex_blob)

            ex_key_handle_pointer = new(advapi32, 'HCRYPTKEY *')
            res = advapi32.CryptImportKey(
                context_handle,
                ex_buffer,
                len(ex_blob),
                null(),
                0,
                ex_key_handle_pointer
            )
            handle_error(res)

            output.ex_key_handle = unwrap(ex_key_handle_pointer)

        return output

    except (Exception):
        if key_handle:
            advapi32.CryptDestroyKey(key_handle)
        if context_handle:
            close_context_handle(context_handle)
        raise


def _advapi32_create_blob(key_info, key_type, algo, signing=True):
    """
    Generates a blob for importing a key to CryptoAPI

    :param key_info:
        An asn1crypto.keys.PublicKeyInfo or asn1crypto.keys.PrivateKeyInfo
        object

    :param key_type:
        A unicode string of "public" or "private"

    :param algo:
        A unicode string of "rsa" or "dsa"

    :param signing:
        If the key handle is for signing - may only be False for rsa keys

    :return:
        A byte string of a blob to pass to advapi32.CryptImportKey()
    """

    if key_type == 'public':
        blob_type = Advapi32Const.PUBLICKEYBLOB
    else:
        blob_type = Advapi32Const.PRIVATEKEYBLOB

    if algo == 'rsa':
        struct_type = 'RSABLOBHEADER'
        if signing:
            algorithm_id = Advapi32Const.CALG_RSA_SIGN
        else:
            algorithm_id = Advapi32Const.CALG_RSA_KEYX
    else:
        struct_type = 'DSSBLOBHEADER'
        algorithm_id = Advapi32Const.CALG_DSS_SIGN

    blob_header_pointer = struct(advapi32, 'BLOBHEADER')
    blob_header = unwrap(blob_header_pointer)
    blob_header.bType = blob_type
    blob_header.bVersion = Advapi32Const.CUR_BLOB_VERSION
    blob_header.reserved = 0
    blob_header.aiKeyAlg = algorithm_id

    blob_struct_pointer = struct(advapi32, struct_type)
    blob_struct = unwrap(blob_struct_pointer)
    blob_struct.publickeystruc = blob_header

    bit_size = key_info.bit_size
    len1 = bit_size // 8
    len2 = bit_size // 16

    if algo == 'rsa':
        pubkey_pointer = struct(advapi32, 'RSAPUBKEY')
        pubkey = unwrap(pubkey_pointer)
        pubkey.bitlen = bit_size
        if key_type == 'public':
            parsed_key_info = key_info['public_key'].parsed
            pubkey.magic = Advapi32Const.RSA1
            pubkey.pubexp = parsed_key_info['public_exponent'].native
            blob_data = int_to_bytes(parsed_key_info['modulus'].native, signed=False, width=len1)[::-1]
        else:
            parsed_key_info = key_info['private_key'].parsed
            pubkey.magic = Advapi32Const.RSA2
            pubkey.pubexp = parsed_key_info['public_exponent'].native
            blob_data = int_to_bytes(parsed_key_info['modulus'].native, signed=False, width=len1)[::-1]
            blob_data += int_to_bytes(parsed_key_info['prime1'].native, signed=False, width=len2)[::-1]
            blob_data += int_to_bytes(parsed_key_info['prime2'].native, signed=False, width=len2)[::-1]
            blob_data += int_to_bytes(parsed_key_info['exponent1'].native, signed=False, width=len2)[::-1]
            blob_data += int_to_bytes(parsed_key_info['exponent2'].native, signed=False, width=len2)[::-1]
            blob_data += int_to_bytes(parsed_key_info['coefficient'].native, signed=False, width=len2)[::-1]
            blob_data += int_to_bytes(parsed_key_info['private_exponent'].native, signed=False, width=len1)[::-1]
        blob_struct.rsapubkey = pubkey

    else:
        pubkey_pointer = struct(advapi32, 'DSSPUBKEY')
        pubkey = unwrap(pubkey_pointer)
        pubkey.bitlen = bit_size

        if key_type == 'public':
            pubkey.magic = Advapi32Const.DSS1
            params = key_info['algorithm']['parameters'].native
            key_data = int_to_bytes(key_info['public_key'].parsed.native, signed=False, width=len1)[::-1]
        else:
            pubkey.magic = Advapi32Const.DSS2
            params = key_info['private_key_algorithm']['parameters'].native
            key_data = int_to_bytes(key_info['private_key'].parsed.native, signed=False, width=20)[::-1]
        blob_struct.dsspubkey = pubkey

        blob_data = int_to_bytes(params['p'], signed=False, width=len1)[::-1]
        blob_data += int_to_bytes(params['q'], signed=False, width=20)[::-1]
        blob_data += int_to_bytes(params['g'], signed=False, width=len1)[::-1]
        blob_data += key_data

        dssseed_pointer = struct(advapi32, 'DSSSEED')
        dssseed = unwrap(dssseed_pointer)
        # This indicates no counter or seed info is available
        dssseed.counter = 0xffffffff

        blob_data += struct_bytes(dssseed_pointer)

    return struct_bytes(blob_struct_pointer) + blob_data


def _bcrypt_load_key(key_object, key_info, container, curve_name):
    """
    Loads a certificate, public key or private key into a Certificate,
    PublicKey or PrivateKey object via CNG

    :param key_object:
        An asn1crypto.x509.Certificate, asn1crypto.keys.PublicKeyInfo or
        asn1crypto.keys.PrivateKeyInfo object

    :param key_info:
        An asn1crypto.keys.PublicKeyInfo or asn1crypto.keys.PrivateKeyInfo
        object

    :param container:
        The class of the object to hold the key_handle

    :param curve_name:
        None or a unicode string of the curve name for an EC key

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PrivateKey, PublicKey or Certificate object, based on container
    """

    alg_handle = None
    key_handle = None

    key_type = 'public' if isinstance(key_info, PublicKeyInfo) else 'private'
    algo = key_info.algorithm
    if algo == 'rsassa_pss':
        algo = 'rsa'

    try:
        alg_selector = key_info.curve[1] if algo == 'ec' else algo
        alg_constant = {
            'rsa': BcryptConst.BCRYPT_RSA_ALGORITHM,
            'dsa': BcryptConst.BCRYPT_DSA_ALGORITHM,
            'secp256r1': BcryptConst.BCRYPT_ECDSA_P256_ALGORITHM,
            'secp384r1': BcryptConst.BCRYPT_ECDSA_P384_ALGORITHM,
            'secp521r1': BcryptConst.BCRYPT_ECDSA_P521_ALGORITHM,
        }[alg_selector]
        alg_handle = open_alg_handle(alg_constant)

        if algo == 'rsa':
            if key_type == 'public':
                blob_type = BcryptConst.BCRYPT_RSAPUBLIC_BLOB
                magic = BcryptConst.BCRYPT_RSAPUBLIC_MAGIC
                parsed_key = key_info['public_key'].parsed
                prime1_size = 0
                prime2_size = 0
            else:
                blob_type = BcryptConst.BCRYPT_RSAFULLPRIVATE_BLOB
                magic = BcryptConst.BCRYPT_RSAFULLPRIVATE_MAGIC
                parsed_key = key_info['private_key'].parsed
                prime1 = int_to_bytes(parsed_key['prime1'].native)
                prime2 = int_to_bytes(parsed_key['prime2'].native)
                exponent1 = int_to_bytes(parsed_key['exponent1'].native)
                exponent2 = int_to_bytes(parsed_key['exponent2'].native)
                coefficient = int_to_bytes(parsed_key['coefficient'].native)
                private_exponent = int_to_bytes(parsed_key['private_exponent'].native)
                prime1_size = len(prime1)
                prime2_size = len(prime2)

            public_exponent = int_to_bytes(parsed_key['public_exponent'].native)
            modulus = int_to_bytes(parsed_key['modulus'].native)

            blob_struct_pointer = struct(bcrypt, 'BCRYPT_RSAKEY_BLOB')
            blob_struct = unwrap(blob_struct_pointer)
            blob_struct.Magic = magic
            blob_struct.BitLength = key_info.bit_size
            blob_struct.cbPublicExp = len(public_exponent)
            blob_struct.cbModulus = len(modulus)
            blob_struct.cbPrime1 = prime1_size
            blob_struct.cbPrime2 = prime2_size

            blob = struct_bytes(blob_struct_pointer) + public_exponent + modulus
            if key_type == 'private':
                blob += prime1 + prime2
                blob += fill_width(exponent1, prime1_size)
                blob += fill_width(exponent2, prime2_size)
                blob += fill_width(coefficient, prime1_size)
                blob += fill_width(private_exponent, len(modulus))

        elif algo == 'dsa':
            if key_type == 'public':
                blob_type = BcryptConst.BCRYPT_DSA_PUBLIC_BLOB
                public_key = key_info['public_key'].parsed.native
                params = key_info['algorithm']['parameters']
            else:
                blob_type = BcryptConst.BCRYPT_DSA_PRIVATE_BLOB
                public_key = _unwrap_private_key_info(key_info)['public_key'].native
                private_bytes = int_to_bytes(key_info['private_key'].parsed.native)
                params = key_info['private_key_algorithm']['parameters']

            public_bytes = int_to_bytes(public_key)
            p = int_to_bytes(params['p'].native)
            g = int_to_bytes(params['g'].native)
            q = int_to_bytes(params['q'].native)

            if key_info.bit_size > 1024:
                q_len = len(q)
            else:
                q_len = 20

            key_width = max(len(public_bytes), len(g), len(p))

            public_bytes = fill_width(public_bytes, key_width)
            p = fill_width(p, key_width)
            g = fill_width(g, key_width)
            q = fill_width(q, q_len)
            # We don't know the count or seed, so we set them to the max value
            # since setting them to 0 results in a parameter error
            count = b'\xff' * 4
            seed = b'\xff' * q_len

            if key_info.bit_size > 1024:
                if key_type == 'public':
                    magic = BcryptConst.BCRYPT_DSA_PUBLIC_MAGIC_V2
                else:
                    magic = BcryptConst.BCRYPT_DSA_PRIVATE_MAGIC_V2

                blob_struct_pointer = struct(bcrypt, 'BCRYPT_DSA_KEY_BLOB_V2')
                blob_struct = unwrap(blob_struct_pointer)
                blob_struct.dwMagic = magic
                blob_struct.cbKey = key_width
                # We don't know if SHA256 was used here, but the output is long
                # enough for the generation of q for the supported 2048/224,
                # 2048/256 and 3072/256 FIPS approved pairs
                blob_struct.hashAlgorithm = BcryptConst.DSA_HASH_ALGORITHM_SHA256
                blob_struct.standardVersion = BcryptConst.DSA_FIPS186_3
                blob_struct.cbSeedLength = q_len
                blob_struct.cbGroupSize = q_len
                blob_struct.Count = byte_array(count)

                blob = struct_bytes(blob_struct_pointer)
                blob += seed + q + p + g + public_bytes
                if key_type == 'private':
                    blob += fill_width(private_bytes, q_len)

            else:
                if key_type == 'public':
                    magic = BcryptConst.BCRYPT_DSA_PUBLIC_MAGIC
                else:
                    magic = BcryptConst.BCRYPT_DSA_PRIVATE_MAGIC

                blob_struct_pointer = struct(bcrypt, 'BCRYPT_DSA_KEY_BLOB')
                blob_struct = unwrap(blob_struct_pointer)
                blob_struct.dwMagic = magic
                blob_struct.cbKey = key_width
                blob_struct.Count = byte_array(count)
                blob_struct.Seed = byte_array(seed)
                blob_struct.q = byte_array(q)

                blob = struct_bytes(blob_struct_pointer) + p + g + public_bytes
                if key_type == 'private':
                    blob += fill_width(private_bytes, q_len)

        elif algo == 'ec':
            if key_type == 'public':
                blob_type = BcryptConst.BCRYPT_ECCPUBLIC_BLOB
                x, y = key_info['public_key'].to_coords()
            else:
                blob_type = BcryptConst.BCRYPT_ECCPRIVATE_BLOB
                public_key = key_info['private_key'].parsed['public_key']
                # We aren't guaranteed to get the public key coords with the
                # key info structure, but BCrypt doesn't seem to have an issue
                # importing the private key with 0 values, which can only be
                # presumed that it is generating the x and y points from the
                # private key value and base point
                if public_key:
                    x, y = public_key.to_coords()
                else:
                    x = 0
                    y = 0
                private_bytes = int_to_bytes(key_info['private_key'].parsed['private_key'].native)

            blob_struct_pointer = struct(bcrypt, 'BCRYPT_ECCKEY_BLOB')
            blob_struct = unwrap(blob_struct_pointer)

            magic = {
                ('public', 'secp256r1'): BcryptConst.BCRYPT_ECDSA_PUBLIC_P256_MAGIC,
                ('public', 'secp384r1'): BcryptConst.BCRYPT_ECDSA_PUBLIC_P384_MAGIC,
                ('public', 'secp521r1'): BcryptConst.BCRYPT_ECDSA_PUBLIC_P521_MAGIC,
                ('private', 'secp256r1'): BcryptConst.BCRYPT_ECDSA_PRIVATE_P256_MAGIC,
                ('private', 'secp384r1'): BcryptConst.BCRYPT_ECDSA_PRIVATE_P384_MAGIC,
                ('private', 'secp521r1'): BcryptConst.BCRYPT_ECDSA_PRIVATE_P521_MAGIC,
            }[(key_type, curve_name)]

            key_width = {
                'secp256r1': 32,
                'secp384r1': 48,
                'secp521r1': 66
            }[curve_name]

            x_bytes = int_to_bytes(x)
            y_bytes = int_to_bytes(y)

            x_bytes = fill_width(x_bytes, key_width)
            y_bytes = fill_width(y_bytes, key_width)

            blob_struct.dwMagic = magic
            blob_struct.cbKey = key_width

            blob = struct_bytes(blob_struct_pointer) + x_bytes + y_bytes
            if key_type == 'private':
                blob += fill_width(private_bytes, key_width)

        key_handle_pointer = new(bcrypt, 'BCRYPT_KEY_HANDLE *')
        res = bcrypt.BCryptImportKeyPair(
            alg_handle,
            null(),
            blob_type,
            key_handle_pointer,
            blob,
            len(blob),
            BcryptConst.BCRYPT_NO_KEY_VALIDATION
        )
        handle_error(res)

        key_handle = unwrap(key_handle_pointer)
        return container(key_handle, key_object)

    finally:
        if alg_handle:
            close_alg_handle(alg_handle)


def load_private_key(source, password=None):
    """
    Loads a private key into a PrivateKey object

    :param source:
        A byte string of file contents, a unicode string filename or an
        asn1crypto.keys.PrivateKeyInfo object

    :param password:
        A byte or unicode string to decrypt the private key file. Unicode
        strings will be encoded using UTF-8. Not used is the source is a
        PrivateKeyInfo object.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the private key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PrivateKey object
    """

    if isinstance(source, PrivateKeyInfo):
        private_object = source

    else:
        if password is not None:
            if isinstance(password, str_cls):
                password = password.encode('utf-8')
            if not isinstance(password, byte_cls):
                raise TypeError(pretty_message(
                    '''
                    password must be a byte string, not %s
                    ''',
                    type_name(password)
                ))

        if isinstance(source, str_cls):
            with open(source, 'rb') as f:
                source = f.read()

        elif not isinstance(source, byte_cls):
            raise TypeError(pretty_message(
                '''
                source must be a byte string, unicode string or
                asn1crypto.keys.PrivateKeyInfo object, not %s
                ''',
                type_name(source)
            ))

        private_object = parse_private(source, password)

    return _load_key(private_object, PrivateKey)


def load_public_key(source):
    """
    Loads a public key into a PublicKey object

    :param source:
        A byte string of file contents, a unicode string filename or an
        asn1crypto.keys.PublicKeyInfo object

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when the public key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A PublicKey object
    """

    if isinstance(source, PublicKeyInfo):
        public_key = source

    elif isinstance(source, byte_cls):
        public_key = parse_public(source)

    elif isinstance(source, str_cls):
        with open(source, 'rb') as f:
            public_key = parse_public(f.read())

    else:
        raise TypeError(pretty_message(
            '''
            source must be a byte string, unicode string or
            asn1crypto.keys.PublicKeyInfo object, not %s
            ''',
            type_name(public_key)
        ))

    return _load_key(public_key, PublicKey)


def parse_pkcs12(data, password=None):
    """
    Parses a PKCS#12 ANS.1 DER-encoded structure and extracts certs and keys

    :param data:
        A byte string of a DER-encoded PKCS#12 file

    :param password:
        A byte string of the password to any encrypted data

    :raises:
        ValueError - when any of the parameters are of the wrong type or value
        OSError - when an error is returned by one of the OS decryption functions

    :return:
        A three-element tuple of:
         1. An asn1crypto.keys.PrivateKeyInfo object
         2. An asn1crypto.x509.Certificate object
         3. A list of zero or more asn1crypto.x509.Certificate objects that are
            "extra" certificates, possibly intermediates from the cert chain
    """

    return _parse_pkcs12(data, password, load_private_key)


def load_pkcs12(source, password=None):
    """
    Loads a .p12 or .pfx file into a PrivateKey object and one or more
    Certificates objects

    :param source:
        A byte string of file contents or a unicode string filename

    :param password:
        A byte or unicode string to decrypt the PKCS12 file. Unicode strings
        will be encoded using UTF-8.

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        oscrypto.errors.AsymmetricKeyError - when a contained key is incompatible with the OS crypto library
        OSError - when an error is returned by the OS crypto library

    :return:
        A three-element tuple containing (PrivateKey, Certificate, [Certificate, ...])
    """

    if password is not None:
        if isinstance(password, str_cls):
            password = password.encode('utf-8')
        if not isinstance(password, byte_cls):
            raise TypeError(pretty_message(
                '''
                password must be a byte string, not %s
                ''',
                type_name(password)
            ))

    if isinstance(source, str_cls):
        with open(source, 'rb') as f:
            source = f.read()

    elif not isinstance(source, byte_cls):
        raise TypeError(pretty_message(
            '''
            source must be a byte string or a unicode string, not %s
            ''',
            type_name(source)
        ))

    key_info, cert_info, extra_certs_info = parse_pkcs12(source, password)

    key = None
    cert = None

    if key_info:
        key = _load_key(key_info, PrivateKey)

    if cert_info:
        cert = _load_key(cert_info.public_key, Certificate)

    extra_certs = [_load_key(info.public_key, Certificate) for info in extra_certs_info]

    return (key, cert, extra_certs)


def rsa_pkcs1v15_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an RSASSA-PKCS-v1.5 signature.

    When the hash_algorithm is "raw", the operation is identical to RSA
    public key decryption. That is: the data is not hashed and no ASN.1
    structure with an algorithm identifier of the hash algorithm is placed in
    the encrypted byte string.

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if certificate_or_public_key.algorithm != 'rsa':
        raise ValueError('The key specified is not an RSA public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm)


def rsa_pss_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an RSASSA-PSS signature. For the PSS padding the mask gen algorithm
    will be mgf1 using the same hash algorithm as the signature. The salt length
    with be the length of the hash algorithm, and the trailer field with be the
    standard 0xBC byte.

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    cp_alg = certificate_or_public_key.algorithm

    if cp_alg != 'rsa' and cp_alg != 'rsassa_pss':
        raise ValueError('The key specified is not an RSA public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm, rsa_pss_padding=True)


def dsa_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies a DSA signature

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if certificate_or_public_key.algorithm != 'dsa':
        raise ValueError('The key specified is not a DSA public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm)


def ecdsa_verify(certificate_or_public_key, signature, data, hash_algorithm):
    """
    Verifies an ECDSA signature

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if certificate_or_public_key.algorithm != 'ec':
        raise ValueError('The key specified is not an EC public key')

    return _verify(certificate_or_public_key, signature, data, hash_algorithm)


def _verify(certificate_or_public_key, signature, data, hash_algorithm, rsa_pss_padding=False):
    """
    Verifies an RSA, DSA or ECDSA signature

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :param rsa_pss_padding:
        If PSS padding should be used for RSA keys

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if not isinstance(certificate_or_public_key, (Certificate, PublicKey)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the Certificate or
            PublicKey class, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    if not isinstance(signature, byte_cls):
        raise TypeError(pretty_message(
            '''
            signature must be a byte string, not %s
            ''',
            type_name(signature)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    cp_alg = certificate_or_public_key.algorithm
    cp_is_rsa = cp_alg == 'rsa' or cp_alg == 'rsassa_pss'

    valid_hash_algorithms = set(['md5', 'sha1', 'sha256', 'sha384', 'sha512'])
    if cp_is_rsa and not rsa_pss_padding:
        valid_hash_algorithms |= set(['raw'])

    if hash_algorithm not in valid_hash_algorithms:
        valid_hash_algorithms_error = '"md5", "sha1", "sha256", "sha384", "sha512"'
        if cp_is_rsa and not rsa_pss_padding:
            valid_hash_algorithms_error += ', "raw"'
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of %s, not %s
            ''',
            valid_hash_algorithms_error,
            repr(hash_algorithm)
        ))

    if not cp_is_rsa and rsa_pss_padding is not False:
        raise ValueError(pretty_message(
            '''
            PSS padding may only be used with RSA keys - signing via a %s key
            was requested
            ''',
            cp_alg.upper()
        ))

    if hash_algorithm == 'raw':
        if len(data) > certificate_or_public_key.byte_size - 11:
            raise ValueError(pretty_message(
                '''
                data must be 11 bytes shorter than the key size when
                hash_algorithm is "raw" - key size is %s bytes, but
                data is %s bytes long
                ''',
                certificate_or_public_key.byte_size,
                len(data)
            ))

    if _backend == 'winlegacy':
        if certificate_or_public_key.algorithm == 'ec':
            return _pure_python_ecdsa_verify(certificate_or_public_key, signature, data, hash_algorithm)
        return _advapi32_verify(certificate_or_public_key, signature, data, hash_algorithm, rsa_pss_padding)
    return _bcrypt_verify(certificate_or_public_key, signature, data, hash_algorithm, rsa_pss_padding)


def _advapi32_verify(certificate_or_public_key, signature, data, hash_algorithm, rsa_pss_padding=False):
    """
    Verifies an RSA, DSA or ECDSA signature via CryptoAPI

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :param rsa_pss_padding:
        If PSS padding should be used for RSA keys

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    algo = certificate_or_public_key.algorithm
    algo_is_rsa = algo == 'rsa' or algo == 'rsassa_pss'

    if algo_is_rsa and rsa_pss_padding:
        hash_length = {
            'sha1': 20,
            'sha224': 28,
            'sha256': 32,
            'sha384': 48,
            'sha512': 64
        }.get(hash_algorithm, 0)
        decrypted_signature = raw_rsa_public_crypt(certificate_or_public_key, signature)
        key_size = certificate_or_public_key.bit_size
        if not verify_pss_padding(hash_algorithm, hash_length, key_size, data, decrypted_signature):
            raise SignatureError('Signature is invalid')
        return

    if algo_is_rsa and hash_algorithm == 'raw':
        padded_plaintext = raw_rsa_public_crypt(certificate_or_public_key, signature)
        try:
            plaintext = remove_pkcs1v15_signature_padding(certificate_or_public_key.byte_size, padded_plaintext)
            if not constant_compare(plaintext, data):
                raise ValueError()
        except (ValueError):
            raise SignatureError('Signature is invalid')
        return

    hash_handle = None

    try:
        alg_id = {
            'md5': Advapi32Const.CALG_MD5,
            'sha1': Advapi32Const.CALG_SHA1,
            'sha256': Advapi32Const.CALG_SHA_256,
            'sha384': Advapi32Const.CALG_SHA_384,
            'sha512': Advapi32Const.CALG_SHA_512,
        }[hash_algorithm]

        hash_handle_pointer = new(advapi32, 'HCRYPTHASH *')
        res = advapi32.CryptCreateHash(
            certificate_or_public_key.context_handle,
            alg_id,
            null(),
            0,
            hash_handle_pointer
        )
        handle_error(res)

        hash_handle = unwrap(hash_handle_pointer)

        res = advapi32.CryptHashData(hash_handle, data, len(data), 0)
        handle_error(res)

        if algo == 'dsa':
            # Windows doesn't use the ASN.1 Sequence for DSA signatures,
            # so we have to convert it here for the verification to work
            try:
                signature = DSASignature.load(signature).to_p1363()
                # Switch the two integers so that the reversal later will
                # result in the correct order
                half_len = len(signature) // 2
                signature = signature[half_len:] + signature[:half_len]
            except (ValueError, OverflowError, TypeError):
                raise SignatureError('Signature is invalid')

        # The CryptoAPI expects signatures to be in little endian byte order,
        # which is the opposite of other systems, so we must reverse it
        reversed_signature = signature[::-1]

        res = advapi32.CryptVerifySignatureW(
            hash_handle,
            reversed_signature,
            len(signature),
            certificate_or_public_key.key_handle,
            null(),
            0
        )
        handle_error(res)

    finally:
        if hash_handle:
            advapi32.CryptDestroyHash(hash_handle)


def _bcrypt_verify(certificate_or_public_key, signature, data, hash_algorithm, rsa_pss_padding=False):
    """
    Verifies an RSA, DSA or ECDSA signature via CNG

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to verify the signature with

    :param signature:
        A byte string of the signature to verify

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :param rsa_pss_padding:
        If PSS padding should be used for RSA keys

    :raises:
        oscrypto.errors.SignatureError - when the signature is determined to be invalid
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library
    """

    if hash_algorithm == 'raw':
        digest = data
    else:
        hash_constant = {
            'md5': BcryptConst.BCRYPT_MD5_ALGORITHM,
            'sha1': BcryptConst.BCRYPT_SHA1_ALGORITHM,
            'sha256': BcryptConst.BCRYPT_SHA256_ALGORITHM,
            'sha384': BcryptConst.BCRYPT_SHA384_ALGORITHM,
            'sha512': BcryptConst.BCRYPT_SHA512_ALGORITHM
        }[hash_algorithm]
        digest = getattr(hashlib, hash_algorithm)(data).digest()

    padding_info = null()
    flags = 0

    cp_alg = certificate_or_public_key.algorithm
    cp_is_rsa = cp_alg == 'rsa' or cp_alg == 'rsassa_pss'

    if cp_is_rsa:
        if rsa_pss_padding:
            flags = BcryptConst.BCRYPT_PAD_PSS
            padding_info_struct_pointer = struct(bcrypt, 'BCRYPT_PSS_PADDING_INFO')
            padding_info_struct = unwrap(padding_info_struct_pointer)
            # This has to be assigned to a variable to prevent cffi from gc'ing it
            hash_buffer = buffer_from_unicode(hash_constant)
            padding_info_struct.pszAlgId = cast(bcrypt, 'wchar_t *', hash_buffer)
            padding_info_struct.cbSalt = len(digest)
        else:
            flags = BcryptConst.BCRYPT_PAD_PKCS1
            padding_info_struct_pointer = struct(bcrypt, 'BCRYPT_PKCS1_PADDING_INFO')
            padding_info_struct = unwrap(padding_info_struct_pointer)
            # This has to be assigned to a variable to prevent cffi from gc'ing it
            if hash_algorithm == 'raw':
                padding_info_struct.pszAlgId = null()
            else:
                hash_buffer = buffer_from_unicode(hash_constant)
                padding_info_struct.pszAlgId = cast(bcrypt, 'wchar_t *', hash_buffer)
        padding_info = cast(bcrypt, 'void *', padding_info_struct_pointer)
    else:
        # Windows doesn't use the ASN.1 Sequence for DSA/ECDSA signatures,
        # so we have to convert it here for the verification to work
        try:
            signature = DSASignature.load(signature).to_p1363()
        except (ValueError, OverflowError, TypeError):
            raise SignatureError('Signature is invalid')

    res = bcrypt.BCryptVerifySignature(
        certificate_or_public_key.key_handle,
        padding_info,
        digest,
        len(digest),
        signature,
        len(signature),
        flags
    )
    failure = res == BcryptConst.STATUS_INVALID_SIGNATURE
    failure = failure or res == BcryptConst.STATUS_INVALID_PARAMETER
    if failure:
        raise SignatureError('Signature is invalid')

    handle_error(res)


def rsa_pkcs1v15_sign(private_key, data, hash_algorithm):
    """
    Generates an RSASSA-PKCS-v1.5 signature.

    When the hash_algorithm is "raw", the operation is identical to RSA
    private key encryption. That is: the data is not hashed and no ASN.1
    structure with an algorithm identifier of the hash algorithm is placed in
    the encrypted byte string.

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if private_key.algorithm != 'rsa':
        raise ValueError('The key specified is not an RSA private key')

    return _sign(private_key, data, hash_algorithm)


def rsa_pss_sign(private_key, data, hash_algorithm):
    """
    Generates an RSASSA-PSS signature. For the PSS padding the mask gen
    algorithm will be mgf1 using the same hash algorithm as the signature. The
    salt length with be the length of the hash algorithm, and the trailer field
    with be the standard 0xBC byte.

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    pkey_alg = private_key.algorithm

    if pkey_alg != 'rsa' and pkey_alg != 'rsassa_pss':
        raise ValueError('The key specified is not an RSA private key')

    return _sign(private_key, data, hash_algorithm, rsa_pss_padding=True)


def dsa_sign(private_key, data, hash_algorithm):
    """
    Generates a DSA signature

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if private_key.algorithm != 'dsa':
        raise ValueError('The key specified is not a DSA private key')

    return _sign(private_key, data, hash_algorithm)


def ecdsa_sign(private_key, data, hash_algorithm):
    """
    Generates an ECDSA signature

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384" or "sha512"

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if private_key.algorithm != 'ec':
        raise ValueError('The key specified is not an EC private key')

    return _sign(private_key, data, hash_algorithm)


def _sign(private_key, data, hash_algorithm, rsa_pss_padding=False):
    """
    Generates an RSA, DSA or ECDSA signature

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :param rsa_pss_padding:
        If PSS padding should be used for RSA keys

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if not isinstance(private_key, PrivateKey):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of PrivateKey, not %s
            ''',
            type_name(private_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    pkey_alg = private_key.algorithm
    pkey_is_rsa = pkey_alg == 'rsa' or pkey_alg == 'rsassa_pss'

    valid_hash_algorithms = set(['md5', 'sha1', 'sha256', 'sha384', 'sha512'])
    if private_key.algorithm == 'rsa' and not rsa_pss_padding:
        valid_hash_algorithms |= set(['raw'])

    if hash_algorithm not in valid_hash_algorithms:
        valid_hash_algorithms_error = '"md5", "sha1", "sha256", "sha384", "sha512"'
        if pkey_is_rsa and not rsa_pss_padding:
            valid_hash_algorithms_error += ', "raw"'
        raise ValueError(pretty_message(
            '''
            hash_algorithm must be one of %s, not %s
            ''',
            valid_hash_algorithms_error,
            repr(hash_algorithm)
        ))

    if not pkey_is_rsa and rsa_pss_padding is not False:
        raise ValueError(pretty_message(
            '''
            PSS padding may only be used with RSA keys - signing via a %s key
            was requested
            ''',
            pkey_alg.upper()
        ))

    if hash_algorithm == 'raw':
        if len(data) > private_key.byte_size - 11:
            raise ValueError(pretty_message(
                '''
                data must be 11 bytes shorter than the key size when
                hash_algorithm is "raw" - key size is %s bytes, but data
                is %s bytes long
                ''',
                private_key.byte_size,
                len(data)
            ))

    if _backend == 'winlegacy':
        if private_key.algorithm == 'ec':
            return _pure_python_ecdsa_sign(private_key, data, hash_algorithm)
        return _advapi32_sign(private_key, data, hash_algorithm, rsa_pss_padding)
    return _bcrypt_sign(private_key, data, hash_algorithm, rsa_pss_padding)


def _advapi32_sign(private_key, data, hash_algorithm, rsa_pss_padding=False):
    """
    Generates an RSA, DSA or ECDSA signature via CryptoAPI

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :param rsa_pss_padding:
        If PSS padding should be used for RSA keys

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    algo = private_key.algorithm
    algo_is_rsa = algo == 'rsa' or algo == 'rsassa_pss'

    if algo_is_rsa and hash_algorithm == 'raw':
        padded_data = add_pkcs1v15_signature_padding(private_key.byte_size, data)
        return raw_rsa_private_crypt(private_key, padded_data)

    if algo_is_rsa and rsa_pss_padding:
        hash_length = {
            'sha1': 20,
            'sha224': 28,
            'sha256': 32,
            'sha384': 48,
            'sha512': 64
        }.get(hash_algorithm, 0)
        padded_data = add_pss_padding(hash_algorithm, hash_length, private_key.bit_size, data)
        return raw_rsa_private_crypt(private_key, padded_data)

    if private_key.algorithm == 'dsa' and hash_algorithm == 'md5':
        raise ValueError(pretty_message(
            '''
            Windows does not support md5 signatures with DSA keys
            '''
        ))

    hash_handle = None

    try:
        alg_id = {
            'md5': Advapi32Const.CALG_MD5,
            'sha1': Advapi32Const.CALG_SHA1,
            'sha256': Advapi32Const.CALG_SHA_256,
            'sha384': Advapi32Const.CALG_SHA_384,
            'sha512': Advapi32Const.CALG_SHA_512,
        }[hash_algorithm]

        hash_handle_pointer = new(advapi32, 'HCRYPTHASH *')
        res = advapi32.CryptCreateHash(
            private_key.context_handle,
            alg_id,
            null(),
            0,
            hash_handle_pointer
        )
        handle_error(res)

        hash_handle = unwrap(hash_handle_pointer)

        res = advapi32.CryptHashData(hash_handle, data, len(data), 0)
        handle_error(res)

        out_len = new(advapi32, 'DWORD *')
        res = advapi32.CryptSignHashW(
            hash_handle,
            Advapi32Const.AT_SIGNATURE,
            null(),
            0,
            null(),
            out_len
        )
        handle_error(res)

        buffer_length = deref(out_len)
        buffer_ = buffer_from_bytes(buffer_length)

        res = advapi32.CryptSignHashW(
            hash_handle,
            Advapi32Const.AT_SIGNATURE,
            null(),
            0,
            buffer_,
            out_len
        )
        handle_error(res)

        output = bytes_from_buffer(buffer_, deref(out_len))

        # CryptoAPI outputs the signature in little endian byte order, so we
        # must swap it for compatibility with other systems
        output = output[::-1]

        if algo == 'dsa':
            # Switch the two integers because the reversal just before switched
            # then
            half_len = len(output) // 2
            output = output[half_len:] + output[:half_len]
            # Windows doesn't use the ASN.1 Sequence for DSA signatures,
            # so we have to convert it here for the verification to work
            output = DSASignature.from_p1363(output).dump()

        return output

    finally:
        if hash_handle:
            advapi32.CryptDestroyHash(hash_handle)


def _bcrypt_sign(private_key, data, hash_algorithm, rsa_pss_padding=False):
    """
    Generates an RSA, DSA or ECDSA signature via CNG

    :param private_key:
        The PrivateKey to generate the signature with

    :param data:
        A byte string of the data the signature is for

    :param hash_algorithm:
        A unicode string of "md5", "sha1", "sha256", "sha384", "sha512" or "raw"

    :param rsa_pss_padding:
        If PSS padding should be used for RSA keys

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the signature
    """

    if hash_algorithm == 'raw':
        digest = data
    else:
        hash_constant = {
            'md5': BcryptConst.BCRYPT_MD5_ALGORITHM,
            'sha1': BcryptConst.BCRYPT_SHA1_ALGORITHM,
            'sha256': BcryptConst.BCRYPT_SHA256_ALGORITHM,
            'sha384': BcryptConst.BCRYPT_SHA384_ALGORITHM,
            'sha512': BcryptConst.BCRYPT_SHA512_ALGORITHM
        }[hash_algorithm]

        digest = getattr(hashlib, hash_algorithm)(data).digest()

    padding_info = null()
    flags = 0

    pkey_alg = private_key.algorithm
    pkey_is_rsa = pkey_alg == 'rsa' or pkey_alg == 'rsassa_pss'

    if pkey_is_rsa:
        if rsa_pss_padding:
            hash_length = {
                'md5': 16,
                'sha1': 20,
                'sha256': 32,
                'sha384': 48,
                'sha512': 64
            }[hash_algorithm]

            flags = BcryptConst.BCRYPT_PAD_PSS
            padding_info_struct_pointer = struct(bcrypt, 'BCRYPT_PSS_PADDING_INFO')
            padding_info_struct = unwrap(padding_info_struct_pointer)
            # This has to be assigned to a variable to prevent cffi from gc'ing it
            hash_buffer = buffer_from_unicode(hash_constant)
            padding_info_struct.pszAlgId = cast(bcrypt, 'wchar_t *', hash_buffer)
            padding_info_struct.cbSalt = hash_length
        else:
            flags = BcryptConst.BCRYPT_PAD_PKCS1
            padding_info_struct_pointer = struct(bcrypt, 'BCRYPT_PKCS1_PADDING_INFO')
            padding_info_struct = unwrap(padding_info_struct_pointer)
            # This has to be assigned to a variable to prevent cffi from gc'ing it
            if hash_algorithm == 'raw':
                padding_info_struct.pszAlgId = null()
            else:
                hash_buffer = buffer_from_unicode(hash_constant)
                padding_info_struct.pszAlgId = cast(bcrypt, 'wchar_t *', hash_buffer)
        padding_info = cast(bcrypt, 'void *', padding_info_struct_pointer)

    if pkey_alg == 'dsa' and private_key.bit_size > 1024 and hash_algorithm in set(['md5', 'sha1']):
        raise ValueError(pretty_message(
            '''
            Windows does not support sha1 signatures with DSA keys based on
            sha224, sha256 or sha512
            '''
        ))

    out_len = new(bcrypt, 'DWORD *')
    res = bcrypt.BCryptSignHash(
        private_key.key_handle,
        padding_info,
        digest,
        len(digest),
        null(),
        0,
        out_len,
        flags
    )
    handle_error(res)

    buffer_len = deref(out_len)
    buffer = buffer_from_bytes(buffer_len)

    if pkey_is_rsa:
        padding_info = cast(bcrypt, 'void *', padding_info_struct_pointer)

    res = bcrypt.BCryptSignHash(
        private_key.key_handle,
        padding_info,
        digest,
        len(digest),
        buffer,
        buffer_len,
        out_len,
        flags
    )
    handle_error(res)
    signature = bytes_from_buffer(buffer, deref(out_len))

    if not pkey_is_rsa:
        # Windows doesn't use the ASN.1 Sequence for DSA/ECDSA signatures,
        # so we have to convert it here for the verification to work
        signature = DSASignature.from_p1363(signature).dump()

    return signature


def _encrypt(certificate_or_public_key, data, rsa_oaep_padding=False):
    """
    Encrypts a value using an RSA public key

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to encrypt with

    :param data:
        A byte string of the data to encrypt

    :param rsa_oaep_padding:
        If OAEP padding should be used instead of PKCS#1 v1.5

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    if not isinstance(certificate_or_public_key, (Certificate, PublicKey)):
        raise TypeError(pretty_message(
            '''
            certificate_or_public_key must be an instance of the Certificate or
            PublicKey class, not %s
            ''',
            type_name(certificate_or_public_key)
        ))

    if not isinstance(data, byte_cls):
        raise TypeError(pretty_message(
            '''
            data must be a byte string, not %s
            ''',
            type_name(data)
        ))

    if not isinstance(rsa_oaep_padding, bool):
        raise TypeError(pretty_message(
            '''
            rsa_oaep_padding must be a bool, not %s
            ''',
            type_name(rsa_oaep_padding)
        ))

    if _backend == 'winlegacy':
        return _advapi32_encrypt(certificate_or_public_key, data, rsa_oaep_padding)
    return _bcrypt_encrypt(certificate_or_public_key, data, rsa_oaep_padding)


def _advapi32_encrypt(certificate_or_public_key, data, rsa_oaep_padding=False):
    """
    Encrypts a value using an RSA public key via CryptoAPI

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to encrypt with

    :param data:
        A byte string of the data to encrypt

    :param rsa_oaep_padding:
        If OAEP padding should be used instead of PKCS#1 v1.5

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    flags = 0
    if rsa_oaep_padding:
        flags = Advapi32Const.CRYPT_OAEP

    out_len = new(advapi32, 'DWORD *', len(data))
    res = advapi32.CryptEncrypt(
        certificate_or_public_key.ex_key_handle,
        null(),
        True,
        flags,
        null(),
        out_len,
        0
    )
    handle_error(res)

    buffer_len = deref(out_len)
    buffer = buffer_from_bytes(buffer_len)
    write_to_buffer(buffer, data)

    pointer_set(out_len, len(data))
    res = advapi32.CryptEncrypt(
        certificate_or_public_key.ex_key_handle,
        null(),
        True,
        flags,
        buffer,
        out_len,
        buffer_len
    )
    handle_error(res)

    return bytes_from_buffer(buffer, deref(out_len))[::-1]


def _bcrypt_encrypt(certificate_or_public_key, data, rsa_oaep_padding=False):
    """
    Encrypts a value using an RSA public key via CNG

    :param certificate_or_public_key:
        A Certificate or PublicKey instance to encrypt with

    :param data:
        A byte string of the data to encrypt

    :param rsa_oaep_padding:
        If OAEP padding should be used instead of PKCS#1 v1.5

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the ciphertext
    """

    flags = BcryptConst.BCRYPT_PAD_PKCS1
    if rsa_oaep_padding is True:
        flags = BcryptConst.BCRYPT_PAD_OAEP

        padding_info_struct_pointer = struct(bcrypt, 'BCRYPT_OAEP_PADDING_INFO')
        padding_info_struct = unwrap(padding_info_struct_pointer)
        # This has to be assigned to a variable to prevent cffi from gc'ing it
        hash_buffer = buffer_from_unicode(BcryptConst.BCRYPT_SHA1_ALGORITHM)
        padding_info_struct.pszAlgId = cast(bcrypt, 'wchar_t *', hash_buffer)
        padding_info_struct.pbLabel = null()
        padding_info_struct.cbLabel = 0
        padding_info = cast(bcrypt, 'void *', padding_info_struct_pointer)
    else:
        padding_info = null()

    out_len = new(bcrypt, 'ULONG *')
    res = bcrypt.BCryptEncrypt(
        certificate_or_public_key.key_handle,
        data,
        len(data),
        padding_info,
        null(),
        0,
        null(),
        0,
        out_len,
        flags
    )
    handle_error(res)

    buffer_len = deref(out_len)
    buffer = buffer_from_bytes(buffer_len)

    res = bcrypt.BCryptEncrypt(
        certificate_or_public_key.key_handle,
        data,
        len(data),
        padding_info,
        null(),
        0,
        buffer,
        buffer_len,
        out_len,
        flags
    )
    handle_error(res)

    return bytes_from_buffer(buffer, deref(out_len))


def _decrypt(private_key, ciphertext, rsa_oaep_padding=False):
    """
    Encrypts a value using an RSA private key

    :param private_key:
        A PrivateKey instance to decrypt with

    :param ciphertext:
        A byte string of the data to decrypt

    :param rsa_oaep_padding:
        If OAEP padding should be used instead of PKCS#1 v1.5

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    if not isinstance(private_key, PrivateKey):
        raise TypeError(pretty_message(
            '''
            private_key must be an instance of the PrivateKey class, not %s
            ''',
            type_name(private_key)
        ))

    if not isinstance(ciphertext, byte_cls):
        raise TypeError(pretty_message(
            '''
            ciphertext must be a byte string, not %s
            ''',
            type_name(ciphertext)
        ))

    if not isinstance(rsa_oaep_padding, bool):
        raise TypeError(pretty_message(
            '''
            rsa_oaep_padding must be a bool, not %s
            ''',
            type_name(rsa_oaep_padding)
        ))

    if _backend == 'winlegacy':
        return _advapi32_decrypt(private_key, ciphertext, rsa_oaep_padding)
    return _bcrypt_decrypt(private_key, ciphertext, rsa_oaep_padding)


def _advapi32_decrypt(private_key, ciphertext, rsa_oaep_padding=False):
    """
    Encrypts a value using an RSA private key via CryptoAPI

    :param private_key:
        A PrivateKey instance to decrypt with

    :param ciphertext:
        A byte string of the data to decrypt

    :param rsa_oaep_padding:
        If OAEP padding should be used instead of PKCS#1 v1.5

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    flags = 0
    if rsa_oaep_padding:
        flags = Advapi32Const.CRYPT_OAEP

    ciphertext = ciphertext[::-1]

    buffer = buffer_from_bytes(ciphertext)
    out_len = new(advapi32, 'DWORD *', len(ciphertext))
    res = advapi32.CryptDecrypt(
        private_key.ex_key_handle,
        null(),
        True,
        flags,
        buffer,
        out_len
    )
    handle_error(res)

    return bytes_from_buffer(buffer, deref(out_len))


def _bcrypt_decrypt(private_key, ciphertext, rsa_oaep_padding=False):
    """
    Encrypts a value using an RSA private key via CNG

    :param private_key:
        A PrivateKey instance to decrypt with

    :param ciphertext:
        A byte string of the data to decrypt

    :param rsa_oaep_padding:
        If OAEP padding should be used instead of PKCS#1 v1.5

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the plaintext
    """

    flags = BcryptConst.BCRYPT_PAD_PKCS1
    if rsa_oaep_padding is True:
        flags = BcryptConst.BCRYPT_PAD_OAEP

        padding_info_struct_pointer = struct(bcrypt, 'BCRYPT_OAEP_PADDING_INFO')
        padding_info_struct = unwrap(padding_info_struct_pointer)
        # This has to be assigned to a variable to prevent cffi from gc'ing it
        hash_buffer = buffer_from_unicode(BcryptConst.BCRYPT_SHA1_ALGORITHM)
        padding_info_struct.pszAlgId = cast(bcrypt, 'wchar_t *', hash_buffer)
        padding_info_struct.pbLabel = null()
        padding_info_struct.cbLabel = 0
        padding_info = cast(bcrypt, 'void *', padding_info_struct_pointer)
    else:
        padding_info = null()

    out_len = new(bcrypt, 'ULONG *')
    res = bcrypt.BCryptDecrypt(
        private_key.key_handle,
        ciphertext,
        len(ciphertext),
        padding_info,
        null(),
        0,
        null(),
        0,
        out_len,
        flags
    )
    handle_error(res)

    buffer_len = deref(out_len)
    buffer = buffer_from_bytes(buffer_len)

    res = bcrypt.BCryptDecrypt(
        private_key.key_handle,
        ciphertext,
        len(ciphertext),
        padding_info,
        null(),
        0,
        buffer,
        buffer_len,
        out_len,
        flags
    )
    handle_error(res)

    return bytes_from_buffer(buffer, deref(out_len))


def rsa_pkcs1v15_encrypt(certificate_or_public_key, data):
    """
    Encrypts a byte string using an RSA public key or certificate. Uses PKCS#1
    v1.5 padding.

    :param certificate_or_public_key:
        A PublicKey or Certificate object

    :param data:
        A byte string, with a maximum length 11 bytes less than the key length
        (in bytes)

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the encrypted data
    """

    return _encrypt(certificate_or_public_key, data)


def rsa_pkcs1v15_decrypt(private_key, ciphertext):
    """
    Decrypts a byte string using an RSA private key. Uses PKCS#1 v1.5 padding.

    :param private_key:
        A PrivateKey object

    :param ciphertext:
        A byte string of the encrypted data

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the original plaintext
    """

    return _decrypt(private_key, ciphertext)


def rsa_oaep_encrypt(certificate_or_public_key, data):
    """
    Encrypts a byte string using an RSA public key or certificate. Uses PKCS#1
    OAEP padding with SHA1.

    :param certificate_or_public_key:
        A PublicKey or Certificate object

    :param data:
        A byte string, with a maximum length 41 bytes (or more) less than the
        key length (in bytes)

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the encrypted data
    """

    return _encrypt(certificate_or_public_key, data, rsa_oaep_padding=True)


def rsa_oaep_decrypt(private_key, ciphertext):
    """
    Decrypts a byte string using an RSA private key. Uses PKCS#1 OAEP padding
    with SHA1.

    :param private_key:
        A PrivateKey object

    :param ciphertext:
        A byte string of the encrypted data

    :raises:
        ValueError - when any of the parameters contain an invalid value
        TypeError - when any of the parameters are of the wrong type
        OSError - when an error is returned by the OS crypto library

    :return:
        A byte string of the original plaintext
    """

    return _decrypt(private_key, ciphertext, rsa_oaep_padding=True)

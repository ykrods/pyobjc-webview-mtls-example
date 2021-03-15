import objc

from logging import getLogger
from contextlib import contextmanager

from Foundation import (
    NSURLCredential,
    NSURLCredentialPersistenceForSession,
)
from Security import (
    errSecSuccess,
    kSecFormatPKCS12,
    kSecItemTypeAggregate,
    SecIdentityGetTypeID,
    SecItemImport,
    SecItemImportExportKeyParameters,
    SecKeychainCreate,
    SecKeychainDelete,
    SecKeychainOpen,
    SecKeychainUnlock,
    SEC_KEY_IMPORT_EXPORT_PARAMS_VERSION,
)
# Prevent `ObjCPointerWarning: PyObjCPointer created: ... type ^{__SecTrust=}`
from Security import SecTrustRef
assert SecTrustRef  # to suppress pyflakes warning


logger = getLogger(__name__)


# patch NSURLCredential.credentialWithIdentity:certificates:persistence:
# see https://github.com/ronaldoussoren/pyobjc/issues/320
objc.registerCFSignature("SecIdentityRef",
                         b"^{__SecIdentity=}",
                         SecIdentityGetTypeID())
objc.registerMetaDataForSelector(
    b'NSURLCredential',
    b'credentialWithIdentity:certificates:persistence:',
    {
        'arguments': {
            2: {'null_accepted': False, 'type': b'@'},
            3: {'_template': True, 'type': b'@'},
            4: {'_template': True, 'type': b'Q'},
        },
        'classmethod': True,
        'hidden': False,
        'retval': {'_template': True, 'type': b"@"}
    }
)


class Keychain:
    path_name = None
    passphrase = None

    def __init__(self, path_name, password):
        self.path_name = path_name
        self.passphrase = password

    def unlockedKeychain(self):
        assert self.path_name
        assert self.passphrase

        status, keychain = SecKeychainOpen(self.path_name, None)
        if status == errSecSuccess:
            status = SecKeychainUnlock(keychain,
                                       len(self.passphrase),
                                       self.passphrase,
                                       True)

            if status == errSecSuccess:
                return keychain
            else:
                # recreate keychain
                SecKeychainDelete(keychain)

        status, keychain = SecKeychainCreate(self.path_name,
                                             len(self.passphrase),
                                             self.passphrase,
                                             False,
                                             None,
                                             None)
        if status == errSecSuccess:
            return keychain

    def importP12(self, p12, passphrase):
        keychain = self.unlockedKeychain()

        keyParams = SecItemImportExportKeyParameters()
        keyParams.passphrase = passphrase.encode("utf-8")
        keyParams.version = SEC_KEY_IMPORT_EXPORT_PARAMS_VERSION
        status, _, _, items = SecItemImport(p12,
                                            None,  # fileNameOrExtension
                                            kSecFormatPKCS12,  # inputFormat
                                            kSecItemTypeAggregate,  # itemType
                                            0,  # flags
                                            keyParams,
                                            keychain,
                                            None)  # &items

        if status != errSecSuccess or len(items) != 1:
            raise Exception("fooo")

        credential = NSURLCredential.credentialWithIdentity_certificates_persistence_(  # NOQA
            items[0], None, NSURLCredentialPersistenceForSession,
        )
        return credential

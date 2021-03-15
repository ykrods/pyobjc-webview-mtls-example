import ssl
import tempfile

from datetime import datetime, timedelta
from ipaddress import IPv4Address
from logging import getLogger

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization.pkcs12 import (
    serialize_key_and_certificates,
)


logger = getLogger(__name__)


class CertManager:
    server_cert = None
    server_key = None
    server_keypass = None
    client_p12 = None
    client_p12pass = None
    client_cert = None

    def generate_certs(self):
        keypass = self.server_keypass = "PASSWORD"  # TODO: generate password
        self.server_cert, self.server_key = generate_server_cert(
            "my-app-server", keypass
        )

        p12pass = self.client_p12pass = "PASSWORD"  # TODO: generate password
        self.client_cert, self.client_p12 = generate_client_cert(
            "my-app-client", p12pass
        )

    def create_ssl_context(self):
        """Create SSLContext for python server"""
        assert self.server_cert
        assert self.server_key
        assert self.server_keypass
        assert self.client_cert

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.verify_mode = ssl.CERT_REQUIRED

        with tempfile.NamedTemporaryFile(mode="w") as tmpf:
            tmpf.write(self.server_cert.decode('utf-8'))
            tmpf.write("\n")
            tmpf.write(self.server_key.decode('utf-8'))
            tmpf.flush()
            ctx.load_cert_chain(tmpf.name, password=self.server_keypass)

        with tempfile.NamedTemporaryFile(mode="wb") as tmpf:
            tmpf.write(self.client_cert)
            tmpf.flush()
            ctx.load_verify_locations(cafile=tmpf.name)

        return ctx


def base_cert(name, key):
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, name),
    ])

    return x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.utcnow()
    ).not_valid_after(
        datetime.utcnow() + timedelta(days=1)
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            content_commitment=False,
            key_encipherment=False,
            data_encipherment=False,
            key_agreement=False,
            crl_sign=False,
            key_cert_sign=True,
            encipher_only=False,
            decipher_only=False,
        ), critical=True,
    )


def generate_server_cert(name, passphrase):
    """
    """
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    cert = base_cert(name, key).add_extension(
        x509.SubjectAlternativeName([
            x509.IPAddress(IPv4Address("127.0.0.1"))
        ]), critical=False
    ).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
        ]), critical=True,
    ).sign(key, hashes.SHA256())

    return (
        cert.public_bytes(serialization.Encoding.PEM),
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.BestAvailableEncryption(
                passphrase.encode('utf-8')
            )
        ),
    )


def generate_client_cert(name, passphrase):
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    cert = base_cert(name, key).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.CLIENT_AUTH,
        ]), critical=True,
    ).sign(key, hashes.SHA256())

    p12 = serialize_key_and_certificates(
        b'client',
        key,
        cert,
        None,
        encryption_algorithm=serialization.BestAvailableEncryption(
            passphrase.encode('utf-8')
        )
    )

    return (
        cert.public_bytes(serialization.Encoding.PEM),
        p12,
    )

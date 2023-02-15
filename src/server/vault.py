from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
import requests



class NetSec:
    '''https://stackoverflow.com/questions/51645324/how-to-setup-a-aiohttp-https-server-and-client'''

    def generate_netsec(self, filepath:str):
            key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )

            with open(f"{filepath}.key", "wb") as f:
                f.write(key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                ))

            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, u"World"),
                x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Kanto"),
                x509.NameAttribute(NameOID.LOCALITY_NAME, u"Indigo Plateau"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"psyducorp"),
                x509.NameAttribute(NameOID.COMMON_NAME, 'AnchiDori'),
            ])

            cert = x509.CertificateBuilder().subject_name(
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
                # Our certificate will be valid for 5 years
                datetime.utcnow() + timedelta(days=365*5)
            ).add_extension(
                x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
                critical=False,
            # Sign our certificate with our private key
            ).sign(key, hashes.SHA256(), default_backend())

            with open(f"{filepath}.crt", "wb") as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))


    def verify_certificate(self, hostname:str, port:str, public_crt_filepath:str):
        r = requests.get(f'https://{hostname}:{port}', verify=public_crt_filepath)
        return r
        



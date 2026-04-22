"""Local QR code data generation for BankID animated QR codes.

Generates the ``bankid.<token>.<time>.<hmac>`` string that a QR-code
renderer can turn into a scannable image.  The server rotates QR data
every second, so call :func:`generate_qr_data` with an incrementing
*elapsed_seconds* counter to keep the code fresh.

Uses only the Python standard library (hmac, hashlib).
"""

from __future__ import annotations

import hashlib
import hmac as _hmac


def generate_qr_data(
    qr_start_token: str,
    qr_start_secret: str,
    elapsed_seconds: int,
) -> str:
    """Build a BankID animated QR code payload.

    Parameters
    ----------
    qr_start_token:
        The ``qrStartToken`` value returned by the ``/start`` endpoint.
    qr_start_secret:
        The ``qrStartSecret`` value returned by the ``/start`` endpoint.
    elapsed_seconds:
        Number of whole seconds since the BankID order was created.

    Returns
    -------
    str
        A string in the format ``bankid.{qr_start_token}.{elapsed_seconds}.{hex_hmac}``
        suitable for encoding into a QR code image.
    """
    auth_code = _hmac.new(
        qr_start_secret.encode("utf-8"),
        str(elapsed_seconds).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return f"bankid.{qr_start_token}.{elapsed_seconds}.{auth_code}"

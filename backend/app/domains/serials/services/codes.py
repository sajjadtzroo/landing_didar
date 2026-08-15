"""Serial-code helpers — pure and stateless. Codes are stored canonical
(uppercase, no separator, e.g. DGVAB12CD34) and rendered DGV-AB12CD34."""

import secrets

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars (0/O, 1/I/L)


def new_code() -> str:
    return "DGV" + "".join(secrets.choice(_ALPHABET) for _ in range(8))


def normalize(raw: str) -> str:
    """Canonicalize a hand-typed code: uppercase, drop separators/spaces.
    `dgv-ab12 cd34` -> `DGVAB12CD34`."""
    return "".join(c for c in (raw or "").upper() if c.isalnum())


def format_code(code: str) -> str:
    """Canonical -> display form (DGV-XXXXXXXX)."""
    return f"{code[:3]}-{code[3:]}" if len(code) > 3 else code


def qr_png(code: str, base_url: str) -> bytes:
    """QR image for a piece's label — encodes the public verify deep-link."""
    import io

    import qrcode

    img = qrcode.make(
        f"{base_url}/verify?code={format_code(code)}",
        box_size=8,
        border=2,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

"""Flake protocol codec (de.imagineon) for Zehnder / getair ComfoSpot.

Clean-room reimplementation of the wire format, reconstructed from a live
network capture and protocol observation. No vendor code is used here.

Frame (header is always 8 bytes, optionally followed by result/length/payload):
  byte0    = code | (hasResult ? 0x80) | (hasPayload ? 0x40)
  byte1..2 = token (uint16 LE)
  byte3    = CRC8 (poly 0x8C) over the header with byte3=0 (incl. result+length)
  byte4..5 = srcAddr (uint16 LE)
  byte6..7 = destAddr (uint16 LE)
  [result : 1 byte]    when hasResult
  [length : uint16 LE] when hasPayload (length of the payload)
  [payload ...]

Payload (property list):
  count (uint16 LE), then count * Property
  Property = type(1) id(2 BE) marker(1) value(type-dependent)
    type 9=float(4 LE), 7=bool(1), 1..6=int (various widths), 8=uuid(16),
    10=datetime(4), 12=bin(len2LE+bytes), 14=string(len2LE+utf8)
"""
from __future__ import annotations

import struct

CRC_POLY = 0x8C


def crc8(data: bytes) -> int:
    """Dallas/Maxim CRC-8 (polynomial 0x8C, reflected)."""
    crc = 0
    for b in data:
        for _ in range(8):
            mix = (crc ^ b) & 1
            crc >>= 1
            if mix:
                crc ^= CRC_POLY
            b >>= 1
    return crc


# Property type sizes (from the converter classes); variable: 12=bin, 14=string.
# code: 1=int32, 2=int16, 3=int8, 4=uint32, 5=uint16, 6=uint8,
#       7=bool, 8=uuid, 9=float, 10=datetime(4)
FIXED_LEN = {1: 4, 2: 2, 3: 1, 4: 4, 5: 2, 6: 1, 7: 1, 8: 16, 9: 4, 10: 4}


def parse_payload(buf: bytes) -> list[tuple[int, int, int, bytes]]:
    """Parse payload bytes into a list of (type, id, marker, value_bytes)."""
    if len(buf) < 2:
        return []
    count = struct.unpack_from("<H", buf, 0)[0]
    off = 2
    props = []
    for _ in range(count):
        if off + 4 > len(buf):
            break
        ptype = buf[off]
        pid = struct.unpack_from(">H", buf, off + 1)[0]
        marker = buf[off + 3]
        off += 4
        if ptype in (12, 14):  # bin / string: 2-byte LE length prefix
            ln = struct.unpack_from("<H", buf, off)[0]
            off += 2
            val = buf[off:off + ln]
            off += ln
        else:
            ln = FIXED_LEN.get(ptype, 0)
            val = buf[off:off + ln]
            off += ln
        props.append((ptype, pid, marker, val))
    return props


def fmt_val(ptype: int, val: bytes) -> str:
    """Human-readable rendering of a property value (for debugging)."""
    if ptype == 9 and len(val) == 4:
        return f"float={struct.unpack('<f', val)[0]:.3f}"
    if ptype == 7 and len(val) == 1:
        return f"bool={bool(val[0])}"
    if ptype in (1, 2, 3, 4, 5, 6):
        return f"int={int.from_bytes(val, 'little')}"
    if ptype == 14:
        return f'str="{val.decode("utf-8", "replace")}"'
    if ptype == 8:
        return "uuid=" + val.hex()
    return "raw=" + val.hex()


def decode_message(buf: bytes, off: int = 0):
    """Read one message starting at off -> (dict, next_off) or (None, off)."""
    if off + 8 > len(buf):
        return None, off
    b0 = buf[off]
    has_result = bool(b0 & 0x80)
    has_payload = bool(b0 & 0x40)
    code = b0 & 0x3F
    token = struct.unpack_from("<H", buf, off + 1)[0]
    csum = buf[off + 3]
    src = struct.unpack_from("<H", buf, off + 4)[0]
    dst = struct.unpack_from("<H", buf, off + 6)[0]
    p = off + 8
    result = None
    if has_result:
        if p >= len(buf):
            return None, off
        result = buf[p]
        p += 1
    plen = 0
    if has_payload:
        if p + 2 > len(buf):
            return None, off
        plen = struct.unpack_from("<H", buf, p)[0]
        p += 2
    if p + plen > len(buf):
        return None, off
    payload = buf[p:p + plen]
    p += plen
    return ({"code": code, "result": result, "has_payload": has_payload,
             "token": token, "csum": csum, "src": src, "dst": dst,
             "payload": payload, "raw": buf[off:p]}, p)


def encode_message(code, token, src, dst, result=None, payload=None) -> bytes:
    """Build a Flake message frame."""
    has_result = result is not None
    has_payload = payload is not None and len(payload) > 0
    b0 = (code & 0x3F) | (0x80 if has_result else 0) | (0x40 if has_payload else 0)
    hdr = bytearray([b0, token & 0xFF, (token >> 8) & 0xFF, 0,
                     src & 0xFF, (src >> 8) & 0xFF, dst & 0xFF, (dst >> 8) & 0xFF])
    if has_result:
        hdr.append(result & 0xFF)
    if has_payload:
        hdr += struct.pack("<H", len(payload))
    hdr[3] = crc8(hdr)  # CRC over the header (byte3=0), incl. result/length
    out = bytes(hdr)
    if has_payload:
        out += payload
    return out


def make_property(ptype, pid, marker, value) -> bytes:
    out = bytes([ptype]) + struct.pack(">H", pid) + bytes([marker])
    if ptype in (12, 14):
        out += struct.pack("<H", len(value)) + value
    else:
        out += value
    return out


def make_payload(props) -> bytes:
    out = struct.pack("<H", len(props))
    for (ptype, pid, marker, value) in props:
        out += make_property(ptype, pid, marker, value)
    return out

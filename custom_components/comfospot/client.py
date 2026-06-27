"""Blocking Flake client and high-level ComfoSpot API.

The low-level :class:`FlakeClient` reimplements the reliable connection/transport
layer (dynamic tokens + ACKs), so a fresh connection works without replaying any
captured bytes. The high-level :class:`ComfoSpot` wraps connection management,
zone discovery, state reads and write commands behind a single lock so it can be
driven from Home Assistant via ``async_add_executor_job``.
"""
from __future__ import annotations

import logging
import socket
import struct
import threading
import time

from .const import (
    CONTROL_PORT,
    DISCOVERY_PORT,
    MAX_STAGE,
    MIN_STAGE,
    PID_HUMIDITY,
    PID_MODE,
    PID_NAME,
    PID_OBJ_ADDR,
    PID_SPEED,
    PID_RUN_HOURS,
    PID_SYS_CO2,
    PID_SYS_DEVICES,
    PID_SYS_FIRMWARE,
    PID_TARGET_TEMP,
    PID_TEMPERATURE,
    ZONE_UUID_BASE,
    ZONE_UUID_LAST_RANGE,
)
from .flake import decode_message, encode_message, make_payload, parse_payload

_LOGGER = logging.getLogger(__name__)


class ComfoSpotError(Exception):
    """Raised when the ComfoSpot cannot be reached or returns an error."""


def discover(timeout: float = 2.0) -> tuple[str, int] | None:
    """Discover the gateway (ip, port) via a UDP broadcast, or return None."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.settimeout(timeout)
    try:
        s.sendto(b"", ("255.255.255.255", DISCOVERY_PORT))
        data, addr = s.recvfrom(255)
        port = int("".join(str(b) for b in data)) if data else CONTROL_PORT
        return addr[0], port
    except OSError:
        return None
    finally:
        s.close()


class FlakeClient:
    """Low-level Flake connection: hello, query, subscribe, read and write."""

    def __init__(self, ip: str, port: int = CONTROL_PORT) -> None:
        self.ip = ip
        self.port = port
        self.sock: socket.socket | None = None
        self.token = 0
        self.my_addr = 0xFFFF
        self.rx = bytearray()
        self.running = False
        self.reader: threading.Thread | None = None
        self.replies: dict[int, dict] = {}
        self.reply_events: dict[int, threading.Event] = {}
        self.state: dict[tuple[int, int], tuple[int, bytes]] = {}
        self.last_assigned_addr: int | None = None
        self.lock = threading.Lock()

    # -- token counter (matches Connection: 1..MAX wraps to MIN) --
    def next_token(self) -> int:
        with self.lock:
            t = self.token
            if t == -1:
                t = 1
            elif t == 0x7FFF:
                t = -0x8000
            else:
                t = t + 1
            self.token = t
            return t & 0xFFFF

    def connect(self) -> None:
        self.sock = socket.create_connection((self.ip, self.port), timeout=5)
        self.sock.settimeout(0.5)
        self.running = True
        self.reader = threading.Thread(target=self._read_loop, daemon=True)
        self.reader.start()

    def close(self) -> None:
        self.running = False
        try:
            if self.sock:
                self.sock.close()
        except OSError:
            pass

    def is_alive(self) -> bool:
        return bool(self.running and self.reader and self.reader.is_alive())

    def _send(self, code, dst, payload=None, result=None, token=None, src=None) -> int:
        if token is None:
            token = self.next_token()
        if src is None:
            src = self.my_addr
        msg = encode_message(code, token, src, dst, result=result, payload=payload)
        self.sock.sendall(msg)
        return token

    def _read_loop(self) -> None:
        while self.running:
            try:
                chunk = self.sock.recv(65536)
                if not chunk:
                    break
                self.rx += chunk
                self._drain()
            except socket.timeout:
                continue
            except OSError:
                break

    def _drain(self) -> None:
        off = 0
        while off < len(self.rx):
            msg, nxt = decode_message(self.rx, off)
            if msg is None:
                break
            off = nxt
            self._handle(msg)
        del self.rx[:off]

    def _handle(self, msg) -> None:
        has_result = msg["raw"][0] & 0x80
        if msg["has_payload"]:
            for (oaddr, pt, pid, val) in self._walk(msg["payload"], msg["src"]):
                self.state[(oaddr, pid)] = (pt, val)
                if pid == PID_OBJ_ADDR and pt in (1, 2, 3, 4, 5, 6):
                    self.last_assigned_addr = int.from_bytes(val, "little")
        if has_result:
            self.replies[msg["token"]] = msg
            ev = self.reply_events.get(msg["token"])
            if ev:
                ev.set()
        else:
            # GW request/notify -> ACK (same token, swap src/dst, result=0)
            try:
                self._send(msg["code"], msg["src"], payload=None, result=0,
                           token=msg["token"], src=msg["dst"])
            except OSError:
                pass

    def _walk(self, payload, oaddr, depth=0):
        """Yield (objAddr, ptype, pid, value), recursing into nested bin objects.

        Only property id 0x000d (a bin) wraps a nested object: <u16 subAddr><payload>.
        """
        if depth > 6:
            return
        for (pt, pid, _mk, val) in parse_payload(payload):
            if pt == 12 and pid == 0x000D and len(val) >= 2:
                sub = int.from_bytes(val[:2], "little")
                yield from self._walk(val[2:], sub if sub else oaddr, depth + 1)
            else:
                yield (oaddr, pt, pid, val)

    def request(self, code, dst, payload=None, wait=2.0):
        token = self.next_token()
        ev = threading.Event()
        self.reply_events[token] = ev
        self._send(code, dst, payload=payload, token=token)
        ev.wait(wait)
        return self.replies.get(token)

    # -- high level --
    def hello(self) -> int:
        self.my_addr = 0xFFFF
        reply = self.request(1, 0x0000, payload=None)
        if reply and reply["has_payload"]:
            for (_pt, pid, _mk, val) in parse_payload(reply["payload"]):
                if pid == PID_OBJ_ADDR:
                    self.my_addr = int.from_bytes(val, "little")
        return self.my_addr

    def query_uuid(self, uuid_bytes: bytes):
        self.last_assigned_addr = None
        payload = make_payload([(8, 0x1001, 0x00, uuid_bytes)])
        self.request(4, 0x0000, payload=payload)
        return self.last_assigned_addr

    def subscribe(self, obj_addr: int):
        return self.request(8, obj_addr, payload=None)

    def set_properties(self, obj_addr, props):
        payload = make_payload([(pt, pid, 0x20, val) for (pt, pid, val) in props])
        return self.request(7, obj_addr, payload=payload)

    def set_property(self, obj_addr, ptype, pid, value_bytes):
        return self.set_properties(obj_addr, [(ptype, pid, value_bytes)])


def _f32(state, key):
    v = state.get(key)
    if v and len(v[1]) == 4:
        return struct.unpack("<f", v[1])[0]
    return None


def _u8(state, key):
    v = state.get(key)
    if v and v[1]:
        return v[1][0]
    return None


def _u32(state, key):
    v = state.get(key)
    if v and len(v[1]) >= 4:
        return struct.unpack("<I", v[1][:4])[0]
    return None


def _str_val(state, key):
    v = state.get(key)
    if v and v[1]:
        try:
            return v[1].decode("utf-8").strip("\x00").strip() or None
        except UnicodeDecodeError:
            return None
    return None


class ComfoSpot:
    """High-level, thread-safe ComfoSpot system facade."""

    def __init__(self, host: str, port: int = CONTROL_PORT) -> None:
        self.host = host
        self.port = port
        self._client: FlakeClient | None = None
        self._lock = threading.Lock()
        self.zones: dict[int, str] = {}      # addr -> name
        self.sys_addrs: list[int] = []       # non-zone (system) object addresses

    # -- connection management --
    def _zone_name(self, addr: int) -> str:
        v = self._client.state.get((addr, PID_NAME)) if self._client else None
        try:
            if v:
                name = v[1].decode("utf-8").strip("\x00").strip()
                if name:
                    return name
        except (UnicodeDecodeError, AttributeError):
            pass
        return f"Zone {addr}"

    def _connect(self) -> None:
        if self._client:
            try:
                self._client.close()
            except OSError:
                pass
        client = FlakeClient(self.host, self.port)
        client.connect()
        client.hello()
        all_objs: dict[int, bytes] = {}
        for last in ZONE_UUID_LAST_RANGE:
            addr = client.query_uuid(ZONE_UUID_BASE + bytes([last]))
            if addr:
                client.subscribe(addr)
                all_objs[addr] = ZONE_UUID_BASE + bytes([last])
        time.sleep(0.8)  # allow the gateway to push the initial snapshot
        self._client = client
        # Real controllable zones expose BOTH speed and mode.
        self.zones = {
            a: self._zone_name(a)
            for a in all_objs
            if (a, PID_SPEED) in client.state and (a, PID_MODE) in client.state
        }
        # System objects (e.g. CO2 / device count) must be kept subscribed too,
        # otherwise the gateway stops pushing their values and they go stale.
        self.sys_addrs = [a for a in all_objs if a not in self.zones]
        if not self.zones:
            raise ComfoSpotError("No controllable zones found")

    def _ensure(self) -> None:
        if self._client and self._client.is_alive():
            return
        self._connect()

    # -- public API (call from executor) --
    def test_connection(self) -> dict[int, str]:
        """Connect once and return the discovered zones (addr -> name)."""
        with self._lock:
            self._connect()
            return dict(self.zones)

    def update(self) -> dict:
        """Keep the connection alive and return a fresh state snapshot."""
        with self._lock:
            self._ensure()
            client = self._client
            # Keepalive: re-subscribe to zones and system objects.
            for addr in list(self.zones) + self.sys_addrs:
                try:
                    client.subscribe(addr)
                except OSError:
                    pass
            return self._snapshot()

    def _snapshot(self) -> dict:
        client = self._client
        st = client.state
        zones = {}
        for addr, name in self.zones.items():
            zones[addr] = {
                "name": name,
                "speed": _f32(st, (addr, PID_SPEED)),
                "mode": _u8(st, (addr, PID_MODE)),
                "target_temp": _f32(st, (addr, PID_TARGET_TEMP)),
                "humidity": _f32(st, (addr, PID_HUMIDITY)),
                "temperature": _f32(st, (addr, PID_TEMPERATURE)),
                "run_hours": _u32(st, (addr, PID_RUN_HOURS)),
            }
        system: dict = {"co2": None, "devices": None, "firmware": None}
        for addr in self.sys_addrs:
            if system["co2"] is None:
                system["co2"] = _f32(st, (addr, PID_SYS_CO2))
            if system["devices"] is None:
                system["devices"] = _u8(st, (addr, PID_SYS_DEVICES))
            if system["firmware"] is None:
                system["firmware"] = _str_val(st, (addr, PID_SYS_FIRMWARE))
        return {"zones": zones, "system": system}

    def set_stage(self, addr: int, stage: int) -> None:
        """Set the manual fan stage (0=off..MAX_STAGE), preserving direction."""
        stage = max(0, min(MAX_STAGE, int(stage)))
        with self._lock:
            self._ensure()
            client = self._client
            mv = client.state.get((addr, PID_MODE))
            cur_mode = mv[1][0] if mv else 0
            # High nibble holds the direction; clear it to force manual mode.
            manual_mode = cur_mode if (cur_mode & 0xF0) == 0 else 0
            reply = client.set_properties(addr, [
                (6, PID_MODE, bytes([manual_mode])),
                (9, PID_SPEED, struct.pack("<f", float(stage))),
            ])
            if reply is None:
                raise ComfoSpotError("No reply from gateway when setting stage")

    def set_mode(self, addr: int, mode: int) -> None:
        """Set the ventilation mode (0=exhaust, 1=supply, 2=alternating)."""
        with self._lock:
            self._ensure()
            reply = self._client.set_property(addr, 6, PID_MODE, bytes([mode & 0x0F]))
            if reply is None:
                raise ComfoSpotError("No reply from gateway when setting mode")

    def set_target_temp(self, addr: int, temp: float) -> None:
        with self._lock:
            self._ensure()
            reply = self._client.set_property(
                addr, 9, PID_TARGET_TEMP, struct.pack("<f", float(temp))
            )
            if reply is None:
                raise ComfoSpotError("No reply from gateway when setting target temp")

    def close(self) -> None:
        with self._lock:
            if self._client:
                self._client.close()
                self._client = None


# Stage <-> percentage helpers (stage 1..MAX_STAGE map across 0..100 %).
def stage_to_percentage(stage: int) -> int:
    stage = max(0, min(MAX_STAGE, int(stage)))
    if stage <= 0:
        return 0
    return round(stage / MAX_STAGE * 100)


def percentage_to_stage(pct: int) -> int:
    if pct <= 0:
        return 0
    return max(MIN_STAGE, min(MAX_STAGE, round(pct / 100 * MAX_STAGE)))

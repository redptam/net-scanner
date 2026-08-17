import ipaddress
import socket
import subprocess
import platform
import re
import logging

LOG = logging.getLogger(__name__)
PING_TIMEOUT = 1

DEFAULT_PORTS = [22, 80, 443]


def parse_ports(port_str: str) -> list[int]:
    ports = set()
    for part in port_str.split(','):
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            try:
                start, end = part.split('-', 1)
                s = int(start)
                e = int(end)
                if s > e or s < 1 or e > 65535:
                    continue
                ports.update(range(s, e + 1))
            except ValueError:
                continue
        else:
            try:
                p = int(part)
                if 1 <= p <= 65535:
                    ports.add(p)
            except ValueError:
                continue
    return sorted(ports)


def ping_host(host: str) -> tuple[bool, float | None]:
    try:
        cmd = ['ping']
        if platform.system().lower() == 'windows':
            cmd += ['-n', '1', '-w', str(int(PING_TIMEOUT * 1000)), host]
        else:
            cmd += ['-c', '1', '-W', str(int(PING_TIMEOUT)), host]

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            latency = None
            if platform.system().lower() == 'windows':
                m = re.search(r'time[=<](\d+)ms', result.stdout)
                if m:
                    latency = float(m.group(1))
            else:
                m = re.search(r'time=([\d.]+)\s*ms', result.stdout)
                if m:
                    latency = float(m.group(1))
            return True, latency
        else:
            for port in DEFAULT_PORTS:
                try:
                    with socket.create_connection((host, port), timeout=PING_TIMEOUT):
                        return True, None
                except Exception:
                    continue
            return False, None
    except Exception as exc:
        LOG.exception("Ping failed for %s: %s", host, exc)
        return False, None


def scan_ports(host: str, ports: list[int] | None = None) -> list[int]:
    if ports is None:
        ports = DEFAULT_PORTS
    open_ports: list[int] = []
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(PING_TIMEOUT)
        try:
            sock.connect((host, port))
            open_ports.append(port)
        except Exception:
            pass
        finally:
            sock.close()
    return open_ports

__all__ = ["parse_ports", "ping_host", "scan_ports", "DEFAULT_PORTS"]

#!/usr/bin/env python3
"""
Detects the local operating system and scans for open TCP ports on Linux.
Usage example:
  python port_scan.py --host 127.0.0.1 --start 1 --end 1024
"""

import argparse
import platform
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List


def is_linux() -> bool:
    return platform.system().lower() == "linux"


def check_port(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def scan_ports(host: str, start: int, end: int, timeout: float, workers: int) -> List[int]:
    open_ports: List[int] = []

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_port = {
            executor.submit(check_port, host, port, timeout): port
            for port in range(start, end + 1)
        }
        for future in as_completed(future_to_port):
            port = future_to_port[future]
            try:
                if future.result():
                    open_ports.append(port)
            except Exception:
                # Ignore unexpected socket errors so the scan can continue.
                continue

    return sorted(open_ports)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scan for open TCP ports on a host (Linux only).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to scan (default: 127.0.0.1)")
    parser.add_argument("--start", type=int, default=1, help="Starting port (default: 1)")
    parser.add_argument("--end", type=int, default=1024, help="Ending port (default: 1024)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.5,
        help="Socket timeout in seconds (default: 0.5)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=100,
        help="Number of concurrent workers (default: 100)",
    )
    return parser.parse_args()


def main() -> None:
    if not is_linux():
        raise SystemExit("Este script só executa a varredura em sistemas Linux.")

    args = parse_args()

    if args.start < 1 or args.end > 65535 or args.start > args.end:
        raise SystemExit("Intervalo de portas inválido. Use valores entre 1 e 65535.")

    open_ports = scan_ports(args.host, args.start, args.end, args.timeout, args.workers)

    if open_ports:
        print(f"Portas abertas em {args.host}: {', '.join(map(str, open_ports))}")
    else:
        print(f"Nenhuma porta TCP aberta encontrada em {args.host} no intervalo {args.start}-{args.end}.")


if __name__ == "__main__":
    main()

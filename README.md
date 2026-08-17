# Network Scanner

A desktop GUI application that scans local networks for active hosts, displaying ping latency and open ports in real time.

Built with Python and Tkinter.

## Features

- Scan any IP range (e.g. `192.168.1.0/24`)
- See ping response times for each host
- Detect open ports per host
- Filter out unresponsive hosts
- Export results to a file

## Requirements

- Python 3.13+

## Installation

Install the package so the `netscanner` command becomes available system-wide:

```bash
pip install .
```

To reinstall after making changes to the source:

```bash
pip install . --force-reinstall
```

## Uninstalling

```bash
pip uninstall net-scanner
```

## Running

Once installed, launch the app from any terminal:

```bash
netscanner
```

Or run it directly without installing:

```bash
python -m net_scanner_gui.main
```

import sys
import socket
import time
from pathlib import Path
from ipaddress import ip_interface

from scapy.all import ARP, Ether, srp
from manuf import manuf
from colorama import Fore, Style, init

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QLabel, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor


# -------- init console colors --------
init(autoreset=True)

IP_FILE = Path("ip.txt")
MAX_HOSTS_WARNING = 4096   # /20


# ---------------- Helpers ----------------

def log(msg, color=Fore.WHITE):
    print(color + msg + Style.RESET_ALL)


def load_network_from_file():
    line = IP_FILE.read_text().strip()
    # only take the part that looks like X.X.X.X/Y
    import re
    match = re.search(r"\d+\.\d+\.\d+\.\d+/\d+", line)
    if not match:
        raise ValueError("No valid IP/CIDR found in ip.txt")
    ip_cidr = match.group(0)

    iface = ip_interface(ip_cidr)
    network = iface.network
    my_ip = iface.ip
    return str(network), str(my_ip), network.num_addresses



# ---------------- Scanner Thread ----------------

class ScanThread(QThread):
    finished_scan = pyqtSignal(dict)

    def __init__(self, network):
        super().__init__()
        self.network = network
        self.parser = manuf.MacParser()

    def run(self):
        devices = {}

        arp = ARP(pdst=self.network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp

        answers = srp(packet, timeout=1, verbose=False)[0]

        for _, r in answers:
            mac = r.hwsrc.lower()
            vendor = self.parser.get_manuf(mac) or "Unknown"

            devices[r.psrc] = {
                "ip": r.psrc,
                "mac": mac,
                "vendor": vendor
            }

        self.finished_scan.emit(devices)


# ---------------- GUI ----------------

class Scanner(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LAN Scanner (IP File + Auto Reload)")
        self.resize(760, 440)

        self.devices = {}
        self.scanning = False
        self.last_ip_mtime = None

        self.network, self.my_ip, self.hosts = self.safe_load_ip()

        layout = QVBoxLayout()
        self.status_label = QLabel()
        layout.addWidget(self.status_label)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["IP Address", "MAC Address", "Vendor"]
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        self.setLayout(layout)

        self.update_status()

        # Adaptive scan interval
        self.timer = QTimer()
        self.timer.timeout.connect(self.start_scan)
        self.timer.start(self.get_scan_interval())

        # Watch ip.txt for changes
        self.watch_timer = QTimer()
        self.watch_timer.timeout.connect(self.check_ip_file)
        self.watch_timer.start(1000)

        self.start_scan()

    # -------- IP handling --------

    def safe_load_ip(self):
        try:
            network, my_ip, hosts = load_network_from_file()
            log(f"[INIT] Loaded {network} from ip.txt", Fore.CYAN)

            if hosts > MAX_HOSTS_WARNING:
                log(
                    f"[WARN] Large subnet ({hosts} hosts) – scanning slowed",
                    Fore.RED
                )

            self.last_ip_mtime = IP_FILE.stat().st_mtime
            return network, my_ip, hosts

        except Exception as e:
            log(f"[ERROR] {e}", Fore.RED)
            sys.exit(1)

    def check_ip_file(self):
        try:
            mtime = IP_FILE.stat().st_mtime
            if mtime != self.last_ip_mtime:
                log("[INFO] ip.txt changed → reloading", Fore.MAGENTA)
                self.network, self.my_ip, self.hosts = self.safe_load_ip()
                self.update_status()
        except Exception:
            pass

    def get_scan_interval(self):
        if self.hosts <= 256:
            return 1000
        elif self.hosts <= 1024:
            return 2000
        else:
            return 4000

    def update_status(self):
        self.status_label.setText(
            f"Network: {self.network} | Your IP: {self.my_ip} | Auto scan"
        )

    # -------- Scanning --------

    def start_scan(self):
        if self.scanning:
            return

        self.scanning = True
        self.thread = ScanThread(self.network)
        self.thread.finished_scan.connect(self.update)
        self.thread.finished.connect(lambda: setattr(self, "scanning", False))
        self.thread.start()

    def update(self, new_devices):
        # ---- Console logs ----
        for ip, d in new_devices.items():
            if ip == self.my_ip:
                log(f"[ME] {ip} {d['mac']}", Fore.BLUE)
            elif ip not in self.devices:
                log(f"[NEW] {ip} {d['mac']} ({d['vendor']})", Fore.YELLOW)
            else:
                log(f"[ON] {ip} {d['mac']}", Fore.GREEN)

        for ip in self.devices:
            if ip not in new_devices:
                log(f"[OFF] {ip}", Fore.RED)

        # ---- GUI table ----
        self.table.setRowCount(0)

        for ip, d in new_devices.items():
            row = self.table.rowCount()
            self.table.insertRow(row)

            ip_item = QTableWidgetItem(d["ip"])
            mac_item = QTableWidgetItem(d["mac"])
            vendor_item = QTableWidgetItem(d["vendor"])

            if ip == self.my_ip:
                color = QColor("#b6fcb6")   # this machine
            elif ip not in self.devices:
                color = QColor("#fff3b0")   # new device
            else:
                color = None

            if color:
                ip_item.setBackground(color)
                mac_item.setBackground(color)
                vendor_item.setBackground(color)

            self.table.setItem(row, 0, ip_item)
            self.table.setItem(row, 1, mac_item)
            self.table.setItem(row, 2, vendor_item)

        self.devices = new_devices


# ---------------- Main ----------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = Scanner()
    win.show()
    sys.exit(app.exec())

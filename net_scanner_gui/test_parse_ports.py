import tkinter as tk
from net_scanner_gui.main import NetworkScannerApp

root = tk.Tk()
root.withdraw()
app = NetworkScannerApp(root)
print(app.parse_ports("80,443,3000-3002"))

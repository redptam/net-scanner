import tkinter as tk
from net_scanner_gui.main import NetworkScannerApp

root = tk.Tk()
root.withdraw()
app = NetworkScannerApp(root)

# Set scanning flag to True and disable buttons to simulate running scan
app.scanning = True
app.start_button.config(state=tk.DISABLED)
app.stop_button.config(state=tk.NORMAL)

# Call stop_scan
app.stop_scan()

# Assertions
assert app.scanning == False, "Scanning flag should be False after stop_scan"
assert app.start_button.cget('state') == tk.NORMAL, "Start button should be enabled after stop_scan"
assert app.stop_button.cget('state') == tk.DISABLED, "Stop button should be disabled after stop_scan"
print("Stop scan test passed.")

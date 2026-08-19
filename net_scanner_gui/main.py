import socket
import subprocess
import threading
import ipaddress
import json
import os
import sys
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from concurrent.futures import ThreadPoolExecutor
import tkinter.font as tkfont

# Configuration
PING_TIMEOUT = 1  # seconds
CONFIG_FILE = "scanner_config.json"
MAX_WORKERS = 20
APP_VERSION = "1.0"
APP_NAME = "Network Scanner"


class NetworkScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("850x600")
        self.font_loaded = False

        # Styling
        self.style = ttk.Style()
        self.style.configure("TFrame", background="#f5f5f5")
        self.style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Status.TLabel", font=("Segoe UI", 9))

        # Load Inter fonts (falls back to Ubuntu if unavailable)
        self._load_fonts()

        # Build menu bar first (before other widgets)
        self.filter_unresponsive = tk.BooleanVar(value=False)

        # Build menu bar first (before other widgets)
        self._build_menu_bar()

        # Main Container
        self.main_container = ttk.Frame(root, padding="15")
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # --- Configuration Frame ---
        config_frame = ttk.LabelFrame(
            self.main_container,
            text=" Scan Configuration ",
            padding="10",
        )
        config_frame.pack(fill=tk.X, pady=(0, 15))

        # Network input
        ttk.Label(config_frame, text="Network (CIDR):").grid(
            row=0, column=0, sticky=tk.W, padx=5, pady=5
        )
        self.network_entry = ttk.Entry(config_frame, width=25)
        self.network_entry.grid(row=0, column=1, padx=5, pady=5)

        # Port input
        ttk.Label(config_frame, text="Ports:").grid(
            row=0, column=2, sticky=tk.W, padx=(15, 5), pady=5
        )
        self.port_entry = ttk.Entry(config_frame, width=25)
        self.port_entry.grid(row=0, column=3, padx=5, pady=5)

        # Load configuration
        config = self.load_config()
        self.network_entry.insert(0, config.get("network", "10.0.0.0/24"))
        self.port_entry.insert(0, config.get("ports", "22,80,443"))

        # --- Controls Frame ---
        controls_frame = ttk.Frame(self.main_container)
        controls_frame.pack(fill=tk.X, pady=(0, 15))

        self.start_button = ttk.Button(
            controls_frame, text="▶ Start Scan", command=self.start_scan
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            controls_frame,
            text="■ Stop Scan",
            command=self.stop_scan,
            state=tk.DISABLED,
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # --- Progress Frame ---
        progress_frame = ttk.Frame(self.main_container)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=(0, 10))

        self.progress_label = ttk.Label(
            progress_frame,
            text="0%",
            font=self._get_font_family("status"),
        )
        self.progress_label.pack(side=tk.RIGHT)

        # --- Results Frame (Table View) ---
        results_frame = ttk.LabelFrame(
            self.main_container,
            text=" Scan Results ",
            padding="5",
        )
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Treeview for table
        columns = ("IP", "Hostname", "Ping", "Ports")
        self.tree = ttk.Treeview(
            results_frame, columns=columns, show="headings", selectmode="browse"
        )

        self.tree.heading("IP", text="IP Address")
        self.tree.heading("Hostname", text="Hostname")
        self.tree.heading("Ping", text="Ping (ms)")
        self.tree.heading("Ports", text="Open Ports")

        self.tree.column("IP", width=75, anchor=tk.W)
        self.tree.column("Hostname", width=180, anchor=tk.W)
        self.tree.column("Ping", width=50, anchor=tk.CENTER)
        self.tree.column("Ports", width=150, anchor=tk.W)

        # Add a scrollbar for the treeview
        scrollbar = ttk.Scrollbar(
            results_frame, orient=tk.VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscroll=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure row tags for coloring
        self.tree.tag_configure("alive", foreground="green")
        self.tree.tag_configure("dead", foreground="red")
        self.tree.tag_configure("error", foreground="blue")

        # Tune treeview row height for 10pt Inter-Regular readability
        self._update_rowheight()

        # --- Status Bar ---
        self.status_bar = ttk.Label(
            root, text="Ready", relief=tk.SUNKEN, anchor=tk.W, style="Status.TLabel"
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Internal State
        self.ports = [22, 80, 443]
        self.scanning = False
        self.ip_to_item = {}
        self.total_hosts = 0
        self.processed_hosts = 0
        self._detached_items: dict[str, int] = {}  # item ID → original index, hidden by filter

        # Scan results data for saving
        self.scan_results = []  # list of dicts: {"ip": str, "hostname": str, "ping": str, "ports": str, "alive": bool}

    # ------------------------------------------------------------------ #
    #  Menu Bar                                                           #
    # ------------------------------------------------------------------ #
    def _build_menu_bar(self):
        """Build the menu bar across the top of the window."""
        menubar = tk.Menu(self.root, tearoff=False)
        self.root.config(menu=menubar)

        # --- File Menu ---
        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Save Scan Results...",
            accelerator="Ctrl+S",
            command=self._on_save_results,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", accelerator="Alt+F4", command=self._on_exit)

        # --- Edit Menu ---
        edit_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=self._on_copy)
        edit_menu.add_command(
            label="Find...", accelerator="Ctrl+F", command=self._on_find
        )

        # --- View Menu ---
        view_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_checkbutton(
            label="Filter unresponsive hosts",
            variable=self.filter_unresponsive,
            command=self._on_filter_unresponsive_toggle,
        )

        # --- Help Menu ---
        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About...", command=self._on_about)

        # Bind keyboard shortcuts
        self.root.bind("<Control-s>", lambda e: self._on_save_results())
        self.root.bind("<Control-S>", lambda e: self._on_save_results())
        self.root.bind("<Control-c>", lambda e: self._on_copy())
        self.root.bind("<Control-C>", lambda e: self._on_copy())
        self.root.bind("<Control-f>", lambda e: self._on_find())
        self.root.bind("<Control-F>", lambda e: self._on_find())

    def _on_save_results(self):
        """Save scan results to a .txt file."""
        if not self.scan_results:
            self.update_status("No scan results to save.")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Scan Results",
        )
        if not file_path:
            return
        try:
            with open(file_path, "w") as f:
                f.write("Network Scan Results\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"{'IP Address':<22}{'Hostname':<28}{'Ping (ms)':<14}{'Open Ports':<20}\n")
                f.write("-" * 60 + "\n")
                for entry in self.scan_results:
                    ip = entry.get("ip", "-")
                    hostname = entry.get("hostname", "-")
                    ping = entry.get("ping", "-")
                    ports = entry.get("ports", "-")
                    f.write(f"{ip:<22}{hostname:<28}{ping:<14}{ports:<20}\n")
            self.update_status(f"Results saved to {file_path}")
        except Exception as e:
            self.update_status(f"Error saving results: {e}")

    def _on_copy(self):
        """Copy selected row(s) from the treeview to clipboard."""
        selected = self.tree.selection()
        if not selected:
            return
        lines = []
        for item in selected:
            values = self.tree.item(item, "values")
            lines.append("  ".join(str(v) for v in values))
        if lines:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(lines))
            self.root.update()

    def _on_find(self):
        """Open a simple find dialog to search for an IP in the table."""
        find_win = tk.Toplevel(self.root)
        find_win.title("Find")
        find_win.geometry("320x80")
        find_win.transient(self.root)
        find_win.grab_set()

        ttk.Label(find_win, text="Find:").pack(side=tk.LEFT, padx=(10, 5), pady=10)
        find_entry = ttk.Entry(find_win, width=25)
        find_entry.pack(side=tk.LEFT, padx=5, pady=10)
        find_entry.focus_set()

        def do_find():
            query = find_entry.get().strip().lower()
            if not query:
                return
            for item in self.tree.get_children():
                values = self.tree.item(item, "values")
                if query in str(values).lower():
                    self.tree.see(item)
                    self.tree.selection_set(item)
                    self.tree.focus(item)
                    return

        ttk.Button(find_win, text="Find", command=do_find).pack(
            side=tk.LEFT, padx=5, pady=10
        )

    def _on_filter_unresponsive_toggle(self):
        """Toggle showing/hiding dead hosts in the treeview."""
        if self.filter_unresponsive.get():
            # Record original index of each dead item before detaching any
            for index, item in enumerate(self.tree.get_children()):
                tag = self.tree.item(item, "tags")
                if "dead" in tag:
                    self._detached_items[item] = index
            for item in self._detached_items:
                self.tree.detach(item)
        else:
            # Reattach each item at its original position, sorted ascending so
            # earlier insertions don't shift the target index of later ones
            for item_id, orig_index in sorted(
                self._detached_items.items(), key=lambda x: x[1]
            ):
                self.tree.reattach(item_id, "", orig_index)
            self._detached_items.clear()

    def _on_about(self):
        """Show the About dialog."""
        about_text = (
            f"{APP_NAME}\n"
            f"Version {APP_VERSION}\n"
            "\n"
            "A GUI application that scans local networks for active hosts\n"
            "and displays ping latency and open ports.\n"
            "\n"
            "Built with Python and Tkinter.\n"
        )
        messagebox.showinfo("About", about_text)

    def _on_exit(self):
        self.root.destroy()

    # ------------------------------------------------------------------ #
    #  Font loading                                                         #
    # ------------------------------------------------------------------ #
    def _load_fonts(self):
        """Load bundled Inter TTF fonts and register them with tkinter.

        Loads Inter-Regular, Inter-Medium, and Inter-SemiBold from the fonts/
        directory co-located with this script. Falls back gracefully if fonts
        are missing or loading fails.
        """
        start_time = time.time()
        font_dir = None
        try:
            # Resolve fonts directory relative to the script location
            if getattr(sys, "frozen", False):
                # Running as compiled app (e.g., PyInstaller)
                font_dir = os.path.join(sys._MEIPASS, "fonts")
            else:
                font_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)), "fonts"
                )

            font_files = [
                ("Inter-Regular", "Inter-Regular.ttf", "Inter-Regular"),
                ("Inter-Medium", "Inter-Medium.ttf", "Inter-Medium"),
                ("Inter-SemiBold", "Inter-SemiBold.ttf", "Inter-SemiBold"),
            ]

            font_loaded = False
            fonts_loaded_count = 0
            for weight_name, filename, family_name in font_files:
                font_path = os.path.join(font_dir, filename) if font_dir else None
                if font_path and os.path.exists(font_path):
                    try:
                        self.root.tk.call(
                            "font", "create", family_name, "-file", font_path
                        )
                        print(f"Loaded font: {filename} ({family_name})")
                        font_loaded = True
                        fonts_loaded_count += 1
                    except tk.TclError as e:
                        print(f"Warning: Failed to load {filename}: {e}")
                else:
                    if font_dir:
                        print(f"Warning: Font file not found: {font_path}")
                    else:
                        print(f"Warning: Fonts directory not found: {font_dir}")

            elapsed_ms = (time.time() - start_time) * 1000
            print(
                f"Font loading completed in {elapsed_ms:.1f}ms ({fonts_loaded_count}/3 weights loaded)"
            )
            if elapsed_ms > 100:
                print(
                    f"Warning: Font loading exceeded 100ms target ({elapsed_ms:.1f}ms)"
                )

            if font_loaded:
                self.font_loaded = True
                self._apply_font_hierarchy()
            else:
                print("Warning: No Inter fonts loaded. Using fallback.")
                self._apply_fallback()

        except Exception as e:
            print(f"Warning: Font loading failed: {e}. Using fallback.")
            self._apply_fallback()

    def _apply_font_hierarchy(self):
        """Apply the Inter font visual hierarchy across all widget styles.

        Visual hierarchy:
          - Headings: Inter-SemiBold 12pt
          - Body text: Inter-Regular 10pt
          - Status text: Inter-Medium 9pt
        """
        # Update existing styles
        self.style.configure("Header.TLabel", font=("Inter-SemiBold", 12))
        self.style.configure("Body.TLabel", font=("Inter-Regular", 10))
        self.style.configure("Status.TLabel", font=("Inter-Medium", 9))

        # Update TButton
        self.style.configure("TButton", font=("Inter-Regular", 10))

        # Update Treeview rows and headers
        self.style.configure("Treeview", font=("Inter-Regular", 10))
        self.style.configure("Treeview.Heading", font=("Inter-SemiBold", 10))

        # Set default font for all labels not assigned a specific style
        # This is applied as a theme-wide default
        self.style.configure(".", font=("Inter-Regular", 10))

        # Frame caption labels (LabelFrame titles) use SemiBold for heading
        self.style.configure("TLabelframe.Label", font=("Inter-SemiBold", 12))

        # Update menu bar to use Inter (for Linux X11/Wayland)
        self.root.option_clear()
        self.root.option_add("*Font", "Inter-Regular 10")
        self.root.option_add("*Menu.Font", "Inter-Regular 10")

        # Store font family names for programmatic access
        self.font_family_heading = "Inter-SemiBold"
        self.font_family_body = "Inter-Regular"
        self.font_family_status = "Inter-Medium"

    def _get_font_family(self, category="body"):
        """Get the font family name for a given category.

        Args:
            category: One of 'heading', 'body', or 'status'

        Returns:
            Font family name string (e.g., 'Inter-SemiBold', 'Inter-Regular')
        """
        families = {
            "heading": getattr(self, "font_family_heading", "Inter-SemiBold"),
            "body": getattr(self, "font_family_body", "Inter-Regular"),
            "status": getattr(self, "font_family_status", "Inter-Medium"),
        }
        return families.get(category, "Inter-Regular")

    def _update_rowheight(self):
        """Update treeview row height for current font size."""
        try:
            font = tkfont.Font(font=self.tree.cget("font"))
            desired_rowheight = int(font.metrics("linespace") * 1.5)
            self.tree.configure(rowheight=max(desired_rowheight, 18))
        except Exception:
            pass

    def _apply_fallback(self):
        """Apply fallback fonts when Inter is unavailable.

        Fallback chain: Ubuntu (system) → DejaVu Sans (tk default).
        """
        self.style.configure("Header.TLabel", font=("Ubuntu", 12, "bold"))
        self.style.configure("Body.TLabel", font=("Ubuntu", 10))
        self.style.configure("Status.TLabel", font=("Ubuntu", 9))
        self.style.configure("TButton", font=("Ubuntu", 10))
        self.style.configure("Treeview", font=("Ubuntu", 10))
        self.style.configure("Treeview.Heading", font=("Ubuntu", 10))
        self.style.configure(".", font=("Ubuntu", 10))
        self.root.option_clear()
        self.root.option_add("*Font", "Ubuntu 10")
        self.root.option_add("*Menu.Font", "Ubuntu 10")
        # Frame caption labels (LabelFrame titles) use bold for heading
        self.style.configure("TLabelframe.Label", font=("Ubuntu", 12, "bold"))
        print(
            "Fallback to Ubuntu font applied. Install Inter fonts for the intended look."
        )
        # Store fallback font family names
        self.font_family_heading = "Ubuntu"
        self.font_family_body = "Ubuntu"
        self.font_family_status = "Ubuntu"

    # ------------------------------------------------------------------ #
    #  Config / UI helpers                                                #
    # ------------------------------------------------------------------ #
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_config(self, network, ports):
        try:
            config = {"network": network, "ports": ports}
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving config: {e}")

    def update_status(self, text):
        self.root.after(0, lambda: self.status_bar.config(text=text))

    def update_progress(self, value, text=None):
        self.root.after(0, lambda: self._update_progress_widget(value, text))

    def _update_progress_widget(self, value, text):
        self.progress_var.set(value)
        self.progress_label.config(text=f"{int(value)}%")
        if text:
            self.status_bar.config(text=text)

    # ------------------------------------------------------------------ #
    #  Scan logic                                                         #
    # ------------------------------------------------------------------ #
    def start_scan(self):
        network_str = self.network_entry.get().strip()
        port_input = self.port_entry.get().strip()

        self.save_config(network_str, port_input)

        if not network_str:
            self.update_status("Error: No network specified.")
            return

        try:
            network = ipaddress.ip_network(network_str, strict=False)
            hosts = list(network.hosts())
            self.total_hosts = len(hosts)
            if self.total_hosts == 0:
                raise ValueError("No hosts found in this network range.")
        except Exception as e:
            self.update_status(f"Invalid network: {e}")
            return

        # Reset UI
        self.scanning = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.tree.delete(*self.tree.get_children())
        self.ip_to_item = {}
        self._detached_items.clear()
        self.processed_hosts = 0
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        self.scan_results = []  # clear previous results

        # Pre-populate Treeview with all hosts as "dead"
        for ip in hosts:
            ip_str = str(ip)
            item_id = self.tree.insert(
                "", tk.END, values=(f"● {ip_str}", "-", "-", "-"), tags=("dead",)
            )
            self.ip_to_item[ip_str] = item_id

        self.update_status(f"Initializing scan on {network_str}...")
        self.ports = self.parse_ports(port_input) if port_input else [22, 80, 443]

        # Start scanning thread
        thread = threading.Thread(
            target=self.scan_network_manager, args=(hosts,), daemon=True
        )
        thread.start()

    def scan_network_manager(self, hosts):
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for ip in hosts:
                if not self.scanning:
                    break
                executor.submit(self.ping_and_scan_host, str(ip))

        if self.scanning:
            self.update_status("Scan completed.")
        else:
            self.update_status("Scan stopped.")

        # Finalize results for saving
        for item in self.tree.get_children():
            values = self.tree.item(item, "values")
            tag = self.tree.item(item, "tags")
            # Clean up IP (remove bullet)
            clean_ip = (
                values[0].replace("● ", "").replace("○ ", "").strip()
                if values[0]
                else "-"
            )
            clean_hostname = (
                values[1].replace("● ", "").replace("○ ", "").strip()
                if values[1]
                else "-"
            )
            self.scan_results.append(
                {
                    "ip": clean_ip,
                    "hostname": clean_hostname,
                    "ping": values[2],
                    "ports": values[3],
                    "alive": "dead" not in tag,
                }
            )

        self.root.after(0, self.enable_start)

    def ping_and_scan_host(self, ip):
        if not self.scanning:
            return

        is_alive, latency = self.ping_host(ip)

        hostname = "-"
        if is_alive:
            try:
                hostname = socket.getfqdn(ip)
            except Exception:
                hostname = "-"

        if is_alive:
            # Update to Alive (Green)
            latency_str = f"{latency:.1f} ms" if latency is not None else "N/A"
            self.root.after(
                0,
                lambda ip=ip, hn=hostname, ls=latency_str: self._update_tree_row(
                    ip, "alive", "● " + ip, "● " + hn, ls, ""
                ),
            )

            # Scan ports
            open_ports = self.scan_ports(ip)
            ports_str = ", ".join(map(str, open_ports)) if open_ports else "None"

            # Update with ports
            if self.scanning:
                self.root.after(
                    0,
                    lambda ip=ip, hn=hostname, ls=latency_str, ps=ports_str: self._update_tree_row(
                        ip, "alive", "● " + ip, "● " + hn, ls, ps
                    ),
                )
        else:
            # Host is dead (Red)
            self.root.after(
                0, lambda ip=ip: self._update_tree_row(ip, "dead", "● " + ip, "○ -", "N/A", "")
            )

        # Update progress
        self.processed_hosts += 1
        progress_percent = (self.processed_hosts / self.total_hosts) * 100
        self.update_progress(
            progress_percent, f"Scanning: {self.processed_hosts}/{self.total_hosts}"
        )

    def _update_tree_row(self, ip, tag, ip_val, hostname_val, ping_val, ports_val):
        item_id = self.ip_to_item.get(ip)
        if item_id:
            self.tree.item(item_id, values=(ip_val, hostname_val, ping_val, ports_val), tags=(tag,))

    def ping_host(self, host):
        """Returns (is_alive, latency_ms)"""
        import platform
        import re

        try:
            if platform.system().lower() == "windows":
                cmd = ["ping", "-n", "1", "-w", str(int(PING_TIMEOUT * 1000)), host]
            else:
                cmd = ["ping", "-c", "1", "-W", str(int(PING_TIMEOUT)), host]

            result = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if result.returncode == 0:
                latency = None
                if platform.system().lower() == "windows":
                    match = re.search(r"time[=<](\d+)ms", result.stdout)
                    if match:
                        latency = float(match.group(1))
                else:
                    match = re.search(r"time=([\d.]+)\s*ms", result.stdout)
                    if match:
                        latency = float(match.group(1))
                return True, latency
            else:
                # Check if it's just dead or an error
                for port in self.ports:
                    try:
                        with socket.create_connection(
                            (host, port), timeout=PING_TIMEOUT
                        ):
                            return True, None  # Alive via port, but ping failed
                    except Exception:
                        continue
                return False, None
        except Exception:
            return False, None

    def scan_ports(self, host):
        open_ports = []
        for port in self.ports:
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

    def parse_ports(self, port_str):
        ports = set()
        for part in port_str.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                try:
                    start, end = part.split("-", 1)
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

    def enable_start(self):
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        if not self.scanning:
            self.status_bar.config(text="Ready")

    def stop_scan(self):
        self.scanning = False
        self.update_status("Stopping scan...")


def main():
    root = tk.Tk()
    app = NetworkScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

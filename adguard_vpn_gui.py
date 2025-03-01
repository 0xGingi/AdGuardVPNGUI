import os
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import urllib.request
import json
import sys

class AdGuardVPNGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AdGuard VPN")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        self.bg_color = "#FFFFFF"
        self.accent_color = "#67B279"
        self.text_color = "#333333"
        self.root.configure(bg=self.bg_color)
        
        # Initialize early logs storage
        self._early_logs = []
        
        self.find_executable()
        
        self.is_logged_in = False
        
        self.setup_tabs()
        
        # Display early logs once the UI is set up
        self.display_early_logs()
        
        # Add permission check
        if not self.check_permissions():
            self.show_permissions_warning()
        
        self.check_login_status()

    def find_executable(self):
        possible_locations = [
            "/usr/bin/adguardvpn-cli",
            "/usr/local/bin/adguardvpn-cli",
            "/opt/adguardvpn_cli/adguardvpn-cli",
            os.path.expanduser("~/.local/bin/adguardvpn-cli"),
            "/usr/bin/adguardvpn"
        ]
        
        # Get the current script directory when running as binary
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
            self.log(f"Running as binary from: {application_path}")
            possible_locations.append(os.path.join(application_path, "adguardvpn-cli"))
        
        for location in possible_locations:
            if os.path.isfile(location) and os.access(location, os.X_OK):
                self.executable = location
                self.log(f"Found executable at: {location}")
                return
        
        try:
            which_result = subprocess.run(["which", "adguardvpn-cli"], 
                                         capture_output=True, text=True, check=False)
            if which_result.returncode == 0 and which_result.stdout.strip():
                self.executable = which_result.stdout.strip()
                self.log(f"Found executable via 'which': {self.executable}")
                return
        except Exception as e:
            self.log(f"Error running 'which': {e}")
        
        self.executable = "/usr/bin/adguardvpn-cli"  # Default fallback
        self.log(f"Using default fallback path: {self.executable}")
        self.root.after(100, self.show_executable_warning)
    
    def show_executable_warning(self):
        result = messagebox.askquestion(
            "Executable Not Found",
            "AdGuard VPN CLI executable was not found in common locations.\n\n"
            "Would you like to select it manually?",
            icon='warning'
        )
        
        if result == 'yes':
            selected_file = filedialog.askopenfilename(
                title="Select AdGuard VPN CLI Executable",
                filetypes=[("All Files", "*.*")]
            )
            if selected_file:
                if os.access(selected_file, os.X_OK):
                    self.executable = selected_file
                else:
                    messagebox.showerror(
                        "Error",
                        f"The selected file '{selected_file}' is not executable."
                    )

    def check_permissions(self):
        """Check if we have permission to run the VPN commands"""
        self.log(f"Checking permissions for: {self.executable}")
        
        if not os.path.exists(self.executable):
            self.log(f"Warning: Executable does not exist at: {self.executable}")
            return False
        
        if not os.access(self.executable, os.X_OK):
            self.log(f"Warning: No execution permission for: {self.executable}")
            return False
        
        # Try to run a basic command
        try:
            result = subprocess.run(
                [self.executable, "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
                env=os.environ.copy()
            )
            if result.returncode == 0:
                self.log(f"Permission check passed: {result.stdout.strip()}")
                return True
            else:
                self.log(f"Permission check failed: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            self.log("Permission check timed out")
            return False
        except Exception as e:
            self.log(f"Permission check error: {e}")
            return False

    def show_permissions_warning(self):
        """Show a warning about permission issues"""
        messagebox.showwarning(
            "Permission Issue",
            f"The application may not have the necessary permissions to run AdGuard VPN commands. "
            f"This can happen when running as a packaged application.\n\n"
            f"You might need to run the application with elevated privileges or "
            f"ensure the VPN CLI ({self.executable}) has the proper permissions."
        )

    def setup_tabs(self):
        self.tab_control = ttk.Notebook(self.root)
        
        # Main tab
        self.main_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="Main")
        self.setup_main_tab()
        
        # Locations tab
        self.locations_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.locations_tab, text="Locations")
        self.setup_locations_tab()
        
        # Settings tab
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="Settings")
        self.setup_settings_tab()
        
        # Exclusions tab
        self.exclusions_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.exclusions_tab, text="Exclusions")
        self.setup_exclusions_tab()
        
        # About tab
        self.about_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.about_tab, text="About")
        self.setup_about_tab()
        
        self.tab_control.pack(expand=1, fill="both")

    def setup_main_tab(self):
        main_frame = tk.Frame(self.main_tab, bg=self.bg_color)
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Status indicators
        status_frame = tk.Frame(main_frame, bg=self.bg_color)
        status_frame.pack(fill="x", pady=10)
        
        self.status_label = tk.Label(status_frame, text="Status: Checking...", font=("Arial", 12, "bold"), bg=self.bg_color)
        self.status_label.pack(side="left")
        
        # Connection indicator (circle)
        self.status_indicator = tk.Canvas(status_frame, width=30, height=30, bg=self.bg_color, highlightthickness=0)
        self.status_indicator.pack(side="left", padx=10)
        self.status_circle = self.status_indicator.create_oval(5, 5, 25, 25, fill="gray")
        
        # Add a refresh button
        refresh_button = tk.Button(
            status_frame,
            text="Refresh",
            command=self.manual_refresh_status,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=5
        )
        refresh_button.pack(side="right")
        
        # Connect/Disconnect button
        self.connect_button = tk.Button(
            main_frame, 
            text="Connect", 
            command=self.toggle_connection,
            bg=self.accent_color,
            fg="white",
            font=("Arial", 12, "bold"),
            relief="flat",
            padx=20,
            pady=10
        )
        self.connect_button.pack(pady=20)
        
        # Connection details
        self.details_frame = tk.LabelFrame(main_frame, text="Connection Details", bg=self.bg_color)
        self.details_frame.pack(fill="both", expand=True, pady=10)
        
        # IP Address
        ip_frame = tk.Frame(self.details_frame, bg=self.bg_color)
        ip_frame.pack(fill="x", pady=5)
        tk.Label(ip_frame, text="IP Address:", width=15, anchor="w", bg=self.bg_color).pack(side="left")
        self.ip_label = tk.Label(ip_frame, text="Not connected", bg=self.bg_color)
        self.ip_label.pack(side="left", fill="x", expand=True)
        
        # Location
        location_frame = tk.Frame(self.details_frame, bg=self.bg_color)
        location_frame.pack(fill="x", pady=5)
        tk.Label(location_frame, text="Location:", width=15, anchor="w", bg=self.bg_color).pack(side="left")
        self.location_label = tk.Label(location_frame, text="Not connected", bg=self.bg_color)
        self.location_label.pack(side="left", fill="x", expand=True)
        
        # Protocol
        protocol_frame = tk.Frame(self.details_frame, bg=self.bg_color)
        protocol_frame.pack(fill="x", pady=5)
        tk.Label(protocol_frame, text="Protocol:", width=15, anchor="w", bg=self.bg_color).pack(side="left")
        self.protocol_label = tk.Label(protocol_frame, text="Not connected", bg=self.bg_color)
        self.protocol_label.pack(side="left", fill="x", expand=True)
        
        # Log display
        log_frame = tk.LabelFrame(main_frame, text="Log", bg=self.bg_color)
        log_frame.pack(fill="both", expand=True, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.config(state="disabled")

    def setup_locations_tab(self):
        locations_frame = tk.Frame(self.locations_tab, bg=self.bg_color)
        locations_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Search frame
        search_frame = tk.Frame(locations_frame, bg=self.bg_color)
        search_frame.pack(fill="x", pady=10)
        
        tk.Label(search_frame, text="Search:", bg=self.bg_color).pack(side="left")
        self.search_entry = tk.Entry(search_frame, width=30)
        self.search_entry.pack(side="left", padx=5)
        
        search_button = tk.Button(
            search_frame, 
            text="Search", 
            command=self.search_locations,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        search_button.pack(side="left", padx=5)
        
        refresh_button = tk.Button(
            search_frame, 
            text="Refresh List", 
            command=self.fetch_locations,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        refresh_button.pack(side="left", padx=5)
        
        # Locations list as a treeview (table) with columns
        list_frame = tk.Frame(locations_frame, bg=self.bg_color)
        list_frame.pack(fill="both", expand=True, pady=10)
        
        # Scrollbars
        tree_scroll_y = tk.Scrollbar(list_frame)
        tree_scroll_y.pack(side="right", fill="y")
        
        tree_scroll_x = tk.Scrollbar(list_frame, orient="horizontal")
        tree_scroll_x.pack(side="bottom", fill="x")
        
        # Create the treeview
        self.location_tree = ttk.Treeview(
            list_frame, 
            columns=("iso", "country", "city", "ping"),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        
        # Connect scrollbars
        tree_scroll_y.config(command=self.location_tree.yview)
        tree_scroll_x.config(command=self.location_tree.xview)
        
        # Define headings
        self.location_tree.heading("iso", text="ISO", command=lambda: self.sort_locations_by_column("iso", False))
        self.location_tree.heading("country", text="Country", command=lambda: self.sort_locations_by_column("country", False))
        self.location_tree.heading("city", text="City", command=lambda: self.sort_locations_by_column("city", False))
        self.location_tree.heading("ping", text="Ping", command=lambda: self.sort_locations_by_column("ping", False))
        
        # Define columns
        self.location_tree.column("iso", width=50, anchor="w")
        self.location_tree.column("country", width=150, anchor="w")
        self.location_tree.column("city", width=150, anchor="w")
        self.location_tree.column("ping", width=70, anchor="e")
        
        # Pack the treeview
        self.location_tree.pack(side="left", fill="both", expand=True)
        
        # Add buttons
        button_frame = tk.Frame(locations_frame, bg=self.bg_color)
        button_frame.pack(fill="x", pady=10)
        
        connect_button = tk.Button(
            button_frame, 
            text="Connect to Selected", 
            command=self.connect_to_selected,
            bg=self.accent_color,
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=15,
            pady=5
        )
        connect_button.pack(side="left", padx=5)
        
        connect_fastest_button = tk.Button(
            button_frame, 
            text="Connect to Fastest", 
            command=self.connect_to_fastest,
            bg=self.accent_color,
            fg="white",
            font=("Arial", 11),
            relief="flat",
            padx=15,
            pady=5
        )
        connect_fastest_button.pack(side="left", padx=5)
        
        # Initial fetch of locations
        self.fetch_locations()

    def setup_settings_tab(self):
        settings_frame = tk.Frame(self.settings_tab, bg=self.bg_color)
        settings_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # VPN Mode settings
        mode_frame = tk.LabelFrame(settings_frame, text="VPN Mode", bg=self.bg_color)
        mode_frame.pack(fill="x", pady=10)
        
        self.mode_var = tk.StringVar(value="TUN")
        tk.Radiobutton(mode_frame, text="TUN Mode", variable=self.mode_var, value="TUN", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        tk.Radiobutton(mode_frame, text="SOCKS Mode", variable=self.mode_var, value="SOCKS", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        
        # SOCKS settings frame
        socks_frame = tk.LabelFrame(settings_frame, text="SOCKS Settings", bg=self.bg_color)
        socks_frame.pack(fill="x", pady=10)
        
        # SOCKS port
        port_frame = tk.Frame(socks_frame, bg=self.bg_color)
        port_frame.pack(fill="x", pady=5, padx=10)
        tk.Label(port_frame, text="SOCKS Port:", width=15, anchor="w", bg=self.bg_color).pack(side="left")
        self.socks_port_entry = tk.Entry(port_frame, width=10)
        self.socks_port_entry.insert(0, "1080")
        self.socks_port_entry.pack(side="left")
        
        # SOCKS host
        host_frame = tk.Frame(socks_frame, bg=self.bg_color)
        host_frame.pack(fill="x", pady=5, padx=10)
        tk.Label(host_frame, text="SOCKS Host:", width=15, anchor="w", bg=self.bg_color).pack(side="left")
        self.socks_host_entry = tk.Entry(host_frame, width=20)
        self.socks_host_entry.insert(0, "127.0.0.1")
        self.socks_host_entry.pack(side="left")
        
        # DNS settings frame
        dns_frame = tk.LabelFrame(settings_frame, text="DNS Settings", bg=self.bg_color)
        dns_frame.pack(fill="x", pady=10)
        
        # DNS server
        dns_server_frame = tk.Frame(dns_frame, bg=self.bg_color)
        dns_server_frame.pack(fill="x", pady=5, padx=10)
        tk.Label(dns_server_frame, text="DNS Server:", width=15, anchor="w", bg=self.bg_color).pack(side="left")
        self.dns_entry = tk.Entry(dns_server_frame, width=30)
        self.dns_entry.pack(side="left")
        
        # Update channel frame
        update_frame = tk.LabelFrame(settings_frame, text="Update Channel", bg=self.bg_color)
        update_frame.pack(fill="x", pady=10)
        
        self.update_channel_var = tk.StringVar(value="release")
        tk.Radiobutton(update_frame, text="Release", variable=self.update_channel_var, value="release", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        tk.Radiobutton(update_frame, text="Beta", variable=self.update_channel_var, value="beta", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        tk.Radiobutton(update_frame, text="Nightly", variable=self.update_channel_var, value="nightly", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        
        # Apply settings button
        apply_button = tk.Button(
            settings_frame, 
            text="Apply Settings", 
            command=self.apply_settings,
            bg=self.accent_color,
            fg="white",
            font=("Arial", 11),
            relief="flat",
            padx=15,
            pady=8
        )
        apply_button.pack(pady=15)
        
        # Load current settings
        self.load_settings()

    def setup_exclusions_tab(self):
        exclusions_frame = tk.Frame(self.exclusions_tab, bg=self.bg_color)
        exclusions_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # Exclusion mode frame
        mode_frame = tk.LabelFrame(exclusions_frame, text="Exclusion Mode", bg=self.bg_color)
        mode_frame.pack(fill="x", pady=10)
        
        self.exclusion_mode_var = tk.StringVar(value="general")
        tk.Radiobutton(mode_frame, text="General Mode (VPN for All Sites Except Exclusions)", 
                      variable=self.exclusion_mode_var, value="general", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        tk.Radiobutton(mode_frame, text="Selective Mode (VPN Only for Specified Sites)", 
                      variable=self.exclusion_mode_var, value="selective", bg=self.bg_color).pack(anchor="w", padx=10, pady=5)
        
        # Apply mode button
        apply_mode_button = tk.Button(
            mode_frame, 
            text="Apply Mode", 
            command=self.apply_exclusion_mode,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        apply_mode_button.pack(anchor="w", padx=10, pady=5)
        
        # Exclusions management frame
        manage_frame = tk.LabelFrame(exclusions_frame, text="Manage Exclusions", bg=self.bg_color)
        manage_frame.pack(fill="both", expand=True, pady=10)
        
        # Add exclusion
        add_frame = tk.Frame(manage_frame, bg=self.bg_color)
        add_frame.pack(fill="x", pady=5, padx=10)
        
        tk.Label(add_frame, text="Add Site:", bg=self.bg_color).pack(side="left")
        self.add_exclusion_entry = tk.Entry(add_frame, width=30)
        self.add_exclusion_entry.pack(side="left", padx=5)
        
        add_button = tk.Button(
            add_frame, 
            text="Add", 
            command=self.add_exclusion,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        add_button.pack(side="left", padx=5)
        
        # List of exclusions
        list_frame = tk.Frame(manage_frame, bg=self.bg_color)
        list_frame.pack(fill="both", expand=True, pady=5, padx=10)
        
        tk.Label(list_frame, text="Current Exclusions:", bg=self.bg_color).pack(anchor="w")
        
        self.exclusions_listbox = tk.Listbox(list_frame, height=10)
        self.exclusions_listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(list_frame, orient="vertical", command=self.exclusions_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.exclusions_listbox.config(yscrollcommand=scrollbar.set)
        
        # Buttons for exclusions management
        button_frame = tk.Frame(manage_frame, bg=self.bg_color)
        button_frame.pack(fill="x", pady=5, padx=10)
        
        remove_button = tk.Button(
            button_frame, 
            text="Remove Selected", 
            command=self.remove_exclusion,
            bg="#E57373",
            fg="white",
            relief="flat",
            padx=10
        )
        remove_button.pack(side="left", padx=5)
        
        clear_button = tk.Button(
            button_frame, 
            text="Clear All", 
            command=self.clear_exclusions,
            bg="#E57373",
            fg="white",
            relief="flat",
            padx=10
        )
        clear_button.pack(side="left", padx=5)
        
        refresh_button = tk.Button(
            button_frame, 
            text="Refresh List", 
            command=self.refresh_exclusions,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        refresh_button.pack(side="right", padx=5)
        
        # Initial fetch of exclusions
        self.refresh_exclusions()

    def setup_about_tab(self):
        about_frame = tk.Frame(self.about_tab, bg=self.bg_color)
        about_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        # App information
        info_frame = tk.Frame(about_frame, bg=self.bg_color)
        info_frame.pack(pady=20)
        
        tk.Label(info_frame, text="AdGuard VPN GUI", font=("Arial", 16, "bold"), bg=self.bg_color).pack()
        
        # Get CLI version
        version = self.run_command(["--version"]).strip()
        version_text = f"CLI Version: {version}" if version else "CLI Version: Unknown"
        
        tk.Label(info_frame, text=version_text, font=("Arial", 12), bg=self.bg_color).pack(pady=5)
        tk.Label(info_frame, text="GUI Version: 1.1.0", font=("Arial", 12), bg=self.bg_color).pack(pady=5)
        
        # Show CLI path
        tk.Label(info_frame, text=f"CLI Path: {self.executable}", font=("Arial", 10), bg=self.bg_color).pack(pady=5)
        
        # Description
        description = """
        AdGuard VPN CLI GUI is a graphical interface for the AdGuard VPN command-line tool.
        It provides easy access to all the features of AdGuard VPN in a user-friendly interface.
        """
        tk.Label(info_frame, text=description, font=("Arial", 10), bg=self.bg_color, justify="center").pack(pady=10)
        
        # Buttons frame
        buttons_frame = tk.Frame(about_frame, bg=self.bg_color)
        buttons_frame.pack(pady=10)
        
        check_update_button = tk.Button(
            buttons_frame, 
            text="Check for Updates", 
            command=self.check_update,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        check_update_button.pack(side="left", padx=5)
        
        export_logs_button = tk.Button(
            buttons_frame, 
            text="Export Logs", 
            command=self.export_logs,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        export_logs_button.pack(side="left", padx=5)
        
        locate_cli_button = tk.Button(
            buttons_frame,
            text="Change CLI Path",
            command=self.change_cli_path,
            bg=self.accent_color,
            fg="white",
            relief="flat",
            padx=10
        )
        locate_cli_button.pack(side="left", padx=5)
        
        # Add logout button
        logout_button = tk.Button(
            buttons_frame,
            text="Logout",
            command=self.logout_user,
            bg="#FF6B6B",
            fg="white",
            relief="flat",
            padx=10
        )
        logout_button.pack(side="left", padx=5)
        
        # Links
        links_frame = tk.Frame(about_frame, bg=self.bg_color)
        links_frame.pack(pady=20)
        
        tk.Label(links_frame, text="Links:", font=("Arial", 12, "bold"), bg=self.bg_color).pack(anchor="w")
        tk.Label(links_frame, text="Website: adguard-vpn.com", fg="blue", cursor="hand2", bg=self.bg_color).pack(anchor="w")
        tk.Label(links_frame, text="GitHub: github.com/AdguardTeam/AdguardVPNCLI", fg="blue", cursor="hand2", bg=self.bg_color).pack(anchor="w")
        tk.Label(links_frame, text="GitHub: github.com/0xGingi/AdguardVPNGUI", fg="blue", cursor="hand2", bg=self.bg_color).pack(anchor="w")

            
    def change_cli_path(self):
        selected_file = filedialog.askopenfilename(
            title="Select AdGuard VPN CLI Executable",
            filetypes=[("All Files", "*.*")]
        )
        
        if selected_file:
            if os.access(selected_file, os.X_OK):
                self.executable = selected_file
                messagebox.showinfo("Success", f"CLI path updated to: {selected_file}")
                
                # Update the path display in the about tab
                for widget in self.about_tab.winfo_children():
                    for child in widget.winfo_children():
                        if isinstance(child, tk.Label) and "CLI Path:" in child.cget("text"):
                            child.config(text=f"CLI Path: {self.executable}")
                            break
            else:
                messagebox.showerror(
                    "Error",
                    f"The selected file '{selected_file}' is not executable."
                )

    # Command execution methods
    def run_command(self, args, check_error=True):
        """Run an AdGuardVPN CLI command synchronously and return the output"""
        try:
            cmd = [self.executable] + args
            self.log(f"Running command: {' '.join(cmd)}")
            
            # Set environment variables that might be needed
            env = os.environ.copy()
            
            # Run the command with proper environment
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                check=False,
                env=env
            )
            
            if result.stdout:
                self.log(f"Command output: {result.stdout.strip()}")
            
            if check_error and result.returncode != 0:
                error_message = f"Command error ({result.returncode}): {result.stderr.strip()}"
                self.log(error_message)
                
                if "you must log in" in result.stderr.lower() or "you are not logged in" in result.stderr.lower():
                    self.is_logged_in = False
                    if messagebox.askyesno("Login Required", 
                                          "You need to log in to use AdGuard VPN.\nWould you like to log in now?"):
                        self.show_login_dialog()
                
                return error_message
            
            return result.stdout
        except Exception as e:
            error_message = f"Error executing command: {e}"
            self.log(error_message)
            return error_message

    def run_command_async(self, args, callback=None):
        def execute():
            try:
                result = self.run_command(args)
                if callback:
                    self.root.after(0, lambda: callback(result))
            except Exception as e:
                self.log(f"Error executing async command: {e}")
        
        threading.Thread(target=execute, daemon=True).start()

    # Main tab methods
    def update_status(self):
        self.run_command_async(["status"], self.process_status)
        
        # Schedule next update
        self.root.after(5000, self.update_status)

    def process_status(self, result):
        # Strip ANSI escape codes from the result
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_result = ansi_escape.sub('', result)
        
        # Log the cleaned output for debugging
        self.log(f"Status check result: {clean_result}")
        
        # Exact pattern matching for connected state
        connected_match = re.search(r'Connected to (.*?) in (.*?) mode, running on (.*?)($|\s)', clean_result)
        disconnected_match = "VPN is disconnected" in clean_result
        
        if connected_match and not disconnected_match:
            # We are connected
            self.status_label.config(text="Status: Connected")
            self.status_indicator.itemconfig(self.status_circle, fill="green")
            self.connect_button.config(text="Disconnect")
            
            # Extract location, protocol, and interface from the match
            location = connected_match.group(1).strip()
            protocol = connected_match.group(2).strip()
            interface = connected_match.group(3).strip()
            
            # If location is empty, use "Unknown location"
            if not location or location.isspace():
                location = "Unknown location"
            
            self.location_label.config(text=location)
            self.protocol_label.config(text=f"{protocol} ({interface})")
            
            # Get IP information using multiple methods
            self.get_ip_information(interface)
        else:
            # We are disconnected
            self.status_label.config(text="Status: Disconnected")
            self.status_indicator.itemconfig(self.status_circle, fill="red")
            self.connect_button.config(text="Connect")
            
            # Clear connection details
            self.ip_label.config(text="Not connected")
            self.location_label.config(text="Not connected")
            self.protocol_label.config(text="Not connected")
            
            # Log this as well
            if "VPN is disconnected" in clean_result:
                self.log("VPN is disconnected.")
            elif "error" in clean_result.lower():
                self.log(f"Error in VPN status: {clean_result}")
            else:
                self.log("Disconnected. Unknown status returned by CLI.")

    def get_ip_information(self, interface=None):
        """Get IP address information using multiple methods"""
        self.log("Attempting to retrieve IP information...")
        
        # First try to get from system commands
        if self.get_ip_from_system(interface):
            return
        
        # Then try from config
        self.run_command_async(["config", "show"], self.extract_ip_from_config)
        
        # Finally, attempt to use an external API
        self.get_ip_from_external_api()

    def get_ip_from_system(self, interface=None):
        """Try to get IP address from system commands"""
        try:
            if os.name == 'posix':  # Linux, macOS
                cmd = ["ip", "addr", "show"]
                if interface:
                    cmd.append(interface)
                    
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    import re
                    # Look for IPv4 addresses
                    ip_pattern = re.compile(r'inet\s+(\d+\.\d+\.\d+\.\d+)')
                    match = ip_pattern.search(result.stdout)
                    if match:
                        ip = match.group(1)
                        self.ip_label.config(text=ip)
                        self.log(f"Found IP from system: {ip}")
                        return True
                    
        except Exception as e:
            self.log(f"Error getting IP from system: {e}")
        
        return False

    def get_ip_from_external_api(self):
        """Use an external API to get the public IP address"""
        try:
            # Create a separate thread to avoid blocking the UI
            def fetch_ip():
                try:
                    import urllib.request
                    import json
                    
                    # Try multiple services in case one fails
                    api_urls = [
                        "https://api.ipify.org/?format=json",
                        "https://httpbin.org/ip",
                        "https://api.myip.com"
                    ]
                    
                    for url in api_urls:
                        try:
                            with urllib.request.urlopen(url, timeout=3) as response:
                                data = json.loads(response.read().decode())
                                ip = None
                                
                                # Different APIs return IP in different JSON structures
                                if "ip" in data:
                                    ip = data["ip"]
                                elif "origin" in data:
                                    ip = data["origin"]
                                
                                if ip:
                                    # Update UI from the main thread
                                    self.root.after(0, lambda: self.ip_label.config(text=ip))
                                    self.root.after(0, lambda: self.log(f"Found IP from external API: {ip}"))
                                    return
                        except Exception:
                            continue
                    
                    # If we get here, all attempts failed
                    self.root.after(0, lambda: self.log("Failed to get IP from external APIs"))
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"Error in IP lookup thread: {e}"))
            
            threading.Thread(target=fetch_ip, daemon=True).start()
        except Exception as e:
            self.log(f"Error starting IP lookup thread: {e}")

    def extract_ip_from_config(self, result):
        # This is a helper function to extract IP from the config output
        import re
        
        # Try to find IP in the config
        ip_match = re.search(r'(?:IP Address|External IP|VPN IP):\s*(\S+)', result)
        if ip_match:
            self.ip_label.config(text=ip_match.group(1))
        else:
            # If not found in config, try a different approach
            self.run_command_async(["status", "--verbose"], self.extract_ip_from_verbose)

    def extract_ip_from_verbose(self, result):
        # Try to extract IP from verbose status
        import re
        
        # Clean ANSI codes
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        clean_result = ansi_escape.sub('', result)
        
        # Look for IP
        ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
        ip_matches = ip_pattern.findall(clean_result)
        if ip_matches:
            self.ip_label.config(text=ip_matches[0])
        else:
            self.ip_label.config(text="IP not available")

    def extract_additional_info(self, result):
        # Parse config output for additional connection details
        lines = result.split('\n')
        
        for line in lines:
            if "VPN location:" in line:
                location = line.split("VPN location:")[1].strip()
                if location:
                    self.location_label.config(text=location)
            
            elif "VPN protocol:" in line:
                protocol = line.split("VPN protocol:")[1].strip()
                if protocol:
                    self.protocol_label.config(text=protocol)
            
            elif "External IP:" in line or "IP Address:" in line:
                ip_part = line.split(":", 1)
                if len(ip_part) > 1 and ip_part[1].strip():
                    self.ip_label.config(text=ip_part[1].strip())

    def toggle_connection(self):
        if not self.is_logged_in:
            self.log("Not logged in. Please log in first.")
            self.show_login_dialog()
            return
        
        if self.connect_button.cget("text") == "Connect":
            self.log("Connecting to VPN...")
            self.status_label.config(text="Status: Connecting...")
            self.status_indicator.itemconfig(self.status_circle, fill="yellow")
            self.connect_button.config(state="disabled")
            
            try:
                cmd = [self.executable, "connect", "--fastest"]
                self.log(f"Running direct connection command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    env=os.environ.copy()  # Ensure environment variables are passed
                )
                
                if result.returncode != 0:
                    self.log(f"Connection error: {result.stderr}")
                    self.handle_connection_result(f"Error: {result.stderr}")
                else:
                    self.handle_connection_result(result.stdout)
            except Exception as e:
                self.log(f"Exception during connection: {str(e)}")
                self.handle_connection_result(f"Error: {str(e)}")
        else:
            self.log("Disconnecting from VPN...")
            self.status_label.config(text="Status: Disconnecting...")
            self.connect_button.config(state="disabled")
            
            try:
                cmd = [self.executable, "disconnect"]
                self.log(f"Running direct disconnect command: {' '.join(cmd)}")
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    env=os.environ.copy()
                )
                
                if result.returncode != 0:
                    self.log(f"Disconnect error: {result.stderr}")
                    self.handle_disconnection_result(f"Error: {result.stderr}")
                else:
                    self.handle_disconnection_result(result.stdout)
            except Exception as e:
                self.log(f"Exception during disconnection: {str(e)}")
                self.handle_disconnection_result(f"Error: {str(e)}")

    def handle_connection_result(self, result):
        self.log_result(result)
        # Enable the button again
        self.connect_button.config(state="normal")
        
        # Check if the connection was successful
        if "error" in result.lower() or "failed" in result.lower():
            self.status_label.config(text="Status: Connection Failed")
            self.status_indicator.itemconfig(self.status_circle, fill="red")
            self.connect_button.config(text="Connect")
            
            # Show more detailed error message
            error_details = "Failed to connect to VPN."
            if "permission" in result.lower() or "access" in result.lower() or "denied" in result.lower():
                error_details += "\n\nThis may be a permissions issue. Try running the application with sudo or from the terminal."
            elif "process" in result.lower():
                error_details += "\n\nFailed to start the VPN process. The VPN service may not be installed or may require elevated privileges."
            
            messagebox.showerror("Connection Failed", error_details)
        else:
            # After connecting, check status to update UI with a small delay
            self.root.after(2000, lambda: self.run_command_async(["status"], self.process_status))

    def handle_disconnection_result(self, result):
        self.log_result(result)
        # Enable the button again
        self.connect_button.config(state="normal")
        
        # After disconnecting, update the UI
        self.status_label.config(text="Status: Disconnected")
        self.status_indicator.itemconfig(self.status_circle, fill="red")
        self.connect_button.config(text="Connect")
        
        # Clear connection details
        self.ip_label.config(text="Not connected")
        self.location_label.config(text="Not connected")
        self.protocol_label.config(text="Not connected")

    def log(self, message):
        # Store early logs for later display
        if not hasattr(self, '_early_logs'):
            self._early_logs = []
        
        # Print to console for debugging
        print(f"LOG: {message}")
        
        # Make sure we're updating the GUI from the main thread
        if threading.current_thread() is threading.main_thread():
            self._update_log(message)
        else:
            # Schedule the update to happen in the main thread
            self.root.after(0, lambda: self._update_log(message))

    def _update_log(self, message):
        # This runs in the main thread
        if not hasattr(self, 'log_text') or self.log_text is None:
            # Store the message for later if log_text doesn't exist yet
            if not hasattr(self, '_early_logs'):
                self._early_logs = []
            self._early_logs.append(message)
            return
        
        try:
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        except Exception as e:
            print(f"Error updating log: {e}")

    def log_result(self, result):
        self.log(result)

    # Locations tab methods
    def fetch_locations(self):
        self.clear_location_tree()
        self.add_loading_indicator()
        
        self.run_command_async(["list-locations"], self.process_locations)

    def clear_location_tree(self):
        """Clear all items from the location tree"""
        for item in self.location_tree.get_children():
            self.location_tree.delete(item)

    def add_loading_indicator(self):
        """Add a loading indicator to the location tree"""
        self.location_tree.insert("", "end", values=("", "Loading locations...", "", ""))

    def process_locations(self, result):
        """Process the locations output from the CLI"""
        self.clear_location_tree()
        
        # Strip ANSI escape codes from the output
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        result = ansi_escape.sub('', result)
        
        lines = result.split('\n')
        header_found = False
        
        for line in lines:
            if not header_found and "ISO" in line and "COUNTRY" in line:
                header_found = True
                continue
            
            if header_found and line.strip():
                # Use regex to split by 2 or more spaces which is how the CLI formats the output
                columns = re.split(r'\s{2,}', line.strip())
                
                if len(columns) >= 4:
                    iso = columns[0]
                    country = columns[1]
                    city = columns[2]
                    ping = columns[3]
                    
                    self.location_tree.insert("", "end", values=(iso, country, city, ping))
        
        # If no locations were found
        if not self.location_tree.get_children():
            self.location_tree.insert("", "end", values=("", "No locations found or not logged in", "", ""))
        
        # Sort by ping by default
        self.sort_locations_by_column("ping", True)

    def sort_locations_by_column(self, column, initial_sort=False):
        """Sort the location tree by the given column"""
        items = [(self.location_tree.set(item, column), item) for item in self.location_tree.get_children('')]
        
        # If it's the ping column, sort numerically
        if column == "ping":
            try:
                items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else float('inf'))
            except (ValueError, TypeError):
                items.sort()
        else:
            items.sort()
        
        # Rearrange items in the tree
        for index, (_, item) in enumerate(items):
            self.location_tree.move(item, '', index)
        
        # If not the initial sort, configure the heading to sort the other way next time
        if not initial_sort:
            self.location_tree.heading(
                column, 
                command=lambda col=column: self.sort_locations_by_reverse_column(col)
            )

    def sort_locations_by_reverse_column(self, column):
        """Sort the location tree by the given column in reverse order"""
        items = [(self.location_tree.set(item, column), item) for item in self.location_tree.get_children('')]
        
        # If it's the ping column, sort numerically
        if column == "ping":
            try:
                items.sort(key=lambda x: int(x[0]) if x[0].isdigit() else float('inf'), reverse=True)
            except (ValueError, TypeError):
                items.sort(reverse=True)
        else:
            items.sort(reverse=True)
        
        # Rearrange items in the tree
        for index, (_, item) in enumerate(items):
            self.location_tree.move(item, '', index)
        
        # Configure the heading to sort normally next time
        self.location_tree.heading(
            column, 
            command=lambda col=column: self.sort_locations_by_column(col, False)
        )

    def search_locations(self):
        """Search for locations matching the search term"""
        search_term = self.search_entry.get().lower()
        if not search_term:
            self.fetch_locations()
            return
        
        if self.location_tree.get_children():
            self.filter_location_tree(search_term)
        else:
            self.clear_location_tree()
            self.add_loading_indicator()
            self.run_command_async(["list-locations"], lambda result: self.process_search(result, search_term))

    def filter_location_tree(self, search_term):
        """Filter the existing location tree by search term"""
        # Hide all items that don't match
        visible_count = 0
        for item in self.location_tree.get_children():
            values = [str(self.location_tree.set(item, col)).lower() for col in ("iso", "country", "city")]
            if any(search_term in value for value in values):
                self.location_tree.item(item, tags=())
                visible_count += 1
            else:
                self.location_tree.item(item, tags=('hidden',))
        
        # Apply a tag to hide non-matching items
        self.location_tree.tag_configure('hidden', hide=True)
        
        if visible_count == 0:
            self.clear_location_tree()
            self.location_tree.insert("", "end", values=("", f"No locations found matching '{search_term}'", "", ""))

    def process_search(self, result, search_term):
        """Process the locations output and filter by search term"""
        self.process_locations(result)
        self.filter_location_tree(search_term)

    def connect_to_selected(self):
        """Connect to the selected location"""
        if not self.is_logged_in:
            self.log("Not logged in. Please log in first.")
            self.show_login_dialog()
            return
        
        selected = self.location_tree.selection()
        if not selected:
            messagebox.showinfo("Information", "Please select a location")
            return
        
        city = self.location_tree.item(selected, "values")[2]
        if not city:
            messagebox.showinfo("Error", "Could not determine the selected location")
            return
        
        self.log(f"Connecting to {city}...")
        self.status_label.config(text="Status: Connecting...")
        self.status_indicator.itemconfig(self.status_circle, fill="yellow")
        self.connect_button.config(state="disabled")
        
        try:
            cmd = [self.executable, "connect", "--location", city]
            self.log(f"Running direct connection command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=os.environ.copy()
            )
            
            if result.returncode != 0:
                self.log(f"Connection error: {result.stderr}")
                self.handle_connection_result(f"Error: {result.stderr}")
            else:
                self.handle_connection_result(result.stdout)
        except Exception as e:
            self.log(f"Exception during connection: {str(e)}")
            self.handle_connection_result(f"Error: {str(e)}")
        
        self.tab_control.select(0)

    def connect_to_fastest(self):
        """Connect to the fastest location"""
        if not self.is_logged_in:
            self.log("Not logged in. Please log in first.")
            self.show_login_dialog()
            return
        
        self.log("Connecting to fastest location...")
        self.status_label.config(text="Status: Connecting...")
        self.status_indicator.itemconfig(self.status_circle, fill="yellow")
        self.connect_button.config(state="disabled")
        
        try:
            cmd = [self.executable, "connect", "--fastest"]
            self.log(f"Running direct connection command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                env=os.environ.copy()
            )
            
            if result.returncode != 0:
                self.log(f"Connection error: {result.stderr}")
                self.handle_connection_result(f"Error: {result.stderr}")
            else:
                self.handle_connection_result(result.stdout)
        except Exception as e:
            self.log(f"Exception during connection: {str(e)}")
            self.handle_connection_result(f"Error: {str(e)}")
        
        self.tab_control.select(0)

    # Settings tab methods
    def load_settings(self):
        # Get current configuration
        config_output = self.run_command(["config", "show"])
        
        # Parse the output to set the UI elements
        lines = config_output.split('\n')
        for line in lines:
            line = line.strip()
            if "VPN mode:" in line:
                mode = line.split("VPN mode:")[1].strip()
                self.mode_var.set(mode)
            elif "SOCKS port:" in line:
                port = line.split("SOCKS port:")[1].strip()
                self.socks_port_entry.delete(0, tk.END)
                self.socks_port_entry.insert(0, port)
            elif "SOCKS host:" in line:
                host = line.split("SOCKS host:")[1].strip()
                self.socks_host_entry.delete(0, tk.END)
                self.socks_host_entry.insert(0, host)
            elif "DNS server:" in line:
                dns = line.split("DNS server:")[1].strip()
                self.dns_entry.delete(0, tk.END)
                self.dns_entry.insert(0, dns)
            elif "Update channel:" in line:
                channel = line.split("Update channel:")[1].strip()
                self.update_channel_var.set(channel)

    def apply_settings(self):
        # Apply VPN mode
        mode = self.mode_var.get()
        self.run_command(["config", "set-mode", mode])
        
        # Apply SOCKS settings
        socks_port = self.socks_port_entry.get()
        socks_host = self.socks_host_entry.get()
        
        if socks_port:
            self.run_command(["config", "set-socks-port", socks_port])
        
        if socks_host:
            self.run_command(["config", "set-socks-host", socks_host])
        
        # Apply DNS settings
        dns_server = self.dns_entry.get()
        if dns_server:
            self.run_command(["config", "set-dns", dns_server])
        
        # Apply update channel
        update_channel = self.update_channel_var.get()
        self.run_command(["config", "set-update-channel", update_channel])
        
        messagebox.showinfo("Settings Applied", "Settings have been applied successfully")

    # Exclusions tab methods
    def apply_exclusion_mode(self):
        mode = self.exclusion_mode_var.get()
        self.run_command(["site-exclusions", "mode", mode])
        messagebox.showinfo("Mode Applied", f"Exclusion mode set to '{mode}'")

    def refresh_exclusions(self):
        self.exclusions_listbox.delete(0, tk.END)
        self.exclusions_listbox.insert(tk.END, "Loading exclusions...")
        
        self.run_command_async(["site-exclusions", "show"], self.process_exclusions)

    def process_exclusions(self, result):
        self.exclusions_listbox.delete(0, tk.END)
        
        lines = result.split('\n')
        mode_line = None
        exclusions = []
        
        for line in lines:
            if "Exclusion mode:" in line:
                mode_line = line
                mode = line.split("Exclusion mode:")[1].strip()
                self.exclusion_mode_var.set(mode)
            elif line.strip() and "Exclusion mode:" not in line and "Site exclusions:" not in line:
                exclusions.append(line.strip())
        
        if exclusions:
            for exclusion in exclusions:
                self.exclusions_listbox.insert(tk.END, exclusion)
        else:
            if mode_line:
                self.exclusions_listbox.insert(tk.END, "No exclusions set")
            else:
                self.exclusions_listbox.insert(tk.END, "Could not retrieve exclusions")

    def add_exclusion(self):
        site = self.add_exclusion_entry.get().strip()
        if not site:
            messagebox.showinfo("Information", "Please enter a site to add")
            return
        
        self.run_command(["site-exclusions", "add", site])
        self.add_exclusion_entry.delete(0, tk.END)
        self.refresh_exclusions()

    def remove_exclusion(self):
        selected = self.exclusions_listbox.curselection()
        if not selected:
            messagebox.showinfo("Information", "Please select an exclusion to remove")
            return
        
        site = self.exclusions_listbox.get(selected[0])
        self.run_command(["site-exclusions", "remove", site])
        self.refresh_exclusions()

    def clear_exclusions(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear all exclusions?"):
            self.run_command(["site-exclusions", "clear"])
            self.refresh_exclusions()

    # About tab methods
    def check_update(self):
        self.log("Checking for updates...")
        result = self.run_command(["check-update"])
        
        if "update available" in result.lower():
            if messagebox.askyesno("Update Available", "An update is available. Would you like to install it?"):
                self.run_command_async(["update", "--yes"], self.log_result)
        else:
            messagebox.showinfo("No Updates", "You are running the latest version")

    def export_logs(self):
        output_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("Zip files", "*.zip"), ("All files", "*.*")],
            title="Save Logs As"
        )
        
        if output_path:
            self.log(f"Exporting logs to {output_path}...")
            self.run_command_async(["export-logs", "--output", output_path], self.log_result)

    def show_license(self):
        result = self.run_command(["license"])
        
        license_window = tk.Toplevel(self.root)
        license_window.title("License Information")
        license_window.geometry("600x400")
        
        license_text = scrolledtext.ScrolledText(license_window, wrap=tk.WORD)
        license_text.pack(fill="both", expand=True, padx=10, pady=10)
        license_text.insert(tk.END, result)
        license_text.config(state="disabled")

    def manual_refresh_status(self):
        """Manually refresh the VPN status"""
        self.log("Manually refreshing VPN status...")
        self.status_label.config(text="Status: Checking...")
        self.status_indicator.itemconfig(self.status_circle, fill="gray")
        
        # Force a process list check to see if the VPN process is actually running
        self.check_vpn_process_running()
        
        # Also run the status command
        self.run_command_async(["status"], self.process_status)

    def check_vpn_process_running(self):
        """Check if the VPN process is actually running using ps"""
        try:
            # Get the base name of the executable
            import os
            exe_name = os.path.basename(self.executable)
            
            # Check the process list
            if os.name == 'posix':
                cmd = ["ps", "-A"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Simple check - look for the executable name in the output
                is_running = exe_name in result.stdout
                
                # Log the finding
                self.log(f"Process check: VPN process '{exe_name}' {'is' if is_running else 'is not'} running")
                
                # If it's not running, ensure the UI reflects disconnected state
                if not is_running:
                    self.status_label.config(text="Status: Disconnected (process not running)")
                    self.status_indicator.itemconfig(self.status_circle, fill="red")
                    self.connect_button.config(text="Connect")
                    self.ip_label.config(text="Not connected")
                    self.location_label.config(text="Not connected")
                    self.protocol_label.config(text="Not connected")

        except Exception as e:
            self.log(f"Error checking process status: {e}")

    def check_login_status(self):
        """Check if the user is logged in to the VPN service"""
        self.log("Checking login status...")
        
        # Run the status command to see if we can access the service
        result = self.run_command(["status"], check_error=False)
        
        if "Before connecting to a location, you must log in" in result or "You are not logged in" in result:
            self.is_logged_in = False
            self.log("You are not logged in to AdGuard VPN")
            
            # Ask user if they want to log in now
            if messagebox.askyesno("Login Required", 
                                  "You need to log in to use AdGuard VPN.\nWould you like to log in now?"):
                self.show_login_dialog()
        else:
            self.is_logged_in = True
            self.log("Login status: Logged in")
            self.update_status()

    def show_login_dialog(self):
        """Show login dialog to authenticate with the VPN service"""
        login_window = tk.Toplevel(self.root)
        login_window.title("Login to AdGuard VPN")
        login_window.geometry("400x250")
        login_window.resizable(False, False)
        login_window.transient(self.root)
        login_window.grab_set()
        
        login_frame = tk.Frame(login_window, bg=self.bg_color, padx=20, pady=20)
        login_frame.pack(fill="both", expand=True)
        
        tk.Label(
            login_frame, 
            text="Log in to AdGuard VPN", 
            font=("Arial", 14, "bold"), 
            bg=self.bg_color
        ).pack(pady=(0, 20))
        
        # Username
        username_frame = tk.Frame(login_frame, bg=self.bg_color)
        username_frame.pack(fill="x", pady=5)
        tk.Label(username_frame, text="Username:", width=12, anchor="w", bg=self.bg_color).pack(side="left")
        username_entry = tk.Entry(username_frame, width=25)
        username_entry.pack(side="left", fill="x", expand=True)
        
        # Password
        password_frame = tk.Frame(login_frame, bg=self.bg_color)
        password_frame.pack(fill="x", pady=5)
        tk.Label(password_frame, text="Password:", width=12, anchor="w", bg=self.bg_color).pack(side="left")
        password_entry = tk.Entry(password_frame, width=25, show="*")
        password_entry.pack(side="left", fill="x", expand=True)
        
        # Message label for errors
        message_label = tk.Label(login_frame, text="", fg="red", bg=self.bg_color)
        message_label.pack(pady=10)
        
        # Login button
        def do_login():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            
            if not username or not password:
                message_label.config(text="Username and password are required")
                return
            
            message_label.config(text="Logging in...")
            login_window.update()
            
            # Run the login command
            result = self.run_command(["login", "--username", username, "--password", password], check_error=False)
            
            if "successfully logged in" in result.lower() or "you are already logged in" in result.lower():
                self.is_logged_in = True
                self.log("Successfully logged in to AdGuard VPN")
                login_window.destroy()
                self.update_status()
            else:
                message_label.config(text="Login failed. Please check your credentials.")
        
        button_frame = tk.Frame(login_frame, bg=self.bg_color)
        button_frame.pack(fill="x", pady=10)
        
        login_button = tk.Button(
            button_frame,
            text="Login",
            command=do_login,
            bg=self.accent_color,
            fg="white",
            font=("Arial", 11, "bold"),
            relief="flat",
            padx=15,
            pady=5
        )
        login_button.pack(side="right", padx=5)
        
        cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=login_window.destroy,
            bg="#CCCCCC",
            fg="black",
            font=("Arial", 11),
            relief="flat",
            padx=15,
            pady=5
        )
        cancel_button.pack(side="right", padx=5)

    def logout_user(self):
        """Log out the current user"""
        if messagebox.askyesno("Confirm Logout", "Are you sure you want to log out?"):
            result = self.run_command(["logout"], check_error=False)
            if "successfully logged out" in result.lower():
                self.is_logged_in = False
                self.log("Successfully logged out")
                messagebox.showinfo("Logged Out", "You have been logged out from AdGuard VPN")
            else:
                self.log(f"Logout error: {result}")
                messagebox.showerror("Logout Error", "Could not log out properly. See logs for details.")

    def display_early_logs(self):
        """Display any logs that were generated before the UI was fully set up"""
        if hasattr(self, '_early_logs') and hasattr(self, 'log_text'):
            for message in self._early_logs:
                try:
                    self.log_text.config(state="normal")
                    self.log_text.insert(tk.END, message + "\n")
                    self.log_text.see(tk.END)
                    self.log_text.config(state="disabled")
                except Exception as e:
                    print(f"Error displaying early log: {e}")
            self._early_logs = []

if __name__ == "__main__":
    root = tk.Tk()
    app = AdGuardVPNGUI(root)
    root.mainloop() 
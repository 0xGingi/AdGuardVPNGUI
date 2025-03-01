# AdGuardVPNGUI

AdGuardVPNGUI provides a GUI for the Linux AdGuard VPN CLI
![Screenshot_20250301_095003](https://github.com/user-attachments/assets/3c385c0e-c4d4-45f8-a642-2f36429d9474)

## Features

- **One-click connection**: Connect to VPN with a single click
- **Location browser**: View and search through all available VPN locations
- **Connection details**: See your connection status, IP address, and location
- **Settings management**: Configure VPN mode, DNS, and update settings
- **Site exclusions**: Manage websites that bypass the VPN
- **Auto-login**: Convenient login dialog with credential management
- **Status monitoring**: Real-time connection status updates

## Dependencies

- Python
- Tkinter
- AdGuard VPN CLI (https://github.com/AdguardTeam/AdguardVPNCLI)

## Installation

### Binary

1. Download the binary from the [releases page](https://github.com/0xGingi/AdguardVPNGUI/releases)
2. Make the binary executable:
   ```
   chmod +x AdGuardVPN
   ```
3. Run the binary:
   ```
   ./AdGuardVPN
   ```

### Build Binary (This will install the binary to /usr/local/bin/AdGuardVPN and create a desktop file)

1. Clone this repository:
   ```
   git clone https://github.com/0xGingi/AdguardVPNGUI.git
   ```
2. Navigate to the project directory:
   ```
   cd AdguardVPNGUI
   ```
3. Build/Install the binary:
   ```
   python build.py
   ```

### Run from Python

1. Clone this repository:
   ```
   git clone https://github.com/0xGingi/AdguardVPNGUI.git
   ```
4. Navigate to the project directory:
   ```
   cd AdguardVPNGUI
   ```
5. Run the application:
   ```
   python adguard_vpn_gui.py
   ```

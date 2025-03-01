import PyInstaller.__main__
import os
import subprocess
import sys

def run_with_check(cmd, error_msg="Command failed"):
    """Run a shell command and check for errors"""
    try:
        result = subprocess.run(cmd, check=True, shell=True, text=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\033[91mERROR: {error_msg}\033[0m")
        print(f"Command: {cmd}")
        print(f"Error: {e.stderr}")
        return False

def create_desktop_file():
    """Create and install the desktop file"""
    print("\n\033[1m=== Creating Desktop Integration ===\033[0m")
    
    desktop_content = """[Desktop Entry]
Name=AdGuard VPN
Comment=GUI for AdGuard VPN CLI
Exec=/usr/local/bin/AdGuardVPN
Terminal=false
Type=Application
Categories=Network;VPN;
"""

    try:
        with open("AdGuardVPN.desktop", "w") as f:
            f.write(desktop_content)
        print("✓ Desktop file created")
    except Exception as e:
        print(f"\033[91mERROR: Failed to create desktop file: {e}\033[0m")
        return False
    
    if not run_with_check("sudo cp AdGuardVPN.desktop /usr/share/applications/",
                        "Failed to copy desktop file to applications directory"):
        return False
    
    if not run_with_check("sudo cp dist/AdGuardVPN /usr/local/bin/",
                        "Failed to copy executable to bin directory"):
        return False
    
    print("\033[92m✓ Desktop integration completed successfully\033[0m")
    return True

def build_binary():
    """Build the binary with PyInstaller"""
    print("\033[1m=== Building AdGuard VPN GUI Binary ===\033[0m")
    
    os.makedirs('dist', exist_ok=True)
    os.makedirs('build', exist_ok=True)
    
    try:
        PyInstaller.__main__.run([
            'adguard_vpn_gui.py',
            '--name=AdGuardVPN',
            '--onefile',
            '--windowed',
            '--clean',
            '--noconfirm',
            '--hidden-import=urllib.request',
            '--hidden-import=json',
            '--hidden-import=threading',
            '--hidden-import=subprocess',
        ])
        
        print("\033[92m✓ Build completed successfully. Executable is in the 'dist' directory.\033[0m")
        return True
    except Exception as e:
        print(f"\033[91mERROR: Build failed: {e}\033[0m")
        return False

def main():
    if not os.path.exists("adguard_vpn_gui.py"):
        print("\033[91mERROR: adguard_vpn_gui.py not found in the current directory\033[0m")
        return 1
    
    if not build_binary():
        return 1
    
    response = input("\nDo you want to create desktop integration? (y/n): ").lower()
    if response.startswith('y'):
        if not create_desktop_file():
            return 1
    
    print("\n\033[92mAll operations completed successfully!\033[0m")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
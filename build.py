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

def install_binary():
    """Install the binary to system path"""
    print("\n\033[1m=== Installing Binary ===\033[0m")
    
    if not run_with_check("sudo cp dist/AdGuardVPN /usr/local/bin/",
                        "Failed to copy executable to bin directory"):
        return False
    
    print("\033[92m✓ Binary installed successfully to /usr/local/bin/AdGuardVPN\033[0m")
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
            '--hidden-import=re',
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
    
    # Ask if the user wants to install the binary to system path
    binary_response = input("\nDo you want to install the binary to /usr/local/bin? (y/n): ").lower()
    binary_installed = False
    
    if binary_response.startswith('y'):
        binary_installed = install_binary()
        if not binary_installed:
            print("\033[93mWarning: Binary installation failed. Desktop integration may not work correctly.\033[0m")
        
    print("\n\033[92mAll operations completed successfully!\033[0m")
    if not binary_installed:
        print("\033[93mNote: The binary was not installed to /usr/local/bin.\033[0m")
        print(f"\033[93mYou can run it directly from: {os.path.abspath('dist/AdGuardVPN')}\033[0m")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
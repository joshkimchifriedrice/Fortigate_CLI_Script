#!./.venv/Scripts/python.exe
"""Credential management module for Fortigate SSH connections."""

import json
from pathlib import Path
from typing import Dict, Optional
from getpass import getpass

from ssh_client import FortigateSSHClient


class CredentialManager:
    """Manages Fortigate credentials in plaintext for QA testing."""

    def __init__(self):
        """Initialize credential manager and config file path."""
        self.config_dir = Path.home() / ".config" / ".fortigate_config"
        self.config_file = self.config_dir / "config.json"
        self._ensure_config_exists()

    def _ensure_config_exists(self) -> None:
        """Create config directory and file if they don't exist."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.config_file.exists():
            self._write_config({"profiles": {}})

    def _read_config(self) -> Dict:
        """Read and parse the config file."""
        try:
            with open(self.config_file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"profiles": {}}

    def _write_config(self, config: Dict) -> None:
        """Write config to file."""
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)

    def save_profile(self, profile_name: str, ip: str, username: str, password: str) -> None:
        """Save a credential profile after validating the connection."""
        while True:
            # Test SSH connection first
            ssh_client = FortigateSSHClient()
            if ssh_client.connect(ip, username, password):
                ssh_client.disconnect()
                print(f"✓ Connection successful to {ip}, credentials are valid.")
                break
            else:
                print(f"✗ Connection failed to {ip} with provided credentials. Please try again.\n")
                
            # Ask for new credentials
            print(f"\nSaving credentials for profile: {profile_name}")
            ip = input("Fortigate IP address: ").strip()
            username = input("Username: ").strip()
            password = getpass("Password: ")
            

        # Only save if connection was successful
        config = self._read_config()
        config["profiles"][profile_name] = {
            "ip": ip,
            "username": username,
            "password": password,
        }
        self._write_config(config)
        print(f"Profile '{profile_name}' saved successfully.")

    def load_profile(self, profile_name: str) -> Optional[Dict]:
        """Load a credential profile."""
        config = self._read_config()
        if profile_name not in config["profiles"]:
            return None

        profile = config["profiles"][profile_name]
        return {
            "ip": profile["ip"],
            "username": profile["username"],
            "password": profile["password"],
        }

    def delete_profile(self, profile_name: str) -> bool:
        """Delete a credential profile."""
        config = self._read_config()
        if profile_name not in config["profiles"]:
            print(f"Profile '{profile_name}' not found.")
            return False

        del config["profiles"][profile_name]
        self._write_config(config)
        print(f"Profile '{profile_name}' deleted successfully.")
        return True

    def list_profiles(self) -> None:
        """List all saved profiles."""
        config = self._read_config()
        profiles = config["profiles"]

        if not profiles:
            print("No profiles saved.")
            return

        print("Saved profiles:")
        for name, data in profiles.items():
            print(f"  {name}: {data['ip']}")

#!./.venv/Scripts/python.exe
"""SSH client module for Fortigate connections."""

import paramiko
import socket
from typing import Optional


class FortigateSSHClient:
    """SSH client for Fortigate connections."""

    def __init__(self):
        """Initialize SSH client."""
        self.client = None
        self.shell = None

    def connect(self, ip: str, username: str, password: str, port: int = 22, timeout: int = 10) -> bool:
        """
        Connect to a Fortigate device via SSH.

        Args:
            ip: IP address of the Fortigate device
            username: SSH username
            password: SSH password
            port: SSH port (default: 22)
            timeout: Connection timeout in seconds

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(ip, port=port, username=username, password=password, timeout=timeout)
            return True
        except paramiko.AuthenticationException:
            print(f"✗ Error: Invalid username or password for {username}@{ip}")
            return False
        except socket.gaierror:
            print(f"✗ Error: IP address '{ip}' does not exist or is unreachable")
            return False
        except socket.timeout:
            print(f"✗ Error: Connection timeout - IP '{ip}' is unreachable")
            return False
        except (OSError, socket.error) as e:
            if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                print(f"✗ Error: Connection timeout - IP '{ip}' is unreachable")
            else:
                print(f"✗ Error: IP address '{ip}' does not exist or is unreachable")
            return False
        except Exception as e:
            print(f"✗ Error: Failed to connect: {str(e)}")
            return False

    def execute_command(self, command: str) -> Optional[str]:
        """
        Execute a command on the Fortigate device.

        Args:
            command: The command to execute

        Returns:
            Command output as a string, or None if execution failed
        """
        if not self.client:
            print("Not connected to a Fortigate device")
            return None

        try:
            stdin, stdout, stderr = self.client.exec_command(command)
            output = stdout.read().decode()
            error = stderr.read().decode()

            if error:
                return f"OUTPUT:\n{output}\n\nERROR:\n{error}"
            return output
        except Exception as e:
            print(f"Command execution error: {e}")
            return None

    def disconnect(self) -> None:
        """Disconnect from the Fortigate device."""
        if self.client:
            self.client.close()
            self.client = None

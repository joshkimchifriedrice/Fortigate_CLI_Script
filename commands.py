"""Command definitions for Fortigate CLI tool."""


class Commands:
    """Command manager with methods for each Fortigate command."""

    @staticmethod
    def darp_command(ssh_client) -> str:
        """Execute DARP diagnostic command and return output."""
        commands_list = ["diagnose debug application darp -1\n"]
        output = []
        
        for cmd in commands_list:
            print(f"Executing: {cmd.strip()}")
            result = ssh_client.execute_command(cmd)
            if result is None:
                raise RuntimeError(f"Command execution failed: {cmd.strip()}")
            output.append(result)
        
        return "\n".join(output)

    @staticmethod
    def wlac_command(ssh_client) -> str:
        """Execute time and wireless controller WLAC diagnostic commands and return output."""
        commands_list = [
            "execute time\n",
            "diagnose wireless-controller wlac -c darrp\n",
        ]
        output = []
        
        for cmd in commands_list:
            print(f"Executing: {cmd.strip()}")
            result = ssh_client.execute_command(cmd)
            if result is None:
                raise RuntimeError(f"Command execution failed: {cmd.strip()}")
            output.append(result)
        
        return "\n".join(output)

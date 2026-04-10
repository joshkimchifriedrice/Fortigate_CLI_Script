#!./.venv/Scripts/python.exe
"""Fortigate SSH CLI tool for remote command execution and log collection."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from getpass import getpass

from credentials import CredentialManager
from ssh_client import FortigateSSHClient
from commands import Commands 


def cmd_creds_save(args):
    """Handle 'creds save' subcommand."""
    cred_manager = CredentialManager()

    print(f"Saving credentials for profile: {args.profile}")
    ip = input("Fortigate IP address: ").strip()
    username = input("Username: ").strip()
    password = getpass("Password: ")

    cred_manager.save_profile(args.profile, ip, username, password)


def cmd_creds_delete(args):
    """Handle 'creds delete' subcommand."""
    cred_manager = CredentialManager()
    cred_manager.delete_profile(args.profile)


def cmd_creds_list(args):
    """Handle 'creds list' subcommand."""
    cred_manager = CredentialManager()
    cred_manager.list_profiles()


def cmd_run(args):
    """Handle 'run' subcommand to execute commands on Fortigate."""
    cred_manager = CredentialManager()

    # Load credentials
    profile = cred_manager.load_profile(args.profile)
    if not profile:
        print(f"Error: Profile '{args.profile}' not found.")
        sys.exit(1)

    # Connect to Fortigate
    ssh_client = FortigateSSHClient()
    print(f"Connecting to {profile['ip']}...")
    if not ssh_client.connect(profile["ip"], profile["username"], profile["password"]):
        sys.exit(1)

    # Map command to method name
    command_method_name = {
        "darrp": "get_darrp_status_command"
    }.get(args.command)
    if not command_method_name:
        print(f"Error: Command '{args.command}' is not supported.")
        ssh_client.disconnect()
        sys.exit(1)
    # Execute command method and get output
    try:
        command_method = getattr(Commands, command_method_name)
        # Pass delay if provided (used by get_darrp_status_command)
        delay_val = getattr(args, 'delay', None)
        if delay_val is not None:
            output = command_method(ssh_client, delay_val)
        else:
            output = command_method(ssh_client)
    except RuntimeError as e:
        print(f"Error: {e}")
        ssh_client.disconnect()
        sys.exit(1)

    ssh_client.disconnect()

    # Display output
    print("\n=== Command Output ===")
    print(output)

    # Save to file if specified
    if getattr(args, 'file', None):
        output_file = Path(getattr(args, 'file'))
        output_file.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(output_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Profile: {args.profile}\n")
            f.write(f"Command: {args.command}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"{'='*60}\n")
            f.write(output)
            f.write("\n")

        print(f"\nOutput appended to: {output_file}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Fortigate SSH CLI tool for remote command execution and log collection\n\nbasic usage:\n" \
        "   1. Run \"python fortigate_tool.py creds save <profile_name>\" to save IP and login credentials for a Fortigate device.\n" \
        "   2. Run \"python fortigate_tool.py run <profile_name> <command>\" to execute a command on the device and display output.\n" \
        "   3. Use the -f option to save command output to a file for later analysis.\n\n" \
        "<command> list:\n" \
        "   darrp - Grab DARRP diagnostic output and parse it based on if the channel has changed since the last check.\n",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Credentials subcommands
    creds_parser = subparsers.add_parser("creds", help="Manage saved credentials")
    creds_subparsers = creds_parser.add_subparsers(dest="creds_command")

    save_parser = creds_subparsers.add_parser("save", help="Save new credentials")
    save_parser.add_argument("profile", help="Profile name")
    save_parser.set_defaults(func=cmd_creds_save)

    delete_parser = creds_subparsers.add_parser("delete", help="Delete saved credentials")
    delete_parser.add_argument("profile", help="Profile name")
    delete_parser.set_defaults(func=cmd_creds_delete)

    list_parser = creds_subparsers.add_parser("list", help="List all saved profiles")
    list_parser.set_defaults(func=cmd_creds_list)

    # Run subcommand
    run_parser = subparsers.add_parser("run", help="Execute command on Fortigate")
    run_parser.add_argument("profile", help="Profile name")
    run_parser.add_argument("command", help="Command to execute")
    # run_parser.add_argument("-f", "--file", help="Append output to file")
    run_parser.add_argument("-d", "--delay", type=int, default=15, help="Delay in seconds between DARRP checks (default: 15)")
    run_parser.set_defaults(func=cmd_run)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

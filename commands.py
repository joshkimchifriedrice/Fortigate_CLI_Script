#!./.venv/Scripts/python.exe
"""Command definitions for Fortigate CLI tool."""

import re
import csv
import time
from datetime import datetime
from pathlib import Path


class Commands:
    """Command manager with methods for each Fortigate command."""

    @staticmethod
    def get_darrp_status_command(ssh_client, delay: int = 30) -> str:
        """Execute DARP diagnostic command and return output.

        This runs an initial `diagnose ... darrp`, parses it, runs the debug
        command, waits `delay` seconds, runs `diagnose ... darrp` again and
        compares `oper_chan` between the two captures. Entries are keyed by
        `wtp_id` and `rId` (if present) so differing rId values are treated as
        separate devices.
        """
        from pathlib import Path
        
        # Setup file paths
        # TODO: Debug on different os and filestructures and coordinate with manager.
        project_dir = Path.cwd()
        log_file = project_dir / "darp_output.log"
        csv_file = project_dir / "channel_changed.csv"
        same_file = project_dir / "channel_same.csv"
        
        # Step 1: Execute "execute time" command
        print("Executing: execute time")
        time_output = ssh_client.execute_command("execute time\n")
        if time_output is None:
            raise RuntimeError("Failed to execute 'execute time'")
        
        # Extract time from output (format: "current time is: HH:MM:SS")
        time_match = re.search(r'current time is:\s*(\d{1,2}):(\d{2}):(\d{2})', time_output)
        if not time_match:
            raise RuntimeError(f"Could not extract time from output: {time_output}")
        
        hours, minutes, seconds = time_match.groups()
        # Build a datetime with today's date combined with the device time
        time_part = datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S").time()
        capture_time = datetime.combine(datetime.now().date(), time_part)
        print(f"Extracted time: {capture_time}")
        
        # Append "execute time" output to log file
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Capture Time: {capture_time}\n")
            f.write(f"{'='*60}\n")
            f.write(time_output)
            f.write("\n")
        
        # Step 2: Execute "diagnose wireless-controller wlac -c darrp"
        print("Executing: diagnose wireless-controller wlac -c darrp")
        wlac_output = ssh_client.execute_command("diagnose wireless-controller wlac -c darrp\n")
        if wlac_output is None:
            raise RuntimeError("Failed to execute 'diagnose wireless-controller wlac -c darrp'")
        
        # Append "diagnose wireless-controller wlac -c darrp" output to log file (first capture)
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Capture Time: {capture_time}\n")
            f.write(f"{'='*60}\n")
            f.write(wlac_output)
            f.write("\n")
        # Parse table from output (first capture)
        wtp_dict_first = Commands._parse_wlac_table(wlac_output)
        print(f"Parsed {len(wtp_dict_first)} WTP entries (first capture)")

        # Step 4: Execute debug command
        # print("Executing: diagnose wireless-controller wlac -c darrp dbg 1")
        # dbg_output = ssh_client.execute_command("diagnose wireless-controller wlac -c darrp dbg 1\n")
        print("Executing: diagnose wireless-controller wlac -c darrp 1")
        dbg_output = ssh_client.execute_command("diagnose wireless-controller wlac -c darrp 1\n")
        if dbg_output is None:
            raise RuntimeError("Failed to execute debug command")

        # Append debug output to log file
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write("Debug Output (darrp dbg 1)\n")
            f.write(f"{'='*60}\n")
            f.write(dbg_output)
            f.write("\n")

        # Wait the configured delay, then capture WLAC table again
        print(f"Waiting {delay} seconds before second capture...")
        time.sleep(delay)

        print("Executing: diagnose wireless-controller wlac -c darrp (second capture)")
        wlac_output2 = ssh_client.execute_command("diagnose wireless-controller wlac -c darrp\n")
        if wlac_output2 is None:
            raise RuntimeError("Failed to execute second 'diagnose wireless-controller wlac -c darrp'")

        # Append second capture to log
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Capture Time (second): {capture_time}\n")
            f.write(f"{'='*60}\n")
            f.write(wlac_output2)
            f.write("\n")

        # Parse second capture
        wtp_dict_second = Commands._parse_wlac_table(wlac_output2)
        print(f"Parsed {len(wtp_dict_second)} WTP entries (second capture)")

        # Step 5: Compare captures and record changes/unchanged devices
        if csv_file.exists():
            for key, first_data in wtp_dict_first.items():
                second_data = wtp_dict_second.get(key)
                first_chan = first_data.get('oper_chan')
                second_chan = second_data.get('oper_chan') if second_data else None

                # Compare first vs second captures
                print(f"Comparing {key}: oper_chan={first_chan} with second capture new_chan={second_chan}")
                print(f"Device {first_data.get('wtp_id')} rId={first_data.get('rId')} first={first_chan} second={second_chan}")

                if second_chan is None or first_chan != second_chan:
                    # Channel changed -> record both channels in channel_changed.csv
                    src = second_data if second_data else first_data
                    row_data = dict(src)
                    row_data['oper_chan'] = first_chan if first_chan is not None else ''
                    row_data['new_chan'] = second_chan if second_chan is not None else ''
                    Commands._append_to_csv(csv_file, capture_time, {key: row_data})
                    print(f"Channel change detected for {key}: {first_chan} -> {second_chan}")
                else:
                    # Channel unchanged -> record in channel_same.csv
                    Commands._append_to_csv(same_file, capture_time, {key: second_data})
                    print(f"No change for {key}: oper_chan = {second_chan}")
        else:
            # CSV doesn't exist - create it with the second-capture entries (latest state)
            base = wtp_dict_second if wtp_dict_second else wtp_dict_first
            Commands._append_to_csv(csv_file, capture_time, base)
            print(f"Created {csv_file} with {len(base)} entries")

            # Separate iterations with newlines.
            for _p in (same_file, csv_file):
                try:
                    with open(_p, 'a', newline='') as _f:
                        _f.write('\n\n\n')
                except Exception as _e:
                    print(f"Error appending newlines to {_p}: {_e}")

        # Return combined output (first wlac, second wlac, debug)
        return time_output + "\n" + wlac_output + "\n" + wlac_output2 + "\n" + dbg_output

    @staticmethod
    def _parse_wlac_table(output: str) -> dict:
        """Parse the WLAC table and return a dictionary of WTP entries."""
        wtp_dict = {}
        lines = output.split('\n')

        # Find the header line (require these columns)
        header_idx = -1
        for i, line in enumerate(lines):
            if 'wtp_id' in line and 'oper_chan' in line:
                # rId may or may not be present in the header; we handle it below
                header_idx = i
                break

        if header_idx == -1:
            print("Warning: Could not find WLAC table header")
            return wtp_dict

        # Parse header
        header_line = lines[header_idx]
        headers = header_line.split()

        # Parse data rows (starting after header)
        for line in lines[header_idx + 1:]:
            line = line.strip()
            if not line or line.startswith('---'):
                continue

            # Split the line into fields
            fields = line.split()
            if len(fields) < len(headers):
                continue

            # Get wtp_id before processing
            wtp_id = fields[0] if fields else None

            # Only include lines that look like actual device entries
            if not wtp_id or not re.match(r'^[A-Z]{2}\w+', wtp_id):
                print(f"Skipping non-device row: {wtp_id}")
                continue

            # Create entry dictionary
            entry = {}
            for i, header in enumerate(headers):
                if i < len(fields):
                    entry[header] = fields[i]

            # Build composite key using wtp_id and rId (if present) so differing rId's are separate
            rId = entry.get('rId', '').strip()
            composite_key = f"{entry['wtp_id']}|{rId}" if rId else entry['wtp_id']

            # Store entry using composite key; keep entry containing original 'wtp_id' and 'rId'
            wtp_dict[composite_key] = entry

        return wtp_dict

    @staticmethod
    def _get_latest_channels(csv_file: Path) -> dict:
        """Get the latest channel for each wtp_id from the CSV file."""
        latest_channels = {}
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Build a dict keyed by composite (wtp_id|rId if rId exists) -> latest oper_chan
                for row in rows:
                    wtp_id = row.get('wtp_id', '').strip()
                    rId = row.get('rId', '').strip()
                    oper_chan = row.get('oper_chan', '').strip()

                    # Only include valid device entries
                    if wtp_id and oper_chan and re.match(r'^[A-Z]{2}\w+', wtp_id):
                        key = f"{wtp_id}|{rId}" if rId else wtp_id
                        latest_channels[key] = oper_chan
        except Exception as e:
            print(f"Error reading CSV file: {e}")
        
        return latest_channels

    @staticmethod
    def _append_to_csv(csv_file: Path, capture_time: datetime, wtp_dict: dict) -> None:
        """Append WTP data to CSV file."""
        # Determine if file exists
        file_exists = csv_file.exists()
        
        # Get all field names
        fieldnames = ['capture_time', 'wtp_id']
        if wtp_dict:
            first_entry = next(iter(wtp_dict.values()))
            fieldnames.extend([k for k in first_entry.keys() if k != 'wtp_id'])
        
        try:
            with open(csv_file, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                # Write header if file doesn't exist
                if not file_exists:
                    writer.writeheader()

                # Write each WTP entry. Use the `wtp_id` value from the data itself so
                # composite dict keys do not end up in the `wtp_id` column.
                for key, data in wtp_dict.items():
                    wtp_id_val = data.get('wtp_id', key)
                    row = {'capture_time': capture_time.strftime("%Y-%m-%d %H:%M:%S"), 'wtp_id': wtp_id_val}
                    row.update(data)
                    writer.writerow(row)
        except Exception as e:
            print(f"Error writing to CSV file: {e}")

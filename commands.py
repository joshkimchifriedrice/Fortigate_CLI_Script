#!./.venv/Scripts/python.exe
"""Command definitions for Fortigate CLI tool."""

import re
import csv
from datetime import datetime
from pathlib import Path


class Commands:
    """Command manager with methods for each Fortigate command."""

    @staticmethod
    def get_darrp_status_command(ssh_client) -> str:
        """Execute DARP diagnostic command and return output."""
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
        capture_time = datetime.strptime(f"{hours}:{minutes}:{seconds}", "%H:%M:%S")
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
        
        # Append "diagnose wireless-controller wlac -c darrp" output to log file
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Capture Time: {capture_time}\n")
            f.write(f"{'='*60}\n")
            f.write(wlac_output)
            f.write("\n")

        # Parse table from output
        wtp_dict = Commands._parse_wlac_table(wlac_output)
        print(f"Parsed {len(wtp_dict)} WTP entries")
        
        # Step 3: Compare with channel_changed.csv
        if csv_file.exists():
            # CSV exists - check for changes per device
            latest_channels = Commands._get_latest_channels(csv_file)
            
            for wtp_id, data in wtp_dict.items():
                current_oper_chan = data.get('oper_chan')
                prev_oper_chan = latest_channels.get(wtp_id)
                print(f"prev_oper_chan: {prev_oper_chan}")
                print(f"current_oper_chan: {current_oper_chan}")
                
                if prev_oper_chan is None or current_oper_chan != prev_oper_chan:
                    # Channel changed for this wtp_id or doesn't exist, add to channel_changed.csv
                    Commands._append_to_csv(csv_file, capture_time, {wtp_id: data})
                    print(f"Channel change detected for {wtp_id}: {prev_oper_chan} -> {current_oper_chan}")
                else:
                    # Channel same for this wtp_id, add to channel_same.csv
                    Commands._append_to_csv(same_file, capture_time, {wtp_id: data})
                    print(f"No change for {wtp_id}: oper_chan = {current_oper_chan}")
        else:
            # CSV doesn't exist - create it with all entries as initial
            Commands._append_to_csv(csv_file, capture_time, wtp_dict)
            print(f"Created {csv_file} with {len(wtp_dict)} entries")
        

        # Step 4: Execute "diagnose wireless-controller wlac -c darrp dbg 1"
        print("Executing: diagnose wireless-controller wlac -c darrp dbg 1")
        dbg_output = ssh_client.execute_command("diagnose wireless-controller wlac -c darrp dbg 1\n")
        if dbg_output is None:
            raise RuntimeError("Failed to execute debug command")
        
        # Append debug output to log file
        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write("Debug Output (darrp dbg 1)\n")
            f.write(f"{'='*60}\n")
            f.write(dbg_output)
            f.write("\n")
        
        # Return combined output
        return time_output + "\n" + wlac_output + "\n" + dbg_output

    @staticmethod
    def _parse_wlac_table(output: str) -> dict:
        """Parse the WLAC table and return a dictionary of WTP entries."""
        wtp_dict = {}
        lines = output.split('\n')
        
        # Find the header line
        header_idx = -1
        for i, line in enumerate(lines):
            if 'wtp_id' in line and 'rId' in line and 'oper_chan' in line:
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
            # Device IDs are typically alphanumeric with patterns like FP231K5N25039751
            if not wtp_id or not re.match(r'^[A-Z]{2}\w+', wtp_id):
                print(f"Skipping non-device row: {wtp_id}")
                continue
            
            # Create entry dictionary
            entry = {}
            for i, header in enumerate(headers):
                if i < len(fields):
                    entry[header] = fields[i]
            
            # Store with wtp_id as key
            wtp_dict[entry['wtp_id']] = entry
        
        return wtp_dict

    @staticmethod
    def _get_latest_channels(csv_file: Path) -> dict:
        """Get the latest channel for each wtp_id from the CSV file."""
        latest_channels = {}
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                # Build a dict of wtp_id -> latest (by capture_time)
                for row in rows:
                    wtp_id = row.get('wtp_id', '').strip()
                    oper_chan = row.get('oper_chan', '').strip()
                    
                    # Only include valid device entries
                    if wtp_id and oper_chan and re.match(r'^[A-Z]{2}\w+', wtp_id):
                        # Store/update latest for this wtp_id
                        latest_channels[wtp_id] = oper_chan
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
                
                # Write each WTP entry
                for wtp_id, data in wtp_dict.items():
                    row = {'capture_time': capture_time.strftime("%Y-%m-%d %H:%M:%S"), 'wtp_id': wtp_id}
                    row.update(data)
                    writer.writerow(row)
        except Exception as e:
            print(f"Error writing to CSV file: {e}")

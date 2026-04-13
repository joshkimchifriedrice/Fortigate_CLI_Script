# FGT CLI SCRIPT
Simple CLI to save Fortigate credentials and run diagnostic commands. See [fortigate_tool.py](fortigate_tool.py).

### **Save Credentials**
- **Command:** `python fortigate_tool.py creds save <profile>`
- **Description:** Runs an interactive prompt to enter `IP`, `Username`, and `Password`, validates the credentials, and saves them under the given profile name.

### **Run a Command (example: darrp)**
- **Command:** `python fortigate_tool.py run <profile> darrp -d 15 -f output.log`
- **Flags:** `-d` / `--delay` sets seconds to wait between the two WLAC captures (default 15). `-f` appends output to a file.
- **Order:** First save a profile, optionally run this command to test, then schedule if desired.

### **Schedule with Windows Task Scheduler**
- **Program/script:** set to your venv Python executable, for example: `C:\full\path\to\project\.venv\Scripts\python.exe`.
- **Add arguments:** `fortigate_tool.py run <profile> darrp -d 15 -f C:\path\to\logs\darrp.log` (replace `<profile>` with the saved profile name).
- **Start in (optional but recommended):** set to the working directory where `fortigate_tool.py` lives (example: `C:\Users\You\Desktop\Scripts\Fortigate_CLI_Script`).
- **Notes:** Save a profile first using the `creds save` step. Test the run command manually before scheduling. Ensure the account running the task can access the venv and working directory.

## **Quick Start And Scheduling**
- **1.** Save credentials: `python fortigate_tool.py creds save myprofile`
- **2.** Test run: `python fortigate_tool.py run myprofile darrp -d 15`
- **3.** Schedule: create a Task Scheduler task pointing to your venv `python.exe`, arguments `fortigate_tool.py run <profile> darrp` as above, and set "Start in" to the project folder like `C:\Users\josh\Desktop\Fortigate_CLI_Script\`.

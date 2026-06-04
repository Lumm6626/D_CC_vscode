"""Create Windows scheduled task for AllergyDailyReport at 10:30 AM daily."""
import subprocess
import sys

task_name = "AllergyDailyReport"
batch_path = r"D:\D_CC_vscode\agents\news\allergy-news-daily\run_allergy_daily.bat"

# Delete old task first (ignore error if not found)
subprocess.run(
    ["schtasks.exe", "/delete", "/tn", task_name, "/f"],
    capture_output=True,
)

# Create new task at 10:30 AM daily
result = subprocess.run(
    [
        "schtasks.exe", "/create",
        "/tn", task_name,
        "/tr", batch_path,
        "/sc", "daily",
        "/st", "10:30",
        "/f",
    ],
    capture_output=True,
    text=True,
)

print(result.stdout)
print(result.stderr, file=sys.stderr)
print(f"[Exit code: {result.returncode}]")

if result.returncode == 0:
    # Verify
    vrf = subprocess.run(
        ["schtasks.exe", "/query", "/tn", task_name],
        capture_output=True,
        text=True,
    )
    if vrf.returncode == 0:
        print("[OK] Task AllergyDailyReport created: daily at 10:30 AM")
    else:
        print("[WARN] Task creation returned 0 but query failed.")
else:
    print("[FAIL] Run as Administrator? Try: right-click create_task.bat -> run as Admin")

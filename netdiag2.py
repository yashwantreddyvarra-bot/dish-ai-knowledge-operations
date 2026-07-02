import subprocess

def ps(c):
    try:
        return subprocess.run(["powershell", "-NoProfile", "-Command", c],
                              capture_output=True, text=True, timeout=60).stdout
    except Exception as e:
        return "ERR %r" % e

out = []
out.append("=== ACTIVE NETWORK CATEGORY (Public blocks inbound) ===")
out.append(ps("Get-NetConnectionProfile | Select-Object Name,InterfaceAlias,IPv4Connectivity,NetworkCategory | Format-List | Out-String -Width 200"))

out.append("=== python.exe INBOUND rules: name | action | enabled | profile | program ===")
out.append(ps(
    "Get-NetFirewallApplicationFilter | Where-Object { $_.Program -like '*python*' } | "
    "ForEach-Object { $p=$_.Program; $_ | Get-NetFirewallRule | Where-Object { $_.Direction -eq 'Inbound' } | "
    "ForEach-Object { '{0} | {1} | {2} | {3} | {4}' -f $_.DisplayName,$_.Action,$_.Enabled,$_.Profile,$p } } | Out-String -Width 300"
))

out.append("=== ANY enabled inbound ALLOW rule on port 5000 ===")
out.append(ps(
    "Get-NetFirewallPortFilter | Where-Object { $_.LocalPort -eq 5000 -or $_.LocalPort -like '*5000-5020*' } | "
    "ForEach-Object { $_ | Get-NetFirewallRule } | Where-Object { $_.Direction -eq 'Inbound' } | "
    "Select-Object DisplayName,Action,Enabled,Profile | Format-Table -AutoSize | Out-String -Width 200"
))

with open(r"C:\Users\yashw\Desktop\dish_doc_automation\netdiag2.txt", "w", encoding="utf-8", errors="replace") as f:
    f.write("\n".join(out))
print("done")

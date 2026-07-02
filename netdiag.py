import subprocess, socket

def run(c):
    try:
        return subprocess.run(c, shell=True, capture_output=True, text=True, timeout=30).stdout
    except Exception as e:
        return "ERR %r" % e

out = []
out.append("HOSTNAME: " + socket.gethostname())
ipc = run('ipconfig')
out.append("IPv4 lines:\n" + "\n".join(l.strip() for l in ipc.splitlines() if "IPv4" in l))
ns = run('netstat -an')
out.append("\nPort 5000 listeners:\n" + "\n".join(l for l in ns.splitlines() if ":5000" in l))
out.append("\nFirewall state:\n" + run('netsh advfirewall show allprofiles state'))
out.append("\nInbound rules matching DISH/5000/python:\n" +
           run('netsh advfirewall firewall show rule name=all dir=in | findstr /i "DISH 5000 python"'))

with open(r"C:\Users\yashw\Desktop\dish_doc_automation\netdiag.txt", "w", encoding="utf-8", errors="replace") as f:
    f.write("\n".join(out))
print("done")

import pexpect
import crypt
import time
from subprocess import check_output
import os
import sys
from playsound import playsound
from send_mail import send_mail

password = "temp"
console_name = sys.argv[1]

try:
    # start the vm 
    p = pexpect.spawn(F"virsh start {console_name}")
    p.expect('started')
    time.sleep(30) # wait for console to come up
    p = pexpect.spawn(F"virsh console {console_name}") # bring up console
    p.logfile = open("logfile_run_and_test.txt", "wb")
    p.expect('.*]')
    p.sendline(" \r")
    p.expect('login: ', timeout=180)
    p.sendline('ahnaqvi')
    p.expect('Password: ', timeout=30)
    p.sendline(password)
    p.sendline('\r')
    p.expect('~.*', timeout=30) # console prompt

    # update and upgrade packages
    p.sendline("sudo su")
    choice = p.expect(['#.*', 'Password: '], timeout=30)
    if choice == 1:
        p.sendline(password + "\n") # if password required
        p.expect('#.*', timeout=300)
    p.sendline("apt --assume-yes update && apt --assume-yes upgrade") # upgrade takes too long.
    package_update_result = p.expect('#.*', timeout=600)


    # disable auto updates
    p.sendline("apt --assume-yes remove unattended-upgrades")
    auto_update_result = p.expect('#.*', timeout=300)


    # install ssh
    p.sendline("apt --assume-yes install openssh-server && dpkg -s openssh-server")
    # check if ssh server installs 
    ssh_server_install_result = p.expect('install ok installed', timeout=300)
    p.expect("#.*", timeout=30)


    # # Activate firewall, install if not there
    p.sendline("dpkg -s ufw")
    p.expect("#.*", timeout=30)
    if "install ok installed" not in p.before.decode():
        p.sendline("apt --assume-yes install ufw")
        p.expect("root@.*", timeout=30)

    # Allow ssh connections
    p.sendline("ufw allow ssh")
    firewall_ports_enabled_result = p.expect("root@.*", timeout=30)


    # check if ssh is up on port 22
    
    # run arp -n to get ip addr of vm, then ssh into it
    output = check_output(["arp", "-n"]).decode().split("\n")
    for i in output:
        if "virbr" in i:
            for j in i.split():
                if "." in j:
                    vm_ip_address = j
    if 'vm_ip_address' not in locals():
        ssh_connection_result = -1 # vm ip not found, failure
    else:
        p.sendline(F"ssh -o StrictHostKeyChecking=no ahnaqvi@{vm_ip_address}")
        p.expect("password.*")
        p.sendline(password)
        ssh_connection_result = p.expect("ahnaqvi@.*")
        p.sendline("exit")
        p.expect("root@.*")

    # set timezone to UTC and check it is set correctly
    # from here: https://unix.stackexchange.com/questions/110522/timezone-setting-in-linux
    p.sendline("unlink /etc/localtime && ln -s /usr/share/zoneinfo/UTC /etc/localtime && date")
    utc_result = p.expect("UTC 2.*", timeout=30) # check if date containes UTC
    p.expect("root@.*", timeout=30)

    # add new admin user
    newuser = "test_user"
    newpassword = "temp"
    hashed_password = crypt.crypt(newpassword, crypt.mksalt(crypt.METHOD_SHA512))

    # add user with home directory, temp passwd and default shell and check if user added
    p.sendline(F'''useradd -m -p {hashed_password} -s /bin/bash {newuser} && 
                usermod -aG sudo {newuser} &&
                su - {newuser} &&
                whoami''')
    useradd_result = p.expect(F"{newuser}", timeout=30)
    p.expect("root@.*", timeout=30)


    # check if user is sudo
    p.sendline("sudo whoami")
    choice = p.expect(["root", ":", pexpect.TIMEOUT])
    if choice == 0: # no sudo password required
        sudo_result = 0
    if choice == 1: # asks for sudo password
        p.sendline(newpassword)
        sudo_result = p.expect("root", timeout=30)
        p.expect("@", timeout=30) # 
    else:
        sudo_result = choice # timeout error
    
    
    # power off vm
    p.sendline("^]\n^C") # break out of virtual console
    p.close()
    os.system(F"virsh shutdown {console_name}")

except Exception as e: # don't pause execution. Instead, note the error in print commands below.
    print(e) # print exception, continue script


# check if all commands executed successfully
if 'ssh_server_install_result' not in locals() or ssh_server_install_result != 0:
    print("installing SSH server failed")
if  'utc_result' not in locals() or utc_result != 0:
    print("setting utc timezone failed")
if  'useradd_result' not in locals() or useradd_result != 0:
    print("useradd failed")
if  'sudo_result' not in locals() or sudo_result != 0:
    print("adding user to sudo failed")
if  'firewall_ports_enabled_result' not in locals() or firewall_ports_enabled_result != 0:
    if ssh_connection_result != 0:
        print("ssh connection failed")
if  'package_update_result' not in locals() or package_update_result != 0:
    print("System packages update failed")
if  'auto_update_result' not in locals() or auto_update_result != 0:
    print("auto update disable failed")

# notify

playsound("glass.ogg") # sound notification. Useful if background process
user = os.getenv("USER")
subject = F"VM {console_name} Test Run"
body = f'''
ssh_server_install_result = {ssh_server_install_result}
utc_result = {utc_result}
useradd_result = {useradd_result}
sudo_result = {sudo_result}
firewall_ports_enabled_result = {firewall_ports_enabled_result}
package_update_result = {package_update_result}
auto_update_result = {auto_update_result}
'''
receiver_smtp_server = "localhost"
sender = "no_reply@localhost"
receiver = [F'{user}@localhost']
dkim_path = "keys/dkim_private_key"
try:
    if len(sys.argv) > 2 and sys.argv[2] == '-e':
        send_mail(sender, receiver,
            receiver_smtp_server, dkim_path,
            subject, body)
except Exception as e:
    print(F"Message not sent. Exception: \n{e.message}\n")
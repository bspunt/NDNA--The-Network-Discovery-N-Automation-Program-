#!/usr/bin/env python
## 
## ------------------------------------------------------------------
##     NDNA: The Network Discovery N Automation Program
##     Copyright (C) 2017  Brett M Spunt, CCIE No. 12745 (US Copyright No. TXu 2-053-026)
## 
##     This file is part of NDNA.
##
##     NDNA is free software: you can redistribute it and/or modify
##     it under the terms of the GNU General Public License as published by
##     the Free Software Foundation, either version 3 of the License, or
##     (at your option) any later version.
## 
##     NDNA is distributed in the hope that it will be useful,
##     but WITHOUT ANY WARRANTY; without even the implied warranty of
##     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##     GNU General Public License for more details.
##
##     This program comes with ABSOLUTELY NO WARRANTY.
##     This is free software, and you are welcome to redistribute it
##
##     You should have received a copy of the GNU General Public License
##     along with NDNA.  If not, see <https://www.gnu.org/licenses/>.
## ------------------------------------------------------------------
## 

import MySQLdb as mdb
import paramiko
import threading
import datetime
import os.path
import subprocess
import time
import sys
import re

#Module for output coloring
from colorama import init, deinit, Fore, Style


# Start to write standard errors to log file
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("/usr/DCDP/logs/NXOS_INVENTORY.log", "w")

    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)  

    def flush(self):
        #this flush method is needed for python 3 compatibility.
        #this handles the flush command by doing nothing.
        #you might want to specify some extra behavior here.
        pass    


sys.stdout = Logger()
#sys.stdout = open('/usr/DCDP/logs/dcdp.log', 'w')
# for future use
# Current_time = time.ctime()
sys.stderr = open("/usr/DCDP/logs/NXOS_INVENTORY-ERR.log", 'w')
#Initialize colorama
init()

#Checking number of arguments passed into the script
if len(sys.argv) == 2:
    #ip_file = sys.argv[1]
    sql_file = sys.argv[1]
	
    print Fore.BLUE + Style.BRIGHT + "* Running NXOS Device Inventory script"

else:
    print Fore.RED + Style.BRIGHT + "\nIncorrect number of arguments (files) passed into the script."
    print Fore.RED + "Please try again.\n"
    sys.exit()

################################################
import getpass
print "   "
print "   "
username = raw_input( "Enter username: " )
print "   "
print "   "
print "______________________________________________" 
print "   "
print "   "
print "______________________________________________" 
print "   "
print "####    ////////// Password will be hidden ///////////"
print "#### Please copy and input your password from an unsaved text file, e.g. not written to disk, a or secure database like KeepPass"
print "   "
password = getpass.getpass()
print "   "
print "______________________________________________" 
print "   "
print "   "
################################################

#Checking SQL connection command file validity
def sql_is_valid():
    global sql_file
	
    while True:
        #Changing output messages
        if os.path.isfile(sql_file) == True:
            print "* Connection to MySQL has been validated..."
            print "* Database Errors will be logged to: " + Fore.YELLOW + "SQL_Error_Log.txt" + Fore.BLUE
            print "* You can view the DB inventory @ http://<your VM IP>/phpmyadmin/index.php\n"
            break
			
        else:
            print Fore.RED + "\n* File %s does not exist! Please check and try again!\n" % sql_file
            sys.exit()
 
try:
    #Calling MySQL file validity function
    sql_is_valid()
    
except KeyboardInterrupt:
    print Fore.RED + "\n\n* Program aborted by user. Exiting...\n"
    sys.exit()
    
    ############# Application #4 - Part #2 #############
	
check_sql = True

def sql_connection(command, values):
    global check_sql
    
    #Define SQL connection parameters
    selected_sql_file = open(sql_file, 'r')
    
    #Starting from the beginning of the file
    selected_sql_file.seek(0)

    sql_host = selected_sql_file.readlines()[0].split(',')[0]
    
    #Starting from the beginning of the file
    selected_sql_file.seek(0)
    
    sql_username = selected_sql_file.readlines()[0].split(',')[1]
    
    #Starting from the beginning of the file
    selected_sql_file.seek(0)
    
    sql_password = selected_sql_file.readlines()[0].split(',')[2]
    
    #Starting from the beginning of the file
    selected_sql_file.seek(0)
    
    sql_database = selected_sql_file.readlines()[0].split(',')[3].rstrip("\n")
    
    #Connecting and writing to database
    try:
        sql_conn = mdb.connect(sql_host, sql_username, sql_password, sql_database)
    
        cursor = sql_conn.cursor()
    
        cursor.execute("USE NXOS_INVENTORY")
        
        cursor.execute(command, values)
        
        #Commit changes
        sql_conn.commit()
        
    except mdb.Error, e:
        sql_log_file = open("SQL_Error_Log.txt", "a")
        
        #Print any SQL errors to the error log file
        print >>sql_log_file, str(datetime.datetime.now()) + ": Error %d: %s" % (e.args[0],e.args[1])
        
        #Closing sql log file:    
        sql_log_file.close()
        
        #Setting check_sql flag to False if any sql error occurs
        check_sql = False
                
    #Closing the sql file
    selected_sql_file.close()


#setup max number of threads for Semaphore method to use. create sema variable for open ssh function to use
maxthreads = 25
sema = threading.BoundedSemaphore(value=maxthreads)

#Open SSHv2 connection to devices
def open_network_connection(ip):
    global check_sql
    
    #Change exception message
    try:
        paramiko.util.log_to_file("/usr/DCDP/logs/paramiko.log")   
        #Define SSH parameters

        #Logging into device
        session = paramiko.SSHClient()
        
        #For testing purposes, this allows auto-accepting unknown host keys
        #Do not use in production! The default would be RejectPolicy
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        sema.acquire()
        time.sleep(20)
        sema.release()

        #Connect to the device using username and password          
        session.connect(ip, username = username, password = password)
        
        #Start an interactive shell session on the router
        connection = session.invoke_shell()	
        
        #Setting terminal length for entire output - disable pagination
        connection.send("terminal length 0\n")
        time.sleep(7)

        #Time length to deal with 37xx and 38xx switch stack bugs
        connection.send("show run | in switchname|hostname\n")
        time.sleep(7)

        selected_cisco_commands = '''show inventory&\
                                  dir&\
                                  sh ver | in version&\
                                  sh ver | in "cisco Nexus"&\
                                  sh ver | in image&\
                                  show ip int brief vrf management&\
                                  show ip int brief | include Eth|Fast|Giga|Te|Vlan&'''
                                                  
        #Splitting commands by the "&" character
        command_list = selected_cisco_commands.split("&")
        
        #Writing each line in the command string to the device
        for each_line in command_list:
            connection.send(each_line + '\n')
            time.sleep(10)

        
#############################################################
        # Get around the 64K bytes (65536). paramiko limitation
        interval = 0.1
        maxseconds = 15
        maxcount = maxseconds / interval
        bufsize = 65535

        input_idx = 0
        timeout_flag = False
        start = datetime.datetime.now()
        start_secs = time.mktime(start.timetuple())
#############################################################
        output = ''

        while True:
            if connection.recv_ready():
                data = connection.recv(bufsize).decode('ascii')
                output += data

            if connection.exit_status_ready():
                break

            now = datetime.datetime.now()
            now_secs = time.mktime(now.timetuple())

            et_secs = now_secs - start_secs
            if et_secs > maxseconds:
                timeout_flag = True
                break

            rbuffer = output.rstrip(' ')
            if len(rbuffer) > 0 and (rbuffer[-1] == '#' or rbuffer[-1] == '>'): ## got a Cisco command prompt
                break
            time.sleep(0.200)
        if connection.recv_ready():
            data = connection.recv(bufsize)
            output += data.decode('ascii')
#############################################################
        
        if re.search(r"% Invalid command", output):
            print Fore.RED + "* Inventory Information extracted from %s" % ip
        elif re.search(r"% Authorization failed", output):
            print "   "
            print "** Authorization failed for %s Looks Like a TACACS issue." % ip
        else:
            print Fore.RED + "* Inventory Information extracted from %s" % ip


        dev_nxos = re.search(r"System version: (.+)", output)
        nxos = dev_nxos.group(1)

        nxosdev_vendor = re.search(r"cisco (.+) .hassis", output)
        nxos_platform = nxosdev_vendor.group(1)

        nxosdev_image_name = re.search(r"file is: (.+)", output)
        nxosimage_name = nxosdev_image_name.group(1)

        local_hostname = re.search(r"name (.+)", output)
        hostname = local_hostname.group(1)

        serial_no_group = re.search(r"SN: (.+)", output)
        serial_no = serial_no_group.group(1)
        
        dev_flash = re.search(r"(.+ bytes total)", output)
        flash = dev_flash.group(1)

        Local_IPs = re.findall(r"Ethernet[0-9].+ ([1-9].+[0-9])", output)
        Local_IPs_var = ' | '.join(Local_IPs)

        Local_SVI_IPs = re.findall(r"Vlan[0-9].+ ([1-9].+[0-9])", output)
        Local_SVI_IPs_var = ' | '.join(Local_SVI_IPs)

        Local_mgmt_IPs = re.findall(r"mgmt0.+ ([1-9].+[0-9])", output)
        Local_mgmt_IPs_var = ' | '.join(Local_mgmt_IPs)

        #Insert/Update if exists all network devices data into the MySQL database table Cisco_NXOS_Inventory. Calling sql_connection function   
        sql_connection("REPLACE INTO Cisco_NXOS_Inventory(Hostname,Local_IPs,Local_SVI_IPs,Local_mgmt_IPs,NXOS_Platform,NXOS_Image,NXOSVersion,Flash,SerialNo) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)", (hostname, Local_IPs_var, Local_SVI_IPs_var, Local_mgmt_IPs_var, nxos_platform, nxosimage_name, nxos, flash, serial_no))
        #Closing the SSH connection
        session.close()
        
    except paramiko.AuthenticationException:
        pass
        print "   "
        print "* Authentication Error for %s ...." % ip

    except AttributeError:
        pass
        print Fore.RED + "* Could not pull in information from device %s* This is probably an NXOS device that is not yet supported for Certain Database Information import" % ip
        print Fore.RED + "* See Release notes, and if needed, please manually add any missing info to Diagram/s like serial no. code version, etc.\n"

ip_list = open('/usr/DCDP/good-IPs/NX-OS-IPs.txt').readlines()

#Creating threads
def create_threads():
    threads = []
    for ip in ip_list:
        th = threading.Thread(target = open_network_connection, args = (ip,))   #args is a tuple with a single element
        th.start()
        threads.append(th)
        
    for th in threads:
        th.join()

#Calling threads creation function
create_threads()

if check_sql == True:
    print "\n* Successfully Built NXOS Database Inventory, excluding Devices that reported issues (If any).\n* See /usr/DCDP/logs/NXOS_INVENTORY.log for Log File"
    print "* If there were any problem devices, please investigate manually before attempting to run the program again, e.g make sure the device is accessible!"

else:
    print Fore.RED + "\n* There was a problem exporting all the data to the Database.\n* Check the files, database and SQL_Error_Log.txt.\n"

#De-initialize colorama
deinit()

#End of program
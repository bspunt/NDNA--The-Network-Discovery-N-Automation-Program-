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


import paramiko
import time
import re
import sys
import threading
import datetime
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


# Start to write standard errors to log file
class Logger(object):
    def __init__(self):
        self.terminal = sys.stdout
        self.log = open("/usr/DCDP/logs/L2-L3-IOS-2nd-Auth.log", "w")

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

sys.stderr = open("/usr/DCDP/logs/L2-L3-IOS-ERR-2nd-Auth.log", 'w')

#setup max number of threads for Semaphore method to use. create sema variable for open ssh function to use
maxthreads = 25
sema = threading.BoundedSemaphore(value=maxthreads)

#Open SSHv2 connection to devices
def open_network_connection(ip):

    try:
        paramiko.util.log_to_file("/usr/DCDP/logs/paramiko.log")   
        #Define SSH parameters

        #Logging into device
        session = paramiko.SSHClient()
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        sema.acquire()
        time.sleep(20)
        sema.release()
        
        session.connect(ip, username = username, password = password)
        connection = session.invoke_shell()	
        connection.send("terminal length 0\n")
        time.sleep(4)
        connection.send("sh run | section router\n")
        time.sleep(32)
        connection.send("sh run | begin router\n")
        time.sleep(32)

        router_output = connection.recv(65535)
        
        if re.search(r"% Invalid input detected at", router_output):
            print "\nCompleted IOS device %s" % ip
            return router_output
        elif re.search(r"% Authorization failed", router_output):
            print "   "
            print "** Authorization failed for %s Looks Like a TACACS issue." % ip
            print "** Try and run the program again."
        else:
            print "\nCompleted IOS device %s" % ip
            return router_output

        session.close()
     
    except paramiko.AuthenticationException:
        pass
        print "   "
        print "* 2nd Authentication Error for %s .....Transient network conditions are preventing connection." % ip
        print "* Wait 15 minutes and run the Whole Program Again...L2-L3 lists must be accurate..Hit CRTL Z to Abort."
        #print "* Closing program...\n"
    except paramiko.SSHException:
        pass
        print "   "
        print "* Incompatible SSH version. Paramiko requires compatible SSH and kex on device %s" % ip

iplist = open('/usr/DCDP/tmp/L2-L3-IOS_auth_error_iplist.txt').readlines()
# remove return from file names, e.g. remove \n from list
iplist = map(lambda s: s.strip(), iplist)

#Creating threads function
def write_files(ip):
    file_name = '/usr/DCDP/configs/' + ip + '_IOS_' + '.txt'
    fo = open(file_name, "w")
    #Calling the SSH function
    router_output = open_network_connection(ip)
    fo.write(router_output)
    fo.close()
    
#Creating threads function
def create_threads():
    threads = []
    for ip in iplist:
        th = threading.Thread(target = write_files, args = (ip,))   #args is a tuple with a single element     
        th.start()
        threads.append(th)
        
    for th in threads:
        th.join()

#Calling threads creation function which then calls the open ssh function
create_threads()
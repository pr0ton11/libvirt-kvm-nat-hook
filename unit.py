###
### Libvirt KVM dynamic nat port forwarding
### (V) 0.1-poc, (C) 2019 Marc Singer
###

import argparse
import sys
import libvirt

# Argument parser
arg = argparse.ArgumentParser(description='Parsing dynamic kvm port forwarding rules')
arg.add_argument('--udp', help='Only parse UDP rules from unit', action='store_false')
arg.add_argument('--tcp', help='Only parse TCP rules from unit', action='store_false')
arg.add_argument('vm', help='Name (libvirt) of the vm to forward ports to') 
args = arg.parse_args()

# At least one protocol should be selected
if (args.udp or args.tcp ) and not (args.tcp and args.udp):
    vmIPAddress=
else:
    print("Invalid protocoll selection. Please use --tcp or --udp")
    exit(1)

def lookupVMIPAdress(vm, index=0):
    # Get a connection object to Libvirt
    con = libvirt.open('qemu:///system')
    # Check if connection is established
    if con == None:
        print("Error: No connection to libvirt")
        exit(1)
    # Get domain as object
    dom = con.lookupByName(vm)
    # Check if domain exists
    if dom == None:
        print("Error: Domain with name " + vm + " does not exist !")
        exit(1)
    # Look up IPv4 Address of first interface and return result
    ifaces = dom.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)
    # Increment to loop trough interfaces
    i = 0
    for (name, val) in ifaces.iteritems():
        if(i == index):
            if val['addrs']:
                for ipaddr in val['addrs']:
                    # Check if the address is IPV4
                    if ipaddr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        # Set IP Address to correct object
                        ip = ipaddr['addr']
                        # Close connection
                        con.close()
                        # Return IP
                        return ip
        # Increment I
        i++
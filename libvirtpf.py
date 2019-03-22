###
### Libvirt KVM dynamic nat port forwarding
### (V) 0.1-poc, (C) 2019 Marc Singer
###

import sys
import os
import libvirt
import json
from xml.dom import minidom

class VM:

    ###
    ### Constructor of VM
    ###
    def __init__(self, name):
        self.name = name
        self.tcp = self.getRules('tcp')
        self.udp = self.getRules('udp')
        self.ip = self.queryIPAddress()
        self.bridge = self.queryNetworkBridge()


    ###
    ### Loads a list of forwarded ports from file
    ###
    def getRules(self, protocol):
        # Open file and read input
        inputfile = open ('./unit/' + self.name + '.vm.json')
        # Parse input as json
        input = json.load(inputfile)
        for element in input:        
            if (protocol == 'tcp'):
                return element.tcp
            if (protocol == 'udp'):
                return element.udp
        # Return none if nothing is in the list
        return None
    ###
    ### Connects to libvirt and recieves an IP address of the vm
    ###
    def queryIPAddress(self):
        # Connect to libvirt
        con = libvirt.open('qemu:///system')
        if (con == None):
            raise Exception('Connection to libvirt failed')
        # Get current domain as object
        dom = con.lookupByName(self.name)
        if (dom == None):
            raise Exception('VM ' + self.name + ' does not exist')
        # Libvirt specific code to get IP Address
        ifaces = dom.interfaceAddresses(libvirt.VIR_DOMAIN_INTERFACE_ADDRESSES_SRC_AGENT, 0)
        for (name, val) in ifaces.iteritems():
            if val['addrs']:
                for ipaddr in val['addrs']:
                    if ipaddr['type'] == libvirt.VIR_IP_ADDR_TYPE_IPV4:
                        return ipaddr['addr']
        # If we did not found any interface throw Exception
        raise Exception('VM ' + self.name + ' does not have any valid network addresses')
    
    ###
    ### Connects to libvirt and recieves a network that a vm is connected to
    ###
    def queryNetworkBridge(self):
         # Connect to libvirt
        con = libvirt.open('qemu:///system')
        if (con == None):
            raise Exception('Connection to libvirt failed')
        # Get current domain as object
        dom = con.lookupByName(self.name)
        if (dom == None):
            raise Exception('VM ' + self.name + ' does not exist')
        # Libvirt specific code to get bridge interface
        raw_xml = dom.XMLDesc(0)
        xml = minidom.parseString(raw_xml)
        interfaceTypes = xml.getElementsByTagName('interface')
        for interfaceType in interfaceTypes:
            if (interfaceType.getAttribute('type') == 'network'):
                interfaceNodes = interfaceType.childNodes
                for interfaceNode in interfaceNodes:
                    if (interfaceNode.nodeName[0:1] != '#'):
                        if (interfaceNode.nodeName == 'source'):
                            for attr in interfaceNode.attributes.keys():
                                if (interfaceNode.attributes[attr].name == 'network'):
                                    return interfaceNode.attributes[attr].value
        raise Exception('Could not retrieve vm ' + self.name + ' source bridge name')
    
    ###
    ### Generate rules for this vm to stop
    ###
    def genStopIPTableRules(self):
        rules = []
        rules.append("iptables -D FORWARD -o " + self.bridge + " -d " + self.ip + " -j ACCEPT")
        for port in self.tcp:
            rules.append("iptables -t nat -D PREROUTING -p tcp --dport " + port + " -j DNAT --to " + self.ip + ":" + port)
        for port in self.udp:
            rules.append("iptables -t nat -D PREROUTING -p udp --dport " + port + " -j DNAT --to " + self.ip + ":" + port)
        return rules
    
    ###
    ### Generate rules for this vm to start
    ###
    def genStartIPTableRules(self):
        rules = []
        rules.append("iptables -I FORWARD -o " + self.bridge + " -d " + self.ip + " -j ACCEPT")
        for port in self.tcp:
            rules.append("iptables -t nat -I PREROUTING -p tcp --dport " + port + " -j DNAT --to " + self.ip + ":" + port)
        for port in self.udp:
            rules.append("iptables -t nat -I PREROUTING -p udp --dport " + port + " -j DNAT --to " + self.ip + ":" + port)
        return rules

    ###
    ### Embed rules in KVM Hook script
    ###
    def embedRules(self):
        script = []
        script.append("# Start of rules generated for " + self.name)
        script.append("if [ \"${1}\" = \"" + self.name + "\" ]; then")
        # Stop or reconnect rules
        script.append("if [ \"${2}\" = \"stopped\" ] || [ \"${2}\" = \"reconnect\" ]; then")
        for rule in self.genStopIPTableRules():
            script.append(rule)
        script.append("fi")
        script.append("if [ \"${2}\" = \"start\" ] || [ \"${2}\" = \"reconnect\" ]; then")
        for rule in self.genStartIPTableRules():
            script.append(rule)
        script.append("fi")
        # Exit if statement
        script.append("fi")
        script.append("# End of rules generated for " + self.name)

# List all files from subfolder unit
units = os.listdir('./unit')
for filename in units:
    # Check if filename is valid
    if (filename.endswith('.vm.json')):
        # Remove filename from vm name and create a new object
        currentUnit = VM(filename.replace('.vm.json',''))
        # Generate rules for this vm
        currentUnitRules = currentUnit.embedRules()
        print(currentUnitRules)

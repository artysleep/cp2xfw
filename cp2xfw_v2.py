import ipaddress
from operator import ne
from sys import argv
from turtle import end_fill
from needed_func import mask_transformation, enum, net_counting, ip_to_bits, bits_to_ip
import textfsm
import re
from pprint import pprint
from ipaddress import IPV4LENGTH, IPv4Address, IPv4Interface, IPv4Network

#inet ifconfig bond1 vlan add 25

def file_read(file):
    #with open(argv[1], 'r') as cfg:
    result = []
    with open(file, 'r') as cfg:
        for line in cfg:
            result.append(line.rstrip())
    return result


#regex = r"add interface (?P<intf>[bond]{4}\d) vlan (?P<vlan>\d+)"
#regex = r"add interface eth(?P<intf>\d) vlan (?P<vlan>\d+)"

def get_intfs_addr(cfg):
    intfs_addr = {}
    regex = (
        r"set interface (?P<intf>[bond]{4}(\d|\d\.\d+))"
        r" ipv4-address (?P<ip>(\d{1,3}\.){3}\d{1,3})"
        r" mask-length (?P<mask>[0-9]{2})"
        )
    for line in cfg:
        match = re.search(regex, line)
        if match:
            ip = match.group("ip")
            cidr = match.group("mask")
            net = ip+"/"+cidr
            intfs_addr.update({match.group("intf") : (ip, str(IPv4Interface(net).netmask), cidr)})
    regex = (
        r"set interface eth(?P<intf>(\d|\d\.\d+))"
        r" ipv4-address (?P<ip>(\d{1,3}\.){3}\d{1,3})"
        r" mask-length (?P<mask>[0-9]{2})"
        )
    for line in cfg:
        match = re.search(regex, line)
        if match:
            ip = match.group("ip")
            cidr = match.group("mask")
            intfs_addr.update({"eth"+str(int(match.group("intf"))-1) : (ip, str(IPv4Interface(net).netmask), cidr)})
    return intfs_addr

def get_up_intfs(cfg):
    intfs_up = []
    regex = r'set interface (?P<intf>[bond]*\d) state on'
    for line in cfg:
        match = re.search(regex, line)
        if match:
            intfs_up.append(match.group("intf"))
    regex = r'set interface eth(?P<intf>\d) state on'
    for line in cfg:
        match = re.search(regex, line)
        if match:
            intfs_up.append("eth" + str(int(match.group("intf"))-1))
    return set(intfs_up)

def get_bonds_intfs(cfg):
    bonds = {}
    tmplst = []
    chk = ""
    regex = r"^add bonding group (?P<bond>\d) interface eth(?P<intf>\d)"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            if match.group("bond") != chk:
                tmplst = []
                tmplst.append(str(int(match.group("intf"))-1))
                bonds.update({match.group("bond") : tmplst})
                chk = match.group("bond")
            else:
                tmplst.append(str(int(match.group("intf"))-1))
                bonds.update({match.group("bond") : tmplst})
    return bonds
    
def output_form(bonds, intfs_up, intfs_addr):
    intf_state = {}
    cmds_out = []
    
    cmds_out.append("\n"*5 + "#"*10 + "INTERFACES" + "#"*10)

    for value in bonds.values():
        for intf in value:
            cmds_out.append(f"inet ifconfig eth{intf} class slave")
            

    for key in bonds.keys():
        cmds_out.append(f'inet bonding add {key} mode 802.3ad slaves eth{" eth".join(bonds[key])}')
        cmds_out.append(f"inet ifconfig bond{key} bonding xmit-hash-policy layer3+4")
    
    for intf in sorted(intfs_up):
        cmds_out.append(f"inet ifconfig {intf} up")
        intf_state.update({intf : {"state":"up"}})

    cmds_out.append("\n"*5 + "#"*10 + "ADDRESSES" + "#"*10)

    for intf in intfs_addr.keys():
        cmds_out.append(f"inet ifconfig {intf} address {' mask '.join(intfs_addr[intf][:2])}")
    #pprint (intf_state)
    #pprint (bonds)
    #pprint(intfs_addr)

    #inet ifcondig bond1 class trunk
    # iplir_template = "[adapter]\n"\
    #                 "name= {}\n"\
    #                 "allowtraffic= on\n"\
    #                 "type= internal\n"\
    #                 "\n"
    
    
    
    
    cmds_out.append("\n"*5 + "#"*10 + "OSPF" + "#"*10)

    cmds_out.append("inet ospf mode on")     
    for net in intfs_addr.values():
        host_addr = net[0] + "/" + net[2]
        cmds_out.append(f"inet ospf network add {IPv4Interface(host_addr).network[0]} netmask {net[1]} area 22")
    cmds_out.append("firewall local add rule src <IP-адрес OSPF-маршрутизатора> dst @local service @OSPF pass")
    cmds_out.append("firewall local add rule src <IP-адрес OSPF-маршрутизатора> dst @multicast service @OSPF pass")
    cmds_out.append("firewall local add rule src @local dst @any service @OSPF pass")

    cmds_out.append("\n"*5 + "#"*10 + "DEFAULTS RULES" + "#"*10)
    
    cmds_out.append("firewall ip-object add name @ADMINS_OIB 10.9.25.64/28")
    cmds_out.append("firewall local add src @ADMINS_OIB dst @local pass")
    cmds_out.append("firewall local add src @any dst @local udp dport 55777 pass")
    cmds_out.append("firewall local add src @local dst @any udp dport 55777 pass")
    cmds_out.append("firewall forward add src @any dst @any udp dport 55777 pass")

    cmds_out.append("\n"*5 + "#"*10 + "IPLIR.INI" + "#"*10)
    
    for intf in intfs_addr.keys():
        cmds_out.append("[adapter]")
        cmds_out.append(f"name= {intf}")
        cmds_out.append("allowtraffic= on")
        cmds_out.append("type= internal")
        cmds_out.append("")

    cmds_out.append("\n"*5 + "#"*10 + "FAILOVER.INI" + "#"*10)
    
    for intf,net in intfs_addr.items():
        #print(intf, IPv4Address(net[0]), net[2])
        host_addr = net[0] + "/" + net[2]
        #print(IPv4Interface(host_addr).network[1])
        cmds_out.append("[channel]")
        cmds_out.append(f"device = {intf}")
        cmds_out.append(f"activeip = {IPv4Interface(host_addr).network[1]} - check")
        cmds_out.append(f"passiveip = {IPv4Address(net[0])}")
        cmds_out.append("testip = 127.0.0.1")
        cmds_out.append(f"ident = iface-{intf.replace('.','-')}")
        cmds_out.append("checkonlyidle = yes")     
        cmds_out.append("")

    return cmds_out

if __name__ == "__main__":
    file = file_read('var-ispdn-n2.txt')
    cmds_out = []
    cmds_out = (output_form(get_bonds_intfs(file), get_up_intfs(file), get_intfs_addr(file)))
    #pprint(get_intfs_addr(file))
    pprint(cmds_out)
    cmds_out =map(lambda x: x + '\n', cmds_out)
    with open("converted.txt", 'w') as output:
        output.writelines(cmds_out)
    
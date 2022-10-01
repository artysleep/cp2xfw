import cmd
import ipaddress
from sys import argv

from pyparsing import Regex
from needed_func import mask_transformation, enum, net_counting, ip_to_bits, bits_to_ip
import textfsm
import re
from pprint import pprint
from ipaddress import IPV4LENGTH, IPv4Address, IPv4Interface, IPv4Network

#inet ifconfig bond1 vlan add 25

def file_read(file):
    #with open(argv[1], 'r') as cfg:
    raw_list, result = [], []
    with open(file, 'r') as cfg:
        for line in cfg:
            raw_list.append(line.rstrip())
    for line in raw_list:
        if "External" in line:
                line = line.replace("External", "eth0")
                result.append(line)
        elif "Internal" in line:
                line = line.replace("Internal", "eth1")
                result.append(line)
        elif "DMZ" in line:
                line = line.replace("DMZ", "eth2")
                result.append(line)
        elif "Sync" in line:
                line = line.replace("Sync", "eth6")
                result.append(line)
        elif "Lan1" in line:
                line = line.replace("DMZ", "eth3")
                result.append(line)
        elif "Lan2" in line:
                line = line.replace("Sync", "eth4")
                result.append(line)
        elif "Lan3" in line:
                line = line.replace("Sync", "eth5")
                result.append(line)
        elif "Mgmt" in line:
                line = line.replace("Sync", "eth5")
                result.append(line)
        else:
            result.append(line)
    pprint(result)
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
            intfs_addr.update({match.group("intf") : [ip, mask_transformation(cidr), cidr]})
    regex = (
        r"set interface (?P<intf>\w{3,8}(|\d)(|\.)\d{0,3})" 
        r" ipv4-address (?P<ip>(\d{1,3}\.){3}\d{1,3})"
        r" mask-length (?P<mask>[0-9]{2})"
        )
    for line in cfg:
        match = re.search(regex, line)
        if match:
            ip = match.group("ip")
            cidr = match.group("mask")
            intfs_addr.update({match.group("intf") : [ip, mask_transformation(cidr), cidr]})
            
    return intfs_addr

def get_up_intfs(cfg):
    intfs_up = []
    regex = r'set interface (?P<intf>[bond]*\d) state on'
    for line in cfg:
        match = re.search(regex, line)
        if match:
            intfs_up.append(match.group("intf"))
    #regex = r'set interface eth(?P<intf>\d) state on'
    regex = r"set interface (?P<intf>\w{3,8}(|\d)) state on"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            intfs_up.append(match.group("intf"))
    #print(set(intfs_up))
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


def get_dhcp_relay(cfg):
    dhcp_rel = []
    dhcp_rel_d = {}
    regex = r"set bootp interface (?P<intf>\S+) relay-to (?P<ip>(\d{1,3}\.){3}\d{1,3})"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            intf = match.group("intf")
            ip = match.group("ip")
            dhcp_rel_d[intf] = ip
            dhcp_rel.append(dhcp_rel_d)
            dhcp_rel_d = {}
    return dhcp_rel
        
def get_router_id(cfg):
    regex = r"set router-id (?P<ip>(\d{1,3}\.){3}\d{1,3})"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            router_id = match.group("ip")
    return router_id

def get_intf_vlans(cfg):
    intf_vlan = []
    regex = r"add interface (?P<intf>\S+) vlan (?P<vlan>\d+)"
    for line in cfg:
        match = re.search(regex, line)
        if match:
           intf_vlan.append({match.group("intf") : match.group("vlan")})
    #print(intf_vlan)
    return intf_vlan

def get_ntp(cfg):
    ntp_lst = []
    regex = r"set ntp server \S+ (?P<ntp>(\d{1,3}\.){3}\d{1,3})"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            ntp_lst.append(match.group("ntp"))
    #print(ntp_lst)
    return ntp_lst

def get_static_routes(cfg):
    regex = (r"set static-route (?P<net>(\d{1,3}\.){3}\d{1,3})\/(?P<bitmask>(\d\d)) nexthop gateway address (?P<nhop>(\d{1,3}\.){3}\d{1,3})")
    static_routes = []
    for line in cfg:
        match = re.search(regex, line)
        if match:
            #print(match.group("net"), match.group("bitmask"), match.group("nhop"))
            static_routes.append((match.group("net"), match.group("bitmask"), match.group("nhop")))
    #print(static_routes)
    return(static_routes)

def get_def_nexthop(cfg):
    regex = r"set static-route default nexthop gateway address (?P<nexthop>(\d{1,3}\.){3}\d{1,3})"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            #print(match.group("nexthop"))
            return(match.group("nexthop"))

def get_cluster_addr(cfg):
    cl_addrs = {}
    regex = r"(?P<intf>\S+)\s+(?P<ip>(\d{1,3}\.){3}\d{1,3})"
    for line in cfg:
        match = re.search(regex, line)
        if match:
            #print(match.group("intf"), match.group("ip"))
            cl_addrs.update({match.group("intf"): match.group("ip")})
    return cl_addrs
    
def output_form(ckp_name, bonds, intfs_up, 
                intfs_addr, dhcp_rel, router_id, 
                intf_vlan, ntp_lst, def_nh, 
                static_routes):
    intf_state = {}
    cmds_out = []
    cmds_out.append("#"*30+"\n")
    cmds_out.append(f"This is Check Point {ckp_name} converted config to HW5.1 Cluster\n")
    cmds_out.append("Use it this output with caution! / Используйте, внимательно перепроверяя всё! \n")
    cmds_out.append("Don`t forget to change Vlan 106 to 166 (with addresses) in topics INTERFACES, OSPF, IPLIR, FAILOVER")
    cmds_out.append("#"*30)
    cmds_out.append("machine hosts add 11.0.0.2 prime-kszi.corp.it.ltg.gazprom.ru")
    cmds_out.append("machine hosts add 11.0.0.2 vpn-kszi.corp.it.ltg.gazprom.ru")
    cmds_out.append("\n"*2+ "#"*10 + "INTERFACES" + "#"*10)

    for value in bonds.values():
        for intf in value:
            cmds_out.append(f"inet ifconfig eth{intf} class slave")
            

    for key in bonds.keys():
        cmds_out.append(f'inet bonding add {key} mode 802.3ad slaves eth{" eth".join(bonds[key])}')
        cmds_out.append(f"inet ifconfig bond{key} bonding xmit-hash-policy layer3+4")
    
    for intf in sorted(intfs_up):
        cmds_out.append(f"inet ifconfig {intf} up")
        intf_state.update({intf : {"state":"up"}})
    
    #inet class trunk
    if intf_vlan:
        for item in intf_vlan:
            for int,vlan in item.items():
                if f"inet ifconfig {int} class trunk" not in cmds_out:
                    cmds_out.append(f"inet ifconfig {int} class trunk")
                    #print(f"inet ifconfig {int} class trunk")
                cmds_out.append(f"inet ifconfig {int} vlan add {vlan}")
                #print(f"inet ifconfig {int} vlan add {vlan}")

    #inet ifconfig
    cmds_out.append("\n"*2+ "#"*10 + "ADDRESSES" + "#"*10)


    # for intf in intfs_addr.keys():
    #     for cl_intf in cl_addrs.keys():
    #         if intf == cl_intf:
    #             #print (intf, cl_intf)
    #             intfs_addr[intf][0] = cl_addrs[cl_intf]
    


    for intf in intfs_addr.keys():
        cmds_out.append(f"inet ifconfig {intf} address {' netmask '.join(intfs_addr[intf][:2])}")
    #pprint (intf_state)
    #pprint (bonds)
    #pprint(intfs_addr)

    #inet ifcondig bond1 class trunk
    # iplir_template = "[adapter]\n"\
    #                 "name= {}\n"\
    #                 "allowtraffic= on\n"\
    #                 "type= internal\n"\
    #                 "\n"
    
    #default route
    cmds_out.append(f"inet route add default next-hop {def_nh}")

    for route in static_routes:
        cmds_out.append(f"inet route add {route[0]} netmask {mask_transformation(route[1])} nexthop {route[2]}")

    #inet ospf
    cmds_out.append("\n"*2+ "#"*10 + "OSPF" + "#"*10)
    cmds_out.append("inet ospf mode on")
    cmds_out.append("inet ospf redistribute add static")
    cmds_out.append(f"inet ospf router-id {router_id}")     
    for net in intfs_addr.values():
        if net[2] != "30":
            host_addr = net[0] + "/" + net[2]
            cmds_out.append(f"inet ospf network add {IPv4Interface(host_addr).network[0]} netmask {net[1]} area 22")
    
    #firewall basic rules
    cmds_out.append("\n"*2+ "#"*10 + "DEFAULTS RULES" + "#"*10)
    cmds_out.append("firewall ip-object add name @ADMINS_OIB 10.9.25.64/28, 10.9.17.98")
    cmds_out.append("firewall ip-object add name @DUDE 10.9.25.86")
    cmds_out.append("firewall ip-object add name @PRIME 10.9.25.13")
    cmds_out.append("firewall ip-object add name @NVS 10.9.25.15")
    cmds_out.append("firewall local add 1 rule \"OSPF any2local\" src @any dst @local service @OSPF pass")
    cmds_out.append("firewall local add 2 rule \"OSPF local2lmcast\" src @local dst @multicast service @OSPF pass")
    cmds_out.append("firewall local add 3 rule \"OSPF local2any\" src @local dst @any service @OSPF pass")
    cmds_out.append("firewall local add 4 rule \"ADMINS_OIB access\" src @ADMINS_OIB dst @local pass")
    # cmds_out.append("firewall local add 5 rule \"ADMINS_OIB access\" src @any dst @local udp dport 55777 pass")
    # cmds_out.append("firewall local add 6 rule \"ViPNet 55777 local2any\" src @local dst @any udp dport 55777 pass")
    cmds_out.append("firewall local add 5 rule \"DUDE SNMP\" src @DUDE dst @local udp dport 161 pass")
    cmds_out.append("firewall local add 6 rule \"DUDE ICMP\" src @DUDE dst @local icmp pass")
    cmds_out.append("firewall local add 7 rule \"PRIME\" src @PRIME dst @local pass")
    cmds_out.append("firewall local add 8 rule \"NVS\" src @NVS dst @local pass")
    # cmds_out.append("firewall forward add 1 rule \"ViPNet 55777 forward\" src @any dst @any udp dport 55777 pass")
    # cmds_out.append("firewall vpn add 1 rule \"OSPF vpn\" src @any dst @any service @OSPF pass")

    #inet snmp 
    cmds_out.append("\n"*2+ "#"*10 + "NVS SNMP" + "#"*10)
    cmds_out.append("inet snmp user add snmpuser md5")
    cmds_out.append("#### YOU NEED TO TYPE PASS HERE TWICE###")
    cmds_out.append("inet snmp user set snmpuser key")
    cmds_out.append("#### AND  HERE TOO###")
    cmds_out.append("inet snmp user set snmpuser trapsess add 10.9.25.15")
    cmds_out.append("inet snmp user set snmpuser trapsess on")
    cmds_out.append("inet snmp v3 ro on")
    cmds_out.append("inet snmp v3 traps on")
    cmds_out.append("inet snmp autostart on")
    cmds_out.append("inet snmp start")
    cmds_out.append("\n"*2+ "#"*10 + "DHCP-Relay" + "#"*10)


    #inet dhcp relay
    intfs_nets = {}
    for intf, net in intfs_addr.items():
        intfs_nets[intf] = IPv4Network(f"{net_counting(net[0],net[2])}/{net[2]}")

    iter = 1
    chk = ""
    for item in dhcp_rel:
        for key,value in item.items():
            #print(net_counting(value))
            if key != chk:
                for intf,net in intfs_nets.items():
                    if IPv4Address(value) in net.hosts():
                        cmds_out.append(f"inet dhcp relay {iter} add listen-interface {key}")
                        #pprint(f"inet dhcp relay {iter} add listen-interface {key}")
                        cmds_out.append(f"inet dhcp relay {iter} add external-interface {intf} server {value}")
                        #pprint (f"inet dhcp relay {iter} add external-interface {intf} server {value}")     
                chk = key
                 
            else:
                for intf,net in intfs_nets.items():
                    if IPv4Address(value) in net.hosts():
                        cmds_out.append(f"inet dhcp relay {iter} add backup-interface {intf} server {value}")
                        #pprint (f"inet dhcp relay {iter} add backup-interface {intf} server {value}")
                        cmds_out.append(f"inet dhcp relay {iter} mode on")
                        cmds_out.append(f"inet dhcp relay {iter} start")
                iter+=1 
   
    #inet ntp mode
    cmds_out.append("\n"*2+ "#"*10 + "NTP" + "#"*10)
    for item in ntp_lst:
        cmds_out.append(f"inet ntp add server {item}") 
    cmds_out.append("inet ntp mode on")
    cmds_out.append("inet ntp start")

    #IPLIR.INI
    cmds_out.append("\n"*2+ "#"*10 + "IPLIR.INI" + "#"*10)
    
    for intf in intfs_addr.keys():
        cmds_out.append("[adapter]")
        cmds_out.append(f"name= {intf}")
        cmds_out.append("allowtraffic= on")
        cmds_out.append("type= internal")
        cmds_out.append("")

    cmds_out.append("\n"*2+ "#"*10 + "FAILOVER.INI" + "#"*10)
    
    for intf,net in intfs_addr.items():
        if net[2] != "30":
            #print(intf, IPv4Address(net[0]), net[2])
            host_addr = net[0] + "/" + net[2]
            #print(IPv4Interface(host_addr).network[1])
            cmds_out.append("[channel]")
            cmds_out.append(f"device = {intf}")
            cmds_out.append(f"activeip = {net[0]}/{net[2]}")
            #cmds_out.append(f"activeip = {IPv4Interface(host_addr).network[1]}/{net[2]} - check") #this is just for xfw
            #cmds_out.append(f"passiveip = {IPv4Address(net[0])}/{net[2]}") #this is just for xfw
            cmds_out.append("testip = 127.0.0.1")
            cmds_out.append(f"ident = iface-{intf.replace('.','-')}")
            cmds_out.append("checkonlyidle = yes")     
            cmds_out.append("")
        else: 
            cmds_out.append("################### FOR N1 ###################")
            cmds_out.append("[sendconfig]")
            cmds_out.append(f"device = {intf}")
            cmds_out.append(f"activeip = {IPv4Address(net[0])+1}")
            cmds_out.append("################### FOR N2 ###################")
            cmds_out.append("[sendconfig]")
            cmds_out.append(f"device = {intf}")
            cmds_out.append(f"activeip = {IPv4Address(net[0])}")


    return cmds_out

if __name__ == "__main__":
    #input_file = argv[1]
    #input_file2 = argv[2]
    input_file = "vld nov\\vld-bt-fw.txt"
    # input_file2 = "nov-fw-cphaprob.txt"
    file = file_read(input_file)
    #cl_addr_file = file_read(input_file2)
    input_file = input_file.strip(".\\").split(".")[0]
    #cmds_out = [f"This is Check Point {input_file} converted config\n", "Use it this output with caution!\n"]
    cmds_out = output_form(input_file, 
                            get_bonds_intfs(file), 
                            get_up_intfs(file), 
                            get_intfs_addr(file), 
                            get_dhcp_relay(file), 
                            get_router_id(file), 
                            get_intf_vlans(file), 
                            get_ntp(file), 
                            get_def_nexthop(file),
                            get_static_routes(file))
                            #,get_cluster_addr(cl_addr_file))
    #pprint(get_dhcp_relay(file))
    #pprint(get_intfs_addr(file))
    #pprint(cmds_out)
    #pprint(get_intf_vlans(file))
    #pprint(get_def_nexthop(file))
    cmds_out =map(lambda x: x + '\n', cmds_out)
    #output_filename = argv[1].strip(".\\").split(".")[0] + "_converted.txt"
    output_filename = input_file + "_converted.txt"
    with open(output_filename, 'w') as output:
        output.writelines(cmds_out)
    
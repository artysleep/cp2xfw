from sys import argv

def mask_transformation(mask):
    mask = int(mask)
    bin_mask = "1" * mask + "0" * (32 - mask)
    m1, m2, m3, m4 = [
        int(bin_mask[0:8], 2),
        int(bin_mask[8:16], 2),
        int(bin_mask[16:24], 2),
        int(bin_mask[24:32], 2),    
    ]
    mask = f"{m1}.{m2}.{m3}.{m4}"
    return mask

def net_counting(ip , mask):
    ipl = ip.split(".")
    ipbit="{:08b}".format(int(ipl[0]))+"{:08b}".format(int(ipl[1]))+"{:08b}".format(int(ipl[2]))+"{:08b}".format(int(ipl[3]))
    netipbit=ipbit[0:int(mask)]+"0"*(32-int(mask))
    maskbit="1"*int(mask)+"0"*(32-int(mask))
    n1, n2, n3, n4 = [
        int(netipbit[0:8],2),
        int(netipbit[8:16],2),
        int(netipbit[16:24],2),
        int(netipbit[24:32],2)
    ]
    netip = f"{n1}.{n2}.{n3}.{n4}"
    #print (f"{ip}/{mask}")
    #print (f"{netip}/{mask}")
    #print (f"{n1:08b}{n2:08b}{n3:08b}{n4:08b}")
    return netip

def ip_to_bits(ip):
    ipl = ip.split(".")
    ipbit="{:08b}".format(int(ipl[0]))+"{:08b}".format(int(ipl[1]))+"{:08b}".format(int(ipl[2]))+"{:08b}".format(int(ipl[3]))
    return ipbit

def bits_to_ip(ipbit):
    n1, n2, n3, n4 = [
        int(ipbit[0:8],2),
        int(ipbit[8:16],2),
        int(ipbit[16:24],2),
        int(ipbit[24:32],2)
    ]

    ip = f"{n1}.{n2}.{n3}.{n4}"
    return ip


#with open(argv[1], 'r') as alltext:
with open("C:/Git/cp2xfw/sample_in.txt", 'r') as alltext:
    allconfig = alltext.read()



with open("C:/Git/cp2xfw/sample_in.txt", 'r') as input, open("C:/Git/cp2xfw/sample_out.txt", 'w+') as output:
#with open(argv[1], 'r') as input, open(argv[2], 'w+') as output:
    bond_int = []
    bond_intd = {}
    bond_intl = []
    bond_ints = ""
    vlanintf = []
    int_ip = []
    int_vlan  = {}
    int_name = ""
    intd = {}
    int_state = []
    static_route_cmd = []
    ospf_route_cmd = []
    ospfl = []
    ospfd = {}
    dhcpservl = []
    dhcpreld = {}
    dhcprelint = ""
    
    for line in input:
        """
        Назначение IP-адресов интерфейсам
        """
        if line.startswith("set interface") and "ipv4-address" in line and "lo" not in line:
            intf = line.split()[2]
            ip = line.split()[-3]
            mask = line.split()[-1]
            mask_addr = mask_transformation(mask)
            netip = net_counting(ip, mask)
            intd.update({intf : [netip, mask]})
            final_str = f"inet ifconfig {intf} address {ip} netmask {mask_addr}"
            int_ip.append(final_str)

        if line.startswith("set interface") and "state on" in line and "lo" not in line:
            intf = line.split()[2]
            final_str = f"inet ifconfig {intf} up"
            int_state.append(final_str)
            
        """
        Заполнение списка интерфейсов для аггрегированного канала
        """
        if line.startswith("add bonding group") and len(line)>21:
            if "group "+bond_ints+" interface" not in line:
                bond_intl = []
                bond_int = line.rstrip().split()
                bond_ints = bond_int[3]
                bond_intl.append(bond_int[-1])
                bond_intd.update({f"bond{bond_ints}":bond_intl})
            else:
                bond_int = line.rstrip().split()
                bond_ints = bond_int[3]
                bond_intl.append(bond_int[-1])
                bond_intd.update({f"bond{bond_ints}":bond_intl})
                bond_ints = bond_int[3]

        """
        Заполнение списка VLANS в соответствии с интерфейсами, собираем в словарь int_vlan
        Необходимо для команд вида inet ifconfig bond1 vlan add 110
        """
        if line.startswith(f"add interface bond"):
            if int_name not in line:
                vlanintf = []
                vlancmdin = line.split()
                vlanintf.append(vlancmdin[-1])
                int_vlan.update({vlancmdin[2] : vlanintf})
                int_name = vlancmdin[2]
            else: 
                vlancmdin = line.split()
                vlanintf.append(vlancmdin[-1])
                int_vlan.update({vlancmdin[2] : vlanintf})
                int_name = vlancmdin[2]

        if line.startswith("add interface eth"):
            if int_name not in line:
                vlanintf = []
                vlancmdin = line.split()
                vlanintf.append(vlancmdin[-1])
                int_vlan.update({vlancmdin[2] : vlanintf})
                int_name = vlancmdin[2]
            else: 
                vlancmdin = line.split()
                vlanintf.append(vlancmdin[-1])
                int_vlan.update({vlancmdin[2] : vlanintf})
                int_name = vlancmdin[2]
        """
        Проверяем наличие маршрута по умолчанию
        """
        if line.startswith("set static-route default nexthop gateway address"):
            def_route_ip = line.split()[-2]
        """
        Проверяем статические маршруты
        """
        if line.startswith("set static-route") and "default" not in line:
            ip = line.split()[2].split("/")[0]
            mask = mask_transformation(line.split()[2].split("/")[1])
            nexthop = line.split()[-2]
            static_route_cmd.append(f"inet route add {ip} netmask {mask} next-hop {nexthop}")
        """
        OSPF: Проверяем router-id area и сети в них
        """
        if line.startswith("set ospf area") and "backbone" not in line and "range" in line:
            area = line.split()[3].split(".")[-1]
            ip = line.split()[-2].split("/")[0]
            mask = mask_transformation(line.split()[-2].split("/")[1])
            ospfl.append([ip, mask])
            ospfd.update({area : ospfl})
        if line.startswith("set router-id"):
            router_id = line.split()[-1]
        """
        DHCP-relay проверка
        """
        if line.startswith("set bootp interface"):
            if "relay-to" in line:
                if dhcprelint in line:
                    dhcpservl.append(line.split()[-2])
                    dhcprelint = line.split()[3]
                    dhcpreld.update({dhcprelint : dhcpservl})
                else:

                    dhcpservl = []
                    dhcpservl.append(line.split()[-2])
                    dhcprelint = line.split()[3]
                    dhcpreld.update({dhcprelint : dhcpservl})

            if "primary" in line:
                ipdhcprel = line.split()[5]


   
    """
    Перевод интерфейсов в режим Slave
    """
    output.write("\n" + " Interfaces to Slave for Bonds ".center(60, "#") + "\n\n")
    for value in bond_intd.values():
        for item in value:
            #print(f"inet ifconfig {item} class slave")
            output.write(f"inet ifconfig {item} class slave\n")
    """
    Формирование команд для создания аггрегированного канала 
    """
    output.write("\n" + " Create Bonds ".center(60, "#") + "\n\n")
    for key,value in bond_intd.items():
         bond_cmd = f"inet bonding add {key} mode 802.3ad slaves "
         for item in value:
            bond_cmd += f"{item}, "
         output.write(bond_cmd.rstrip(", ") + "\n")
    """
    Перевод интерефейсов в режим trunk
    """
    output.write("\n" + " Interfaces to Trunk ".center(60, "#") + "\n\n")
    for key in int_vlan.keys():
        #print(f"inet ifcondig {key} class trunk")
        output.write(f"inet ifcondig {key} class trunk\n")
    """
    Вывод списка VLANS в соответствии с интерфейсами, распаковываем словарь int_vlan
    Необходимо для команд вида inet ifconfig bond1 vlan add 110
    """
    output.write("\n" + " Adding Vlans ".center(60, "#") + "\n\n")
    #print(int_vlan)
    for key,value in int_vlan.items():
         for item in value:
             #print(f"inet ifconfig {key} vlan add {item}")
             output.write(f"inet ifconfig {key} vlan add {item}\n")
    """
    Вывод на печать адресов интерфейсов
    """
    output.write("\n" + " IP-addresses to Interfaces ".center(60, "#") + "\n\n")
    for item in int_ip:
        output.write(item + "\n")
        """
    Перевод интерфейсов в UP
    """
    output.write("\n" + " Interfaces to UP state ".center(60, "#") + "\n\n")
    for item in set(int_state):
        if "." not in item:
            output.write(item + "\n")
    """
    Маршрут по умолчанию
    """
    output.write("\n" + " Default route ".center(60, "#") + "\n\n")
    if def_route_ip:
        output.write(f"inet route add default next-hop {def_route_ip}\n")
    """
    Прочие статические маршруты
    """
    output.write("\n" + " Static routes ".center(60, "#") + "\n\n")
    if static_route_cmd:
        for item in static_route_cmd:
            output.write(item + "\n")

    """
    OSPF 
    """
    output.write("\n" + " OSPF ".center(60, "#") + "\n\n")
    if ospfd:
        ruleforospfs = ("firewall local add 1 rule ”MyOspfLocal” src @any dst @local service @OSPF pass\n"
        "firewall local add 1 rule ”MyOspfMulticast” src @any dst @multicast service @OSPF pass\n"
        "firewall local add 1 rule ”OspfFromMe” src @local dst @any service @OSPF pass\n")
        output.write(f"inet ospf router-id {router_id}\n")
        for key, value in ospfd.items():
            for item in value:
                output.write(f"inet ospf network add {item[0]} netmask {item[1]} area {key}\n")
        output.write(ruleforospfs)
        output.write(f"inet ospf mode on\n")
    
    """
    DHCP-relay
    """
    output.write("\n" + " DHCP- relay ".center(60, "#") + "\n\n")
    dhcperl_tmpl = []
    hypotheses = []
    intf_to_dhcpserver = {}
    tempd = {}
    cmdl = []
    if dhcpreld:
        for key,value in dhcpreld.items():
            for dhcpserv in value:
                #print(key,dhcpserv)
                tempd.update({key: ip_to_bits(dhcpserv)}) #intname должен ходить на dhcp в битах
        for intf_in_temp,bitmask in tempd.items():
            for intf, net in intd.items():
                if ip_to_bits(net[0]).rstrip("0") in bitmask:
                    dhcperl_tmpl.append([intf_in_temp, intf, bits_to_ip(bitmask), net[1]])
        for item in dhcperl_tmpl:
            for intf, net in intd.items():
                if net_counting(item[2],item[3]) in net:
                    for key, value in dhcpreld.items():
                        for serv in value:
                            if key == item[0]:
                                cmdl.append([key,serv,item[1]])
    tmpitem = ""
    for item in cmdl:
        if tmpitem != item[0]:
            #print(f"inet dhcp relay add listen-interface {item[0]}")
            output.write(f"inet dhcp relay add listen-interface {item[0]}\n")
            tmpitem = item[0]
        #print(f"inet dhcp relay add external-interface {item[2]} server {item[1]}")
        output.write(f"inet dhcp relay add external-interface {item[2]} server {item[1]}\n")
    #print(f"inet dhcp relay mode on\ninet dhcp relay start\n")
    output.write(f"inet dhcp relay mode on\ninet dhcp relay start\n")


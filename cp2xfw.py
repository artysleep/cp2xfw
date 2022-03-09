from sys import argv
from typing import final


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

with open("C:/Git/cp2xfw/sample_in.txt", 'r') as alltext:
    allconfig = alltext.read()

with open("C:/Git/cp2xfw/sample_in.txt", 'r') as input, open("C:/Git/cp2xfw/script_out.txt", 'w+') as output:
    bond_int = []
    bond_intd = {}
    bond_intl = []
    bond_ints = ""
    vlanintf = []
    int_ip = []
    int_vlan  = {}
    int_name = ""
    int_state = []
    static_route_cmd = []
    
    for line in input:
        """
        Назначение IP-адресов интерфейсам
        """
        if line.startswith("set interface") and "ipv4-address" in line and "lo" not in line:
            intf = line.split()[2]
            ip = line.split()[-3]
            mask = line.split()[-1]
            mask = mask_transformation(mask)
            final_str = f"inet ifconfig {intf} address {ip} netmask {mask}"
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
    Перевод интерфейсов в режим Slave
    """
    output.write("\n" + "Interfaces to Slave for Bonds".center(60, "#") + "\n\n")
    for value in bond_intd.values():
        for item in value:
            #print(f"inet ifconfig {item} class slave")
            output.write(f"inet ifconfig {item} class slave\n")
    """
    Формирование команд для создания аггрегированного канала 
    """
    output.write("\n" + "Create Bonds".center(60, "#") + "\n\n")
    for key,value in bond_intd.items():
         bond_cmd = f"inet bonding add {key} mode 802.3ad slaves "
         for item in value:
            bond_cmd += f"{item}, "
         output.write(bond_cmd.rstrip(", ")+"\n")
    """
    Перевод интерефейсов в режим trunk
    """
    output.write("\n" + "Interfaces to Trunk".center(60, "#") + "\n\n")
    for key in int_vlan.keys():
        #print(f"inet ifcondig {key} class trunk")
        output.write(f"inet ifcondig {key} class trunk\n")
    """
    Вывод списка VLANS в соответствии с интерфейсами, распаковываем словарь int_vlan
    Необходимо для команд вида inet ifconfig bond1 vlan add 110
    """
    output.write("\n" + "Adding Vlans".center(60, "#") + "\n\n")
    for key,value in int_vlan.items():
         for item in value:
             #print(f"inet ifconfig {key} vlan add {item}")
             output.write(f"inet ifconfig {key} vlan add {item}\n")
    """
    Вывод на печать адресов интерфейсов
    """
    output.write("\n" + "IP-addresses to Interfaces".center(60, "#") + "\n\n")
    for item in int_ip:
        output.write(item + "\n")
        """
    Перевод интерфейсов в UP
    """
    output.write("\n" + "Interfaces to UP state".center(60, "#") + "\n\n")
    for item in set(int_state):
        if "." not in item:
            output.write(item + "\n")
    """
    Маршрут по умолчанию
    """
    output.write("\n" + "Default route".center(60, "#") + "\n\n")
    if def_route_ip:
        output.write(f"inet route add default next-hop {def_route_ip}\n")
    """
    Прочие статические маршруты
    """
    output.write("\n" + "Static routes".center(60, "#") + "\n\n")
    if static_route_cmd:
        for item in static_route_cmd:
            output.write(item + "\n")

    output.write("\n" + "OSPF".center(60, "#") + "\n\n")
    



            
            



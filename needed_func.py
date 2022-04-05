def mask_transformation(mask):
    mask = int(mask)
    bin_mask = "1" * mask + "0" * (32 - mask)
    octet_list = [
        int(bin_mask[0:8], 2),
        int(bin_mask[8:16], 2),
        int(bin_mask[16:24], 2),
        int(bin_mask[24:32], 2),    
    ]
    mask = ".".join(str(n) for n in octet_list)
    return mask

def enum(filename):
    with open(filename, "r") as file:
        for index, line in enumerate(file, 1):
            print(f"{index:<5}{line}", end = "")

def net_counting(ip , mask):
    ipl = ip.split(".")
    ipbit="{:08b}".format(int(ipl[0]))+"{:08b}".format(int(ipl[1]))+"{:08b}".format(int(ipl[2]))+"{:08b}".format(int(ipl[3]))
    netipbit=ipbit[0:int(mask)]+"0"*(32-int(mask))
    octet_list = [
        int(netipbit[0:8],2),
        int(netipbit[8:16],2),
        int(netipbit[16:24],2),
        int(netipbit[24:32],2)
    ]
    netip = ".".join(str(n) for n in octet_list)
    return netip

def ip_to_bits(ip):
    ipl = ip.split(".")
    ipbit="{:08b}".format(int(ipl[0]))+"{:08b}".format(int(ipl[1]))+"{:08b}".format(int(ipl[2]))+"{:08b}".format(int(ipl[3]))
    return ipbit

def bits_to_ip(ipbit):
    octet_list = [
        int(ipbit[0:8],2),
        int(ipbit[8:16],2),
        int(ipbit[16:24],2),
        int(ipbit[24:32],2)
    ]
    ip = ".".join(str(n) for n in octet_list)
    return ip
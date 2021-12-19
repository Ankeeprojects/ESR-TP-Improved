import sys
import xml.etree.ElementTree as ET 
 

#Função que calcula o peso de um determinado link underlay
def calculate_weight(bandwidth,delay,jitter,loss,duplicate):
    MAX_BANDWIDTH = 1000000000 # 1 Gbps
    MAX_DELAY = 1000000 #1 seg
    MAX_JITTER = 1000000 #1 seg

    bandwidth = bandwidth if bandwidth!=0 and bandwidth<MAX_BANDWIDTH else MAX_BANDWIDTH
    delay = delay if delay<MAX_DELAY else MAX_DELAY
    jitter = jitter if jitter<MAX_JITTER else MAX_JITTER
    
    bandwidth_normalized = 1 - (bandwidth/MAX_BANDWIDTH)
    delay_normalized = delay/MAX_DELAY
    jitter_normalized = jitter/MAX_JITTER
    loss_normalized = loss/100
    duplicate_normalized = duplicate/100
    
    return bandwidth_normalized*0.2 + delay_normalized*0.2 + jitter_normalized*0.2 + loss_normalized*0.2 + duplicate_normalized*0.2

#Reads xml to interpretable class
def read_xml(file_name):
    with open(file_name, 'r') as f:
        data = f.read()
    return ET.fromstring(data)

#Parses all the switches
def read_switches(parsed_data,switches_to_remove):
    switches = parsed_data.find('networks')
    for switch in switches:
        switches_to_remove[switch.get('id')] = switch.get('name')

#Parses all nodes 
def read_nodes(parsed_data,nodes_to_write):
    nodes = parsed_data.find('devices')
    for node in nodes:
        nodes_to_write[node.get('id')] = (node.get('name'),node.get('type'))

#Parses all links between nodes
def read_links(parsed_data,switches_to_remove,links_to_write,nodes_to_write):
    links = parsed_data.find('links')
    for link in links:
        node1_id = link.get('node1')
        node2_id = link.get('node2')
        link_tuple = (node1_id,node2_id)
        iface1 = link.find('iface1')
        if iface1 is None:
            if nodes_to_write[node2_id][1] == "PC":
                pass
            else:
                #its a switch link with node1_id 
                for link_aux in links:
                    node1_aux = link_aux.get('node1')
                    node2_aux = link_aux.get('node2')
                    if node1_aux==node1_id and node2_id!=node2_aux and (nodes_to_write[node2_id][1] not in ['PC','host'] or nodes_to_write[node2_aux][1] not in ['PC','host']):
                        link_tuple = (node2_id,node2_aux)
                        iface2 = link.find('iface2')
                        ip_1 = iface2.get("ip4")
                        iface2_aux = link_aux.find('iface2')
                        ip_2 = iface2_aux.get("ip4")
                        options_1 = link.find('options')
                        bandwidth_1 = options_1.get('bandwidth') #bandwidth in bps
                        delay_1 = options_1.get('delay')
                        jitter_1 = options_1.get('jitter')
                        loss_1 = options_1.get('loss')
                        duplicate_1 = options_1.get('dup')
                        options_2 = link_aux.find('options')
                        bandwidth_2 = options_2.get('bandwidth') #bandwidth in bps
                        delay_2 = options_2.get('delay')
                        jitter_2 = options_2.get('jitter')
                        loss_2 = options_2.get('loss')
                        duplicate_2 = options_2.get('dup')
                        weight = calculate_weight(min(int(bandwidth_1),int(bandwidth_2)),max(int(delay_1),int(delay_2)),max(int(jitter_1),int(jitter_2)),max(float(loss_1),float(loss_2)),max(int(duplicate_1),int(duplicate_2)))
                        link_tuple_info = (ip_1,ip_2,weight)
                        links_to_write[link_tuple] = link_tuple_info
                    else:
                        pass
        else:
            ip_1 = iface1.get("ip4")
            iface2 = link.find('iface2')
            ip_2 = iface2.get("ip4")
            options = link.find('options')
            bandwidth = options.get('bandwidth') #bandwidth in bps
            delay = options.get('delay')
            jitter = options.get('jitter')
            loss = options.get('loss')
            duplicate = options.get('dup')
            weight = calculate_weight(int(bandwidth),int(delay),int(jitter),float(loss),float(duplicate))
            link_tuple_info = (ip_1,ip_2,weight)
            links_to_write[link_tuple] = link_tuple_info

#Writes all the classes to config file
def write_to_config(nodes_to_write,links_to_write):
    pcs = set()
    with open('config', 'w') as config:
        for id,info in nodes_to_write.items():
            if info[1]=="host":
                config.write(id)
                found = False
                for tuple1,tuple2 in links_to_write.items(): # cycle to get ip of a server interface 
                    if tuple1[0]==id and not found:
                        config.write(" "+tuple2[0] +"\n")
                        found = True
                    elif tuple1[1]==id and not found:
                        config.write(" "+tuple2[1] +"\n")
                        found = True
                    else:
                        pass
            elif info[1]=="PC":
                pcs.add(id)
        for pc in pcs:
            config.write(pc + " ")
        config.write("\n")
        for tuple1,tuple2 in links_to_write.items():
            config.write(tuple1[0]+" "+tuple2[0]+" "+tuple1[1]+" "+tuple2[1]+" "+str(tuple2[2])+"\n")


def main():
    parsed_data = read_xml(sys.argv[1])
    nodes_to_write={}
    links_to_write={}
    switches_to_remove={}

    read_nodes(parsed_data, nodes_to_write)
    read_switches(parsed_data, switches_to_remove)
    read_links(parsed_data, switches_to_remove, links_to_write, nodes_to_write)

    write_to_config(nodes_to_write,links_to_write)

    print("Wrote all the information from underlay to file named config")

main()
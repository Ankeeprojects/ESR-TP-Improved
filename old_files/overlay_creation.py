import xml_interpreter as XML
import re



def print_nodes(nodes_to_write):
    for id,info in nodes_to_write.items():
        print("Identificador: ",id," Nome: ",info[0]," Tipo: ",info[1])


def read_chosen_nodes(nodes_to_write):
    overlay_nodes_to_write = {}
    chosen = input("""
    Insira os nodos que deseja que façam parte do Overlay (<identificador> separados por espaços):
    
Nodos: """) 
    for id in re.split(" ",chosen):
        overlay_nodes_to_write[id] = nodes_to_write[id]
    return overlay_nodes_to_write

def ask_nodes_overlay(nodes_to_write, links_to_write):
    print_nodes(nodes_to_write)
    overlay_nodes_to_write = read_chosen_nodes(nodes_to_write)
    return overlay_nodes_to_write

def get_link(links_to_write,node_1,node_2):
    tuple_key = (node_1,node_2)
    result = tuple_key in links_to_write #checks if key is on links, otherwise its represented in opposing order
    link = links_to_write[tuple_key] if result else links_to_write[tuple_key[::-1]] #reverses the tuple and searches for it again
    return 1-result,link

def read_chosen_links(paths,links_to_write):
    overlay_links_to_write = {}
    chosen = input("""
    Insira os links que deseja que façam parte do Overlay (<identificador> separados por espaços):
    
Links: """) 
    for id in re.split(" ",chosen):
        chosen_path = paths[int(id)]

        id_1 = chosen_path[0]
        result_1,link_1 = get_link(links_to_write,id_1,chosen_path[1])
        ip_1 = link_1[result_1]

        id_2 = chosen_path[-1]
        result_2,link_2 = get_link(links_to_write,id_2,chosen_path[-2])
        ip_2 = link_2[result_2]

        total_weights = 0.0
        for i,id_1 in enumerate(chosen_path):
            if i>0:
                id_2 = chosen_path[i-1]
                res,link_info = get_link(links_to_write,id_1,id_2)
                total_weights += link_info[2]
        weight = total_weights/(i+1)

        overlay_links_to_write[(id_1, id_2)] = (ip_1, ip_2, weight)
    return overlay_links_to_write


def ask_links_overlay(overlay_nodes_to_write,paths,links_to_write):
    overlay_links_to_write = {}
    print("")
    for i,path in enumerate(paths):
        print(i,"- Chegar ao nó ",overlay_nodes_to_write[path[-1]]," partindo de ",overlay_nodes_to_write[path[0]])
    return read_chosen_links(paths,links_to_write)

def get_path(node_id, overlay_nodes_to_write, visited_nodes, links_to_write, path):
    paths = []
    visited_nodes.append(node_id)
    if len(path) != 1 and path[-1] in overlay_nodes_to_write.keys():
        return [path.copy()]
    count=0
    for link in links_to_write.keys():
        if link[0]==node_id or link[1]==node_id:
            #print("Link[0] ",link[0]," and Link[1] ", link[1], " so I chose ",int(link[0]==node_id))
            #if enters here then one of the points of the link is node_id
            next_node = link[int(link[0]==node_id)]
            if next_node not in visited_nodes:
                path.append(next_node)
                paths_aux = get_path(next_node, overlay_nodes_to_write, visited_nodes, links_to_write, path)
                path.pop()
                paths = paths + paths_aux
    return paths


def get_paths(overlay_nodes_to_write,links_to_write):
    paths = []
    for node in overlay_nodes_to_write.keys():
        paths = paths + get_path(node, overlay_nodes_to_write, [], links_to_write, [node])
    return paths



def main():
    parsed_data = XML.read_xml()
    nodes_to_write={}
    links_to_write={}
    switches_to_remove={}

    XML.read_nodes(parsed_data, nodes_to_write)
    XML.read_switches(parsed_data, switches_to_remove)
    XML.read_links(parsed_data, switches_to_remove, links_to_write)


    overlay_nodes_to_write = ask_nodes_overlay(nodes_to_write, links_to_write)

    paths = get_paths(overlay_nodes_to_write, links_to_write)

    overlay_links_to_write = ask_links_overlay(overlay_nodes_to_write,paths,links_to_write)

    write_to_config(overlay_nodes_to_write,overlay_links_to_write)

    print("Wrote all the information to file named config")


main()
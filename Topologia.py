import json
import sys
from json import JSONDecoder, JSONDecodeError
from socket import *
import threading
import time
from datetime import datetime
import re

class Topologia:
    starter_node : str # id do nodo do servidor 
    starter_node_ip : str # ip do nodo do servidor
    underlay_data : dict # id do nodo para lista de tuplos com indicação do ip de ligação ao nodo adjacente no underlay, o peso dessa ligação e id desse nodo (ex: (10.0.0.4,0.4,5))
    underlay_best_path : dict #id do nodo para tuplo com id do nodo que o trouxe até este e lista de tuplos com indicação do ip de ligação ao nodo adjacente no underlay, o peso dessa ligação e id desse nodo (ex: (10.0.0.4,0.4,5))
    active_nodes : set # set de ids dos nodos ativos no overlay
    overlay_data : dict # id do nodo overlay para tuplo com ip para voltar atrás e lista de tuplos com indicação do ip de ligação do nodo adjacente no overlay e id desse nodo
    node_interfaces : dict # id do nodo underlay para lista de ips das suas interfaces

    caminhos : dict 

    # leitor do config
    def __init__(self):
        self.underlay_data = {} 
        self.active_nodes = set()
        self.underlay_best_path = {}
        self.overlay_data = {}
        self.node_interfaces = {}
        self.caminhos = {}
        self.id_caminhos = {}
        clients = set()

        with open('config', 'r') as config:
            server_line = re.split(" ",config.readline()[:-1])
            self.starter_node = server_line[0]
            self.starter_node_ip = server_line[1]
            clients = set(re.split(" ",config.readline()[:-2]))
            self.active_nodes.add(self.starter_node)
            for line in config.readlines():
                content = re.split(" ",line)
                content[4] = re.split("\n",content[4])
                content[4] = content[4][0]
                #content[0] - id do nodo X
                #content[1] - ip da interface de entrada do nodo X
                #content[2] - id do nodo Y
                #content[3] - ip da interface de entrada do nodo Y
                #content[4] - peso do link para futuro cálculo de menores caminhos
                self.initiate_node(content[0])
                self.underlay_data[content[0]].append((content[3],content[4],content[2])) # ligação do nodo X -> Y
                self.node_interfaces[content[0]].add(content[1])
                self.initiate_node(content[2])
                self.underlay_data[content[2]].append((content[1],content[4],content[0])) # ligação do nodo Y -> X
                self.node_interfaces[content[2]].add(content[3])
            self.calculate_fastest_path()
        for key,value in self.node_interfaces.items():
            self.node_interfaces[key]=list(value)
       
        

        self.caminhos['10'] = [[self.node_interfaces['16'][-1]],
                                [self.node_interfaces['8'][-1], self.node_interfaces['7'][-1], self.node_interfaces['4'][-1],
                                    self.node_interfaces['6'][-1], self.node_interfaces['12'][-1], self.node_interfaces['13'][-1]],
                                [self.node_interfaces['9'][-1], self.node_interfaces['5'][-1], self.node_interfaces['4'][-1],
                                    self.node_interfaces['11'][-1]]]

        self.id_caminhos['10'] =  [['16'],['8','7','4','6','12', '13'],['9','5','4','11']]

    # Função que retorna o id do servidor
    def get_starter_node(self):
        return self.starter_node
        
    # Inicia informações do nodo caso não tenha sido ainda iniciado
    def initiate_node(self,node):
        if self.underlay_data.get(node) is None:
                    self.underlay_data[node]=[]
                    self.underlay_best_path[node]=[None,[]]
                    self.overlay_data[node] = [None,[]]
                    self.node_interfaces[node] = set()

    #  Retorna node_id através de interface_ip dado à função
    def get_node_info(self,ip : str):
        for value in self.underlay_data.items():
            node_id = -1
            for info in value[1]:
                if info[0]==ip:
                    node_id = info[2]
                    break
            if node_id!=-1:
                break
        return node_id

    # Retorna os vizinhos de um nodo no grafo overlay
    def get_neighbors(self,node_id : str):
        neighbors = []
        for node in self.overlay_data[node_id][1]:
            neighbors.append((self.node_interfaces[node[1]].copy(),node[1]))
        return neighbors

    # Retorna o nodo imediatamente atrás desse no grafo dos melhores caminhos overlay
    def get_behind(self,node_id):
        return self.overlay_data[node_id][0]

    def calculate_fastest_path(self):
        link_waiting_list = []
        visited = [self.starter_node]
        for link in self.underlay_data[self.starter_node]:
            link_waiting_list.append((self.starter_node,link[0],link[1],link[2]))
        while link_waiting_list != []:
            best_link = get_best_weight(link_waiting_list) # escolhe melhor link para nodo não visitado
            link_waiting_list = [x for x in link_waiting_list if not same_node(x,best_link)] # remove links para o mesmo nodo
            self.underlay_best_path[best_link[0]][1].append(tuple(list(best_link)[1:])) # adiciona link ao melhor caminho
            self.underlay_best_path[best_link[3]][0] = best_link[0] # adiciona nodo como "pai" do nodo atingível com este link
            visited.append(best_link[3]) # adiciona nodo aos visitados
            link_waiting_list = add_new_links_to_queue(best_link[3],self.underlay_data[best_link[3]],visited) + link_waiting_list# adiciona novos links à queue para nodos ainda não visitados
            
    def get_ip_link(self,node_1,node_2):
        for link in self.underlay_data[node_1]:
            if link[2]==node_2:
                return link[0]

    def define_overlay(self):
        for node in self.active_nodes: # Cleaning all the info from overlay
            self.overlay_data[node] = [None,[]]
        for node in self.active_nodes:
            if node == self.starter_node: # caso o nodo seja o nodo inicial não tentamos encontrar o anterior pois não existe
                pass
            else:
                before_node = self.find_last_node_overlay(node)
                ip_behind = self.node_interfaces[before_node][-1]
                self.overlay_data[node][0] = ip_behind
                self.overlay_data[before_node][1].append((self.node_interfaces[node][-1],node))
            
    def find_last_node_overlay(self,node_id):
        before_node = self.underlay_best_path[node_id][0] # nodo underlay que leva ao nodo de overlay atual
        while before_node not in self.active_nodes: # encontrar o nodo overlay que liga ao nodo que estamos a percorrer
            before_node = self.underlay_best_path[before_node][0]
        return before_node 
                
    def get_closest_overlay(self,ip):
        node_id = self.get_node_info(ip)
        overlay_node = self.find_last_node_overlay(node_id)
        return self.node_interfaces[overlay_node][-1]
        
        
    def add_node_overlay(self,node_id : str):
        self.active_nodes.add(node_id)
        self.define_overlay()

    def remove_node_overlay(self,node_id : str):
        self.active_nodes.remove(node_id)
        self.define_overlay()

#Função auxiliar que retorna uma lista com os novos links a partir do nodo, para nodos que não tenham ainda sido visitados
def add_new_links_to_queue(cur_node,new_links,visited):
    returning_list = []
    for link in new_links:
        if link[2] not in visited:
            returning_list.append((cur_node,link[0],link[1],link[2]))
    return returning_list

# Função auxiliar que calcula o melhor link tendo em conta o peso na lista dada
def get_best_weight(link_waiting_list : list):
    smallest = 1.1; #Valor superior a qualquer valor na lista
    for link in link_waiting_list:
        best_link = link if float(link[2])<smallest else best_link
    return best_link

# Função auxiliar que retorna True quando dois links têm o mesmo destino
def same_node(link_1,link_2):
    return link_1[3] == link_2[3]
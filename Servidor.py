import sys
from socket import *
import threading
import json
from datetime import datetime, timedelta
import time
from Topologia import *

class Servidor:
    vizinhos : list
    lock : threading.Lock
    ficheiros : dict
    topologia : Topologia

    def __init__(self, ficheiros):
        self.lock = threading.Lock()
        self.server_port = 12000
        self.beacon_port = 42000
        self.ficheiros = ficheiros
        self.topologia = Topologia()

    def init_server(self):
        threading.Thread(target=self.server).start()
        threading.Thread(target=self.beacon_server).start()
        threading.Thread(target=self.activity_server).start()

    def server(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.server_port))

        while True:
            message, address = s.recvfrom(1024)

            threading.Thread(target=self.processa_pedido,args=(message,address)).start()
            

    def processa_pedido(self, message, address):
        s = socket(AF_INET, SOCK_DGRAM)
        id = self.topologia.get_node_info(address[0])
        print(f"Mensagem: {message} id: {id}")

        s.sendto(str.encode(id), address)
        
        caminhos = self.topologia.caminhos[id]

        for num,caminho in enumerate(caminhos):
            print(f"Caminho {num} para nodo {id}: {caminho}")

        resposta = json.dumps(caminhos)

        s.sendto(str.encode(resposta), address)

        indices = self.topologia.id_caminhos[id]
        print(indices)
        resp = json.dumps(indices)

        s.sendto(str.encode(resp), address)
        s.close()

    def activity_server(self):
        pass
    
    def beacon_server(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.beacon_port))

        while True:
            message, address = s.recvfrom(256)

            print(f"Recebi uma mensagem do {address}: {message}")
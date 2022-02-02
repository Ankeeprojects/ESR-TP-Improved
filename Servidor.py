import sys
from socket import *
import threading
import json
from datetime import datetime, timedelta
import time
from Topologia import *

class Servidor:
    vizinhos : dict
    lock : threading.Lock
    ficheiros : dict
    topologia : Topologia
    id : str
    join_port : int

    def __init__(self, ficheiros):
        self.id = '16'
        self.lock = threading.Lock()
        self.server_port = 12000
        self.beacon_port = 42000
        self.ficheiros = ficheiros
        self.topologia = Topologia()
        self.vizinhos = dict()
        self.join_port = 42001

    def init_server(self):
        threading.Thread(target=self.server).start()
        threading.Thread(target=self.beacon_server).start()
        threading.Thread(target=self.beacon_sender).start()
        threading.Thread(target=self.activity_server).start()
        threading.Thread(target=self.join_server).start()

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

    def join_server(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.join_port))

        while True:
            message, address = s.recvfrom(256)

            print(f"O {message} está a juntar-se!")
            self.adiciona_vizinho(message, address)
            s.sendto(self.id.encode('utf-8'), address)

    def adiciona_vizinho(self, message, address):
        print("Adicionando")
        self.lock.acquire()
        self.vizinhos[message] = [address[0], datetime.now()]
        print(self.vizinhos)
        self.lock.release()

    def activity_server(self):
        while True:
            self.lock.acquire()

            for vizinho, info in self.vizinhos.items():
                diferenca = datetime.now() - info[1]
                print(diferenca.total_seconds())
                if diferenca.total_seconds() > 0.4:
                    self.vizinhos.pop(vizinho)
                    threading.Thread(target=self.procura_vizinho, args=(vizinho,)).start()
                    break
                else:
                    print("passou!")

            self.lock.release()
            time.sleep(0.2)
    
    def procura_vizinho(self, vizinho):
        pass

    def beacon_server(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.beacon_port))

        while True:
            message, address = s.recvfrom(256)

            print(f"Recebi uma mensagem do {address}: {message}")

            self.lock.acquire()
            if message in self.vizinhos:
                self.vizinhos[message][1] = datetime.now()

            self.lock.release()

    def beacon_sender(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)

            for vizinho in self.vizinhos.values():
                s.sendto(self.id.encode('utf-8'), (vizinho[0], self.beacon_port))
                
            time.sleep(0.2)
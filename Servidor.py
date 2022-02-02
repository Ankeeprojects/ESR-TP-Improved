import sys
from socket import *
import threading
import json
from datetime import datetime, timedelta
import time
from Topologia import *
from Caminhos import *

class Servidor:
    vizinhos : dict
    lock : threading.Lock
    ficheiros : dict
    topologia : Topologia
    id : str
    join_port : int
    caminhos : Caminhos

    def __init__(self, ficheiros):
        self.id = '16'
        self.lock = threading.Lock()
        self.server_port = 12000
        self.beacon_port = 42000
        self.ficheiros = ficheiros
        self.topologia = Topologia()
        self.vizinhos = dict()
        self.join_port = 42001
        self.caminhos = Caminhos()

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

    def encontra_vizinho(self, caminho : list, indice : int):
        s = socket(AF_INET, SOCK_DGRAM)
        s.settimeout(0.1)

        for curr,ip in enumerate(caminho):
            s.sendto(self.id.encode('utf-8'), (ip, self.join_port))
            try:
                message, address = s.recvfrom(1024)
                message = message.decode()

                self.caminhos.current_indices[indice] = curr
                self.adiciona_vizinho(message, address)
                return
            except timeout:
                #print("Timeout!")
                continue
    
    def adiciona_vizinho(self, message, address):
        print("Adicionando")
        self.lock.acquire()
        self.vizinhos[message] = [address[0], datetime.now()]
        print(self.vizinhos)
        self.lock.release()

    def join_server(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.join_port))

        while True:
            message, address = s.recvfrom(256)
            message = message.decode()

            self.adiciona_vizinho(message, address)
            s.sendto(self.id.encode('utf-8'), address)

            print(f"O {message} está a juntar-se!")

            self.verifica_melhor(message)

            
    def verifica_melhor(self, nodo):
        for indice, caminho in enumerate(self.caminhos.index_caminhos):
            try:
                indice_novo = caminho.index(nodo)
                indice_atual = self.caminhos.current_indices[indice]

                if indice_atual == -1:
                    print("Era o primeiro!")
                    self.lock.acquire()
                    self.caminhos.current_indices[indice] = indice_novo
                    self.lock.release()               
                    print(f"Indice atual: {indice_atual}\nIndice novo:{indice_novo}\nnodo: {nodo}")
                    break
                elif indice_novo < indice_atual:
                    print("O nodo era melhor!")
                    self.lock.acquire()
                    self.vizinhos.pop(caminho[indice_atual])
                    self.caminhos.current_indices[indice] = indice_novo
                    self.lock.release()               
                    print(f"Indice atual: {indice_atual}\nIndice novo:{indice_novo}\nnodo: {nodo}")
                    break

            except ValueError:
                print("Não estava!")
                continue

    def beacon_server(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.beacon_port))

        while True:
            message, address = s.recvfrom(256)

            print(f"Recebi uma mensagem do {address}: {message}")
            message = message.decode()
            
            self.lock.acquire()
            if message in self.vizinhos:
                self.vizinhos[message][1] = datetime.now()
                print("Já está!") 
            self.lock.release()

    def activity_server(self):
        while True:
            self.lock.acquire()

            for vizinho, info in self.vizinhos.items():
                diferenca = datetime.now() - info[1]
                print(diferenca.total_seconds())
                if diferenca.total_seconds() > 0.25:
                    self.vizinhos.pop(vizinho)
                    threading.Thread(target=self.procura_vizinho, args=(vizinho,)).start()
                    break
                else:
                    print("passou!")

            self.lock.release()
            time.sleep(0.2)
    
    def procura_vizinho(self, vizinho):
        for ind_caminho, caminho in enumerate(self.caminhos.index_caminhos):
            try:
                indice = caminho.index(vizinho) + 1
                self.encontra_vizinho(self.caminhos.lista_caminhos[ind_caminho][indice:], 0)
                    

            except ValueError:
                print("Não está!")

    def beacon_sender(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)

            for vizinho in self.vizinhos.values():
                s.sendto(self.id.encode('utf-8'), (vizinho[0], self.beacon_port))
                
            time.sleep(0.2) 


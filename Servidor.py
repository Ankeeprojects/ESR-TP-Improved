import sys
from socket import *
import threading
import json
from datetime import datetime, timedelta
import time
from Topologia import *
from Caminhos import Caminhos
from Stream_info import Stream_Info

class Servidor:
    vizinhos : dict
    lock : threading.Lock
    ficheiros : dict
    topologia : Topologia
    id : str
    join_port : int
    caminhos : Caminhos
    beacon_port : int
    stream_loc_port : int
    streams : list

    def __init__(self, ficheiros):
        self.id = '16'
        self.lock = threading.Lock()
        self.server_port = 12000
        self.beacon_port = 42000
        self.join_port = 42001
        self.stream_loc_port = 42002 
        self.ficheiros = ficheiros
        self.topologia = Topologia()
        self.vizinhos = dict()
        self.streams = []
        self.caminhos = Caminhos(False)

    def init_server(self):
        threading.Thread(target=self.server).start()
        threading.Thread(target=self.beacon_server).start()
        threading.Thread(target=self.beacon_sender).start()
        threading.Thread(target=self.activity_server).start()
        threading.Thread(target=self.join_server).start()
        threading.Thread(target=self.stream_locator).start()

        portas = []
        for ficheiro, porta in self.ficheiros.items():
            print(f"Servidor com o ficheiro {ficheiro} e a porta {porta}")
            portas.append(porta)
            threading.Thread(target=self.streaming_server, args=(ficheiro,porta)).start()

        self.caminhos.add_portas(portas)
    
    def streaming_server(self, ficheiro, porta):
        streaming = Stream_Info(ficheiro, porta, self.topologia)
        self.streams.append(streaming)
        streaming.init()
        
    def stream_locator(self):
        s = socket(AF_INET, SOCK_DGRAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.stream_loc_port))

        print(f"Localizador de streams a correr na porta {self.stream_loc_port}")

        while True:
            mensagem, address = s.recvfrom(256)
            mensagem = mensagem.decode()

            print(f"O gajo {address} est?? pedir {mensagem}")

            client_id = self.topologia.get_node_info(address[0])


            if mensagem in self.ficheiros:
                port = str(self.ficheiros[mensagem])
                #lista = [porta for porta in self.ficheiros.values()]               
                caminhos = self.topologia.caminhos[client_id]

                indices = self.topologia.id_caminhos[client_id]
                resp = [client_id, port, caminhos, indices]
                s.sendto(json.dumps(resp).encode('utf-8'), address)               
            else:
                print("N??o tenho o ficheiro!")
            
           
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

        portas = [porta for porta in self.ficheiros.values()]

        s.sendto(json.dumps(portas).encode('utf-8'), address)

        s.sendto(json.dumps(self.topologia.identifiers).encode('utf-8'), address)
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

            print(f"O {message} est?? a juntar-se!")

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
                print("N??o estava!")
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
                #print("J?? est??!") 
            self.lock.release()

    def activity_server(self):
        while True:
            self.lock.acquire()

            for vizinho, info in self.vizinhos.items():
                diferenca = datetime.now() - info[1]
                #print(diferenca.total_seconds())
                if diferenca.total_seconds() > 0.25:
                    self.vizinhos.pop(vizinho)
                    threading.Thread(target=self.procura_vizinho, args=(vizinho,)).start()
                    break
                #else:
                    #print("passou!")

            self.lock.release()
            time.sleep(0.2)
    
    def procura_vizinho(self, vizinho):
        for ind_caminho, caminho in enumerate(self.caminhos.index_caminhos):
            try:
                indice = caminho.index(vizinho) + 1
                self.encontra_vizinho(self.caminhos.lista_caminhos[ind_caminho][indice:], 0)
                    

            except ValueError:
                print("N??o est??!")

    def beacon_sender(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)

            for vizinho in self.vizinhos.values():
                s.sendto(self.id.encode('utf-8'), (vizinho[0], self.beacon_port))
                
            time.sleep(0.2) 


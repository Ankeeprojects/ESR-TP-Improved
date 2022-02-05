import json
import sys
from json import JSONDecoder, JSONDecodeError
from socket import *
import threading
import time
from datetime import datetime
from Caminhos import Caminhos
from Node_info import Node_Info
import re


class Nodo:
    
    beacon_port: int
    server_port: int
    server_ip: str
    caminhos : Caminhos
    id : str
    identifiers : dict
    streams : dict

    def __init__(self) -> None:
        
        self.beacon_port = 42000
        self.join_port = 42001
        self.server_ip = '10.0.3.10'
        self.server_port = 12000
        self.caminhos = Caminhos(True)
        self.streams = dict()

    def init(self):
        threading.Thread(target=self.beacon_server).start()
        threading.Thread(target=self.beacon_sender).start()
        threading.Thread(target=self.join_server).start()
        threading.Thread(target=self.activity_server).start()
        

        s = socket(AF_INET, SOCK_DGRAM)
        s.sendto('0'.encode('utf-8'), (self.server_ip, self.server_port)) 
        message = s.recv(256)

        self.id = str(json.loads(message))  

        message = s.recv(8192)

        self.caminhos.lista_caminhos = json.loads(message)

        print(self.caminhos.lista_caminhos)

        message = s.recv(8192)
        self.caminhos.index_caminhos = json.loads(message)
        
        print(self.caminhos.index_caminhos)

        for _ in range(len(self.caminhos.lista_caminhos)):
            self.caminhos.current_indices.append(-1)

        message = s.recv(1024)  
        
        portas = json.loads(message)

        message = s.recv(4096)

        self.identifiers = json.loads(message)

        
        s.close()

        self.caminhos.add_portas(portas)

        for indice, caminho in enumerate(self.caminhos.lista_caminhos):
            threading.Thread(target=self.encontra_vizinho, args=(caminho, indice, [], 0)).start()
    
        for porta in portas:
            threading.Thread(target=self.stream_server, args=(porta,)).start()

           
    def stream_server(self, porta:int):
        streaming = Node_Info(porta, self.identifiers, self.caminhos, self.id)
        self.streams[porta] = streaming
        streaming.init()


    def encontra_vizinho(self, caminho : list, indice : int, busca_stream : list, offset : int):
        s = socket(AF_INET, SOCK_DGRAM)
        s.settimeout(0.2)
        print(f"Vou buscar substituto para {busca_stream}")

        for curr,ip in enumerate(caminho):
            print(f"Estou a tentar ligar-me ao {ip}")
            s.sendto(self.id.encode('utf-8'), (ip, self.join_port))
            try:
                message, address = s.recvfrom(1024)
                message = message.decode()

                self.caminhos.current_indices[indice] = curr + offset

                print(f"O indice deste gajo é o {self.caminhos.current_indices[indice]}")
                self.adiciona_vizinho(message, address)

                for porta in busca_stream:
                    s.sendto(f'3 {self.id}'.encode('utf-8'), (self.identifiers[message], porta+1))
                    self.caminhos.streamer[porta] = message

                return
            except timeout:
                #print("Timeout!")
                continue
    
    def adiciona_vizinho(self, message, address):
        print("Adicionando")
        self.caminhos.lock.acquire()
        self.caminhos.vizinhos[message] = [address[0], datetime.now()]
        print(self.caminhos.vizinhos)
        self.caminhos.lock.release()

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

                print(f"cheguei aqui para ver quem é o melhor! .{indice_novo} vs {indice_atual}")

                if indice_atual == -1:
                    print("Era o primeiro!")
                    self.caminhos.lock.acquire()
                    self.caminhos.current_indices[indice] = indice_novo
                    self.caminhos.lock.release()               
                    print(f"Indice atual: {indice_atual}\nIndice novo:{indice_novo}\nnodo: {nodo}")
                    break
                elif indice_novo < indice_atual:
                    print("O nodo era melhor!")
                    self.caminhos.lock.acquire()
                    
                    self.caminhos.current_indices[indice] = indice_novo
                    s = socket(AF_INET, SOCK_DGRAM)
                    for porta, id in self.caminhos.streamer.items():
                        print(f"Estou a comparar o {id} com {caminho[indice_atual]}")   
                        if id == caminho[indice_atual]:
                            self.caminhos.streamer[porta] = nodo
                            s.sendto(f'3 {self.id}'.encode('utf-8'), (self.identifiers[nodo], porta+1))
                            self.streamer[porta].retira_nodo(nodo)
                            self.streaming_nodes[message[1]]

                    self.caminhos.vizinhos.pop(caminho[indice_atual])                    
                    self.caminhos.lock.release()               
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

            self.caminhos.lock.acquire()
            if message in self.caminhos.vizinhos:
                self.caminhos.vizinhos[message][1] = datetime.now()
                #print("Já está!") 
            self.caminhos.lock.release()

    def activity_server(self):
        while True:
            self.caminhos.lock.acquire()

            for vizinho, info in self.caminhos.vizinhos.items():
                diferenca = datetime.now() - info[1]
                #print(diferenca.total_seconds())
                if diferenca.total_seconds() > 0.25:

                    self.caminhos.vizinhos.pop(vizinho)

                    print(self.caminhos.streamer)
                    print(self.caminhos.streamer.values())
                    busca_stream = []
                    for key, value in self.caminhos.streamer.items():
                        if value == vizinho:
                            busca_stream.append(key)
                            self.caminhos.streamer[key] = None
                            print("O Gajo que me estava a dar stream morreu!!")

                    threading.Thread(target=self.procura_vizinho, args=(vizinho,busca_stream)).start()
                    break
                #else:
                    #print("passou!")
                    
            self.caminhos.lock.release()
            threading.Event().wait(0.2)
    
    def procura_vizinho(self, vizinho, busca_stream):
        for ind_caminho, caminho in enumerate(self.caminhos.index_caminhos):
            try:
                indice = caminho.index(vizinho) + 1
                self.encontra_vizinho(self.caminhos.lista_caminhos[ind_caminho][indice:], ind_caminho, busca_stream, indice)
                
            except ValueError:
                print("Não está!")

    def beacon_sender(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)

            for vizinho in self.caminhos.vizinhos.values():
                s.sendto(self.id.encode('utf-8'), (vizinho[0], self.beacon_port))
                
            threading.Event().wait(0.2)

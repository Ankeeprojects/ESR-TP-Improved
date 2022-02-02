import json
import sys
from json import JSONDecoder, JSONDecodeError
from socket import *
import threading
import time
from datetime import datetime
from Caminhos import *
import re


class Nodo:
    vizinhos: dict
    beacon_port: int
    server_port: int
    server_ip: str
    lock : threading.Lock
    caminhos : Caminhos
    id : str

    def __init__(self) -> None:
        self.vizinhos = dict()
        self.beacon_port = 42000
        self.join_port = 42001
        self.server_ip = '10.0.3.10'
        self.server_port = 12000
        self.lock = threading.Lock()
        self.caminhos = Caminhos()

    def init(self):
        threading.Thread(target=self.beacon_server).start()
        threading.Thread(target=self.beacon_sender).start()
        threading.Thread(target=self.join_server).start()
        threading.Thread(target=self.activity_server).start()

        s = socket(AF_INET, SOCK_DGRAM)
        s.sendto('0'.encode('utf-8'), (self.server_ip, self.server_port)) 
        message, address = s.recvfrom(256)

        self.id = str(json.loads(message))  

        message, address = s.recvfrom(8192)

        self.caminhos.lista_caminhos = json.loads(message)

        print(self.caminhos.lista_caminhos)

        message, address = s.recvfrom(8192)
        self.caminhos.index_caminhos = json.loads(message)
        
        print(self.caminhos.index_caminhos)

        s.close()

        for indice, caminho in enumerate(self.caminhos.lista_caminhos):
            threading.Thread(target=self.encontra_vizinho, args=(caminho, indice)).start()
    
    

    def encontra_vizinho(self, caminho : list, indice : int):
        s = socket(AF_INET, SOCK_DGRAM)
        s.settimeout(0.2)

        for index,ip in enumerate(caminho):
            s.sendto(self.id.encode('utf-8'), (ip, self.join_port))
            try:
                message, address = s.recvfrom(1024)
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
            self.adiciona_vizinho(message, address)
            print(f"O {message} está a juntar-se!")

            s.sendto(self.id.encode('utf-8'), address)

      
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
                    threading.Thread(target=self.procura_vizinho, args=(vizinho.decode(),)).start()
                    break
                else:
                    print("passou!")

            self.lock.release()
            time.sleep(0.2)
    
    def procura_vizinho(self, vizinho):
        for caminho in self.caminhos.index_caminhos:
            print(vizinho)
            print(caminho)
            if vizinho in caminho:
                print("O gajo está aqui!")
            else:
                print("Não está!")

    def beacon_sender(self):
        while True:
            s = socket(AF_INET, SOCK_DGRAM)

            for vizinho in self.vizinhos.values():
                s.sendto(self.id.encode('utf-8'), (vizinho[0], self.beacon_port))
                
            time.sleep(0.2) 

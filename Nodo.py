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
    vizinhos: list
    beacon_port: int
    server_port: int
    server_ip: str
    lock : threading.Lock
    caminhos : Caminhos
    id : str

    def __init__(self) -> None:
        self.vizinhos = []
        self.beacon_port = 42000
        self.server_ip = '10.0.3.10'
        self.server_port = 12000
        self.lock = threading.Lock()
        self.caminhos = Caminhos()

    def init(self):
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
            s.sendto(self.id.encode('utf-8'), (ip, self.beacon_port))
            try:
                message, address = s.recvfrom(1024)
            except timeout:
                print("Timeout!!! Try again...")
                continue


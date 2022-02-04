import threading
import socket

class Caminhos:
    index_caminhos: list
    lista_caminhos: list
    current_indices: list
    vizinhos: dict
    lock : threading.Lock

    def __init__(self) -> None:
        self.index_caminhos = []
        self.lista_caminhos = []
        self.current_indices = []
        self.vizinhos = dict()
        self.lock = threading.Lock()

    def flood (self, id, porta, user, address):

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(2)

        self.lock.acquire()
        for vizinho, info in self.vizinhos.items():
            print(f"{vizinho} -- {info[0]}")
            
            #success = False

            if vizinho != user:
                s.sendto(f"0 {id}".encode('utf-8'), (info[0], porta+1))
            else: 
                print("Não vou mandar de volta para o {user}!")
        self.lock.release()

        try:
            message = s.recv(256)
            print(f"O GAJO RESPONDEU: {message}!")
            s.sendto(f"1 {id}".encode('utf-8'), address)
            success = True
        except socket.timeout:
            print("Didn't work!")
            #self.server_ip_pool.pop(0)

        
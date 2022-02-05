from socket import *
from Topologia import Topologia
from VideoStream import *
import threading
import time
from RtpPacket import *
from Caminhos import Caminhos

class Node_Info:
    streaming_nodes : dict
    s : socket
    attempting : bool
    broadcasting : bool
    lock : threading.Lock
    identifiers : list
    caminhos : Caminhos

    def __init__(self, porta, identifiers, caminhos, id) -> None:
        self.streaming_nodes = dict()
        self.porta = porta
        self.lock = threading.Lock()

        self.s = socket(AF_INET, SOCK_DGRAM)
        self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.s.bind(('', porta+1))

        self.stream_socket = socket(AF_INET, SOCK_DGRAM)
        self.stream_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.stream_socket.bind(('', porta))

        self.identifiers = identifiers

        self.attempting = False

        self.caminhos = caminhos

        self.id = id

    def init(self):
        print(f"Streaming server a correr na porta {self.porta+1}")

        threading.Thread(target=self.stream).start()

        while True:
            message, address = self.s.recvfrom(1024)

            message = message.decode().split(" ")

            print(f"Recebi isto: {message[0]} {message[1]}")
            
            if message[0] == '0':
                print("Este gajo quer stream")
                if not self.attempting:
                    self.attempting = True
                    
                    self.caminhos.flood(self.id, self.porta, message[1], address)

                
                #self.s.sendto('1'.encode('utf-8'), address)
            elif message[0] == '2':
                print(f"A fechar o stream para o {message[1]}")

                self.lock.acquire()
                self.streaming_nodes.pop(message[1])

                if not bool(self.streaming_nodes):
                    self.broadcasting = False
                    self.attempting = False
                self.lock.release()
                #message, address = self.s.recvfrom(1024)
                #else:
                #    pass
            elif message[0] == '3':
                print(f"Recebi confirmação do stream para o {message[1]} {address}")

                print(f"Estou a enviar para o {self.identifiers[self.caminhos.streamer[self.porta]]}")
                self.s.sendto(f'3 {self.id}'.encode('utf-8'), (self.identifiers[self.caminhos.streamer[self.porta]], self.porta+1))
                self.lock.acquire()
                self.streaming_nodes[message[1]] = self.identifiers[message[1]]
                self.lock.release()


            #client_id = self.topologia.get_node_info(str(clientInfo['rtspSocket'][1][0]))
            #print(f"O cliente é o {client_id} e recebi isto na porta {porta+1}")
            #print(str(clientInfo['rtspSocket']))
            
            
            #for ficheiro, porta in self.ficheiros.items():
            #self.ligacoes[porta].connections[client_id] = [clientInfo, "INIT"]
            
            #ServerWorker(self.ligacoes, self.ficheiros, client_id, porta).run()
            #server.recvRtspRequest()

    def stream (self):
        while True:
            
            #threading.Event().wait(0.03)

            data = self.stream_socket.recv(25000)

            self.lock.acquire()
            for nodo in self.streaming_nodes.values():
                print(f"Estou a enviar para {nodo} {self.porta}")
                self.stream_socket.sendto(data, (nodo, self.porta))

            self.lock.release()

    def make_RTP(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26 # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)
        return rtpPacket.getPacket()
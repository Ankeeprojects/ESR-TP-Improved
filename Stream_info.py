from socket import *
from Topologia import Topologia
from VideoStream import *
import threading
import time
from RtpPacket import *

class Stream_Info:
    streaming_nodes : dict
    s : socket
    attempting : bool
    broadcasting : bool
    lock : threading.Lock
    topologia : Topologia

    def __init__(self, ficheiro, porta, topologia) -> None:
        self.streaming_nodes = dict()
        self.ficheiro = ficheiro
        self.porta = porta
        self.lock = threading.Lock()

        self.s = socket(AF_INET, SOCK_DGRAM)
        self.s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.s.bind(('', porta+1))

        self.stream_socket = socket(AF_INET, SOCK_DGRAM)
        self.stream_socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.topologia = topologia

        self.attempting = True

    def init(self):
        print(f"Streaming server a correr na porta {self.porta+1}")

        threading.Thread(target=self.stream).start()

        while True:
            message, address = self.s.recvfrom(1024)

            message = message.decode().split(" ")

            print(f"Recebi isto: {message[0]} {message[1]}")
            
            if message[0] == '0':
                print("Este gajo quer stream")
                #if not self.attempting:
                
                self.attempting = True
                self.s.sendto('1 16'.encode('utf-8'), address)
            elif message[0] == '2':
                print(f"A fechar o stream para o {message[1]}")
                self.lock.acquire()
                self.streaming_nodes.pop(message[1])
                self.lock.release()
            elif message[0] == '3':
                print(f"Recebi confirmação do stream para o {message[1]} {address}")
                self.lock.acquire()
                self.streaming_nodes[message[1]] = self.topologia.node_interfaces[message[1]][-1]
                self.lock.release()
            
                #message, address = self.s.recvfrom(1024)
                #else:
                #    pass
            #client_id = self.topologia.get_node_info(str(clientInfo['rtspSocket'][1][0]))
            #print(f"O cliente é o {client_id} e recebi isto na porta {porta+1}")
            #print(str(clientInfo['rtspSocket']))
            
            
            #for ficheiro, porta in self.ficheiros.items():
            #self.ligacoes[porta].connections[client_id] = [clientInfo, "INIT"]
            
            #ServerWorker(self.ligacoes, self.ficheiros, client_id, porta).run()
            #server.recvRtspRequest()

    def stream (self):
        stream = VideoStream(self.ficheiro)
        while True:
            
            threading.Event().wait(0.03)
            #time.sleep(0.03)

            data = stream.nextFrame()

            frameNumber = stream.frameNbr()  
            self.lock.acquire()
            imprimir = frameNumber % 30 == 0   
            if imprimir:
                print(f"Ficheiro: {self.ficheiro} Frame Number: {frameNumber} Porta: {self.porta}")
            #print(self.streaming_nodes)
            for nodo in self.streaming_nodes.values():
                #print(f"Estou a enviar para {nodo} {self.porta}")
                self.stream_socket.sendto(self.make_RTP(data, frameNumber), (nodo, self.porta))

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
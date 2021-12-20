import json
import sys
from json import JSONDecoder, JSONDecodeError
from socket import *
import threading
import time
from datetime import datetime
import re
from Nodo_Stream import Nodo_Stream
import Server_Stream
import Ligacoes_RTP
import ServerWorker
import signal

class Nodo:
    hello_port: int
    behind: str
    vizinhos: list # lista de tuplos com ip e id do nodo vizinhos
    ligacao_behind: socket
    lock: threading.Lock
    num_thread: int
    curr_threads: dict
    network_port: int
    streaming_port: int
    id: int
    ip_updates: str
    stream: Nodo_Stream
    ligacoes : dict

    def __init__(self, mensagem):
        self.host = AF_INET
        self.hello_port = 42000
        self.behind = None
        self.vizinhos = {}
        self.lock = threading.Lock()
        self.num_thread = 0
        self.curr_threads = {}
        self.network_port = 41999
        self.ipupdates = ""
        self.streaming_port = 36001 #Maybe change this
        self.ligacoes = dict()
        self.stream = Nodo_Stream(self.ligacoes)
        self.stream.run(mensagem)
        
        
    def hello(self):
        """Função que será threaded para envio de hello's para o servidor 
        de modo a manter o nodo como ativo do outro lado
        """
        self.lock.acquire()
        self.ligacao_behind = socket(AF_INET, SOCK_STREAM)
        self.ligacao_behind.connect((self.behind, self.hello_port))

        behind = self.behind
        self.lock.release()

        agora = datetime.now()
        print(agora)
        while True:
            try:
                while behind == self.behind:
                    
                    print(f"Enviei hello para o {self.behind}")
                    time.sleep(2)
                    self.ligacao_behind.send(str(self.id).encode('utf-8'))
                    #self.ligacao_behind.send("mingos".encode('utf-8'))
                    
                self.ligacao_behind.send('C'.encode('utf-8'))
                print("tentei mandar isto!")
                time.sleep(1)
            except BrokenPipeError:
                print("O pipe morreu!")
                self.ligacao_behind.close()

            while behind == self.behind:
                time.sleep(1)
                pass    
            

            self.lock.acquire()    
            behind = self.behind
            
            self.ligacao_behind.close()
            print(f"Vou tentar ligar-me ao {behind}")
            self.ligacao_behind = socket(AF_INET, SOCK_STREAM)    
            self.ligacao_behind.connect((self.behind, self.hello_port))
            self.lock.release()
            
    def forward(self):
        s = socket(AF_INET, SOCK_STREAM)
        s.bind((self.ip_updates, self.hello_port))

        s.listen()

        while True:
            prox_link, info = s.accept()
            print(f"Recebi ligação do {prox_link}")
            tmp = threading.Thread(target=self.forward_thread, args=(prox_link, info))
            tmp.start()
            self.curr_threads[info[0]] = (info[1], tmp)

            self.num_thread+= 1

    def forward_thread(self, cliente, info):
       # print(f"I am thread coise")
       # print(info[0])
        id = None
        mudanca_ligacao = False

        for nodo in self.vizinhos:
            if info[0] in nodo[0]:
            #if info[0] in nodo[0]:
                #print("Este gajo é vizinho!")
                id = nodo[1]
                print(id)
                break                
            #print(f"O nodo é {nodo[0]} e o vizinho é {info[0]}")  

        while True:
            try:
                s = cliente.recv(1024).decode('utf-8')
                if len(s) == 0:
                        if not mudanca_ligacao:
                            print(f'O cliente {id} desconectou-se. Alterar topologia')
                            #mensagem = "0" + id
                            mensagem = "0" + id
                            self.ligacao_behind.send(mensagem.encode('utf-8'))
                        #else:
                        #    print(f'O cliente {id} desligou-se mas é chill')
                        #try:
                        sys.exit(0)
                        #except:
                        #    pass
                elif s[-1] == 'C':
                    #print("O gajo tentou avisar! É só mudança de topologia")
                    mudanca_ligacao = True
                else:
                    print(f"Recebi um hello do {s}")
                    self.ligacao_behind.send(s.encode('utf-8'))
            except (timeout,error):
                #LIDAR COM ISTO
                print("seeya")
                cliente.close()
                sys.exit(1)
               
    
    def get_definicoes(self, s : socket, update : bool):
        """Função responsável por receber as condições do nodo (vizinhos e nodo anterior de overlay)
        
        Args:
            s (Socket): socket da conexão
        """
           
        tup = s.recv(1024).decode('utf-8').split('\n')
        
        #print("Consegui receber coisas!")
        self.lock.acquire()
        #print(f"tup0 {tup[0]}\ntup1 {tup[1]}\ntup2 {tup[2]}")
        self.vizinhos = json.loads(tup[0])
        behind = json.loads(tup[1])
        #print(f"Behind = {behind}, self = {self.behind}")
        
        #IMPORTANTE TIRAR ISTO SE DER MERDA
        """
        if self.behind is not None and self.behind != behind:
            #print("O gajo atrás mudou!")
            print("Estava a transmitir mas morri") 
            request = 'TEARDOWN ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.stream.rtspSeq)
            self.stream.rtspSocket.send(request.encode())
        else:
            print("Não mudou ou não era None")
        """
        self.behind = behind
        self.stream.behind = behind

        #print(f"O behind do stream é o {self.stream.behind}")

        if not update:
            info = json.loads(tup[2])
            #print(f"A info é {type(info)}")
            self.id = info[0]
            self.ip_updates = info[1]
            #print(f"O meu ID é o {self.id} e o meu ip para updates é o {self.ip_updates}")
        #else:
        #    print("É só update, mas recebi!")

        print(f"O meu nodo para trás é o {self.behind}")
        self.lock.release()
    
    def network_updates(self):
        """Função que verifica a existência de updates na topologia e 
        altera as definições do nodo consoante o que receba
        """
        s = socket(AF_INET, SOCK_STREAM)
        print(f"Estou a abrir os updates no ip {self.ip_updates} e porta {self.network_port}")
        s.bind((self.ip_updates, self.network_port))

        s.listen()

        while True:
            servidor, info = s.accept()
            self.get_definicoes(servidor, True)
            
            #print("recebi isto porque sou burro :)")
            #tmp = threading.Thread(target=self.teste, args=(servidor, info)) #novo
            #tmp.start() #novo
            

    def streaming_server(self, ficheiro):
        
        self.rtspSocket = socket(AF_INET, SOCK_STREAM)
        self.rtspSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.rtspSocket.bind(('', self.streaming_port))
        self.rtspSocket.listen(5)  
		# Receive client info (address,port) through RTSP/TCP session
        
        print(f"Streaming server a correr na porta {self.streaming_port}")

        
        while True:
            clientInfo = {}
            
            clientInfo['rtspSocket'] = self.rtspSocket.accept()
            print("Connected to: %s" % str(clientInfo['rtspSocket'][1]))
            client_ip = str(clientInfo['rtspSocket'][1][0])
            #client_id = self.topologia.get_node_info(str(clientInfo['rtspSocket'][1][0]))
            #print(f"O cliente é o {client_id}")
            print(str(clientInfo['rtspSocket']))
            
            self.ligacoes.connections[client_ip] = [clientInfo, "INIT"]
            ServerWorker.ServerWorker(self.ligacoes, ficheiro, client_ip).run()
            #server.recvRtspRequest()

    def signal_handler(self, signal, frame):
        print(f'You pressed Ctrl+C! E o meu estado é {self.stream.state}')
        try:
            
            print(f"As cenas do gajo são : {self.stream.ligacoes.items()}")
            
            for ligacao in self.stream.ligacoes.connections.values():
                if ligacao[0].get('rtspSocket'):
                    ligacao[0]['rtspSocket'].close()
                    print("Matei este gajo!")
                else:
                    print("Não tinha!")

            if self.stream.state == self.stream.PLAYING or self.stream.state == self.stream.READY:
                print("Estava a transmitir mas morri") 
                request = 'TEARDOWN ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.stream.rtspSeq)
                self.stream.rtspSocket.send(request.encode())        
            self.stream.rtspSocket.close()
            self.rtspSocket.close()
            print("Cheguei aqui bla")
            sys.exit(0)
        except:
                sys.exit(0)


    def evento(self):
        print('Press Ctrl+C')
        forever = threading.Event()
        forever.wait()

    def init(self, server, port: int):
        """Função de inicialização de um nodo, responsável por definir as condições iniciais 
        do nodo e iniciar as threads de hellos, forwarding e updates.

        Args:
            server ([type]): ip do servidor ao qual vai pedir as suas condições iniciais
            port (int): porta de ligação ao servidor
        """
        signal.signal(signal.SIGINT, self.signal_handler)
        
        threading.Thread(target=self.evento)
        
        s = socket(AF_INET, SOCK_STREAM)
        #print("Cheguei aqui!")
        s.connect((server, port))

        #print("Conectei-me e esta merda está operacional.")
        
        self.get_definicoes(s, False)
        
        s.close()
        try :
            threading.Thread(target=self.streaming_server, args= ('movie.Mjpeg',)).start() 
            threading.Thread(target=self.network_updates).start()    
            threading.Thread(target=self.forward).start()
            threading.Thread(target=self.hello).start()
        except KeyboardInterrupt:
            print("Pronto cá estamos")    
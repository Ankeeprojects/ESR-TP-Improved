import sys
from socket import *
import threading
import json
from datetime import datetime, timedelta
import time
import Topologia
from ServerWorker import ServerWorker
import Server_Stream
import Ligacoes_RTP

class Servidor:
    nodos_atividade: dict # dict de id do nodo para time do último hello
    num_thread: int
    threads: dict
    network_port: int
    lock : threading.Lock
    topologia : Topologia
    streaming_port : int
    server_port : int
    ligacoes : dict
    ficheiros : dict

    def __init__(self, ficheiros):
        self.nodos_atividade = dict()
        self.num_thread = 0
        self.threads = dict()
        self.network_port = 41999
        self.lock = threading.Lock()
        self.topologia = Topologia.Topologia()
        self.streaming_port = 36001
        self.server_port = 12000
        self.stream_loc_port = 36002
        self.ligacoes = dict()
        self.ficheiros = ficheiros

    def init_server(self):
        threading.Thread(target=self.server).start()
        threading.Thread(target=self.hello_server).start()
        threading.Thread(target=self.activity_server).start()
        threading.Thread(target=self.streaming_server).start()
        threading.Thread(target=self.stream_locator).start()

    def stream_locator(self):
        s = socket(AF_INET, SOCK_STREAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.stream_loc_port))

        s.listen()

        print(f"Localizador de streams a correr na porta {self.stream_loc_port}")

        while True:
            cliente, info = s.accept()
            print("cheguei aqui!")
            print(type(info[0]))
            node_id = self.topologia.get_node_info(str(info[0]))
            #print(f"Este cliente é o {node_id}")
            mensagem = cliente.recv(256).decode('utf-8')
            
            print(f"O gajo está pedir {mensagem}")

            nodo_stream = self.topologia.get_closest_overlay(str(info[0]))
            port = str(self.ficheiros[mensagem])

            mensagem = str(nodo_stream) + "\n" + port
            print(f"O nodo mais próximo é o {nodo_stream} e deve abrir a porta {port}")
            cliente.send(mensagem.encode('utf-8'))
            cliente.close()           

    def streaming_server(self):
        for ficheiro, porta in self.ficheiros.items():
            self.ligacoes[porta] = Ligacoes_RTP.Ligacoes_RTP()
        
        self.rtspSocket = socket(AF_INET, SOCK_STREAM)
        self.rtspSocket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.rtspSocket.bind(('', self.streaming_port))
        self.rtspSocket.listen(5)        
		# Receive client info (address,port) through RTSP/TCP session
        
        print(f"Streaming server a correr na porta {self.streaming_port}")

        Server_Stream.Server_Stream(self.ligacoes).run(self.ficheiros)

        while True:
            clientInfo = {}
            clientInfo['rtspSocket'] = self.rtspSocket.accept()
            print("Connected to: %s" % str(clientInfo['rtspSocket'][1]))
            
            client_id = self.topologia.get_node_info(str(clientInfo['rtspSocket'][1][0]))
            print(f"O cliente é o {client_id}")
            print(str(clientInfo['rtspSocket']))
            
            
            for ficheiro, porta in self.ficheiros.items():
                self.ligacoes[porta].connections[client_id] = [clientInfo, "INIT"]
            
            ServerWorker(self.ligacoes, self.ficheiros, client_id, 36000 ).run()
            #server.recvRtspRequest()
        
    def signal_handler(self, signal, frame):
        print('You pressed Ctrl+C!')
        try:
            if self.stream.state == self.stream.PLAYING or self.stream.state == self.stream.READY:
                print("Estava a transmitir mas morri") 
                request = 'TEARDOWN ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.stream.rtspSeq)
                self.stream.rtspSocket.send(request.encode())
                self.stream.rtspSocket.close()
            sys.exit(0)
        except:
                sys.exit(0)

    def activity_server(self):
        #s = socket(AF_INET, SOCK_STREAM)
        #s.bind(('', self.network_port))

        while True:
            time.sleep(2)
            
            nodos_apagados = []

            self.lock.acquire()    
            for nodo,last_hello in self.nodos_atividade.items():
                diferenca = datetime.now() - last_hello

                if nodo != self.topologia.get_starter_node():
                    if diferenca.seconds > 5 and nodo not in nodos_apagados and nodo != '9':
                        print("O gajo deu timeout!")
                        nodos_apagados.append(nodo)
                    #else:
                    #    print("O gajo está fixe!")

            if nodos_apagados:
                print(f"Vou apagar os nodos: {nodos_apagados}")
                

                for nodo in nodos_apagados:
                    self.nodos_atividade.pop(nodo)
                    self.topologia.remove_node_overlay(nodo)
                #TODO: MANDAR A NOVA TOPOLOGIA AOS RESTANTES
                
                #s = socket(AF_INET, SOCK_STREAM)
                        
                for nodo in self.nodos_atividade:
                    if nodo != self.topologia.get_starter_node():
                        #print(f"O nodo é o {nodo}")
                        #print(f"O IP do gajo é o {self.topologia.node_interfaces[nodo][-1]}")
                        s = socket(AF_INET, SOCK_STREAM) #novo
                 
                        s.connect((self.topologia.node_interfaces[nodo][-1], 41999))
                        #print("consegui ligar-me!")
                        self.envia_info_topologia(nodo,s, False)
                        s.close() #novo
                '''
                for nodo, info in self.nodos_atividade.items():
                    if nodo != 'O1':
                    #if nodo == 'O2':
                        print(info[0])
                        s.connect((info[0], self.network_port))
                        vizinhos = dict()

                        vizinhos["O3"] = ['10.0.1.2', 12000, 100]
                        
                        vizinhos_d = json.dumps(vizinhos, sort_keys=True, default=str)

                        behind = json.dumps(self.nodos_atividade["O1"], default=str)

                        s.send(str.encode("\n".join([str(vizinhos_d), str(behind)])))
                '''
            self.lock.release()

    def ligacao_nodo(self, cliente: socket, info: tuple):
        """Função chamada sempre que um nodo faz uma ligação so servidor

        Args:
            cliente (socket): socket utilizada para comunicar com esse cliente
            info (tuple): tuplo que tem na primeira posição o ip da interface que se ligou e na segunda, a porta utilizada para essa ligação
        """
        print(f'Estou a receber uma ligação do {info[0]}:{info[1]}')
        node_id = self.topologia.get_node_info(str(info[0]))
        self.topologia.add_node_overlay(node_id)
        #print(f'node_id tem o tipo {type(node_id)}')
        self.nodos_atividade[node_id] = datetime.now()

        if self.topologia.get_behind(node_id) == '10.0.3.10':
            self.ligacoes.lock.acquire()
            self.ligacoes.connections = dict()
            self.ligacoes.lock.release()
        #s.bind(('', 42001)
        #time.sleep(3)
        #TODO: VER COMO CHEGAR AO IP CORRETO
        for nodo, _ in self.nodos_atividade.items():
            print(f"node_id = {node_id} node = {nodo} starter= {self.topologia.starter_node}")
            if nodo != self.topologia.get_starter_node():
                if nodo != node_id:
                    #print(f"O nodo é o {nodo}")
                    #print(f"O IP do gajo é o {self.topologia.node_interfaces[nodo][-1]}")

                    try:
                        s = socket(AF_INET, SOCK_STREAM)
                        s.connect((self.topologia.node_interfaces[nodo][-1], 41999))
                        #print(f'Aqui vai o link: {type(link)}')
                        self.envia_info_topologia(nodo, s, False)    
                    finally:
                        s.close()
                else: 
                    self.envia_info_topologia(nodo, cliente, True)

        
    def envia_info_topologia(self, nodo : str, cliente : socket, login : bool):
        print(f'nodo = {nodo}')
        vizinhos = self.topologia.get_neighbors(nodo)
        print(f'vizinhos = {vizinhos}')
        vizinhos_json = json.dumps(vizinhos, default=str)
        
        behind = self.topologia.get_behind(nodo)
        print(f'behind = {behind}')
        
        behind_json = json.dumps(behind, default=str)

        if login:
            info = (nodo, self.topologia.node_interfaces[nodo][-1])
            info_json = json.dumps(info)

            conteudo = "\n".join([str(vizinhos_json), str(behind_json), str(info_json)])
            print(conteudo)
            cliente.send(str.encode(conteudo))
        else:
            cliente.send(str.encode("\n".join([str(vizinhos_json), str(behind_json)])))

    def server(self):
        """Função responsável por lidar com conexões de nodos para a ligação dos mesmos
        """
        s = socket(AF_INET, SOCK_STREAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind(('', self.server_port))

        s.listen()

        print(f"Servidor a correr na porta {12000}")

        self.nodos_atividade[self.topologia.get_starter_node()] = datetime.now()

        while True:
            cliente, info = s.accept()
            threading.Thread(target=self.ligacao_nodo, args=(cliente, info)).start()

        s.close()

    def hello_worker(self, num_thread: int, cliente: socket, info: tuple, stop):
        """Função que será threaded para tratar os hellos recebidos do lado de cada nodo

        Args:
            num_thread (int): número da thread
            cliente (socket): socket para comunicar com o nodo
            info (tuple): informação recebida do nodo
            stop ([type]): [description]
        """
        cliente.settimeout(4)
        #print("cheguei aqui!")
        mudanca_ligacao = False

        while True:
            try:
                mensagem = cliente.recv(1024).decode('utf-8')
                
                if len(mensagem) == 0:
                    pass
                elif mensagem[-1] == 'C':
                    mudanca_ligacao = True
                elif mensagem[0] != '0':
                    print(f"Recebi um hello do {mensagem}")

                    if self.nodos_atividade.get(mensagem):
                        self.nodos_atividade[mensagem] = datetime.now()
                        print("Timer updated")
                else: 
                    print(mensagem[1:])
                    nodo = mensagem[1:]

                    self.lock.acquire()
                    if self.nodos_atividade.get(nodo):
                        self.nodos_atividade.pop(nodo)
                        self.topologia.remove_node_overlay(nodo)
                        
                        for nodo in self.nodos_atividade:
                            if nodo != self.topologia.get_starter_node():
                                #print(f"O nodo é o {nodo}")
                                #print(f"O IP do gajo é o {self.topologia.node_interfaces[nodo][-1]}")
                                s = socket(AF_INET, SOCK_STREAM) #novo
                        
                                s.connect((self.topologia.node_interfaces[nodo][-1], 41999))
                                #print("consegui ligar-me!")
                                self.envia_info_topologia(nodo,s, False)
                                s.close() #novo
                    self.lock.release()

                # else:
                #     print(f"Recebi um hello do {s}")
                #     #print(type(s))
                #     if self.nodos_atividade.get(s):
                #         self.nodos_atividade[s][1] = datetime.now()
                #         print("Timer updated!!!")

            except (timeout, error):
                #LIDAR COM ISTO, TALVEZ NÃO SEJA PRECISO PORQUE O SISTEMA RESOLVE
                print(f'O cliente {info[0]} deu timeout. Alterar topologia.')
                sys.exit(1)
            else:
                if len(mensagem) == 0:
                    if not mudanca_ligacao:
                        print(f'O cliente {info[0]} desconectou-se. Alterar topologia.')
                        
                        for id, ips in self.topologia.node_interfaces.items():
                            if info[0] in ips:
                                nodo = id
                                print(f"O nodo que morreu é o {id}")
                                break
                        
                        if self.nodos_atividade.get(nodo):
                            self.nodos_atividade.pop(nodo)
                            self.topologia.remove_node_overlay(nodo)

                        for nodo in self.nodos_atividade:
                            if nodo != self.topologia.get_starter_node():
                                #print(f"O nodo é o {nodo}")
                                #print(f"O IP do gajo é o {self.topologia.node_interfaces[nodo][-1]}")
                                s = socket(AF_INET, SOCK_STREAM) #novo
                        
                                s.connect((self.topologia.node_interfaces[nodo][-1], 41999))
                                #print("consegui ligar-me!")
                                self.envia_info_topologia(nodo,s, False)
                                s.close() #novo
                    else:
                        print("O nodo desconectou-se por mudança de topologia.")
                    sys.exit(0)
                    
    def hello_server(self):
        """Função threaded que está responsável por gerir threads para cada ligação de hellos vinda de nodos
        """
        host = ''
        port = 42000

        s = socket(AF_INET, SOCK_STREAM)
        s.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        s.bind((host, port))

        s.listen()

        print(f"Servidor de hellos está a correr na thread {threading.currentThread()}")

        stop_threads = False
        while True:
            cliente, info = s.accept()
            #print("Recebi ligação pra hellos!")
            tmp = threading.Thread(target=self.hello_worker, args=(self.num_thread, cliente, info, lambda: stop_threads))
            tmp.start()
            self.threads[info[0]] = [info[1], tmp]

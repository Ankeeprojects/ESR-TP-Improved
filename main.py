import sys
import os
from Nodo import *
from Servidor import *
from tkinter import TclError, Tk
from Client import Client

def main():
    num_args = len(sys.argv)
    print(num_args)
    if num_args > 2:
        
        ficheiros = dict()
        step = 0
        for ficheiro in sys.argv[1:]:
            ficheiros[ficheiro] = 36000 + step
            step+=3

        print(f"Estou a ler {ficheiros}")
        s = Servidor(ficheiros)
        s.init_server()

    elif num_args < 2:

        with open("config","r") as file:
            server_ip = re.split(" ",file.readline()[:-1])[1]
        
        s = socket(AF_INET, SOCK_STREAM)
        s.connect((server_ip, 36002))

        s.send('0'.encode('utf-8'))

        mensagem = s.recv(256).decode('utf-8').split("\n")

        portas = [int(x) for x in mensagem[:-1]]
        print(portas)
        n = Nodo(portas)
        n.init(server_ip, 12000)

    elif num_args == 2:
        #serverAddr = sys.argv[1]
        serverPort = 36002
        #rtpPort = sys.argv[3]
        fileName = sys.argv[1]

        with open("config","r") as file:
            serverAddr = re.split(" ",file.readline()[:-1])[1]

        s = socket(AF_INET, SOCK_STREAM)
        s.connect((serverAddr, int(serverPort)))

        print(f"liguei-me ao {serverAddr}:{serverPort}")
        print("Consegui ligar-me ao server para pedir info de stream")
        s.send(fileName.encode('utf-8'))
        dados = s.recv(1024).decode('utf-8')

        lista = dados.split("\n")
        print(lista)
        ip, rtpPort = lista[0], lista[1]
        print(f"O IP do server é o {ip} e a porta é {rtpPort}")
        
        portas = lista[2:]

        print(portas)

        root = Tk()
        try:
            # Create a new client
            app = Client(root, ip, rtpPort, fileName, serverAddr, serverPort)
            app.master.title("RTPClient")	
            root.mainloop()
            root.update()
        except TclError:
            os._exit(0)
    else:
        print("Número de argumentos inválido.")


if __name__ == "__main__":
    main()

import sys
import os
from Nodo import *
from Servidor import *
from tkinter import TclError, Tk
#from Client import Client

#12000 --> Servidor para obter ID etc
#42000 --> Hellos

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
        nodo = Nodo()
        nodo.init()
       

    elif num_args == 2:
        serverPort = 42002
        fileName = sys.argv[1]

        with open("config","r") as file:
            serverAddr = re.split(" ",file.readline()[:-1])[1]

        s = socket(AF_INET, SOCK_DGRAM)

        s.sendto(fileName.encode('utf-8'), (serverAddr, serverPort))

        info, address = s.recvfrom(1024)

        info = json.loads(info)

        
        #s.sendto("")
        """
        root = Tk()
        try:
            # Create a new client
            app = Client(root, ip, rtpPort, fileName, serverAddr, serverPort, portas)
            app.master.title("RTPClient")	
            root.mainloop()
            root.update()
        except TclError:
            os._exit(0)
        """
    else:
        print("Número de argumentos inválido.")



if __name__ == "__main__":
    main()

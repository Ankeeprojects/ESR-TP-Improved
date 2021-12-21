from VideoStream import *
from RtpPacket import *
import Ligacoes_RTP
import threading
import traceback
import sys
import time

class Server_Stream:
    ligacoes : dict

    def __init__(self, ligacoes):
        self.ligacoes = ligacoes
        
    def run(self, ficheiro, porta):
        print(f"Ficheiro: {ficheiro} porta: {porta}")
        threading.Thread(target=self.sendRtp, args=(ficheiro,porta)).start()

    def sendRtp(self, ficheiro, porta):
        """Send RTP packets over UDP."""
        stream = VideoStream(ficheiro)
        while True:
            #self.clientInfo['event'].wait(0.05) 
            time.sleep(0.03)
            # Stop sending if request is PAUSE or TEARDOWN
            #if self.clientInfo['event'].isSet(): 
            #        break 
                    
            #Cena que quero meter do outro lado
            data = stream.nextFrame()
            #print("será?")
            frameNumber = stream.frameNbr()  
            imprimir = frameNumber % 30 == 0   
            if imprimir:
                print(f"Ficheiro: {ficheiro} Frame Number: {frameNumber} Porta: {porta}")
            
            self.ligacoes[porta].lock.acquire() #novo
            for elemento in self.ligacoes[porta].connections.values():
                #print(elemento[1])
                if elemento[1] == 2:    
                    try:
                        address = elemento[0]['rtspSocket'][1][0]
                        #VOLTAR A METER
                        #port = int(elemento[0]['rtpPort'])
                        if imprimir:
                            print(f"Estou a enviar para o {address}:{porta}")

                        elemento[0]['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,porta))
                    except:
                        print("Vizinho mudou!")
                        # print("RTP Address: %s, Port: %d, FrameNum: %d" % (address,port,frameNumber))
                        # print('-'*60)
                        # traceback.print_exc(file=sys.stdout)
                        # print('-'*60)
                        # sys.exit(1)
            self.ligacoes[porta].lock.release()

    def makeRtp(self, payload, frameNbr):
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
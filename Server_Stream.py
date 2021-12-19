from VideoStream import *
from RtpPacket import *
import Ligacoes_RTP
import threading
import traceback
import sys
import time

class Server_Stream:
    ligacoes : list
    stream : VideoStream
    ligacoes : Ligacoes_RTP.Ligacoes_RTP

    def __init__(self, ligacoes, filename):
        self.ligacoes = ligacoes
        self.stream = VideoStream(filename)

    def run(self):
        threading.Thread(target=self.sendRtp).start()

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            #self.clientInfo['event'].wait(0.05) 
            time.sleep(0.03)
            # Stop sending if request is PAUSE or TEARDOWN
            #if self.clientInfo['event'].isSet(): 
            #        break 
                    
            #Cena que quero meter do outro lado
            data = self.stream.nextFrame()
            #print("será?")
            frameNumber = self.stream.frameNbr()     
            if frameNumber % 30 == 0:
                print("Frame Number: " + str(frameNumber))
            
            self.ligacoes.lock.acquire() #novo
            for elemento in self.ligacoes.connections.values():
                #print(elemento[1])
                if elemento[1] == 2:    
                    try:
                        address = elemento[0]['rtspSocket'][1][0]
                        port = int(elemento[0]['rtpPort'])
                        print(f"Estou a enviar para o {address}")

                        elemento[0]['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,port))
                    except:
                        print("Vizinho mudou!")
                        # print("RTP Address: %s, Port: %d, FrameNum: %d" % (address,port,frameNumber))
                        # print('-'*60)
                        # traceback.print_exc(file=sys.stdout)
                        # print('-'*60)
                        # sys.exit(1)
            self.ligacoes.lock.release()

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
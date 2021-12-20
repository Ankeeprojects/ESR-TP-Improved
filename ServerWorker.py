from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket

class ServerWorker:
	SETUP = 'SETUP'
	PLAY = 'PLAY'
	PAUSE = 'PAUSE'
	TEARDOWN = 'TEARDOWN'
	
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT

	OK_200 = 0
	FILE_NOT_FOUND_404 = 1
	CON_ERR_500 = 2
	
	clientInfo = {}

	ficheiro : str

	port : int

	def __init__(self, ligacoes, ficheiro, id, port):
		self.ligacoes = ligacoes
		self.ficheiro = ficheiro
		self.id = id
		self.port = port

	def run(self):
		threading.Thread(target=self.recvRtspRequest).start()
	
	def recvRtspRequest(self):
		"""Receive RTSP request from the client."""
		try:
			connSocket = self.ligacoes[self.port].connections[self.id][0]['rtspSocket'][0]
			while True:            
				data = connSocket.recv(256)
				if data:
					print("Data received:\n" + data.decode("utf-8"))
					self.processRtspRequest(data.decode("utf-8"))
				else:
					connSocket.close()
					print("Estourou")
					sys.exit(0)
					#break
		except ConnectionResetError:
			print("não deu!")

	def processRtspRequest(self, data):
		"""Process RTSP request sent from the client."""
		# Get the request type
		request = data.split('\n')
		line1 = request[0].split(' ')
		requestType = line1[0]
		
		# Get the media file name
		filename = line1[1]
		
		# Get the RTSP sequence number 
		seq = request[1].split(' ')
		
		# Process SETUP request
		if requestType == self.SETUP:
			self.ligacoes[self.port].lock.acquire()
			self.ligacoes[self.port].connections[self.id][1] = self.READY
			
			print(f"Recebi um pedido na porta {self.port}")
			# Generate a randomized RTSP session ID
			self.ligacoes[self.port].connections[self.id][0]['session'] = randint(100000, 999999)
			
			# Send RTSP reply
			self.replyRtsp(self.OK_200, seq[1])
			
			# Get the RTP/UDP port from the last line
			self.ligacoes[self.port].connections[self.id][0]['rtpPort'] = self.port

			#for nodo, cenas in self.ligacoes.connections.items():
			#	print(f"O nodo {nodo} tem a info {cenas}")

			self.ligacoes[self.port].lock.release()

		#TODO
		# Process PLAY request 		
		elif requestType == self.PLAY:
			#if self.ligacoes.connections[self.id][1] == self.READY:
				print("processing PLAY\n")
				self.ligacoes[self.port].connections[self.id][1] = self.PLAYING
				
				# Create a new socket for RTP/UDP
				self.ligacoes[self.port].connections[self.id][0]["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				
				self.replyRtsp(self.OK_200, seq[1])
				
				# Create a new thread and start sending RTP packets
				#self.ligacoes.connections[self.id][0]['event'] = threading.Event()
				#self.ligacoes.connections[self.id][0]['worker']= threading.Thread(target=self.sendRtp) 
				#self.ligacoes.connections[self.id][0]['worker'].start()
		
		# Process PAUSE request
		elif requestType == self.PAUSE:
			if self.ligacoes[self.port].connections[self.id][1] == self.PLAYING:
				print("processing PAUSE\n")
				self.ligacoes[self.port].connections[self.id][1] = self.READY
				
				#self.clientInfo['event'].set()
			
				self.replyRtsp(self.OK_200, seq[1])
		
		# Process TEARDOWN request
		elif requestType == self.TEARDOWN:
			print("processing TEARDOWN\n")
			
			#if 'event' in self.clientInfo:
			#	self.clientInfo['event'].set()
			
			self.replyRtsp(self.OK_200, seq[1])

			for porta in self.ligacoes:
				if self.ligacoes[self.port].connections.get(self.id):
					self.ligacoes[self.port].lock.acquire()
					self.ligacoes[self.port].connections[self.id][0]['rtpSocket'].close()
					self.ligacoes[self.port].connections.pop(self.id)
					self.ligacoes[self.port].lock.release()
			#for nodo in self.ligacoes[self.port].connections.keys():
			#	print(nodo)
			# Close the RTP socket
			#if 'rtpSocket' in self.clientInfo:
			
	def sendRtp(self):
		"""Send RTP packets over UDP."""
		while True:
			self.clientInfo['event'].wait(0.05) 
			
			# Stop sending if request is PAUSE or TEARDOWN
			if self.clientInfo['event'].isSet(): 
				break 
				
			#Cena que quero meter do outro lado
			data = self.clientInfo['videoStream'].nextFrame()
			
			#for elemento in lista:
			#   if elemento[1] == "PLAYING":
			if data: 
				frameNumber = self.clientInfo['videoStream'].frameNbr()
				print("Frame Number: " + str(frameNumber))
				try:
					address = self.clientInfo['rtspSocket'][1][0]
					port = int(self.clientInfo['rtpPort'])
					self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),(address,port))
				except:
					print("RTP Address: %s, Port: %d, FrameNum: %d" % (address,port,frameNumber))
					print('-'*60)
					traceback.print_exc(file=sys.stdout)
					print('-'*60)
					sys.exit(1)

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
		
	def replyRtsp(self, code, seq):
		"""Send RTSP reply to the client."""
		if code == self.OK_200:
			#print("200 OK")
			reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.ligacoes[self.port].connections[self.id][0]['session'])
			connSocket = self.ligacoes[self.port].connections[self.id][0]['rtspSocket'][0]
			connSocket.send(reply.encode())
		
		# Error messages
		elif code == self.FILE_NOT_FOUND_404:
			print("404 NOT FOUND")
		elif code == self.CON_ERR_500:
			print("500 CONNECTION ERROR")

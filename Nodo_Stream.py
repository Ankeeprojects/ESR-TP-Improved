from os import initgroups
from VideoStream import *
from RtpPacket import *
import Ligacoes_RTP
import threading
import traceback
import sys
import time
import socket

class Nodo_Stream:
	stream : VideoStream
	ligacoes : Ligacoes_RTP.Ligacoes_RTP
	streaming : bool

	INIT = 0
	READY = 1
	PLAYING = 2
	TIMEOUT = 3
	#state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	def __init__(self, ligacoes):
		self.ligacoes = ligacoes
		self.streaming = False
		self.behind = None
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.rtp_port = 36000
		self.rtsp_port = 36001
		self.rtspSeq = list()
		self.sessionId = list()
		self.requestSent = list()
		self.teardownAcked = 0
		#self.connectToServer()
		self.frameNbr = 0
		self.state = dict()

		self.rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self.rtpSocket.settimeout(0.5)
		except:
			pass

		self.rtpSocket.bind(('', 36000))

	def run(self, porta):
		threading.Thread(target=self.sendRtp, args=(porta,)).start()
		self.state = 0
		self.requestSent = -1
		self.rtspSeq = 0
		self.sessionId = 0


	def sendRtp(self, porta):
		"""Send RTP packets over UDP."""
		print(f"A minha porta é {porta}")
		while True:
			#self.clientInfo['event'].wait(0.05) 
			
			#time.sleep(0.03)
				# Stop sending if request is PAUSE or TEARDOWN
				#if self.clientInfo['event'].isSet(): 
				#        break         
				#Cena que quero meter do outro lado		
			behind = self.behind	
			if self.state == self.PLAYING and behind == self.behind:
				try:
					#print("Cheguei aqui e estou a tentar receber qualquer coisa")
					data = self.rtpSocket.recv(20480)
					#print("cheguei aqui?")
					if data:
						#rtpPacket = RtpPacket()
						#rtpPacket.decode(data)
						
						#currFrameNbr = rtpPacket.seqNum()
						#print("Current Seq Num: " + str(currFrameNbr))
											
						#if currFrameNbr > self.frameNbr or (self.REPEAT and (self.frameNbr - currFrameNbr) > 50): # Discard the late packet if didnt start again
							#print("Isto é verdade")
							
							# frameNumber = self.stream.frameNbr()     
							# if frameNumber % 30 == 0:
							# 	print("Frame Number: " + str(frameNumber))
						try:
							quantos_streaming = 0
							self.ligacoes[porta].lock.acquire()
							for elemento in self.ligacoes[porta].connections.values():
							#print(elemento[1])
								if elemento[1] == 2:
									quantos_streaming+=1    
									try:
										address = elemento[0]['rtspSocket'][1][0]
										port = int(elemento[0]['rtpPort'])
										#elemento[0]['rtpSocket'].sendto(rtpPacket,(address,port))
										elemento[0]['rtpSocket'].sendto(data,(address,port))
									except:
										#print("RTP Address: %s, Port: %d, FrameNum: %d" % (address,port,frameNumber))
										print('-'*60)
										traceback.print_exc(file=sys.stdout)
										print('-'*60)
										sys.exit(1)
						finally:
							self.ligacoes[porta].lock.release()

						if quantos_streaming == 0:
							self.rtspSeq+=1
							request = 'PAUSE ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.rtspSeq[porta])
							self.rtspSocket.send(request.encode())
							#self.state = self.PAUSE

							print("Fiquei sem pessoal!")

							while quantos_streaming == 0:
								for elemento in self.ligacoes[porta].connections.values():
									if elemento[1] == 2:
										quantos_streaming = 1
								time.sleep(0.4)
							print("Já tenho pessoal de novo!")

							self.rtspSeq[porta]+=1

							request = 'PLAY ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.rtspSeq[porta])

							self.rtspSocket.send(request.encode())

						
							#self.frameNbr = currFrameNbr
							#print("Payload length: " + str(len(rtpPacket.getPayload())))
							#self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
						#elif not self.REPEAT and (self.frameNbr - currFrameNbr) > 50:
						#	break

							#Inserir informação do que acontece se ninguém estiver a ouvir 
							#Enviar Pause para trás!
				except socket.timeout:
						# Upon receiving ACK for TEARDOWN request,
						# close the RTP socket
						print("Dei timeout!")

						self.state = self.TIMEOUT		
						try :
							#if self.teardownAcked == 1:
								#self.rtpSocket.shutdown(socket.SHUT_RDWR)
								self.rtpSocket.close()
								#break
								#pass
						except:
							pass
						
			else:
				#TODO
				self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				
				while self.behind is None:
					print("Ainda não!")
					time.sleep(0.2)

				print(f"O meu behind é o {self.behind}")
				try:
					self.rtspSocket.connect((self.behind, self.rtsp_port))
					print("Connected to " + self.behind)
				except:
					print("Não consegui ligar-me ao ")
				
				threading.Thread(target=self.recvRtspReply).start()

				if self.state == self.TIMEOUT:
					print("Entrei nesta cena")
					self.rtspSeq = 1
					self.state = self.INIT
					self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
					self.rtpSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
					
					try:
						self.rtpSocket.settimeout(0.5)
					except:
						pass
					self.rtpSocket.bind(('', porta))
				else:
					self.rtspSeq += 1

				print(self.rtpSocket)
				print(f'vou enviar um rtsp de {self.rtspSeq}')
				request = 'SETUP ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.rtspSeq) + '\nRTP PORT NUM: ' + str(porta)

				#maybe not needed
				self.requestSent = self.SETUP

				self.rtspSocket.send(request.encode())

				#verificar se o vizinho mudou probably para os timeouts
				# if self.state == self.READY:
				# 	print("está fixe!")
				# else:
				# 	print("nope!")
				# time.sleep(10)
				print(self.state)
				while self.state == self.INIT:
					time.sleep(0.2)

				self.rtspSeq += 1
		
				print('\nPLAY event\n')
				
				print("aqui também?")
				# Write the RTSP request to be sent.
				# request = ...
				request = 'PLAY ' + 'movie.Mjpeg' + '\nCseq: ' + str(self.rtspSeq)
				# Keep track of the sent request.
				# self.requestSent = ...
				self.requestSent = self.PLAY	
				#print("será?")

				self.rtspSocket.send(request.encode())

				while self.state != self.PLAYING:
					time.sleep(0.2)

				print("ESTOU A PLAYAR")
				#time.sleep(5)

	def recvRtspReply(self):
			"""Receive RTSP reply from the server."""
			try:
				while True:
					reply = self.rtspSocket.recv(1024)
					
					if reply: 
						self.parseRtspReply(reply.decode("utf-8"))
					
					# Close the RTSP socket upon requesting Teardown
					if self.requestSent == self.TEARDOWN:
						self.rtspSocket.shutdown(socket.SHUT_RDWR)
						print("Fechei cenas")
						self.rtspSocket.close()
						break
			except:
				print("Vim ter aqui")			
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		print(f"Data: {data}")
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		#print(f"o seqnum é {seqNum} e o outro é {self.rtspSeq}")

		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			print(f"o meu session ID é o {self.sessionId} e o outro é o {session}")
			#ALTERADO
			#if self.sessionId == 0:
			self.sessionId = session
			
			# Process only if the session ID is the same
			#if self.sessionId == session:
			if int(lines[0].split(' ')[1]) == 200: 
				if self.requestSent == self.SETUP:
					#-------------
					# TO COMPLETE
					#-------------
					# Update RTSP state.
					# self.state = ...
					print("processing SETUP\n")
					if self.state == self.INIT:
						self.state = self.READY
					# Open RTP port.
					
					#self.openRtpPort() 
				elif self.requestSent == self.PLAY:
					# self.state = ...
					if self.state == self.READY:
						self.state = self.PLAYING
					print('\nPLAY sent\n')
				elif self.requestSent == self.PAUSE:
					# self.state = ...
					if self.state == self.PLAYING:
						self.state = self.READY
					# The play thread exits. A new thread is created on resume.
					self.playEvent.set()
				elif self.requestSent == self.TEARDOWN:
					# self.state = ...
					self.state = self.INIT
					# Flag the teardownAcked to close the socket.
					self.teardownAcked = 1 
					if self.playEvent:
						self.playEvent.set()

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
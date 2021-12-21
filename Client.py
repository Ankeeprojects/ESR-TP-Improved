from tkinter import *
import tkinter.messagebox as messagebox
from PIL import Image, ImageTk, ImageFile
import socket, threading, sys, traceback, os, time

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"
ImageFile.LOAD_TRUNCATED_IMAGES = True

class Client:
	INIT = 0
	READY = 1
	PLAYING = 2
	state = INIT
	
	SETUP = 0
	PLAY = 1
	PAUSE = 2
	TEARDOWN = 3

	REPEAT = True
	
	# Initiation..
	def __init__(self, master, serveraddr, rtpport, filename, stream_locator, stream_loc_port):
		self.master = master
		self.master.protocol("WM_DELETE_WINDOW", self.handler)
		self.createWidgets()
		self.serverAddr = serveraddr
		self.serverPort = int(rtpport) + 1
		self.rtpPort = int(rtpport)
		self.fileName = filename
		self.rtspSeq = 0
		self.sessionId = 0
		self.requestSent = -1
		self.teardownAcked = 0
		self.connectToServer()
		self.frameNbr = 0
		self.stream_locator = stream_locator
		self.stream_loc_port = int(stream_loc_port)
		
	def createWidgets(self):
		"""Build GUI."""
		# Create Setup button
		self.setup = Button(self.master, width=20, padx=3, pady=3)
		self.setup["text"] = "Setup"
		self.setup["command"] = self.setupMovie
		self.setup.grid(row=1, column=0, padx=2, pady=2)
		
		# Create Play button		
		self.start = Button(self.master, width=10, padx=3, pady=3)
		self.start["text"] = "Play"
		self.start["command"] = self.playMovie
		self.start.grid(row=1, column=1, padx=2, pady=2)
		
		# Create Pause button			
		self.pause = Button(self.master, width=5, padx=3, pady=3)
		self.pause["text"] = "Pause"
		self.pause["command"] = self.pauseMovie
		self.pause.grid(row=1, column=2, padx=2, pady=2)
		
		# Create Teardown button
		self.teardown = Button(self.master, width=10, padx=3, pady=3)
		self.teardown["text"] = "Teardown"
		self.teardown["command"] =  self.exitClient
		self.teardown.grid(row=1, column=3, padx=2, pady=2)

		self.repeat = Button(self.master, width=10, padx=3, pady=3)
		self.repeat["text"] = "Repeat"
		self.repeat["command"] =  self.repeatAction
		self.repeat.grid(row=2, column=1, padx=2, pady=2)

		self.repeatLabel = Label(self.master, width=10, padx=20, pady=20)
		self.repeatLabel['text'] = "Repeat: Activated"
		self.repeatLabel.grid(row=2,column=0,padx=2,pady=2)
		
		# Create a label to display the movie
		self.label = Label(self.master, height=19)
		self.label.grid(row=0, column=0, columnspan=4, sticky=W+E+N+S, padx=5, pady=5) 
	
	def repeatAction(self):
		if self.REPEAT:
			self.REPEAT = False
			self.repeatLabel['text'] = "Repeat: Deactivated" 
		else:
			self.REPEAT = True
			self.repeatLabel['text'] = "Repeat: Activated" 

	def setupMovie(self):
		"""Setup button handler."""
		if self.state == self.INIT:
			self.sendRtspRequest(self.SETUP)
	
	def exitClient(self):
		"""Teardown button handler."""
		self.sendRtspRequest(self.TEARDOWN)	
		self.master.destroy() # Close the gui window
		try:
			os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT) # Delete the cache image from video
		except:
			print("No cache to remove")

	def pauseMovie(self):
		"""Pause button handler."""
		if self.state == self.PLAYING:
			self.sendRtspRequest(self.PAUSE)
	
	def playMovie(self):
		"""Play button handler."""
		if self.state == self.READY:
			# Create a new thread to listen for RTP packets
			threading.Thread(target=self.listenRtp).start()
			self.playEvent = threading.Event()
			self.playEvent.clear()
			self.sendRtspRequest(self.PLAY)
	
	def listenRtp(self):		
		"""Listen for RTP packets."""
		while True:
			server = self.serverAddr
			#print(f"O meu estado é {self.state}, ready é {self.READY} e playing é {self.PLAYING}")
			"""or self.state == self.READY"""
			if self.state == self.PLAYING or self.state == self.READY: 
				#try:
					#print(self.rtpSocket)
					data = self.rtpSocket.recv(25480)
					#print("recebi alguma coisa!")
					if data:
						rtpPacket = RtpPacket()
						rtpPacket.decode(data)
						
						currFrameNbr = rtpPacket.seqNum()
						if currFrameNbr % 30 == 0:
							print("Current Seq Num: " + str(currFrameNbr))
											
						if currFrameNbr > self.frameNbr or (self.REPEAT and (self.frameNbr - currFrameNbr) > 50): # Discard the late packet if didnt start again
							self.frameNbr = currFrameNbr
							#print("Payload length: " + str(len(rtpPacket.getPayload())))
							self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
						elif not self.REPEAT and (self.frameNbr - currFrameNbr) > 50:
							break
					else:
						print("Fui co crl")	
			#	except:
					
					# Upon receiving ACK for TEARDOWN request,
					# close the RTP socket
					# print("Vim cá ter lol")
					# try :
					# 	#if self.teardownAcked == 1:
					# 	#self.rtpSocket.shutdown(socket.SHUT_RDWR)
					# 	self.rtpSocket.close()
					# 	#	break
					# 	self.state = self.INIT #novo
						
					# 	self.sendRtspRequest(self.TEARDOWN) #novo
					# except:
					# 	pass
				
			else:

				print("Consegui aqui chegar!")
				s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				s.connect((self.stream_locator, self.stream_loc_port))

				print("Consegui ligar-me ao server para pedir info de stream")

				dados = s.recv(1024).decode('utf-8')
				
				lista = dados.split("\n")
				print(lista)
				self.serverAddr, self.rtpPort = lista[0], int(lista[1])
				print(f"O IP do server é o {self.serverAddr}")

				#self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
				
				self.connectToServer()


				self.state = self.INIT
				self.sendRtspRequest(self.SETUP)

				while self.state != self.READY:
					print("ainda não está!")
					time.sleep(0.2)

				self.sendRtspRequest(self.PLAY)

				while self.state != self.PLAYING:
					print("ainda não está!")
					time.sleep(0.2)

				print("Optimo, cheguei aqui!")
				# Stop listening upon requesting PAUSE or TEARDOWN
			if self.playEvent.isSet(): 
				break
					
	def writeFrame(self, data):
		"""Write the received frame to a temp image file. Return the image file."""
		cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
		file = open(cachename, "wb")
		file.write(data)
		file.close()
		
		return cachename
	
	def updateMovie(self, imageFile):
		"""Update the image file as video frame in the GUI."""
		photo = ImageTk.PhotoImage(Image.open(imageFile))
		self.label.configure(image = photo, height=288) 
		self.label.image = photo
		
	def connectToServer(self):
		"""Connect to the Server. Start a new RTSP/TCP session."""
		self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			print(f"A tentar conectar-me ao {self.serverAddr}:{self.serverPort}")
			self.rtspSocket.connect((self.serverAddr, self.serverPort))
			print("Connected to " + self.serverAddr)
		except:
			messagebox.showwarning('Connection Failed', 'Connection to \'%s\' failed.' %self.serverAddr)
	
	def sendRtspRequest(self, requestCode):
		"""Send RTSP request to the server."""	
		#-------------
		# TO COMPLETE
		#-------------
		request = ''
		# Setup request
		if requestCode == self.SETUP and self.state == self.INIT:
			threading.Thread(target=self.recvRtspReply).start()
			# Update RTSP sequence number.
			# ...
			self.rtspSeq += 1
			# Write the RTSP request to be sent.
			# request = ...
			request = 'SETUP ' + self.fileName + '\nCseq: ' + str(self.rtspSeq) + '\nRTP PORT NUM: ' + str(self.rtpPort)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.SETUP
			#print("mandei o setup!")
		# Play request
		elif requestCode == self.PLAY and self.state == self.READY:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq += 1
			print('\nPLAY event\n')
			# Write the RTSP request to be sent.
			# request = ...
			request = 'PLAY ' + self.fileName + '\nCseq: ' + str(self.rtspSeq) + "\n" + str(self.rtpPort)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PLAY
		# Pause request
		elif requestCode == self.PAUSE and self.state == self.PLAYING:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq += 1
			print('\nPAUSE event\n')
			
			# Write the RTSP request to be sent.
			# request = ...
			request = 'PAUSE ' + self.fileName + '\nCseq: ' + str(self.rtspSeq) + '\n' + str(self.rtpPort)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.PAUSE

		# Teardown request
		elif requestCode == self.TEARDOWN and not self.state == self.INIT:
			# Update RTSP sequence number.
			# ...
			self.rtspSeq += 1
			print('\nTEARDOWN event\n')
			
			# Write the RTSP request to be sent.
			# request = ...
			request = 'TEARDOWN ' + self.fileName + '\nCseq: ' + str(self.rtspSeq)
			# Keep track of the sent request.
			# self.requestSent = ...
			self.requestSent = self.TEARDOWN

		else:
			return
		
		# Send the RTSP request using rtspSocket.
		# ...
		print(request)
		self.rtspSocket.send(request.encode())
		# print('\nData sent:\n' + request)
	
	def recvRtspReply(self):
		"""Receive RTSP reply from the server."""
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
	
	def parseRtspReply(self, data):
		"""Parse the RTSP reply from the server."""
		lines = data.split('\n')
		seqNum = int(lines[1].split(' ')[1])
		
		# Process only if the server reply's sequence number is the same as the request's
		if seqNum == self.rtspSeq:
			session = int(lines[2].split(' ')[1])
			# New RTSP session ID
			self.sessionId = session
			
			# Process only if the session ID is the same
			if self.sessionId == session:
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
						self.openRtpPort() 
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
	
	def openRtpPort(self):
		"""Open RTP socket binded to a specified port."""

		#-------------
		# TO COMPLETE
		#-------------
		# Create a new datagram socket to receive RTP packets from the server
		# self.rtpSocket = ...
		self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Set the timeout value of the socket to 0.5sec
		# ...
		try:
			self.rtpSocket.settimeout(1.5)
		except:
			pass
		try:
			self.rtpSocket.bind(('',self.rtpPort))
			print(f"A porta é {self.rtpPort}")
			# Bind the socket to the address using the RTP port given by the client user
			# ...
			print('\nBind \n')
		except:
			messagebox.showwarning('Unable to Bind', 'Unable to bind PORT=%d' %self.rtpPort)

	def handler(self):
		"""Handler on explicitly closing the GUI window."""
		self.pauseMovie()
		if messagebox.askokcancel("Quit?", "Are you sure you want to quit?"):
			self.exitClient()
		else: # When the user presses cancel, resume playing.
			self.playMovie()

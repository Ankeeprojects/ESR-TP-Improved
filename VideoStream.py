import cv2

class VideoStream:
	def __init__(self, filename):
		self.filename = filename
		try:
			self.file = cv2.VideoCapture(filename)
		except:
			raise IOError
		self.frameNum = 0
		
	def nextFrame(self):
		"""Get next frame."""
		success, data = self.file.read()
		if not success: 
			self.file.release()
			self.file = cv2.VideoCapture(self.filename)
			success, data = self.file.read()
			self.frameNum = 0

		self.frameNum += 1
		data = cv2.imencode('.jpg', data, [cv2.IMWRITE_JPEG_QUALITY, 90])[1].tobytes()
		return data
		
	def frameNbr(self):
		"""Get frame number."""
		return self.frameNum
	
	
import threading

class Ligacoes_RTP:
    connections : dict
    lock : threading.Lock
    transmitir : bool
    behind : tuple

    def __init__(self):
        self.connections = dict()
        self.lock = threading.Lock()
        self.transmitir = False
        self.behind = None
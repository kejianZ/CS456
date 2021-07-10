from socket import *
import socket as s
import sys
from packet import Packet

class receiver_proc:
    def __init__(self, args):
        self.valid = False
        if(len(args) != 5):
            print("4 arguements should be provided to sender")
            return                   
        try:
            self.emu_add = args[1]
            self.emu_port = int(args[2])
            self.rec_port = int(args[3])
            self.filename = args[4]
            self.valid = True
        except OSError as e:
            print("Valid type of arguements should be provided")

        self.last_receive = -1
        self.sendSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.recSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.buffer = [None for _ in range(32)]
        self.sendSocket.bind(('', 0))
        self.recSocket.bind(('', self.rec_port))

    def run(self):
        self.file_writer = open(self.filename, 'w')
        if not self.valid:
            return
        while True:
            packet, sadd = self.recSocket.recvfrom(1024)
            print(Packet(packet))
            p_type, seq, length, payload = Packet(packet).decode()
            if p_type == 1:
                self.write_packet(seq, payload)                
            elif p_type == 2:
                self.sendAck(-1)
                break
        self.sendSocket.close()
        self.recSocket.close()
        self.file_writer.close()

    def write_packet(self, seq, payload):
        if seq == (self.last_receive + 1) % 32: # a packet of correct order arrived
            self.file_writer.write(payload)
            for i in range(1, 31): # check if previous buffered payload in buffer
                if self.buffer[(seq + i) % 32] == None:
                    break
                else:
                    self.file_writer.write(self.buffer[(seq + i) % 32])
                    self.buffer[(seq + i) % 32] = None  # clear the block in the buffer   
            self.last_receive = seq
        elif seq <= self.last_receive + 10 or seq <= (self.last_receive + 10) % 32:
            if self.buffer[seq] == None: # discard if previous buffered
                self.buffer[seq] = payload

        self.sendAck(self.last_receive)
    
    def sendAck(self, seq_num):
        if seq_num == -1:
            packet = Packet(2,0,0,'').encode()
        else:
            packet = Packet(0,seq_num,0,'').encode()
        self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))

    
        

        
sender = receiver_proc(sys.argv)  
sender.run()

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
        self.buffer = [None for _ in range(32)]             # buffer to store not-in-order packet 
        self.sendSocket.bind(('', 0))                       # socket to send ACK packet
        self.recSocket.bind(('', self.rec_port))

    def run(self):
        self.file_writer = open(self.filename, 'w')
        if not self.valid:
            return
        while True:
            packet, _ = self.recSocket.recvfrom(1024)
            p_type, seq, _, payload = Packet(packet).decode()
            if p_type == 1:         # data packet
                self.write_packet(seq, payload)                
            elif p_type == 2:       # EOT packet
                self.sendAck(-1)    # return a same EOT packet
                break
        self.sendSocket.close()
        self.recSocket.close()
        self.file_writer.close()

    def write_packet(self, seq, payload):
        if seq == (self.last_receive + 1) % 32:         # a packet of correct order arrived
            self.file_writer.write(payload)
            tem = seq
            for i in range(1, 10):                      # check if previous buffered payload in buffer
                if self.buffer[(seq + i) % 32] == None:
                    break
                else:
                    self.file_writer.write(self.buffer[(seq + i) % 32])
                    self.buffer[(seq + i) % 32] = None  # clear the block in the buffer
                    tem += 1   
            self.last_receive = tem % 32
        elif self.dis(self.last_receive, seq) <= 10:
            if self.buffer[seq] == None:                # discard if previous buffered
                self.buffer[seq] = payload

        self.sendAck(self.last_receive)

    def dis(self, p1, p2):
        if p2 > p1:
            return p2 - p1
        else:
            return p2 - p1 + 32

    def sendAck(self, seq_num):
        if seq_num == -1:
            packet = Packet(2,0,0,'').encode()
        else:
            packet = Packet(0,seq_num,0,'').encode()
        self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))

sender = receiver_proc(sys.argv)  
sender.run()

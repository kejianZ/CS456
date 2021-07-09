from socket import *
import socket as s
import struct
import sys
import threading

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

        self.last_ack = -1
        self.sendSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.sendSocket.bind(('', 0))
        self.recSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.recSocket.bind(('', self.rec_port))

    def run(self):
        couter = 0
        output = open(self.filename, 'w')
        if not self.valid:
            return
        while True:
            packet, sadd = self.recSocket.recvfrom(1024)
            p_type, seq, length, payload = self.process_packet(packet)
            if p_type == 1:
                output.write(payload)
                self.sendAck(seq)
            elif p_type == 2:
                break
        self.sendSocket.close()
        self.recSocket.close()
        output.close()

    def process_packet(self, byte_stream):
        p_type = int.from_bytes(byte_stream[0:4], byteorder='little', signed=False)
        seq_num = int.from_bytes(byte_stream[4:8], byteorder='little', signed=False)
        length = int.from_bytes(byte_stream[8:12], byteorder='little', signed=False)
        data = byte_stream[12:].decode()
        return p_type, seq_num, length, data
    
    def sendAck(self, seq_num):
        packet = struct.pack('III0s', 0, seq_num, 0, ''.encode())
        self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))

    
        

        
sender = receiver_proc(sys.argv)  
sender.run()

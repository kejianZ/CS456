import time
from socket import *
import socket as s
import struct
import sys
import threading

class server_proc:
    def __init__(self, args):
        self.valid = False
        if(len(args) != 6):
            print("5 arguements should be provided to sender")
            return                   
        try:
            self.emu_add = args[1]
            self.emu_port = int(args[2])
            self.ack_port = int(args[3])
            self.timeout = int(args[4])
            self.filename = args[5]
            self.valid = True
        except OSError as e:
            print("Valid type of arguements should be provided")

        self.last_ack = -1
        self.ack_lock = threading.Lock()
        self.wdn_sem = threading.Semaphore(1)
        self.ackSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.ackSocket.bind(('', self.ack_port))
        self.sendSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.sendSocket.bind(('', 0))

    def send_thread(self):
        couter = 0
        while True:
            chunk = self.file.read(500)
            if not chunk:
                break
            self.wdn_sem.acquire()
            packet = self.cons_packet(1, couter // 32, chunk)
            self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))
        packet = self.cons_packet(2, 0, '')
        self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))
    
    def ack_thread(self):
        while(True):           
            ack_msg, sadd = self.ackSocket.recvfrom(1024)

            p_type, ack_seq, length, payload = self.process_packet(ack_msg)
            if p_type == 0:
                for i in range(0, ack_seq - self.last_ack):
                    self.wdn_sem.release()
                self.last_ack = ack_seq
    
    def timer_thread(self):
        print()

    def process_packet(self, byte_stream):
        p_type = int.from_bytes(byte_stream[0:4], byteorder='little', signed=False)
        seq_num = int.from_bytes(byte_stream[4:8], byteorder='little', signed=False)
        length = int.from_bytes(byte_stream[8:12], byteorder='little', signed=False)
        data = byte_stream[12:].decode()
        return p_type, seq_num, length, data
    
    def cons_packet(self, type, seq_num, payload):
        style = 'III' + str(len(payload)) + 's'
        packet = struct.pack(style, type, seq_num, len(payload), payload.encode())
        return packet

    def run(self):
        if not self.valid:
            return
        try:
            self.file = open(self.filename)
        except:
            print("An error occures while opening the file")
            return
        
        self.send_thread()
        

        
sender = server_proc(sys.argv)  
sender.run()
# tem = sender.cons_packet(1,2,"hello kitty!")
# print(tem) 
# print(sender.process_packet(tem))      

# ss = struct.pack('III10s', 1, 23, 43, "abcdefghij".encode())
# print(ss)

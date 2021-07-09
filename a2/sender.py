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
        self.last_send = 0
        self.wdn_size = 1
        self.wdn_sem = threading.Semaphore(self.wdn_size)
        self.ackSocket = s.socket(AF_INET, SOCK_DGRAM)
        self.sendSocket = s.socket(AF_INET, SOCK_DGRAM)   
        self.finish = False
        self.buffer = [None for _ in range(32)]
        self.timer_started = False

        self.ackSocket.bind(('', self.ack_port))
        self.sendSocket.bind(('', 0))

    def send_thread(self):
        while True:
            chunk = self.file.read(5)
            if not chunk:   # reach the EOF
                break
            self.wdn_sem.acquire()  # if there are avalible space in sender window
            packet = self.cons_packet(1, self.last_send, chunk)
            self.buffer[self.last_send] = packet
            if not self.timer_started:
                self.timer_started = True
                self.start_time = time.time()
            self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))
            self.last_send = (self.last_send + 1) % 32
        packet = self.cons_packet(2, 0, '') # send EOT packet
        self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))
    
    def ack_thread(self):
        while(True):           
            ack_msg, sadd = self.ackSocket.recvfrom(1024)

            p_type, ack_seq, length, payload = self.process_packet(ack_msg)
            if p_type == 0: # ACK message
                for i in range(min(ack_seq - self.last_ack,self.wdn_size)):
                    self.wdn_sem.release()
                if self.wdn_size < 10:
                    self.wdn_size += 1
                    self.wdn_sem.release() # increment window size by 1
                self.last_ack = ack_seq
                if self.last_send == self.last_ack:
                    self.timer_started = False
                else:
                    self.start_time = time.time()
            else:   # receiver receive the EOT message and response with another EOT message
                self.finish = True  # tell timer to terminate
                break
    
    def timer_thread(self):
        while(True):
            if self.finish:
                break
            if self.timer_started and time.time() - self.start_time > self.timeout: # timeout occures
                self.resend()
        

    def run(self):
        if not self.valid:
            return
        try:
            self.file = open(self.filename)
        except:
            print("An error occures while opening the file")
            return
        
        # create thread for sending packet, receiving acknowledgement and timer
        send_t = threading.Thread(target=self.send_thread)
        ack_t = threading.Thread(target=self.ack_thread)
        timer_t = threading.Thread(target=self.timer_thread)
        send_t.start()
        ack_t.start()
        timer_t.start()
        send_t.join()
        ack_t.join()
        timer_t.join()
    
    def resend(self):
        self.sendSocket.sendto(self.buffer[(self.last_ack + 1) % 32], (self.emu_add, self.emu_port))
        self.wdn_size = 1
        self.wdn_sem = threading.Semaphore(0)   # reset window size to 1, and because we resend the timeout packet, reduce avaliable space to 0
        self.start_time = time.time()

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
        

        
sender = server_proc(sys.argv)  
sender.run()
# tem = sender.cons_packet(1,2,"hello kitty!")
# print(tem) 
# print(sender.process_packet(tem))      

# ss = struct.pack('III10s', 1, 23, 43, "abcdefghij".encode())
# print(ss)

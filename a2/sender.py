from os import write
import time
from socket import *
import socket as s
import sys
import threading
from packet import Packet

class sender_proc:
    def __init__(self, args):
        # check if arguments pass in of valid form
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

        # initiate fileds in sender process
        self.last_ack = -1
        self.last_send = -1
        self.send_ptr = 0                                   # seq num of next packet should be sent
        self.wdn_size = 1
        self.finish = False
        self.buffer = [None for _ in range(32)]             # buffer used to resend data
        self.timer_started = False
        self.event_ctr = 0                                  # global event couter for logging
        self.all_sent = False

        self.ackSocket = s.socket(AF_INET, SOCK_DGRAM)      # socket used to receive ACK
        self.sendSocket = s.socket(AF_INET, SOCK_DGRAM)  
        
        self.wdn_sem = threading.Semaphore(self.wdn_size)   # semaphore is used for sending window      
        self.timerlck = threading.Lock()                    # lock used to protect timer
        self.wdnlck =threading.Lock()                       # both timer and receive thread modify wdn_size
        self.loglck = threading.Lock()                      # lock used to protect logger
        self.crtlck = threading.Lock()                      # lock used to protect send send pointer

        self.seqlog = open('seqnum.log', 'w')
        self.acklog = open('ack.log', 'w')
        self.nlog = open('N.log', 'w')

        self.ackSocket.bind(('', self.ack_port))
        self.sendSocket.bind(('', 0))
        self.log('n', str(self.wdn_size))                   # the first event set window size to 1
    
    def __del__(self):
        self.sendSocket.close()
        self.ackSocket.close()
        self.seqlog.close()
        self.acklog.close()
        self.nlog.close()
        if self.valid:
            self.file.close()
    
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
            

    def send_thread(self):
        while True:
            if self.all_sent:
                if self.last_ack == self.last_send:
                    break
            self.wdn_sem.acquire()                          # if there are avalible space in sender window
            if self.send_ptr != (self.last_send + 1) % 32:  # send_ptr <= last_send means the packet has been sent
                self.resend_data()
            else:
                chunk = self.file.read(500)     
                if self.all_sent or not chunk:              # reach the EOF
                    self.all_sent = True
                    self.wdn_sem.release()
                    continue
                self.send_data(chunk)         
        self.log('seq', 'EOT')         
        self.sendSocket.sendto(Packet(2, 0, 0, '').encode(), (self.emu_add, self.emu_port)) # send EOT packet
        
    def ack_thread(self):
        while(True):           
            ack_msg, _ = self.ackSocket.recvfrom(1024)
            p_type, ack_seq, _, _ = Packet(ack_msg).decode()
            if p_type == 0:             # ACK message
                self.process_ack(ack_seq)
            else:                       # EOT message
                self.log('ack', 'EOT')
                self.finish = True      # tell timer to terminate
                break

    def timer_thread(self):
        while(True):
            if self.finish: # EOT received, should terminate now
                break
            self.timerlck.acquire()
            if self.timer_started and time.time() - self.start_time > self.timeout / 1000: # timeout occures
                self.reset_ptr()
            self.timerlck.release()
    
    def resend_data(self):
        self.log('seq', str(self.send_ptr))
        self.sendSocket.sendto(self.buffer[self.send_ptr], (self.emu_add, self.emu_port))
        self.crtlck.acquire()
        self.send_ptr = (self.send_ptr + 1) % 32
        self.crtlck.release()

        self.timerlck.acquire()
        if not self.timer_started:              # if timer not started, start it with current time
            self.timer_started = True
            self.start_time = time.time()
        self.timerlck.release() 
     
    def send_data(self, chunk):
        packet = Packet(1, self.send_ptr, len(chunk), chunk).encode()
        self.log('seq', str(self.send_ptr))
        self.sendSocket.sendto(packet, (self.emu_add, self.emu_port))
        self.buffer[self.send_ptr] = packet    # buff package at buffer
        self.crtlck.acquire()
        self.last_send = (self.last_send + 1) % 32
        self.send_ptr = (self.send_ptr + 1) % 32
        self.crtlck.release()
        
        self.timerlck.acquire()
        if not self.timer_started:              # if timer not started, start it with current time
            self.timer_started = True
            self.start_time = time.time()
        self.timerlck.release() 
    
    def process_ack(self, ack_seq):
        dis = self.ack_distance(ack_seq)
        if dis > 10:             
            return                                  # acknowledge with sequence number not in the window, discard it
        self.last_ack = ack_seq                     # valid new ack sequence number, update last_ack
        self.log('ack', str(self.last_ack))

        self.timerlck.acquire() 
        if self.send_ptr == (self.last_ack + 1) % 32:
            self.timer_started = False              # no more flying packet, stop timer
        else:
            self.start_time = time.time()           # reset timer if there exist flying packet
        self.timerlck.release()
               
        self.wdnlck.acquire()
        for _ in range(min(dis, self.wdn_size)):    # move window forward by dis or maybe window size was reset
            self.wdn_sem.release()
        # every time receive ack incremend window size by 1 if smaller than 10    
        if self.wdn_size < 10:
            self.wdn_size += 1
            self.log('n', str(self.wdn_size))
            self.wdn_sem.release()
        self.wdnlck.release()

    def ack_distance(self, ack_seq):
        if ack_seq >= self.last_ack:
            return ack_seq - self.last_ack
        else:
            return ack_seq + 32 - self.last_ack
    
    def reset_ptr(self):
        self.wdnlck.acquire()
        self.wdn_size = 1
        self.log('n', str(self.wdn_size))
        self.crtlck.acquire()
        self.send_ptr = (self.last_ack + 1) % 32
        self.crtlck.release()
        self.reset_wdn_sem()        # reset window size to 1
        self.wdnlck.release()
        self.start_time = time.time()
    
    def reset_wdn_sem(self):
        while True:
            if self.wdn_sem._value > 0:  
                self.wdn_sem.acquire(blocking=False)    # set window semaphore value to 0
            else:
                break
        self.wdn_sem.release()                          # set window semaphore value to 1

    def log(self, file, content, debug = False):
        self.loglck.acquire()
        if debug:
            writer = self.acklog
            content = file + ': ' + content
        elif file == 'seq':
            writer = self.seqlog
        elif file == 'ack':
            writer = self.acklog
        elif file == 'n':
            writer = self.nlog
        else:
            return
        writer.write('t=' + str(self.event_ctr) + ' ' + content + '\n')
        self.event_ctr += 1
        self.loglck.release()
                
sender = sender_proc(sys.argv)  
sender.run()
del sender
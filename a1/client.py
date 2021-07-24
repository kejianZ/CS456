from socket import *
import socket as s
import sys

class client_proc:
    def __init__(self, args):
        self.valid = False
        if(len(args) != 5):
            print("4 arguements should be provided to the client")
            return

        try:
            # parse server address from first arguement
            s.gethostbyname(args[1])
            self.server_add = args[1]
            # parse server welcome port number from second arguement
            self.server_port = int(args[2])
            # parse request code from third arguement     
            self.req_code = int(args[3])
            # message needs to be procced by server
            self.msg = args[4]
            
            self.valid = True

        except s.error:
            print("A valid ip address should be provided")  
        except ValueError:
            print("A vaid port number or request number should be provided")

    # the negotiation stage
    def tcp_connect(self):
        if not self.valid:  # valid and meaningful arguements are not provided
            return

        try:
            self.connected = False
            tcpSocket = s.socket(AF_INET, SOCK_STREAM)
            tcpSocket.connect((self.server_add, self.server_port))
            # send req_code to server
            tcpSocket.send(str(self.req_code).encode())
            # get the udp listening socket port on server 
            self.trans_port = int(tcpSocket.recv(256).decode())
            self.connected = True
        except Exception as e:
            print("An exception occured at negotiation stage, abroting...")
            print(e)
        finally:        
            tcpSocket.close()

    # the transection stage
    def udp_communicate(self):
        if not self.valid or not self.connected:    #either arguements not valid or tcp negotiation unsuccessful
            return

        try:
            udpSocket = s.socket(AF_INET, SOCK_DGRAM)
            # send message need to be processed to server specified udp port
            udpSocket.sendto(self.msg, (self.server_add, self.trans_port))
            return_msg, sadd = udpSocket.recvfrom(1024)
            print(return_msg.decode())
        except Exception as e:
            print("An exception occured at transection stage, abroting...")
            print(e)
        finally:
            udpSocket.close()

client = client_proc(sys.argv)
client.tcp_connect()
client.udp_communicate()

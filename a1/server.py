from socket import *
import socket as s
import sys

class server_proc:
    def __init__(self, args):
        self.valid = False
        if(len(args) != 2):
            print("A req_code should be proivded to the server")
            return
                    
        try:
            self.req_code = int(args[1])
            self.valid = True
        except:
            print("A req_code should be an integer")

    def start_service(self):
        if not self.valid:  # valid arguement is not provided
            return

        try:
            self.nego_socket = s.socket(AF_INET, SOCK_STREAM)
            self.nego_socket.bind(('', 0))  # bind to an os specified free port
            self.nego_port = self.nego_socket.getsockname()[1]  # get the port number of listenning port
            print('SERVER_PORT=' + str(self.nego_port))
            self.nego_socket.listen(1)
            self.serving = True
            while self.serving:
                self.process_msg()
        except Exception as e:
            print("An exception occured while setting up the listening port, aborting...")
            print(e)
        finally:
            self.nego_socket.close()

    def process_msg(self):
        try:        
            connectionSocket, addr = self.nego_socket.accept()  # accpet tcp connection from the client
            creq_code = int(connectionSocket.recv(256).decode())    # req_code send from the client
            if creq_code == self.req_code:
                trans_socket = socket(AF_INET, SOCK_DGRAM)
                trans_socket.bind(('', 0))  # bind udp transection socket to an os specified valid port
                trans_port = trans_socket.getsockname()[1]
                connectionSocket.send(str(trans_port).encode()) # send the upd socket port to the client via tcp
                connectionSocket.close()
            else:
                # req_code not matched, proceed to next service circle
                print("Client provides incorrect req_code, socket closing...")
                connectionSocket.close()
                return

            message, cadd = trans_socket.recvfrom(1024) # receive message from the client
            result = message.decode()[::-1].encode()    # reverse the message
            trans_socket.sendto(result, cadd)   # send reversed message to the client
            trans_socket.close()
        except KeyboardInterrupt:
            self.serving = False
            print('')
            return
        except Exception as e:
            print("An exception occured while servering a client, terminate current service circle")
            print(e)
            

server = server_proc(sys.argv)
server.start_service()
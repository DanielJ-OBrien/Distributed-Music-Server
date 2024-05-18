import socket
import time
from _thread import *
from threading import Thread
import pygame
import hashlib

class ClientMain:
    
    def __init__(self):
        
        #Socket info stored for all functions to access.
        self._s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.loggedin = False

    def DataProcessor(self):
        #The first of two threaded function. This is always looping to recieve and process packets sent to the client.
        while True:
            try:
                #Recieves data and increased the recieved packet count ID.
                rData = self._s.recv(1024).decode('utf-8')
                #Same as the server, these lines will always run and pick out the useful parts of the package 
                command, message = rData.split(' ', 1)
                #Matches the command recieved by the client to call the correct function.
                match command:
                    case "displaymessage":
                        self.DisplayMessage(message)
                    case "connectto":
                        self.ConnectTo(message)
                    case "login":
                        self.loggedin = True
                    case "sendfile":
                        self.ReceiveFile(message)
            except Exception as e:
                pass
        
    def PlaySong(self, filename):
        null, filename = filename.split(' ', 1)
        # Initialize the mixer
        pygame.mixer.init()

        try:
            # Load the song
            pygame.mixer.music.load(filename)

            # Play the song
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error playing song: {e}")
            
    def StopSong(self):
        try:
            # Stop the song
            pygame.mixer.music.stop()
        except Exception as e:
            print(f"Error stopping song: {e}")
            
    def DisplayMessage(self, message):
        #Prints the passed message
        try:
            print(message)
        except Exception as e:
            print(f"5. {e}")
            pass   
        
    def ConnectTo(self, message):
        HOST, PORT = message.split(' ', 1)
        HOST = str(HOST).strip("(',)")
        PORT = str(PORT).strip("(,')")
        PORT = int(PORT)
        print(f"Connecting to {HOST}:{PORT}")
        try:
            self._s.close()
            self._s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self._s.connect((HOST,PORT))
        except Exception as e:
            print("Failed to connect:", e)
            
    def ReceiveFile(self, filename):
        try:
            # Receives the size of the file
            filename, checksum, file_size = filename.split(' ', 2)
            received_size = 0

            with open(filename, 'wb') as file:
                print("Receiving file...")
                while received_size < int(file_size):
                    data = self._s.recv(1024)
                    file.write(data)
                    received_size += len(data)

            print("Finished receiving file")
            
            hash_md5 = hashlib.md5()
            with open(filename, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            result = hash_md5.hexdigest()
            
            print(checksum, result)
            if(checksum == result):
                print("File integrity verified")
        
        
        except Exception as e:
            print(f"Error receiving file: {e}")
        
    def DataSender(self):
        #The second threaded function. This one allows user input to the console for sending messages.
        while True:
            try:
                #Prevents spam.
                time.sleep(1)
                uip = input()
                try:
                    self.SendMessage(uip)
                except Exception as e:
                    #If sending the message fails, it is assumed the server has disconnected. This sets the states to False again and closes the thread.
                    print("Message failed due to server disconnect.")
                    print(e)
                    return
            except:
                pass
    
    def SendMessage(self, message):
        #VERY important function. Sends a message to the server.
        if("playmusic" in message):
            if(self.loggedin == False):
                print("You must be logged in to play music.")
                return
        if("playsong" in message):
            self.PlaySong(message)
            return
        if("stopsong" in message):
            self.StopSong()
            return
        
        parts = message.split()
        if len(parts) < 2:
            print("All commands to server must follow the format 'x (space) y'")
            return
        
        str(message)
        message = message.encode('utf-8')
        self._s.send(message)

    def RunClient(self):
        #The starting function
        while True:
            try:
                #Attempts standard socket connection activities. If it succeeds, it ensures all values are returned to their default for a new server connection.
                hostname = socket.gethostname()
                HOST = socket.gethostbyname(hostname)
                PORT = 50001
                self._s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self._s.connect((HOST,PORT))
                self._s.setblocking(0)
                while True:
                    #Creates threads for the data processor and reciever.
                    try:
                        thread1 = Thread(target = self.DataProcessor, args =())
                        thread2 = Thread(target = self.DataSender, args =())
                        thread1.start()
                        thread2.start()
                        #Loops to prevents new threads being made. Breaks if there has been a problem with the connection.
                        while True:
                            pass
                        break
                    except Exception as e:
                        #Prints the connection error to the user and waits 5 seconds. Also sets _stop to true to ensure threads are closed.
                        print(f"8. {e}")
                        time.sleep(5)
            except Exception as e:
                #Loops every 5 seconds, attempting to reconnect to the server without errors or restarts.
                print("Attempting to reconnect...")
                time.sleep(5)
                pass
    
if __name__ == "__main__":
    #Creates instance of the client class and runs the connection function.
    client = ClientMain()
    client.RunClient()
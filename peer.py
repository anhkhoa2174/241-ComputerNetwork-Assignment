import socket
import threading
import os
from tool import *
from file import File
import random
import time
import pickle
from threading import Thread
import sys

PEER_IP = get_host_default_interface_ip()
LISTEN_DURATION = 5
PORT_FOR_PEER= random.randint(12600, 22000)

class peer:
    def __init__(self):
        self.peerIP = PEER_IP # peer's IP
        self.peerID = PORT_FOR_PEER # peer' ID
        self.portForPeer = PORT_FOR_PEER # port for peer conection with other peers
        self.portForTracker = PORT_FOR_PEER + 1 # port for peer connection with tracker
        self.lock = threading.Lock()
        self.fileInRes = []
        self.isRunning = False
        self.peerDownloadingFrom = []
        self.server = []

         # A socket for listening from other peers in the network
        self.peerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.peerSocket.bind((self.peerIP, self.portForPeer))

        print(f"A peer with IP address {self.peerIP}, ID {self.portForTracker} has been created")

        
        self.connected_client_conn_list = [] # Current clients conn connected to this client
        self.connected_client_addr_list = [] # Current clients addr connected to this client
        self.nconn_threads = []


    @property # This creates an own respo for peer to save metainfo file
    def peerOwnRes(self):
        peerOwnRes = "my_own_respo_" + str(self.peerID)
        os.makedirs(peerOwnRes, exist_ok=True)
        peerOwnRes += "/"
        return peerOwnRes
    
    def getFileInRes(self) -> list:
        ownRespository = os.listdir("peer_respo")
        files = []
        if len(ownRespository) == 0:
            return files
        else: 
            for name in ownRespository:
                if(os.path.getsize("peer_respo/" + name) == 0):
                    os.remove("peer_respo/" + name)
                else:
                    files.append(File(self.peerOwnRes+name))


                    # # Testing creating metainfo
                    # file_obj = File("peer_respo/"+name)
                    # files.append(file_obj)
                    # # Get metainfo and save into a text file
                    # self.save_metainfo_to_txt(file_obj.meta_info)
        return files
    # def save_metainfo_to_txt(self, metainfo):
    #     # The path to txt file that saves metainfo of a specific file
    #     file_path = os.path.join(self.peerOwnRes, f"{metainfo.fileName}_metainfo.txt")
        
    #     # Write metainfo into file
    #     with open(file_path, "w", encoding="utf-8") as file:
    #         file.write(f"File Name: {metainfo.fileName}\n")
    #         file.write(f"File Length: {metainfo.length} bytes\n")
    #         file.write(f"Piece Length: {metainfo.pieceLength} bytes\n")
    #         file.write(f"Number of Pieces: {int(metainfo.numOfPieces)}\n")
    #         file.write(f"SHA-1 Hashes of Pieces: {metainfo.pieces.hex()}\n")
        
    #     print(f"Metainfo for {metainfo.fileName} has been saved to {file_path}")

    def list_clients(self):
        if client_addr_list:
            print("Connected Clients:")
            for i, client in enumerate(client_addr_list, start=1):
                print(f"{i}. IP: {client[0]}, Port: {client[1]}")
        else:
            print("No clients are currently connected.") 
            # List of clients connected to this client
    def list_connected_clients(self):
        if self.connected_client_addr_list:
            print("Connected Clients:")
            for i, client in enumerate(self.connected_client_addr_list, start=1):
                print(f"{i}. IP: {client[0]}, Port: {client[1]}")
        else:
            print("No clients are currently connected.")

    def new_connection(self, conn, addr):
        conn.settimeout(1)  # Setting timeout to check the stop_event

        # Receive peer port separately
        string_peer_port = conn.recv(1024).decode("utf-8")
        peer_port = int(string_peer_port)

        # Record the new peer metainfo
        self.connected_client_conn_list.append(conn)
        self.connected_client_addr_list.append((addr[0], peer_port))

        print(f"Peer ('{addr[0]}', {peer_port}) connected.")

        while not stop_event.is_set():
            try:
                data = conn.recv(1024)
                command = data.decode("utf-8")
                if not data:
                    break
                # TODO: process at client side
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error occurred: {e}")
                break

        conn.close()
        self.connected_client_conn_list.remove(conn)
        self.connected_client_addr_list.remove((addr[0], peer_port))
        print(f"Peer ('{addr[0]}', {peer_port}) removed.")

    def update_client_list(self, tracker_socket):
        global client_addr_list
        # Create command for the Tracker
        command = "update_client_list"
        tracker_socket.send(command.encode("utf-8"))
        print("Client List requested.")

        # Receive the clients list from the Tracker
        pickle_client_addr_list = tracker_socket.recv(4096)
        client_addr_list = pickle.loads(pickle_client_addr_list)
        print("Client List received.")

    # Connect to the Tracker
    def new_conn_tracker(self, tracker_socket, server_host, server_port):
        while not stop_event.is_set():
            try:
                data = tracker_socket.recv(1024)
                command = data.decode("utf-8")
                if not data:
                    break
            except socket.timeout:
                continue
            except Exception:
                print("Error occured!")
                break

        tracker_socket.close()
        print(f"Tracker ('{server_host}', {server_port}) removed.")


    def connect_to_tracker(self, server_host, server_port):
        try:
            tracker_socket = socket.socket()
            tracker_socket.settimeout(1) # Setting timeout to check the stop_event
            tracker_socket.connect((server_host, server_port))
            print(f"Tracker ('{server_host}', {server_port}) connected.")
        except ConnectionRefusedError:
            print(f"Could not connect to Tracker {server_host}:{server_port}")

        # Send client port separately
        string_client_port = str(self.portForPeer)
        tracker_socket.send(string_client_port.encode("utf-8"))
        time.sleep(1)

        thread_tracker = Thread(target=self.new_conn_tracker, args=(tracker_socket, server_host, server_port))
        thread_tracker.start()
        self.nconn_threads.append(thread_tracker)
    
        self.update_client_list(tracker_socket)
        return tracker_socket

        # Connect to other peers
    def new_conn_peer(self, peer_socket, peer_ip, peer_port):
        while not stop_event.is_set():
            try:
                data = peer_socket.recv(1024)
                command = data.decode("utf-8")
                if not data:
                    break
            except socket.timeout:
                continue
            except Exception:
                print("Error occured!")
                break

        peer_socket.close()
        self.connected_client_conn_list.remove(peer_socket)
        self.connected_client_addr_list.remove((peer_ip, peer_port))
        print(f"Peer ('{peer_ip}', {peer_port}) removed.")


    def connect_to_all_peers(self):
        for peer in client_addr_list:
            if peer[0] == self.IP and peer[1] == self.portForPeer:
                continue
            self.connect_to_peer(peer[0], peer[1])

    # Connect to one specific peer
    def connect_to_peer(self, peer_ip, peer_port):
        try:
            if peer_ip == self.client_ip and peer_port == self.portForPeer:
                print("Cannot connect to self.")
                return
            peer_socket = socket.socket()
            peer_socket.settimeout(5) # Setting timeout to check the stop_event
            peer_socket.connect((peer_ip, peer_port))
            print(f"Connected to peer {peer_ip}:{peer_port}")
        except ConnectionRefusedError:
            print(f"Could not connect to peer {peer_ip}:{peer_port}")
    
        # Record the new peer metainfo
        self.connected_client_conn_list.append(peer_socket)
        self.connected_client_addr_list.append((peer_ip, peer_port))

        # Send peer port separately
        string_peer_port = str(peer_port)
        peer_socket.send(string_peer_port.encode("utf-8"))
        time.sleep(1)

        thread_peer = Thread(target=self.new_conn_peer, args=(peer_socket, peer_ip, peer_port))
        thread_peer.start()
        self.nconn_threads.append(thread_peer)


    def disconnect_to_all_peers(self):
        for conn, addr in zip(self.connected_client_conn_list, self.connected_client_addr_list):
            try:
                conn.close()  # Close the connection to the peer
                print(f"Disconnected from peer ('{addr[0]}', {addr[1]})")
            except Exception as e:
                print(f"Error disconnecting from peer ('{addr[0]}', {addr[1]}): {e}")
    
    # Clear the client_list after closing all connections
    # connected_client_conn_list.clear()
    # connected_client_addr_list.clear()
        print("All peers disconnected.")

    def client_program(self):
        print(f"Peer IP: {self.peerIP} | Peer Port: {self.portForPeer}")
        print("Listening on: {}:{}".format(self.peerIP, self.portForPeer))

        self.peerSocket.listen(10)

        while not stop_event.is_set():
            try:
                conn, addr = self.peerSocket.accept()
                nconn = Thread(target=self.new_connection, args=(conn, addr))
                nconn.start()
                self.nconn_threads.append(nconn)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Peer error: {e}")
                break

        self.peerSocket.close()
        print(f"Peer {self.peerIP} stopped.")

    def shutdown_peer(self):
        stop_event.set()
        for nconn in self.nconn_threads:
            nconn.join()
        print("All threads have been closed.") 


if __name__ == "__main__":
    my_peer = peer()
    try:
        peer_thread = Thread(target=my_peer.client_program)
        peer_thread.start()

        while True:
            command = input("Peer> ")
            if command == "test":
                print("The program is running normally.")
            elif command.startswith("connect_tracker"):
                parts = command.split()
                if len(parts) == 3:
                    server_host = parts[1]
                    try:
                        server_port = int(parts[2])
                        tracker_socket = my_peer.connect_to_tracker(server_host, server_port)
                    except ValueError:
                        print("Invalid port.")
                else:
                    print("Usage: connect_tracker <IP> <Port>")
            elif command == "list_clients":
                my_peer.list_clients()
            elif command == "update_client_list":
                my_peer.update_client_list(tracker_socket)
            elif command == "list_connected_peers":
                my_peer.list_connected_clients()
            # elif command == "connect_to_all_peers":
            #     my_peer.connect_to_all_peers()    
            elif command.startswith("connect_to_peer"):
                parts = command.split()
                if len(parts) == 3:
                    peer_ip = parts[1]
                    try:
                        peer_port = int(parts[2])
                        my_peer.connect_to_peer(peer_ip, peer_port)
                    except ValueError:
                        print("Invalid port.")
                else:
                    print("Usage: connect_to_peer <IP> <Port>")
            elif command == "disconnect_to_all_peers":
                my_peer.disconnect_to_all_peers()  
            elif command == "exit":
                print("Exiting Tracker Terminal.")
                break
            else:
                print("Unknown Command.")
    except KeyboardInterrupt:
        print("\nThe Client Terminal interrupted by user. Exiting Client Terminal...")
    finally:
        print("Client Terminal exited.")
    
    my_peer.shutdown_peer()
    my_peer.join()
    sys.exit(0)


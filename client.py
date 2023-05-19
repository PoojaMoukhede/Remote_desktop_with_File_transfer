import socket
from PIL import Image, ImageGrab, ImageTk
import pygetwindow
import os
import win32gui
import lz4.frame
from io import BytesIO
from threading import Thread
from multiprocessing import freeze_support, Process, Queue as Multiprocess_queue
from pynput.keyboard import Listener as Key_listener
from pynput.mouse import Button, Listener as Mouse_listener
import tkinter as tk
from tkinter.font import Font
from tkinter import ttk, messagebox, filedialog
import connection_common
import win32api
from datetime import datetime
import pygame
import subprocess
import time
import ftplib
import socket
# from tkinter import *
from tkinter import filedialog , StringVar
from tkinter import ttk
import os
from tkinterdnd2 import *


def send_event(sock,message):
    connection_common.send_data(sock, 2, message)
    # print(sock,'----sock')
    # print(message,'----message')

def mouse_controlling(sock, event_queue, resize, cli_width, cli_height, disp_width, disp_height):
    while True:
        event_code = event_queue.get()
        x = event_queue.get()
        y = event_queue.get()
        x, y, inside_the_display = check_in_display(x, y, resize, cli_width, cli_height, disp_width, disp_height)
        if event_code == 0 or event_code == 7:
            if inside_the_display: 
                if event_code == 7:
                    x = event_queue.get()
                    y = event_queue.get()
                message = bytes(f"{event_code:<2}" + str(x) + "," + str(y), "utf-8")
                send_event(sock,message)
        elif event_code in range(1, 10):
            if inside_the_display:
                message = bytes(f"{event_code:<2}", "utf-8")
                send_event(sock,message)


def XY_scale(x, y, cli_width, cli_height, disp_width, disp_height):
    X_scale = cli_width / disp_width
    # print("X_scale -----------",X_scale)
    Y_scale = cli_height / disp_height
    # print("Y_scale -----------",Y_scale)
    x *= X_scale
    y *= Y_scale
    return round(x, 1), round(y, 1)


def check_in_display(x, y, resize, cli_width, cli_height, disp_width, disp_height):
    active_window = pygetwindow.getWindowsWithTitle(f"Remote Desktop")
    if active_window and (len(active_window) == 1):
        x, y = win32gui.ScreenToClient(active_window[0]._hWnd, (x, y))
        if (0 <= x <= disp_width) and (0 <= y <= disp_height):
            if resize:
                x, y = XY_scale(x, y, cli_width, cli_height, disp_width, disp_height)
            return x, y, True
    return x, y, False

def on_move(x, y):
    mouse_event.put(0)  
    mouse_event.put(x)
    mouse_event.put(y)


def on_click(x, y, button, pressed):
    if pressed:                                             # mouse down
        mouse_event.put(button_code.get(button)[0])
        mouse_event.put(x)
        mouse_event.put(y)
    else:                                                   # mouse up
        mouse_event.put(button_code.get(button)[1]) 
        mouse_event.put(x)
        mouse_event.put(y)

def on_scroll(x, y, dx, dy):
    mouse_event.put(7) 
    mouse_event.put(x)
    mouse_event.put(y)
    mouse_event.put(dx)
    mouse_event.put(dy)

def keyboard_controlling(key, event_code):
    active_window = pygetwindow.getActiveWindow()
    if active_window and active_window.title == "Remote Desktop":
        if hasattr(key, "char"):
            msg = bytes(event_code + key.char, "utf-8")
        else:
            msg = bytes(event_code + key.name, "utf-8")
        send_event(remote_server_socket,msg)

def on_press(key):
    keyboard_controlling(key, "-1")  # -1 indicate a key press event

def on_release(key):
    keyboard_controlling(key, "-2")   # -2 indicate a key release event.


def receive_and_put_in_list(client_socket, jpeg_list):
    chunk_prev_message = bytes()
    size_of_header = 10
    
    try:
        while True:
            message = connection_common.data_recive(client_socket, size_of_header, chunk_prev_message)
            if message:
                jpeg_list.put(lz4.frame.decompress(message[0])) 
                chunk_prev_message = message[1]
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        print("Thread automatically closed")


def display_data(jpeg_list, status_list, disp_width, disp_height, resize):
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    pygame.init()
    display_surface = pygame.display.set_mode((disp_width, disp_height))
    pygame.display.set_caption(f"Remote Desktop")
    clock = pygame.time.Clock()
    display = True

    while display:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                status_list.put("stop")  
                pygame.quit()
                return
        jpeg_buffer = BytesIO(jpeg_list.get())
        img = Image.open(jpeg_buffer)
        py_image = pygame.image.frombuffer(img.tobytes(), img.size, img.mode)
        if resize:
            py_image = pygame.transform.scale(py_image, (disp_width, disp_height))
        jpeg_buffer.close()
        display_surface.blit(py_image, (0, 0))
        pygame.display.flip()
        clock.tick(60)
        
def capture_screen(queue,disp_width,disp_height):
    while True:
        frame = ImageGrab.grab()  # Capture the screen frame
        frame = frame.resize((disp_width, disp_height))  # Resize the frame
        image_bytes = BytesIO()
        frame.save(image_bytes, format='PNG')  # Convert the frame to PNG format
        compressed_bytes = lz4.frame.compress(image_bytes.getvalue())  # Compress the frame
        queue.put(compressed_bytes)  # Put the compressed frame into the queue

def cleanup_process():
    process_list = [process1, process2]
    for process in process_list:
        if process:
            if process.is_alive():
                process.kill()
            process.join()
    mouse_listner.stop()
    mouse_listner.join()
    keyboard_listner.stop()
    keyboard_listner.join()
    print("cleanup finished")


def cleanup_display_process(status_list):
    if status_list.get() == "stop":
        connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("stop_capture", "utf-8"))
        cleanup_process()


def remote_display():
    global thread2, mouse_listner,keyboard_listner, process1, process2, remote_server_socket, mouse_event  
    print("Send start message")
    connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("start_capture", "utf-8"))
    print("Start message sent")
    disable_choice = messagebox.askyesno("Remote Box", "Disable remote device wallpaper?(yes,Turn black)")

    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # remote display sockets
    # print(remote_server_socket,"----remote display socket")
    remote_server_socket.connect((server_ip, server_port))
    
    connection_common.send_data(remote_server_socket, HEADER_COMMAND_SIZE, bytes(str(disable_choice), "utf-8"))
    print("\n")
    print(f">>Now you can CONTROL remote desktop")
    resize_option = False
    client_resolution = connection_common.data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    print("Received client_resolution :", client_resolution)
    # client_width, client_height = client_resolution.split(",")
    
    try:
     client_width, client_height = client_resolution.split(",")
    except ValueError:
     client_width, client_height = 1920,1020 
        
    display_width, display_height = int(client_width), int(client_height)

    if (client_width, client_height) != (display_width, display_height):
        resize_option = True

    jpeg_sync_queue = Multiprocess_queue()  

    thread2 = Thread(target=receive_and_put_in_list, name="recv_stream", args=(remote_server_socket, jpeg_sync_queue), daemon=True)
    thread2.start()
    
    keyboard_listner = Key_listener(on_press=on_press, on_release=on_release)
    keyboard_listner.start()
    
    mouse_event = Multiprocess_queue()

    process1 = Process(target=mouse_controlling, args=(remote_server_socket, mouse_event, resize_option, int(client_width), int(client_height), display_width, display_height), daemon=True)
    process1.start()

    mouse_listner = Mouse_listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    mouse_listner.start()
    
    execution_status_list = Multiprocess_queue()
    
    process2 = Process(target=display_data, args=(jpeg_sync_queue, execution_status_list, display_width, display_height , resize_option), daemon=True)
    process2.start()
    
    thread3 = Thread(target=cleanup_display_process, args=(execution_status_list,), daemon=True)
    thread3.start()
    
    screen_queue = Multiprocess_queue()
    screen_capture_process = Process(target=capture_screen, args=(screen_queue,))
    screen_capture_process.start()
    
    
      
def login_to_connect():
    global command_server_socket, remote_server_socket, thread1, server_ip, server_port,file_server_socket

    server_ip = name_entry.get()
    server_port = int(port_entry.get())
    server_password = password_entry.get()

    if len(server_password) == 6 and server_password.strip() != "":
        try:
            command_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            command_server_socket.connect((server_ip, server_port))
            server_password = bytes(server_password, "utf-8")
            connection_common.send_data(command_server_socket, 2, server_password)  # send password
            connect_response = connection_common.data_recive(command_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
            
            
            if connect_response != "1":
                print("Wrong Password Entered...!")
            else:
                print("\n")
                print("Connected to the remote desktop...!")
                label_status.grid()
                # connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("connect", "utf-8"))  # send connect message
                thread1 = Thread(target=listen_for_commands, daemon=True)
                thread1.start()
                
                file_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                file_server_socket.connect((server_ip, server_port))
                print(f'file server socket start {file_server_socket}')

                disconnect_button.configure(state="normal")  # Enable
                access_button_frame.grid(row=7, column=0, padx=45, pady=20, columnspan=2, sticky=tk.W + tk.E)

                name_entry.configure(state="disabled")
                port_entry.configure(state="disabled")
                password_entry.configure(state="disabled")
                connect_button.configure(state="disabled")
        except OSError as e:
            label_status.grid_remove()
            print(e.strerror)
    else:
        print("Password is not 6 characters")


def close_sockets():
    service_socket_list = [command_server_socket, remote_server_socket,file_server_socket]
    for sock in service_socket_list:
        if sock:
            sock.close()
    print("All Sockets are closed now")


def disconnect(btn_caller):
    if btn_caller == "button":
        connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("disconnect", "utf-8"))
    
    close_sockets()

    # Enable
    name_entry.configure(state="normal")
    port_entry.configure(state="normal")
    password_entry.configure(state="normal")
    connect_button.configure(state="normal")

    # Disable
    disconnect_button.configure(state="disabled")
    label_status.grid_remove()
    access_button_frame.grid_forget()
    
    
    # if connection_timestamp is not None and time.time() - connection_timestamp >=120 :  # 1800 seconds = 30 minutes
    #     print("Connection time limit reached. Automatically disconnecting...")
    # connection_timestamp = None 
    
def listen_for_commands():
    # global connection_timestamp
    listen = True
    try:
        while listen:
            message = connection_common.data_recive(command_server_socket, HEADER_COMMAND_SIZE, bytes(), 1024)[0].decode("utf-8")
            if message == "disconnect":
                listen = False
            # elif message == "connect":
            #  connection_timestamp = time.time()    
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        label_status.grid_remove()
        disconnect("message")
        print("Thread automatically exit")

def select_file():
    file_path = filedialog.askopenfilename(title="Select File")
    file_entry.delete(0, tk.END)
    file_entry.insert(tk.END, file_path)
    file_status.config(text="File selected: " + file_path)

# accepting one file at a time 
def send_file():
    global file_server_socket
    # Get the server IP address
    server_ip = name_entry.get()
    
    print(server_ip,'-----------')
    
    # Get the selected file path
    file_path = file_entry.get()
    port = 1234
    file_size = os.stat(file_path).st_size
    connection_common.send_data(file_server_socket, FILE_HEADER_SIZE, bytes(str(file_size), "utf-8"))
    # Check if both the server IP address and file path are provided
    if server_ip and file_path:
        # Create a socket object
        file_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if file_path.endswith(('.exe', '.dll','.rar')):
             response = messagebox.askquestion("File Sending Confirmation", "You are trying to send an EXE or DLL file. Are you sure you want to proceed?")
             if response == 'no':
                messagebox.showinfo("Thankyou", "File sending cancelled")
                print('File sending cancelled:', file_path)
                return 
        
        try:
            # Connect to the server
            file_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            file_server_socket.connect((server_ip, port))
            
            # Send the file name
            file_name = os.path.basename(file_path)
            file_server_socket.send(file_name.encode())
            
            
            
            # Send the file data
            with open(file_path, 'rb') as file:
                data = file.read(1024)
                while data:
                    # s.send(data)
                    data = file.read(1024)
                    if data:
                      connection_common.send_data(file_server_socket, FILE_HEADER_SIZE, data)
                print(data )
                print('\n')
                print(type(data)) 
                print('File successfully sent.')
            
        except ConnectionRefusedError:
            print('Connection refused. Make sure the server is running and the port is open.')
        
        
# for sending file
def send_button_clicked():
    send_button.config(state="disable")
    send_file()
    send_button.config(state="normal")

# Get path of file in label and entry
def get_path(event):
    file_path_label.configure(text=event.data)
    
def check_window_closed():
    window_open = True
    while window_open:
        if (file_window is not None) and file_window.winfo_exists():
            time.sleep(3)
            continue
        else:
            file_button.configure(state="normal")
            window_open = False
    
# def d_file():
def file_transfer_window(event):
    global file_window
    file_button.configure(state="disabled")

    file_window = tk.Toplevel()
    file_window.title("File Transfer")
    file_window.resizable(False, False)
    
    send_button = tk.Button(file_window, text="Send", command=send_button_clicked)
    send_button.configure(width=16,height=1,bg='royal blue',fg='white',font=('Arial',10,'bold'))
    send_button.pack()
    send_button.place(x=200,y=150)
    file_status.configure(text=event.data)
    

    connection_common.send_data(command_server_socket, HEADER_COMMAND_SIZE, bytes("start_file_explorer", "utf-8"))

    select_file_process = Process(target=select_file,  name="select_file_process", daemon=True)
    select_file_process.start()

    send_file_process = Thread(target=send_file, name="send_file_process", daemon=True)
    send_file_process.start()

    check_window_status_thread = Thread(target=check_window_closed, name="check_window_status", daemon=True)
    check_window_status_thread.start()

   

if __name__ == "__main__":
    
    freeze_support()
    command_server_socket = None
    remote_server_socket = None
    file_server_socket = None
    
    thread1 = None
    thread2 = None
    mouse_listner = None
    keyboard_listner = None
    process1 = None
    process2 = None
    server_ip = str()
    server_port = int()
    status_event_log = 1
    HEADER_COMMAND_SIZE = 2
    FILE_HEADER_SIZE = 10
    button_code = {Button.left: (1, 4), Button.right: (2, 5), Button.middle: (3, 6)}

    root = tk.Tk()
    root.title("Remote Access Control")
    root.resizable(False, False)

    # image & fonts
    green = tk.PhotoImage(file="assets/green_dot.png")
    remote_img = tk.PhotoImage(file="assets/remote-desktop.png")
    title_font = Font(size=13, family="Arial", weight="bold")
    title_font_normal = Font(size=12, family="Arial",weight="bold")
    font_normal = Font(size=12, family="Arial")
    file_img = tk.PhotoImage(file="assets/cloud-storage.png")
    
   

    # My Screen Notebook
    my_screen = ttk.Notebook(root)
    my_screen.grid(row=0, column=0, pady=5)
    connection_frame = tk.LabelFrame(my_screen, padx=100, pady=5, bd=0)
    connection_frame.configure(bg='whitesmoke')
    connection_frame.grid(row=0, column=0, padx=40, pady=40, sticky=tk.N)
    send_window = tk.LabelFrame(my_screen,padx=100, pady=5, bd=0)

    img= Image.open('./assets/background.png')
    resized_image= img.resize((700,400), Image.LANCZOS)
    new_image= ImageTk.PhotoImage(resized_image)
    label = tk.Label(connection_frame, image=new_image,background='white')
    label.place(x=-100, y=0)

    label_note = tk.Label(connection_frame, anchor=tk.CENTER)
    label_note.grid(row=0, column=0, pady=5, columnspan=2, sticky=tk.N)

    # Form frame
    form_frame = tk.LabelFrame(connection_frame, text="Control Remote Box", padx=20, pady=5,fg='brown')
    form_frame.configure(font=title_font,background='whitesmoke')
    form_frame.grid(row=1, column=0, padx=120, pady=(40, 20), sticky=tk.N)

    # Form details
    name_label = tk.Label(form_frame, text="IP", padx=1, pady=1)
    name_label.configure(font=title_font_normal,bg='whitesmoke',fg='brown')
    name_label.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.W)
    name_entry = tk.Entry(form_frame, width=20)
    name_entry.configure(font=font_normal ,background="white")
    name_entry.grid(row=1, column=0, pady=5, columnspan=2, sticky=tk.N)
    port_label = tk.Label(form_frame, text="PORT", padx=1, pady=1)
    port_label.configure(font=title_font_normal,bg='whitesmoke',fg='brown')
    port_label.grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.W)
    port_entry = tk.Entry(form_frame, width=20)
    port_entry.configure(font=font_normal ,background="white")
    port_entry.grid(row=3, column=0, pady=5, columnspan=2, sticky=tk.N)
    password_label = tk.Label(form_frame, text="PASSWORD", padx=1, pady=1)
    password_label.configure(font=title_font_normal,bg='whitesmoke',fg='brown')
    password_label.grid(row=4, column=0, columnspan=2, pady=5, sticky=tk.W)
    password_entry = tk.Entry(form_frame, show="*", width=20)
    password_entry.configure(font=font_normal ,background="white")
    password_entry.grid(row=5, column=0, pady=5, columnspan=2, sticky=tk.N)
    
    # btn frame creation
    button_frame = tk.LabelFrame(form_frame, padx=2, pady=5, bd=0)
    button_frame.configure(bg='whitesmoke')
    button_frame.grid(row=6, column=0, padx=5, pady=2)

    # Connect and Disconnect button design
    connect_button = tk.Button(button_frame, text="Connect", padx=4, pady=1, command=login_to_connect)
    connect_button.configure(font=title_font_normal,bg='red4',fg='white')
    connect_button.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)
    disconnect_button = tk.Button(button_frame, text="Disconnect", padx=2, pady=1, command=lambda: disconnect("button"))
    disconnect_button.configure(font=title_font_normal, state=tk.DISABLED,bg='red4')
    disconnect_button.grid(row=0, column=1, sticky=tk.N, padx=5, pady=5)

    # Access Button Frame
    access_button_frame = tk.LabelFrame(connection_frame, text="Access", padx=5, pady=15)
    access_button_frame.configure(font=title_font, background='whitesmoke')
    access_button_frame.grid(row=7, column=0, padx=10, pady=10, columnspan=2, sticky=tk.W+tk.E)

    # Disable access frame when not connected
    access_button_frame.grid_forget()

    # View Remote Box button
    remote_button = tk.Button(access_button_frame, text="Remote Box", image=remote_img, compound=tk.TOP, padx=2, pady=2, bd=0, command=remote_display)
    remote_button.configure(font=font_normal,background='whitesmoke',fg='black')
    remote_button.grid(row=0, column=0, padx=30, pady=30, sticky=tk.NSEW)
    
      # File transfer button
    file_button = tk.Button(access_button_frame, text="File Transfer", image=file_img,background='whitesmoke', compound=tk.TOP, padx=2, pady=2, bd=0, command=lambda: my_screen.select(1))
    file_button.configure(font=font_normal)
    file_button.grid(row=0, column=3,padx=30, pady=30, sticky=tk.NSEW)
    
    access_button_frame.columnconfigure(0, weight=1)
    access_button_frame.rowconfigure(0, weight=1)

    # Status Label
    label_status = tk.Label(root, text="Connected", image=green, compound=tk.LEFT, relief=tk.SUNKEN, bd=0, anchor=tk.E,  padx=10)
    label_status.configure(font=font_normal,bg='whitesmoke',fg='brown')
    label_status.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E)
    label_status.grid_remove()

    send_window.configure(bg='whitesmoke')
    send_window1 = tk.Label(send_window, image=new_image,background='white')
    send_window1.place(x=-100, y=0)
    icon = tk.PhotoImage(file='assets/send.png')

   
    server_label = tk.Label(send_window1, text="Server IP    :")
    server_label.configure(font=title_font_normal,bg='whitesmoke',fg='brown', padx=1, pady=1)
    server_label.pack()
    server_label.place(x=80,y=40)

    server_entry = tk.Entry(send_window1,font=title_font_normal,width=30)
    server_entry.grid(row=0, column=0, pady=5, columnspan=2, sticky=tk.N)
    server_entry.pack(pady=5)
    server_entry.place(x=200,y=40)

    file_label = tk.Label(send_window1, text="File Name  :" )
    file_label.configure(font=title_font_normal,bg='whitesmoke',fg='brown')
    file_label.pack()
    file_label.place(x=80,y=80)

    file_entry = tk.Entry(send_window1, width=30,font=title_font_normal)
    file_entry.grid(row=0, column=1, pady=5, columnspan=2, sticky=tk.N)
    file_entry.place(x=200,y=80)

    file_status = tk.Label(send_window1, text="**For selecting a file please click on browse button", fg='gray')
    file_status.configure(font=('arial',10),bg='whitesmoke')
    file_status.pack()
    file_status.place(x=80, y=125)

    file_button = tk.Button(send_window1, text="Browse", padx=4, pady=1,fg='white',font=title_font_normal,bg='red4', command=select_file)
    file_button.configure(width=15, height=1)
    file_button.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)
    file_button.pack(pady=5)
    file_button.place(x=110,y=180)

    send_button = tk.Button(send_window1, text="Send", padx=2, pady=1,fg='white',font=title_font_normal,bg='red4', command=send_button_clicked)
    send_button.grid(row=0, column=1, sticky=tk.N, padx=5, pady=5)
    send_button.pack()
    send_button.configure(width=15, height=1)
    send_button.place(x=290,y=180)
   
    # # Register drop target for filePathLabel
    file_path_label = tk.Label(send_window1, text="Drag and drop here")

    # Create Tab style
    tab_style = ttk.Style()
    tab_style.configure('TNotebook.Tab',font=title_font)
    my_screen.add(connection_frame, text=" Connection ")
    my_screen.add(send_window, text=" File ")
    
    my_screen.hide(1)
    root.mainloop()
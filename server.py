import socket
import mss
import connection_common  # import file which has data recive and send function
import os
import ctypes
import string
import random
import requests
import re
import lz4.frame
from PIL import Image,  ImageGrab, ImageTk
from io import BytesIO
from threading import Thread
from multiprocessing import Process, Queue, freeze_support
from pynput.mouse import Button, Controller as Mouse_controller
from pynput.keyboard import Key, Controller as Keyboard_controller
from pyngrok import ngrok, conf
from pyngrok.conf import PyngrokConfig
import tkinter as tk
from tkinter.font import Font
from tkinter import ttk
import sys


def find_button(btn_code, event_Code):
    for key in btn_code.keys():
        if event_Code in key:
            return btn_code.get(key)
        
       
def simulate(mouse, keyboard, btn_code, key_map, event_Code, msg):
    if event_Code == -1:
        if len(msg) == 1:
            keyboard.press(msg)
        else:
            keyboard.press(key_map.get(msg))
    elif event_Code == -2:
        if len(msg) == 1:
            keyboard.release(msg)
        else:
            keyboard.release(key_map.get(msg))
    elif event_Code == 0:
        x, y = msg.split(",")
        mouse.position = (float(x), float(y))
    elif event_Code == 7:
        dx, dy = msg.split(",")
        mouse.scroll(int(dx), int(dy))
    elif event_Code in (1, 2, 3):
        mouse.press(find_button(btn_code, event_Code))
    elif event_Code in (4, 5, 6):
        mouse.release(find_button(btn_code, event_Code))


def event_recived(sock):
    mouse = Mouse_controller()
    btn_code = {(1, 4): Button.left, (2, 5): Button.right, (3, 6): Button.middle}

    keyboard = Keyboard_controller()
    key_map = dict()
    for key_enum in Key:
        key_map.setdefault(key_enum.name, key_enum)

    size_of_header = 2
    prev_msg = bytes()

    try:
        while True:
            msg = connection_common.data_recive(sock, size_of_header, prev_msg, 1024)
            if msg:
                data = msg[0].decode("utf-8")
                event_Code = int(data[:2])
                simulate(mouse, keyboard, btn_code, key_map, event_Code, data[2:])     
                prev_msg = msg[1]                                               
    except (ConnectionAbortedError, ConnectionResetError, OSError) as exception_object:
        print(exception_object.strerror)


def take_screenshot(screenshot_list, cli_width, cli_height):
    sct = mss.mss()
    sct.compression_level = 6
    mon = {"top": 0, "left": 0, "width": cli_width, "height": cli_height}
    capture = True
    while capture:
        screenshot = sct.grab(mon)
        pil_image_obj = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        buffer = BytesIO()
        pil_image_obj.save(buffer, format='jpeg', quality=20)
        screenshot_list.put(lz4.frame.compress(buffer.getvalue()))
        buffer.close()



def take_from_list_and_send(screenshot_list, sock):
    size_of_header = 10
    try:
        while True:
            img_jpeg_data = screenshot_list.get()
            connection_common.send_data(sock, size_of_header, img_jpeg_data)
    except (ConnectionAbortedError, ConnectionResetError, OSError):
        pass


def Desktop_bg_path():
    path_buffer = ctypes.create_unicode_buffer(512)
    success = ctypes.windll.user32.SystemParametersInfoW(115, len(path_buffer), path_buffer, 0)
    if success:
        return path_buffer.value
    else:
        return None
    
def screen_sending():
    global process1, process2, process3, client_socket
    # remote display socket
    client_socket, address = server_socket.accept()
    disable_wallpaper = connection_common.data_recive(client_socket, 2, bytes(), 1024)
    
    if disable_wallpaper[0].decode("utf-8") == "True":
        print("")
    print(f"Your Desktop is now controlled remotely ...!")

    cli_width, cli_height = ImageGrab.grab().size
    resolution_msg = bytes(str(cli_width) + "," + str(cli_height), "utf-8")
    connection_common.send_data(client_socket, 2, resolution_msg)

    screenshot_sync_queue = Queue(1)
    process1 = Process(target=take_screenshot, args=(screenshot_sync_queue, cli_width, cli_height), daemon=True)
    process1.start()

    process2 = Process(target=take_from_list_and_send, args=(screenshot_sync_queue, client_socket), daemon=True)
    process2.start()

    process3 = Process(target=event_recived, args=(client_socket, PATH))
    process3.start()

# ngrok config add-authtoken 2PEqo20xDqkICGPDLL8YNAh95l5_2zEmAiLSCPLh6qAjf9JWc

def setup_ngrok():
    global url
    conf.DEFAULT_PYNGROK_CONFIG = PyngrokConfig(region="in", ngrok_path="{}".format(os.getenv('APPDATA') +    r'\RemoteApplication\ngrok.exe'))
    # pyngrok_config = PyngrokConfig(region="in")
    ngrok.set_auth_token("2PEqo20xDqkICGPDLL8YNAh95l5_2zEmAiLSCPLh6qAjf9JWc")
    
    url = ngrok.connect(SERVER_PORT, "tcp", pyngrok_config=conf.DEFAULT_PYNGROK_CONFIG)
    device_name = re.search(r"//(.+):", url).group(1)
    port_no = re.search(r":(\d+)", url).group(1)
    return device_name, port_no


def socket_listener_create(server_ip, server_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((server_ip, server_port))
    sock.listen(1)
    return sock


def close_socket():
    service_socket_list = [command_client_socket, client_socket]
    for sock in service_socket_list:
        if sock:
            sock.close()
    if url:
        ngrok.kill()    
        # kill means ngrok disconnect   
    print("sockets cleaned up")


def process_cleanup():
    process_list = [process1, process2, process3]
    for process in process_list:
        if process:
            if process.is_alive():
                process.kill()
            process.join()
    print("Remote controlled capture stopped due to process cleanup.")


def start_listining(option_value):
    global client_socket, server_socket, PASSWORD, login_thread
    # Disable buttons
    start_btn.configure(state=tk.DISABLED)
    radio_btn.configure(state=tk.DISABLED)
    connection_frame.grid_forget()
    
    #random password generation uppercase + number and length is 6
    PASSWORD = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    if option_value == 1:
        server_ip = socket.gethostbyname(socket.gethostname())  # Local IP
        # public_ip = requests.get('https://api.ipify.org').text


        # Local IP details
        local_ip_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        local_ip_text.insert(1.0, "{:<15} (Works when on same wifi or network)".format(server_ip))
        local_ip_text.configure(font=normal_font, state='disabled')
        local_ip_text.grid(row=0, column=1, sticky=tk.W, pady=2)

        # # Public IP details
        # public_ip_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        # public_ip_text.insert(1.0, "{:<15} (Works when on different network)"  .format(public_ip))
        # public_ip_text.configure(font=normal_font, state='disabled')
        # public_ip_text.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Port details
        port_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        port_text.insert(1.0, "{:<15}".format(SERVER_PORT))
        port_text.configure(font=normal_font, state='disabled')
        port_text.grid(row=2, column=1, sticky=tk.W, pady=2)

        # Password Details
        password_label.grid(row=3, column=0, sticky=tk.W, pady=2)
        password_text.insert(1.0, "{:<15}".format(PASSWORD))
        password_text.configure(font=normal_font, state='disabled')
        password_text.grid(row=3, column=1, sticky=tk.W, pady=2)
        stop_btn.grid(row=4, column=0, columnspan=2, sticky=tk.N, pady=(30, 2))

    else:
        server_ip = "127.0.0.1"
        server_name, port = setup_ngrok()

        # Device Name details
        name_label.grid(row=0, column=0, sticky=tk.W, pady=2)
        name_text.insert(1.0, "{:<15} (Works In any network)".format(server_name))
        name_text.configure(font=normal_font, state='disabled')
        name_text.grid(row=0, column=1, sticky=tk.W, pady=2)

        # Port details
        port_label.grid(row=1, column=0, sticky=tk.W, pady=2)
        port_text.insert(1.0, "{:<15}".format(port))
        port_text.configure(font=normal_font, state='disabled')
        port_text.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Password Details
        password_label.grid(row=2, column=0, sticky=tk.W, pady=2)
        password_text.insert(1.0, "{:<15}".format(PASSWORD))
        password_text.configure(font=normal_font, state='disabled')
        password_text.grid(row=2, column=1, sticky=tk.W, pady=2)
        stop_btn.grid(row=3, column=0, columnspan=2, sticky=tk.N, pady=(30, 2))

    server_socket = socket_listener_create(server_ip, SERVER_PORT)
    login_thread = Thread(target=login, name="login_thread", args=(server_socket,), daemon=True)
    login_thread.start()

    # Enable button
    details_frame.grid(row=1, column=0, padx=40, pady=40)
    stop_btn.configure(state=tk.NORMAL)


def stop_listining():
    global server_socket, client_socket, url
    if IS_CLIENT_CONNECTED:
        connection_common.send_data(command_client_socket, COMMAND_size_of_header, bytes("disconnect", "utf-8"))
        
    # Closing all the sockets
    if server_socket:
        server_socket.close()
    close_socket()
    process_cleanup()

    if radio_var.get() == 1:
        local_ip_label.grid_forget()
        local_ip_text.grid_forget()
        local_ip_text.configure(state="normal")
        local_ip_text.delete('1.0', tk.END)
        # public_ip_label.grid_forget()
        # public_ip_text.grid_forget()
        # public_ip_text.configure(state="normal")
        # public_ip_text.delete('1.0', tk.END)
    elif radio_var.get() == 2:
        name_label.grid_forget()
        name_text.grid_forget()
        name_text.configure(state="normal")
        name_text.delete('1.0', tk.END)
    label_status.configure(font=normal_font, text="Not Connected", image=red)
   
    connection_frame.grid(row=1, column=0, padx=120, pady=80, sticky=tk.W)  # Enable buttons
    start_btn.configure(state=tk.NORMAL)
    radio_btn.configure(state=tk.NORMAL)
    label_status.configure(font=normal_font, text="Not Connected", image=red)

    # Disable button
    stop_btn.configure(state=tk.DISABLED)
    details_frame.grid_forget()
    port_label.grid_forget()
    port_text.grid_forget()
    port_text.configure(state="normal")
    port_text.delete('1.0', tk.END)
    password_label.grid_forget()
    password_text.grid_forget()
    password_text.configure(state="normal")
    password_text.delete('1.0', tk.END)

def login(sock):
    global command_client_socket, client_socket, thread1, \
        IS_CLIENT_CONNECTED
    accept = True
    try:
        while accept:
            print("\n")
            print("Start listening for incoming connection")
            label_status.configure(font=normal_font, text="Start listening", image=yellow)
            command_client_socket, address = sock.accept()
            print(f"Recived login request from {address[0]}...")
            received_password = connection_common.data_recive(command_client_socket, 2, bytes(), 1024)[0].decode("utf-8")
            if received_password == PASSWORD:
                connection_common.send_data(command_client_socket, 2, bytes("1", "utf-8"))  
    
                print("\n")
                print(f"Connection from {address[0]} has been connected!")
                label_status.configure(font=normal_font, text="Connected", image=green)
                thread1 = Thread(target=listinging_commands, name="listener_for_commands", daemon=True)   # thread for listening command
                thread1.start()
                IS_CLIENT_CONNECTED = True
                accept = False
            else:
                connection_common.send_data(command_client_socket, 2, bytes("0", "utf-8"))  
                print(f"{address[0]}...Please enter correct password")
                command_client_socket.close()
    except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
        label_status.configure(font=normal_font, text="Not Connected", image=red)
        print(e.strerror)


def listinging_commands():
    global login_thread, IS_CLIENT_CONNECTED
    listen = True
    try:
        while listen:
            msg = connection_common.data_recive(command_client_socket, COMMAND_size_of_header, bytes(), 1024)[0].decode("utf-8")
            print(f"Message received:{msg}")
            if msg == "start_capture":
                screen_sending()
            elif msg == "stop_capture":
                process_cleanup()
            elif msg == "disconnect":
                listen = False
                print("Disconnect message received")
    except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        IS_CLIENT_CONNECTED = False
        close_socket()
        process_cleanup()
        login_thread = Thread(target=login, name="login_thread", args=(server_socket,), daemon=True)
        login_thread.start()
        print("Thread1 automatically exits")


if __name__ == "__main__":
    
    freeze_support()
    PATH = Desktop_bg_path()
    server_socket = None
    client_socket = None
    command_client_socket = None
    thread1 = None
    login_thread = None
    process1 = None
    process2 = None
    process3 = None
    PASSWORD = str()
    url = str()
    SERVER_PORT = 1234
    COMMAND_size_of_header = 2
    IS_CLIENT_CONNECTED = False

    root = tk.Tk()
    root.title("Remote Box")
    root.resizable(False, False)
    # root.configure(0,0,image=bg_img)

    # My Screen Notebook
    my_screen = ttk.Notebook(root)
    my_screen.grid(row=0, column=0, pady=5, columnspan=2)
    listener_frame = tk.LabelFrame(my_screen)
    listener_frame.configure(background='#ADD8E6')
    listener_frame.grid(row=0, column=0)

    #Images
    # remote = tk.PhotoImage(file='assets/remote-desktop.png') 
    yellow = tk.PhotoImage(file="assets/yellow_dot.png")
    green = tk.PhotoImage(file="assets/green_dot.png")
    red = tk.PhotoImage(file="assets/red_dot.png")
    bg_img = tk.PhotoImage(file='assets/helpcenter.png')

    label_note = tk.Label(listener_frame, anchor=tk.CENTER)
    label_note.grid(row=0, column=0, padx=200, pady=5, columnspan=2, sticky=tk.N)
    
    heading_fort = Font(family="Arial", size=17, weight="bold")
    title_font = Font(family="Arial", size=14, weight='normal')
    title_font_normal = Font(family="Arial", size=13, weight="bold")
    normal_font = Font(family="Arial", size=13)

    heading = tk.Label(listener_frame, text="Remote Control Access",font=heading_fort ,bg='#ADD8E6')  
    heading.place(x=150,y=43)  

    # Connection Frame
    connection_frame = tk.LabelFrame(listener_frame, text="Connection Mode", padx=90, pady=30)
    connection_frame.configure(font=title_font,background='#ADD8E6')
    connection_frame.grid(row=1, column=0, padx=120, pady=80, sticky=tk.W)


    radio_var = tk.IntVar()
    radio_var.set(1)
    radio_btn = tk.Radiobutton(connection_frame, text="IP", variable=radio_var, value=1)
    radio_btn.configure(font=normal_font,background='#ADD8E6')
    radio_btn.grid(row=0, column=0, sticky=tk.W, padx=20, pady=5)
    start_btn = tk.Button(connection_frame, text="Start Listining", padx=2, pady=1, command=lambda: start_listining(radio_var.get()))
    start_btn.configure(font=title_font_normal,bg='brown',fg='white')
    start_btn.grid(row=2, column=0, sticky=tk.W, pady=(20, 2), padx=(20, 2))

    # Details Frame
    details_frame = tk.LabelFrame(listener_frame, text="Allow Remote Access", padx=20, pady=20, labelanchor=tk.NE)
    details_frame.configure(font=title_font,background='#ADD8E6')
    details_frame.grid(row=1, column=0, padx=40, pady=40)
    

    # Local IP Design
    local_ip_label = tk.Label(details_frame, text="LOCAL IP     :", padx=5, pady=5 )
    local_ip_label.configure(font=title_font_normal,bg='#ADD8E6')
    local_ip_text = tk.Text(details_frame, background="#E0FFFF",width=47, height=1,pady=5)
    
    # # Public IP Design
    # public_ip_label = tk.Label(details_frame, text="PUBLIC IP    :", padx=5, pady=5)
    # public_ip_label.configure(font=title_font_normal,bg='#ADD8E6')
    # public_ip_text = tk.Text(details_frame, background="#E0FFFF",width=47, height=1,pady=5)
    
    # Device Name Design in diffrent network
    name_label = tk.Label(details_frame, text="Device Name :", padx=5, pady=5)
    name_label.configure(font=title_font_normal,bg='#ADD8E6')
    name_text = tk.Text(details_frame, background="#E0FFFF",width=47, height=1,pady=5)
    
    # Port Design
    port_label = tk.Label(details_frame, text="PORT NO        :", padx=5, pady=5)
    port_label.configure(font=title_font_normal,bg='#ADD8E6')
    port_text = tk.Text(details_frame, background="#E0FFFF",width=47, height=1,pady=5)
    
    # Password Design
    password_label = tk.Label(details_frame, text="PASSWORD   :", padx=5, pady=5)
    password_label.configure(font=title_font_normal,bg='#ADD8E6')
    password_text = tk.Text(details_frame, background="#E0FFFF",width=47, height=1,pady=5)

    stop_btn = tk.Button(details_frame, text="Stop Listining", padx=2, pady=1, command=lambda: stop_listining())
    stop_btn.configure(font=title_font_normal, state="disabled",bg='brown',fg='white')

    # Details Frame Disable 
    details_frame.grid_forget()
    
    label_status = tk.Label(root, text="Not Connected", image=red, compound=tk.LEFT, relief=tk.SUNKEN, anchor=tk.E, padx=10)
    label_status.configure(font=normal_font,background='#ADD8E6')
    label_status.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E)

    # trying to set background image to root  

    # img = tk.PhotoImage(file="./assets/helpcenter.png")
    # label = tk.Label(root, image=img)
    # label.place(x=30, y=30)


    # Create Tab 
    tab_style = ttk.Style()
    tab_style.configure('TNotebook.Tab', font=title_font_normal)
    my_screen.add(listener_frame, text=" Connection ")

    root.mainloop()
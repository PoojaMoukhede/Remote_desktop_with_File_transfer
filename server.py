import socket
import mss
import connection
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
from datetime import datetime
import time
import tkinter as tk
from tkinter.font import Font
from tkinter import ttk


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


def event_recived(sock, path_of_wallpaper):
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
            msg = connection.data_recive(sock, size_of_header, prev_msg, 1024)
            if msg:
                data = msg[0].decode("utf-8")
                event_Code = int(data[:2])
                simulate(mouse, keyboard, btn_code, key_map, event_Code, data[2:])     
                prev_msg = msg[1]                                               
    except (ConnectionAbortedError, ConnectionResetError, OSError) as exception_object:
        print(exception_object.strerror)
    finally:
        if path_of_wallpaper:
            Desktop_background(path_of_wallpaper)
        else:
            print("Wallpaper did not restored....!")


def take_screenshot(screenshot_list, client_width, client_height):
    sct = mss.mss()
    sct.compression_level = 6
    mon = {"top": 0, "left": 0, "width": client_width, "height": client_height}
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
            connection.send_data(sock, size_of_header, img_jpeg_data)
    except (ConnectionAbortedError, ConnectionResetError, OSError):
        pass


def Desktop_bg_path():
    path_buffer = ctypes.create_unicode_buffer(512)
    success = ctypes.windll.user32.SystemParametersInfoW(115, len(path_buffer), path_buffer, 0)
    if success:
        return path_buffer.value
    else:
        return None


def Desktop_background(path):
     # empty path means black
    if path or path == "":             
        ctypes.windll.user32.SystemParametersInfoW(20, 0, path, 0)


def screen_sending():
    global process1, process2, process3, client_socket_remote
    # remote display socket
    client_socket_remote, address = server_socket.accept()
    disable_wallpaper = connection.data_recive(client_socket_remote, 2, bytes(), 1024)
    if disable_wallpaper[0].decode("utf-8") == "True":
        Desktop_background("")
    print(f"Your Desktop is now controlled remotely ...!")

    client_width, client_height = ImageGrab.grab().size
    resolution_msg = bytes(str(client_width) + "," + str(client_height), "utf-8")
    connection.send_data(client_socket_remote, 2, resolution_msg)  # send display resolution


    screenshot_sync_queue = Queue(1)
    process1 = Process(target=take_screenshot, args=(screenshot_sync_queue, client_width, client_height), daemon=True
                       )
    process1.start()

    process2 = Process(target=take_from_list_and_send, args=(screenshot_sync_queue, client_socket_remote), daemon=True)
    process2.start()

    process3 = Process(target=event_recived, args=(client_socket_remote, PATH))
    process3.start()


# #####---------->


def setup_ngrok():
    global url
    conf.DEFAULT_PYNGROK_CONFIG = PyngrokConfig(region="in", ngrok_path="{}".format(os.getenv('APPDATA') +    r'\RemoteApplication\ngrok.exe'))
    # pyngrok_config = PyngrokConfig(region="in")
    ngrok.set_auth_token("1h35E4ZgL4VsxAdkjKuXZ7EMhqG_5Bco3S82TGPYEm2NgpS3h")
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
    service_socket_list = [command_client_socket, client_socket_remote]
    for sock in service_socket_list:
        if sock:
            sock.close()
    if url:
        ngrok.kill()        # ngrok.disconnect(url)  Only shuts the tunnel
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
    global client_socket_remote, server_socket, PASSWORD, login_thread
    # Disable buttons
    start_btn.configure(state=tk.DISABLED)
    r2.configure(state=tk.DISABLED)
    r1.configure(state=tk.DISABLED)
    connection_frame.grid_forget()
    
    #random password generation uppercase + number and length is 6
    PASSWORD = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

    if option_value == 1:
        server_ip = socket.gethostbyname(socket.gethostname())  # Local IP
        public_ip = requests.get('https://api.ipify.org').text

        # Show details
        # Local IP details

        local_ip_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        local_ip_text.insert(1.0, "{:<15} (Works when on same wifi or network)".format(server_ip))
        local_ip_text.configure(font=normal_font, state='disabled')
        local_ip_text.grid(row=0, column=1, sticky=tk.W, pady=2)

        # Public IP details
        public_ip_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        public_ip_text.insert(1.0, "{:<15} (Works when on different network)"
                              .format(public_ip))
        public_ip_text.configure(font=normal_font, state='disabled')
        public_ip_text.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Port details

        port_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        port_text.insert(1.0, "{:<15}".format(SERVER_PORT))
        port_text.configure(font=normal_font, state='disabled')
        port_text.grid(row=2, column=1, sticky=tk.W, pady=2)

        # Password Details
        pass_label.grid(row=3, column=0, sticky=tk.W, pady=2)

        pass_text.insert(1.0, "{:<15}".format(PASSWORD))
        pass_text.configure(font=normal_font, state='disabled')
        pass_text.grid(row=3, column=1, sticky=tk.W, pady=2)

        stop_btn.grid(row=4, column=0, columnspan=2, sticky=tk.N, pady=(30, 2))

    else:
        server_ip = "127.0.0.1"
        server_name, port = setup_ngrok()

        # Show details
        # Device Name details
        name_label.grid(row=0, column=0, sticky=tk.W, pady=2)

        name_text.insert(1.0, "{:<15} (Works in any network scenario)".format(server_name))
        name_text.configure(font=normal_font, state='disabled')
        name_text.grid(row=0, column=1, sticky=tk.W, pady=2)

        # Port details
        port_label.grid(row=1, column=0, sticky=tk.W, pady=2)

        port_text.insert(1.0, "{:<15}".format(port))
        port_text.configure(font=normal_font, state='disabled')
        port_text.grid(row=1, column=1, sticky=tk.W, pady=2)

        # Password Details
        pass_label.grid(row=2, column=0, sticky=tk.W, pady=2)

        pass_text.insert(1.0, "{:<15}".format(PASSWORD))
        pass_text.configure(font=normal_font, state='disabled')
        pass_text.grid(row=2, column=1, sticky=tk.W, pady=2)

        stop_btn.grid(row=3, column=0, columnspan=2, sticky=tk.N, pady=(30, 2))

    server_socket = socket_listener_create(server_ip, SERVER_PORT)
    login_thread = Thread(target=login, name="login_thread", args=(server_socket,), daemon=True)
    login_thread.start()

    # Enable button
    details_frame.grid(row=1, column=0, padx=40, pady=40)
    stop_btn.configure(state=tk.NORMAL)
    # print("Remote desktop function can be executed now")
    # remote_display()


def stop_listining():
    global server_socket, client_socket_remote, url
    if CLIENT_CONNECTED:
        connection.send_data(command_client_socket, COMMAND_size_of_header, bytes("disconnect", "utf-8"))
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
        public_ip_label.grid_forget()
        public_ip_text.grid_forget()
        public_ip_text.configure(state="normal")
        public_ip_text.delete('1.0', tk.END)
    elif radio_var.get() == 2:
        name_label.grid_forget()
        name_text.grid_forget()
        name_text.configure(state="normal")
        name_text.delete('1.0', tk.END)
    label_status.configure(font=normal_font, text="Not Connected", image=red_img)
    # Enable buttons
    connection_frame.grid(row=1, column=0, padx=120, pady=80, sticky=tk.W)
    start_btn.configure(state=tk.NORMAL)
    r2.configure(state=tk.NORMAL)
    r1.configure(state=tk.NORMAL)
    label_status.configure(font=normal_font, text="Not Connected", image=red_img)

    # Disable button
    stop_btn.configure(state=tk.DISABLED)
    details_frame.grid_forget()
    my_screen.hide(1)

    port_label.grid_forget()
    port_text.grid_forget()
    port_text.configure(state="normal")
    port_text.delete('1.0', tk.END)

    pass_label.grid_forget()
    pass_text.grid_forget()
    pass_text.configure(state="normal")
    pass_text.delete('1.0', tk.END)

def login(sock):
    global command_client_socket, client_socket_remote, chat_client_socket, file_client_socket, thread1, \
        CLIENT_CONNECTED
    accept = True
    try:
        while accept:
            print("\n")
            print("Start listening for incoming connection")
            add_text_event_widget(" ----> Start listening for incoming connection")
            label_status.configure(font=normal_font, text="Start listening for incoming connection", image=yellow_img)
            command_client_socket, address = sock.accept()
            print(f"Recived login request from {address[0]}...")
            pass_recv = connection.data_recive(command_client_socket, 2, bytes(), 1024)[0].decode("utf-8")
            if pass_recv == PASSWORD:
                connection.send_data(command_client_socket, 2, bytes("1", "utf-8"))  # success_code--> 1
                # chat socket
                # chat_client_socket, address = sock.accept()
                # file transfer socket
                # file_client_socket, address = sock.accept()
                print("\n")
                print(f"Connection from {address[0]} has been connected!")
                add_text_event_widget(f" ---->Connection from {address[0]} has been connected!")
                label_status.configure(font=normal_font, text="Connected", image=green_img)
                # thread for listening to commands
                thread1 = Thread(target=listinging_commands, name="listener_for_commands", daemon=True)
                thread1.start()
                CLIENT_CONNECTED = True
                # thread for chat
                # recv_chat_msg_thread = Thread(target=receive_chat_message, name="recv_chat_msg_thread", daemon=True)
                # recv_chat_msg_thread.start()
                # enable button frame

                # my_screen.add(chat_frame, text=" Chat ")
                accept = False
            else:
                connection.send_data(command_client_socket, 2, bytes("0", "utf-8"))  # failure_code--> 0
                print(f"{address[0]}...Please enter correct password")
                add_text_event_widget(f"----> {address[0]}...Please enter correct password")
                command_client_socket.close()
    except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
        label_status.configure(font=normal_font, text="Not Connected", image=red_img)
        print(e.strerror)
        add_text_event_widget(f" ----> {e.strerror}")


def listinging_commands():
    global login_thread, CLIENT_CONNECTED
    listen = True
    try:
        while listen:
            msg = connection.data_recive(command_client_socket, COMMAND_size_of_header, bytes(), 1024)[0].decode("utf-8")
            print(f"Message received:{msg}")
            add_text_event_widget(f" ---> Message received:{msg}")
            if msg == "start_capture":
                screen_sending()
            elif msg == "stop_capture":
                process_cleanup()
            elif msg == "disconnect":
                listen = False
                print("Disconnect message received")
    except (ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
        add_text_event_widget(f" ---> {e.strerror}")
    except ValueError:
        pass
    finally:
        my_screen.hide(1)
        CLIENT_CONNECTED = False
        close_socket()
        process_cleanup()
        login_thread = Thread(target=login, name="login_thread", args=(server_socket,), daemon=True)
        login_thread.start()
        print("Thread1 automatically exits")


def add_text_event_widget(msg):
    text_event_log.configure(state=tk.NORMAL, font=font_event_log_date, width=77, height=28)
    text_event_log.insert(tk.END, "\n")
    text_event_log.insert(tk.END, datetime.fromtimestamp(time.time()).strftime("%d-%m-%Y %I:%M %p"))
    text_event_log.configure(font=event_log_font, width=77, height=28)
    text_event_log.insert(tk.END, msg)
    text_event_log.configure(state="disabled")


def add_text_chat_display_widget(msg, name):
    text_chat_widget.configure(state=tk.NORMAL)
    text_chat_widget.insert(tk.END, "\n")
    text_chat_widget.insert(tk.END, name + ": " + msg)
    text_chat_widget.configure(state="disabled")


# def send_chat_message(event):
#     try:
#         msg = input_text_widget.get()
#         if msg and msg.strip() != "":
#             input_text_widget.delete(0, "end")
#             connection.send_data(chat_client_socket, CHAT_size_of_header, bytes(msg, "utf-8"))
#             add_text_chat_display_widget(msg, LOCAL_CHAT_NAME)
#     except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
#         print(e.strerror)


# def receive_chat_message():
#     try:
#         while True:
#             msg = connection.data_recive(chat_client_socket, CHAT_size_of_header, bytes())[0].decode("utf-8")
#             add_text_chat_display_widget(msg, REMOTE_CHAT_NAME)
#     except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
#         print(e.strerror)
#     except ValueError:
#         pass


# def download_file(filename):
#     prev_msg = bytes()
#     msg = connection.data_recive(file_client_socket, FILE_size_of_header, prev_msg)
#     file_size = int(msg[0].decode("utf-8"))
#     msg = connection.data_recive(file_client_socket, FILE_size_of_header, msg[1])
#     file_mode = msg[0].decode("utf-8")
#     prev_msg = msg[1]
#     total_data_size = int()
#     with open(filename, file_mode) as f:
#         while total_data_size < file_size:
#             msg = connection.data_recive(file_client_socket, FILE_size_of_header, prev_msg)
#             data = msg[0]
#             prev_msg = msg[1]
#             if file_mode == "w" and data:
#                 f.write(data.decode("utf-8"))
#             elif file_mode == "wb" and data:
#                 f.write(data)
#             total_data_size += len(data)


def scan_dir():
    try:
        obj = os.scandir(PATH)
        return obj
    except PermissionError:
        print("No permission to acces this resource")
        back_button("function")
        return None


# def toggle_event_log():
#     global status_event_log
#     if status_event_log == 1:
#         event_frame.grid_forget()
#         status_event_log = 0
#     elif status_event_log == 0:
#         event_frame.grid(row=3, column=0, columnspan=2, padx=40, pady=5, sticky=tk.W)
#         status_event_log = 1


if __name__ == "__main__":
    freeze_support()

    PATH = Desktop_bg_path()

    server_socket = None
    command_client_socket = None
    client_socket_remote = None
    # chat_client_socket = None
    # file_client_socket = None
    # browse_file_client_socket = None

    thread1 = None
    login_thread = None
    process1 = None
    process2 = None
    process3 = None

    PASSWORD = str()
    url = str()
    SERVER_PORT = 1234
    # CHAT_size_of_header = 10
    # FILE_size_of_header = 10
    COMMAND_size_of_header = 2
    CLIENT_CONNECTED = False
    LOCAL_CHAT_NAME = "Me"
    REMOTE_CHAT_NAME = "Remote Box"

    # Create Root Window
    root = tk.Tk()
    root.title("Remote Box")
    root.iconbitmap("logo.ico")
    root.resizable(False, False)

    
    # My Notebook
    my_screen = ttk.Notebook(root)
    my_screen.grid(row=0, column=0, pady=5, columnspan=2)

    #Images
    yellow_img = tk.PhotoImage(file="assets/gui_icons/yellow_16.png")
    green_img = tk.PhotoImage(file="assets/gui_icons/green_16.png")
    red_img = tk.PhotoImage(file="assets/gui_icons/red_16.png")

    # <------Connection Tab -------------->
    listener_frame = tk.LabelFrame(my_screen, bd=0)
    listener_frame.grid(row=0, column=0)

    # Logo Label
    img_logo = ImageTk.PhotoImage(Image.open("assets/gui_icons/logo.png"))
    label_note = tk.Label(listener_frame, image=img_logo, anchor=tk.CENTER)
    label_note.grid(row=0, column=0, padx=200, pady=5, columnspan=2, sticky=tk.N)

# My fonts
    title_font = Font(family="Arial", size=14, weight="bold")
    title_font_normal = Font(family="Arial", size=13, weight="bold")
    normal_font = Font(family="Arial", size=13)
    font_event_log_date = Font(family="Arial", size=7)
    event_log_font = Font(family="Arial", size=10)


    # Connection Frame
    connection_frame = tk.LabelFrame(listener_frame, text="Connection Mode", padx=90, pady=30)
    connection_frame.configure(font=title_font)
    connection_frame.grid(row=1, column=0, padx=120, pady=80, sticky=tk.W)

    # Radio button
    radio_var = tk.IntVar()
    radio_var.set(1)
    r1 = tk.Radiobutton(connection_frame, text="IP", variable=radio_var, value=1)
    r1.configure(font=normal_font)
    r1.grid(row=0, column=0, sticky=tk.W, padx=20, pady=5)

    r2 = tk.Radiobutton(connection_frame, text="Device Name", variable=radio_var, value=2)
    r2.configure(font=normal_font)
    r2.grid(row=1, column=0, sticky=tk.W, padx=20, pady=5)

    # Start listener
    start_btn = tk.Button(connection_frame, text="Start Listener", padx=2, pady=1,
                             command=lambda: start_listining(radio_var.get()))
    start_btn.configure(font=title_font_normal)
    start_btn.grid(row=2, column=0, sticky=tk.W, pady=(20, 2), padx=(20, 2))

    # Details Frame
    details_frame = tk.LabelFrame(listener_frame, text="Allow Remote Access", padx=20, pady=20, labelanchor=tk.NE)
    details_frame.configure(font=title_font)
    details_frame.grid(row=1, column=0, padx=40, pady=40)

    # Details label and text
    # Local IP details
    local_ip_label = tk.Label(details_frame, text="LOCAL IP      :", padx=5, pady=5)
    local_ip_label.configure(font=title_font_normal)
    local_ip_text = tk.Text(details_frame, pady=5, width=47, height=1, background="#e6e6e6", bd=0)
    # Public IP details
    public_ip_label = tk.Label(details_frame, text="PUBLIC IP     :", padx=5, pady=5)
    public_ip_label.configure(font=title_font_normal)
    public_ip_text = tk.Text(details_frame, pady=5, width=47, height=1, background="#e6e6e6", bd=0)
    # Device Name details
    name_label = tk.Label(details_frame, text="Device Name :", padx=5, pady=5)
    name_label.configure(font=title_font_normal)
    name_text = tk.Text(details_frame, pady=5, width=47, height=1, background="#e6e6e6", bd=0)
    # Port details
    port_label = tk.Label(details_frame, text="Port no         :", padx=5, pady=5)
    port_label.configure(font=title_font_normal)
    port_text = tk.Text(details_frame, pady=5, width=47, height=1, background="#e6e6e6", bd=0)
    # Password Details
    pass_label = tk.Label(details_frame, text="Password     :", padx=5, pady=5)
    pass_label.configure(font=title_font_normal)
    pass_text = tk.Text(details_frame, pady=5, width=47, height=1, background="#e6e6e6", bd=0)

    # stop listener
    stop_btn = tk.Button(details_frame, text="Stop Listener", padx=2, pady=1,
                            command=lambda: stop_listining())
    stop_btn.configure(font=title_font_normal, state="disabled")

    # Disable details frame
    details_frame.grid_forget()

    # <-------------Event log Tab --------------------->
    # Event_log Frame
    event_frame = tk.LabelFrame(my_screen, text="", padx=20, pady=20, relief=tk.FLAT)
    event_frame.configure(font=event_log_font)
    event_frame.grid(row=3, column=0, columnspan=2, padx=40, pady=5, sticky=tk.W)

    # Scroll bar to event frame
    scroll_widget = tk.Scrollbar(event_frame)
    scroll_widget.grid(row=0, column=1, sticky=tk.N + tk.S)

    # Text Widget
    text_event_log = tk.Text(event_frame, width=65, height=26, padx=10, pady=10, yscrollcommand=scroll_widget.set)
    text_event_log.insert(1.0, "")
    text_event_log.configure(state='disabled')
    text_event_log.grid(row=0, column=0)

    scroll_widget.config(command=text_event_log.yview)

    # Status Label
    label_status = tk.Label(root, text="Not Connected", image=red_img, compound=tk.LEFT, relief=tk.SUNKEN, bd=0, anchor=tk.E, padx=10)
    label_status.configure(font=normal_font)
    label_status.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E)

    # <------Chat Tab -------------->
    # chat_frame = tk.LabelFrame(my_screen, padx=20, pady=20, bd=0)
    # chat_frame.grid(row=0, column=0, sticky=tk.N)

    # text_frame = tk.LabelFrame(chat_frame, bd=0)
    # text_frame.grid(row=0, column=0)

    # Scroll bar to event frame
    # scroll_chat_widget = tk.Scrollbar(chat_frame)
    # scroll_chat_widget.grid(row=0, column=1, sticky=tk.N + tk.S)

    # Text Widget
    # text_chat_widget = tk.Text(chat_frame, width=50, height=20, font=("Arial", 14), padx=10, pady=10,
    #                            yscrollcommand=scroll_chat_widget.set)
    # text_chat_widget.configure(state='disabled')
    # text_chat_widget.grid(row=0, column=0, sticky=tk.N)

    # scroll_chat_widget.config(command=text_chat_widget.yview)

    # Frame for input text
    # input_text_frame = tk.LabelFrame(chat_frame, pady=5, bd=0)
    # input_text_frame.grid(row=1, column=0, sticky=tk.W)

    # Text Widget
    # input_text_widget = tk.Entry(input_text_frame, width=50)
    # input_text_widget.configure(font=("Arial", 14))
    # input_text_widget.bind("<Return>", send_chat_message)
    # input_text_widget.grid(row=0, column=0, pady=10, sticky=tk.W)

    # Create Tab style
    tab_style = ttk.Style()
    tab_style.configure('TNotebook.Tab', font=('Arial', '13', 'bold'))

    # Tab Creation
    my_screen.add(listener_frame, text=" Connection ")
    # my_screen.add(chat_frame, text=" Chat ")
    my_screen.add(event_frame, text=" Event Logs ")

    # Hide Tab
    my_screen.hide(1)

    root.mainloop()
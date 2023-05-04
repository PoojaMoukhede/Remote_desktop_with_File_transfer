import socket
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter.font import Font
import connection_common  # import file which has data recive and send function
from PIL import Image, ImageGrab, ImageTk
import pygetwindow
from pynput.mouse import Button, Listener as Mouse_listener
import win32gui
import os
from io import BytesIO
import pygame
import lz4.frame
from threading import Thread
from multiprocessing import freeze_support, Process, Queue as Multiprocess_queue
from pynput.keyboard import Listener as Key_listener

def send_event_to_remote(message, sock):
    connection_common.send_data(sock, 2, message)

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
                send_event_to_remote(message, sock)
        elif event_code in range(1, 10):
            if inside_the_display:
                message = bytes(f"{event_code:<2}", "utf-8")
                send_event_to_remote(message, sock)


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


def receive_and_put_in_list(client_socket, jpeg_list):
    size_of_header = 10
    chunk_prev_message = bytes()

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
        print("Thread automatically exits")


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
        connection_common.send_data(command_server_socket, COMMAND_size_of_header, bytes("stop_capture", "utf-8"))
        cleanup_process()


def remote_display():
    global Thread2, mouse_listner, process1, process2, remote_server_socket, mouse_event  ,keyboard_listner
    print("Sending start capture message")
    connection_common.send_data(command_server_socket, COMMAND_size_of_header, bytes("start_capture", "utf-8"))
    print("Sent start capture message")
    disable_choice = messagebox.askyesno("Remote Box", "Disable remote device wallpaper?(yes,Turn black)")

    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)     # remote display sockets
    remote_server_socket.connect((server_ip, server_port))
    
    connection_common.send_data(remote_server_socket, COMMAND_size_of_header, bytes(str(disable_choice), "utf-8"))
    print("\n")
    print(f">>Now you can CONTROL remote desktop")
    resize_option = False
    server_width, server_height = ImageGrab.grab().size
    client_resolution = connection_common.data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    client_width, client_height = client_resolution.split(",")
    display_width, display_height = int(client_width), int(client_height)


    if (client_width, client_height) != (display_width, display_height):
        resize_option = True

    jpeg_sync_queue = Multiprocess_queue()

    Thread2 = Thread(target=receive_and_put_in_list, name="recv_stream", args=(remote_server_socket, jpeg_sync_queue), daemon=True)
    Thread2.start()
  
    mouse_event = Multiprocess_queue()

    process1 = Process(target=mouse_controlling, args=(remote_server_socket, mouse_event, resize_option, int(client_width), int(client_height), display_width, display_height), daemon=True)
    process1.start()

    mouse_listner = Mouse_listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    mouse_listner.start()
    
    execution_status_list = Multiprocess_queue()
    process2 = Process(target=display_data, args=(jpeg_sync_queue, execution_status_list, display_width, display_height , resize_option), daemon=True)
    process2.start()
    
    Thread3 = Thread(target=cleanup_display_process, args=(execution_status_list,), daemon=True)
    Thread3.start()
    
    keyboard_listner = Key_listener(on_press=on_press, on_release=on_release)
    keyboard_listner.start()

def connect():
    global command_server_socket, remote_server_socket, Thread1, server_ip, \
        server_port

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
                Thread1 = Thread(target=listen_for_commands, daemon=True)
                Thread1.start()
                
                disconnect_button.configure(state="normal")   # Enable
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
    service_socket_list = [command_server_socket, remote_server_socket]
    for sock in service_socket_list:
        if sock:
            sock.close()
    print("All Sockets are closed now")


def disconnect(btn_caller):
    if btn_caller == "button":
        connection_common.send_data(command_server_socket, COMMAND_size_of_header, bytes("disconnect", "utf-8"))
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
    my_screen.hide(1)
    my_screen.hide(2)


def listen_for_commands():
    listen = True
    try:
        while listen:
            message = connection_common.data_recive(command_server_socket, COMMAND_size_of_header, bytes(), 1024)[0].decode("utf-8")
            if message == "disconnect":
                listen = False
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        label_status.grid_remove()
        disconnect("message")
        print("Thread automatically exit")

def keyboard_controlling(key,event_code):
    active_window = pygetwindow.getActiveWindow()
    if active_window:
        if active_window.title == f"Remote Desktop":
            if key.char:
                 msg = bytes(event_code + key.char, "utf-8") 
                 send_event_to_remote(msg, remote_server_socket)
            else:
                msg = bytes(event_code + key.name, "utf-8") 
                send_event_to_remote(msg, remote_server_socket)


def on_press(key):
    keyboard_controlling(key, "-1")


def on_release(key):
    keyboard_controlling(key, "-2")


if __name__ == "__main__":
    
    freeze_support()
    command_server_socket = None
    remote_server_socket = None
    Thread1 = None
    Thread2 = None
    mouse_listner = None
    keyboard_listner = None
    process1 = None
    process2 = None
    server_ip = str()
    server_port = int()
    status_event_log = 1
    COMMAND_size_of_header = 2
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
    
   

    # My Screen Notebook
    my_screen = ttk.Notebook(root)
    my_screen.grid(row=0, column=0, pady=5)
    connection_frame = tk.LabelFrame(my_screen, padx=100, pady=5, bd=0)
    connection_frame.configure(bg='whitesmoke')
    connection_frame.grid(row=0, column=0, padx=40, pady=40, sticky=tk.N)

    img= Image.open('./assets/background.png')
    resized_image= img.resize((700,400), Image.ANTIALIAS)
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
    connect_button = tk.Button(button_frame, text="Connect", padx=4, pady=1, command=connect)
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
    remote_button.configure(font=font_normal,background='whitesmoke',fg='white')
    remote_button.grid(row=0, column=0, padx=30, pady=30, sticky=tk.NSEW)
    
    access_button_frame.columnconfigure(0, weight=1)
    access_button_frame.rowconfigure(0, weight=1)
    
    # Status Label
    label_status = tk.Label(root, text="Connected", image=green, compound=tk.LEFT, relief=tk.SUNKEN, bd=0, anchor=tk.E,  padx=10)
    label_status.configure(font=font_normal,bg='whitesmoke',fg='brown')
    label_status.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E)
    label_status.grid_remove()

    # Create Tab style
    tab_style = ttk.Style()
    tab_style.configure('TNotebook.Tab',font=title_font)
    my_screen.add(connection_frame, text=" Connection ")

    root.mainloop()
    
    # FOR CHECKING - 192.168.1.167
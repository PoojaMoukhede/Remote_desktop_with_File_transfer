import socket
import tkinter as tk
from tkinter.font import Font
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageGrab, ImageTk
import pygetwindow
import connection_common  # import file which has data recive and send function
from pynput.mouse import Button, Listener as Mouse_listener
import re
import os
import time
import win32gui
import pygame
import lz4.frame
from io import BytesIO
from threading import Thread
from multiprocessing import freeze_support, Process, Queue as Multiprocess_queue
from pynput.keyboard import Listener as Key_listener


def send_event(msg, sock):
    connection_common.send_data(sock, 2, msg)


def mouse_info(sock, event_queue, resize, cli_width, cli_height, display_width, display_height):
    while True:
        event_code = event_queue.get()
        x = event_queue.get()
        y = event_queue.get()
        x, y, within_display = check_within_display(x, y, resize, cli_width, cli_height, display_width, display_height)
        if event_code == 0 or event_code == 7:
            if within_display:
                if event_code == 7:
                    x = event_queue.get()
                    y = event_queue.get()
                msg = bytes(f"{event_code:<2}" + str(x) + "," + str(y), "utf-8")
                send_event(msg, sock)
        elif event_code in range(1, 10):
            if within_display:
                msg = bytes(f"{event_code:<2}", "utf-8")
                send_event(msg, sock)


def scale_x_y(x, y, cli_width, cli_height, display_width, display_height):
    scale_x = cli_width / display_width
    scale_y = cli_height / display_height
    x *= scale_x
    y *= scale_y
    return round(x, 1), round(y, 1)


def check_within_display(x, y, resize, cli_width, cli_height, display_width, display_height):
    active_window = pygetwindow.getWindowsWithTitle(f"Remote Desktop")
    if active_window and (len(active_window) == 1):
        x, y = win32gui.ScreenToClient(active_window[0]._hWnd, (x, y))
        if (0 <= x <= display_width) and (0 <= y <= display_height):
            if resize:
                x, y = scale_x_y(x, y, cli_width, cli_height, display_width, display_height)
            return x, y, True
    return x, y, False

def on_scroll(x, y, dx, dy):
    mouse_event.put(7) 
    mouse_event.put(x)
    mouse_event.put(y)
    mouse_event.put(dx)
    mouse_event.put(dy)

def on_click(x, y, button, pressed):
    if pressed: 
        # mouse down
        mouse_event.put(button_code.get(button)[0])
        mouse_event.put(x)
        mouse_event.put(y)
    else: 
        # mouse up
        mouse_event.put(button_code.get(button)[1])
        mouse_event.put(x)
        mouse_event.put(y)


def on_move(x, y):
    # print("Mouse listener working")
    mouse_event.put(0)  
    mouse_event.put(x)
    mouse_event.put(y)



def recv_and_put_into_queue(client_socket, jpeg_list):
    header_size = 10
    partial_prev_msg = bytes()

    try:
        while True:
            msg = connection_common.data_recive(client_socket, header_size, partial_prev_msg)
            if msg:
                jpeg_list.put(lz4.frame.decompress(msg[0])) 
                partial_prev_msg = msg[1]
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        print("Thread2 automatically exits")


def display_data(jpeg_list, status_queue, display_width, display_height, resize):
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
    pygame.init()
    display_surface = pygame.display.set_mode((display_width, display_height))
    pygame.display.set_caption(f"Remote Desktop")
    clock = pygame.time.Clock()
    display = True

    while display:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                status_queue.put("stop")
                pygame.quit()
                return
        jpeg_buffer = BytesIO(jpeg_list.get())
        img = Image.open(jpeg_buffer)
        py_image = pygame.image.frombuffer(img.tobytes(), img.size, img.mode)
        if resize:
            py_image = pygame.transform.scale(py_image, (display_width, display_height))
        jpeg_buffer.close()
        display_surface.blit(py_image, (0, 0))
        pygame.display.flip()
        clock.tick(60)


def cleanup_process_threads():
    process_list = [process1, process2]
    for process in process_list:
        if process:
            if process.is_alive():
                process.kill()
            process.join()
    listener_key.stop()
    listener_key.join()
    listener_mouse.stop()
    listener_mouse.join()
    print("cleanup finished")


def cleanup_display_process(status_queue):
    if status_queue.get() == "stop":
        connection_common.send_data(command_server_socket, COMMAND_HEADER_SIZE, bytes("stop_capture", "utf-8"))
        cleanup_process_threads()

def remote_display():
    global thread2, listener_key, listener_mouse, process1, process2, remote_server_socket, mouse_event
    print("Sending start_capture message")
    connection_common.send_data(command_server_socket, COMMAND_HEADER_SIZE, bytes("start_capture", "utf-8"))
    print("Sent start_capture message")
    disable_choice = messagebox.askyesno("Remote Box", "Disable remote device wallpaper?(yes,Turn black)")

    # remote display socket
    remote_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_server_socket.connect((server_ip, server_port))
    # wallpaper_settings
    print(f"Disable choice: {disable_choice}")
    connection_common.send_data(remote_server_socket, COMMAND_HEADER_SIZE, bytes(str(disable_choice), "utf-8"))
    print("\n")
    print(f"----->NOW YOU CAN CONTROL REMOTE DESKTOP")
    resize_option = False
    server_width, server_height = ImageGrab.grab().size
    client_resolution = connection_common.data_recive(remote_server_socket, 2, bytes(), 1024)[0].decode("utf-8")
    client_width, client_height = client_resolution.split(",")
    display_width, display_height = int(client_width), int(client_height)
    

    if (client_width, client_height) != (display_width, display_height):
        resize_option = True

    jpeg_sync_queue = Multiprocess_queue()

    thread2 = Thread(target=recv_and_put_into_queue, name="recv_stream", args=(remote_server_socket, jpeg_sync_queue), daemon=True)
    thread2.start()

    mouse_event = Multiprocess_queue()

    process1 = Process(target=mouse_info, args=(remote_server_socket, mouse_event, resize_option, int(client_width), int(client_height), display_width, display_height), daemon=True)
    process1.start()

    listener_mouse = Mouse_listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll)
    listener_mouse.start()
    
    execution_status_queue = Multiprocess_queue()
    process2 = Process(target=display_data, args=(jpeg_sync_queue, execution_status_queue, display_width, display_height , resize_option), daemon=True)
    process2.start()
    thread3 = Thread(target=cleanup_display_process, args=(execution_status_queue,), daemon=True)
    thread3.start()


def login():
    # resize_option = False
    global command_server_socket, remote_server_socket, thread1, server_ip, \
        server_port

    server_ip = name_entry.get()
    server_port = int(port_entry.get())
    server_pass = pass_entry.get()
    if len(server_pass) == 6 and server_pass.strip() != "":
        try:
            command_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            command_server_socket.connect((server_ip, server_port))
            server_pass = bytes(server_pass, "utf-8")
            connection_common.send_data(command_server_socket, 2, server_pass)  # send password
            login_response = connection_common.data_recive(command_server_socket, 2, bytes(), 1024)[0].decode("utf-8")

            if login_response != "1":
                print("WRONG Password!..")
            else:
                print("\n")
                print("Connected to the remote computer!")

                label_status.grid()
                execute = False

                thread1 = Thread(target=listen_for_commands, daemon=True)
                thread1.start()


                # Enable
                disconnect_button.configure(state="normal")
                access_button_frame.grid(row=7, column=0, padx=45, pady=20, columnspan=2, sticky=tk.W + tk.E)
                # Disable
                name_entry.configure(state="disabled")
                port_entry.configure(state="disabled")
                pass_entry.configure(state="disabled")
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
    print("Closed all the sockets")


def disconnect(caller):
    if caller == "button":
        connection_common.send_data(command_server_socket, COMMAND_HEADER_SIZE, bytes("disconnect", "utf-8"))

    close_sockets()

    # Enable
    name_entry.configure(state="normal")
    port_entry.configure(state="normal")
    pass_entry.configure(state="normal")
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
            msg = connection_common.data_recive(command_server_socket, COMMAND_HEADER_SIZE, bytes(), 1024)[0].decode("utf-8")
            if msg == "disconnect":
                listen = False
    except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, OSError) as e:
        print(e.strerror)
    except ValueError:
        pass
    finally:
        if (file_window is not None) and file_window.winfo_exists():
            file_window.destroy()
            print("top window destroyed")
        label_status.grid_remove()
        disconnect("message")
        print("Thread1 automatically exits")


def check_window_closed():
    window_open = True
    while window_open:
        if (file_window is not None) and file_window.winfo_exists():
            time.sleep(3)
            continue
        else:
            file_button.configure(state="normal")
            window_open = False




if __name__ == "__main__":
    freeze_support()

    command_server_socket = None
    remote_server_socket = None

    thread1 = None
    thread2 = None
    listener_key = None
    listener_mouse = None
    process1 = None
    process2 = None

    server_ip = str()
    server_port = int()
    status_event_log = 1
    LOCAL_PATH = r""

    REMOTE_PATH = r""
    file_window = None
    COMMAND_HEADER_SIZE = 2

    button_code = {Button.left: (1, 4), Button.right: (2, 5), Button.middle: (3, 6)}


    # Create Root Window
    root = tk.Tk()
    root.title("Remote Box")
    # root.iconbitmap("logo.ico")
    root.resizable(False, False)

    # icons
    green = tk.PhotoImage(file="assets/green_dot.png")

    # My fonts
    title_font = Font(family="Arial", size=14, weight="bold")
    title_font_normal = Font(family="Arial", size=13, weight="bold")
    font_normal = Font(family="Arial", size=13)

    # My Notebook
    my_screen = ttk.Notebook(root)
    my_screen.grid(row=0, column=0, pady=5)

    connection_frame = tk.LabelFrame(my_screen, padx=100, pady=5, bd=0)
    connection_frame.grid(row=0, column=0, padx=40, pady=40, sticky=tk.N)

    # Logo Label
    label_note = tk.Label(connection_frame, anchor=tk.CENTER)
    label_note.grid(row=0, column=0, pady=5, columnspan=2, sticky=tk.N)

    # Form elements frame
    form_frame = tk.LabelFrame(connection_frame, text="Control Remote Box", padx=20, pady=5)
    form_frame.configure(font=title_font)
    form_frame.grid(row=1, column=0, padx=120, pady=(40, 20), sticky=tk.N)

    # Form for Input data
    name_label = tk.Label(form_frame, text="Device Name/IP", padx=5, pady=5)
    name_label.configure(font=title_font_normal)
    name_label.grid(row=0, column=0, pady=5, columnspan=2, sticky=tk.W)

    name_entry = tk.Entry(form_frame, width=20)
    name_entry.configure(font=font_normal)
    name_entry.grid(row=1, column=0, pady=5, columnspan=2, sticky=tk.N)

    port_label = tk.Label(form_frame, text="Port", padx=5, pady=5)
    port_label.configure(font=title_font_normal)
    port_label.grid(row=2, column=0, pady=5, columnspan=2, sticky=tk.W)

    port_entry = tk.Entry(form_frame, width=20)
    port_entry.configure(font=font_normal)
    port_entry.grid(row=3, column=0, pady=5, columnspan=2, sticky=tk.N)

    pass_label = tk.Label(form_frame, text="Password", padx=5, pady=5)
    pass_label.configure(font=title_font_normal)
    pass_label.grid(row=4, column=0, pady=5, columnspan=2, sticky=tk.W)

    pass_entry = tk.Entry(form_frame, show="*", width=20)
    pass_entry.configure(font=font_normal)
    pass_entry.grid(row=5, column=0, pady=5, columnspan=2, sticky=tk.N)

    # Button frame
    button_frame = tk.LabelFrame(form_frame, padx=2, pady=5, bd=0)
    button_frame.grid(row=6, column=0, padx=5, pady=2)

    # Connect and Disconnect button
    connect_button = tk.Button(button_frame, text="Connect", padx=4, pady=1, command=login)
    connect_button.configure(font=title_font_normal)
    connect_button.grid(row=0, column=0, sticky=tk.N, padx=5, pady=5)

    disconnect_button = tk.Button(button_frame, text="Disconnect", padx=2, pady=1, command=lambda: disconnect("button"))
    disconnect_button.configure(font=title_font_normal, state=tk.DISABLED)
    disconnect_button.grid(row=0, column=1, sticky=tk.N, padx=5, pady=5)

    # Access Button Frame
    access_button_frame = tk.LabelFrame(connection_frame, text="Access", padx=5, pady=15)
    access_button_frame.configure(font=title_font)
    access_button_frame.grid(row=7, column=0, padx=10, pady=10, columnspan=2, sticky=tk.W+tk.E)

    # Disable access frame when not connected
    access_button_frame.grid_forget()

    # images
    remote_img = tk.PhotoImage(file="assets/remote-desktop.png")
    
    # View Remote Box button
    remote_button = tk.Button(access_button_frame, text="Remote Box", image=remote_img, compound=tk.TOP, padx=2,
                              pady=2, bd=0, command=remote_display)
    remote_button.configure(font=font_normal)
    remote_button.grid(row=0, column=1, sticky=tk.W, padx=30)  # padx =60

    # Event_log Frame
    event_frame = tk.LabelFrame(my_screen, text="Event Log", padx=20, pady=20, relief=tk.FLAT)
    event_frame.configure(font=title_font)
    event_frame.grid(row=3, column=0, columnspan=2, padx=40, pady=5, sticky=tk.W)

    # Scroll bar to event frame
    scroll_widget = tk.Scrollbar(event_frame)
    scroll_widget.grid(row=0, column=1, sticky=tk.N + tk.S)

    # Text Widget
    text_1 = tk.Text(event_frame, width=50, height=7, font=("Arial", 13), padx=10, pady=10, yscrollcommand=scroll_widget.set)
    text_1.insert(1.0, "By Default Show Event Logs")
    text_1.configure(state='disabled')
    text_1.grid(row=0, column=0)
    scroll_widget.config(command=text_1.yview)

    # Status Label
    label_status = tk.Label(root, text="Connected", image=green, compound=tk.LEFT, relief=tk.SUNKEN, bd=0, anchor=tk.E,  padx=10)
    label_status.configure(font=font_normal)
    label_status.grid(row=3, column=0, columnspan=2, sticky=tk.W + tk.E)
    label_status.grid_remove()

    # Create Tab style
    tab_style = ttk.Style()
    tab_style.configure('TNotebook.Tab', font=('Arial', '13', 'bold'))

    # Tab Creation
    my_screen.add(connection_frame, text=" Connection ")
    my_screen.add(event_frame, text=" Event Logs ")

    # Hide Tab by there id 
    my_screen.hide(1)

    root.mainloop()

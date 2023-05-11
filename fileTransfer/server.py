from tkinter import *
import socket
from tkinter import messagebox
from tkinter import filedialog
import os



def select_file():

    global fileName
  
    initial_dir = os.path.expanduser('~/Downloads')
    fileName = filedialog.askopenfilename(initialdir=initial_dir,
                                          title="Select Image File",
                                          filetypes=(('Text Files', '*.txt'), ('All Files', '*.*')))
    if fileName:
        directory = os.path.join(initial_dir, 'Received')
        os.makedirs(directory, exist_ok=True)
        destination = os.path.join(directory, os.path.basename(fileName))
        os.rename(fileName, destination)
        return destination
    else:
        return None


def sender():
    s = socket.socket()
    host = socket.gethostbyname(socket.gethostname())
    port = 8080
    s.bind((host, port))
    s.listen(1)
    print(host, "Waiting for incoming connection...")
    conn, addr = s.accept()
    file = open(fileName, 'rb')
    file_data = file.read(1024)
    conn.send(file_data)
    
    
    print("File successfully transferred")

#     # Set the values of sender_id and file_name
#     sender_id.set(host)
#     print(sender_id," sender id ")
#     file_name.set(os.path.basename(fileName))
#     print("FILE :",file_name)


# Server (Sender) GUI
root = Tk()
root.title("Send")
root.geometry('450x560+500+200')
root.configure(bg="#f4fdfe")
root.resizable(False, False)

sender_id = StringVar()
file_name = StringVar()

icon1 = PhotoImage(file='../assets/send.png')
root.iconphoto(False, icon1)

background_common = PhotoImage(file='../assets/both.png')
Label(root, image=background_common).place(x=-2, y=0)

scan_img = PhotoImage(file='../assets/id.png')
Label(root, image=scan_img, bg='#f4fdfe').place(x=100, y=250)

host = socket.gethostbyname(socket.getfqdn())
Label(root, text=f'ID : {host}', bg='white', fg='black').place(x=140, y=280)

Button(root, text='+ select file', width=10, height=1, font='arial 14 bold', bg='#fff', fg='#000', command=select_file).place(x=40, y=205)
Button(root, text='SEND', width=10, height=1, font='arial 14 bold', bg='#272727', fg='#fff', command=sender).place(x=280, y=205)

root.mainloop()

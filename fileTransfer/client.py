from tkinter import *
import socket
from tkinter import messagebox
from tkinter import filedialog
import os


def receiver():
    # ID = SenderID.get("1.0", "end-1c")
    fileName0 = Incoming_File_Name.get("1.0", "end-1c")
    
    s = socket.socket()
    host = socket.gethostbyname(socket.gethostname())
    SenderID.insert(1.0,'{:<15}'.format(host))
    Incoming_File_Name.insert(1.0,'{:<15}'.format(fileName0))
    
    port = 8080
    print(SenderID," sender id ")
    print("FILE :",Incoming_File_Name)
    
    try:
        s.connect((host, port))
        file = open(fileName0, 'wb')
        file_data = s.recv(1024)
        
         
        while file_data:
            file.write(file_data)
            file_data = s.recv(1024)
        
        file.close()
        print("File successfully received")
        
        # Set the values of sender_id and file_name
        # SenderID.insert(host)
        Incoming_File_Name.insert(fileName0)
        
        # SenderID.delete("1.0", END)
        # Incoming_File_Name.delete("1.0", END)
       
       
        
    except Exception as e:
        messagebox.showerror("Error", str(e))
    
    s.close()

# Client (Receiver) GUI
root = Tk()
root.title("Receive")
root.geometry('450x560+500+200')
root.configure(bg="#f4fdfe")
root.resizable(False, False)

SenderID = StringVar()
Incoming_File_Name = StringVar()

icon2 = PhotoImage(file='../assets/recieve.png')
root.iconphoto(False, icon2)

background_common = PhotoImage(file='../assets/both.png')
Label(root, image=background_common).place(x=-2, y=0)

Label(root, text='Receive', font=('arial', 20), bg='#f4fdfe').place(x=100, y=250)

Label(root, text='Sender Id', font=('arial', 10, 'bold'), bg='#f4fdfe').place(x=20, y=340)
SenderID = Text(root, width=25,height=1, fg='black', border=2, bg='white', font=('arial', 15))
SenderID.place(x=20, y=370)
SenderID.focus()

Label(root, text='Incoming File Name', font=('arial', 10, 'bold'), bg='#f4fdfe').place(x=20, y=420)
Incoming_File_Name = Text(root, width=25,height=1, fg='black', border=2, bg='white', font=('arial', 15))
Incoming_File_Name.place(x=20, y=450)

imageIcon = PhotoImage(file='')
recieve_btn = Button(root, text='Receive', compound=LEFT, image=imageIcon, width=130, bg='#39c790', font='arial 14 bold', command=receiver)
recieve_btn.place(x=20, y=500)

root.mainloop()

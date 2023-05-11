# from tkinter import *
# import socket
# from tkinter import messagebox
# from tkinter import filedialog
# import os

# root = Tk()
# root.title("ShareME")
# root.geometry("450x560+500+200")
# root.configure(bg="#f4fdfe")
# root.resizable(False,False)

# sender_id = StringVar()
# file_name = StringVar()

# def Send():
#     # print('reciving....')
#     window=Toplevel(root)
#     window.title("Send")
#     window.geometry('450x560+500+200')
#     window.configure(bg="#f4fdfe")
#     window.resizable(False,False)
    
#     def select_file():
#         global fileName
#         fileName = filedialog.askopenfilename(initialdir=os.getcwd(),
#                                               title="Select file Image",
#                                               filetype=(('file_type','*.txt'),('all files','*.*')))
        
#     def sender():
#         s = socket.socket()
#         host = socket.gethostbyname(socket.getfqdn()) #socket.getfqdn()
#         port=8080
#         s.bind((host,port))
#         s.listen(1)
#         print(host,"Waiting for incoming connection......")    
#         conn, addr = s.accept()
#         file = open(fileName,'rb')
#         file_data = file.read(1024)
#         conn.send(file_data)
#         print("File successfully transferred")
#         sender_id.set(host)
#         file_name.set(os.path.basename(fileName)) 
    
#     icon1=PhotoImage(file='../assets/send.png')
#     window.iconphoto(False,icon1)
    
#     background_common = PhotoImage(file='../assets/both.png')
#     Label(window,image=background_common).place(x=-2,y=0)
    
#     scan_img = PhotoImage(file='../assets/id.png')
#     Label(window,image=scan_img,bg='#f4fdfe').place(x=100,y=250) 
    
#     host = socket.gethostname()
#     Label(window,text=f'ID : {host}',bg='white',fg='black').place(x=140,y=280)
    
#     Button(window,text='+ select file',width=10,height=1,font='arial 14 bold',bg='#fff',fg='#000',command=select_file).place(x=40,y=205)
#     Button(window,text='SEND',width=10,height=1,font='arial 14 bold',bg='#272727',fg='#fff',command=sender).place(x=280,y=205)

#     window.mainloop()


# def Receive():
#     # print("sending.....")
#     window2=Toplevel(root)
#     window2.title("Receive")
#     window2.geometry('450x560+500+200')
#     window2.configure(bg="#f4fdfe")
#     window2.resizable(False,False)
    
#     def receiver():
#         ID = SenderID.get("1.0", "end-1c")
#         fileName0 = Incoming_File_Name.get("1.0", "end-1c")
        
#         s = socket.socket()
#         host = socket.gethostbyname(socket.gethostname())
#         port = 8080
#         s.connect((ID,port))
#         file = open(fileName0,'wb')
#         file_data = s.recv(1024)
#         file.write(file_data)
#         file.close()
#         print("File successfully received")
#         sender_id.set(ID)
#         file_name.set(fileName0)
        
        
    
#     icon2 = PhotoImage(file='../assets/recieve.png')
#     window2.iconphoto(False,icon2)
    
#     background_common = PhotoImage(file='../assets/both.png')
#     Label(window2,image=background_common).place(x=-2,y=0)
    
#     Label(window2,text='Receive',font=('arial',20),bg='#f4fdfe').place(x=100,y=250)
    
#     Label(window2, text='Sender ID', font=('arial', 10, 'bold'), bg='#f4fdfe').place(x=20, y=340)
#     SenderID = Text(window2, width=25,height=1, fg='black', border=2, bg='white', font=('arial', 15))
#     SenderID.place(x=20, y=370)
#     SenderID.focus()
#     SenderID.insert(1.0, sender_id.get())
    
#     Label(window2, text='Incoming File Name', font=('arial', 10, 'bold'), bg='#f4fdfe').place(x=20, y=420)
#     Incoming_File_Name = Text(window2, width=25,height=1, fg='black', border=2, bg='white', font=('arial', 15))
#     Incoming_File_Name.place(x=20, y=450)
#     Incoming_File_Name.insert(1.0, file_name.get())
    
#     imageIcon = PhotoImage(file='')
#     rr = Button(window2,text='Receive',compound=LEFT,image=imageIcon,width=130,bg='#39c790',font='arial 14 bold',command=receiver)
#     rr.place(x=20,y=500)
    
#     window2.mainloop()


# #icon
# image_icon = PhotoImage(file='../assets/share.png')
# root.iconphoto(False,image_icon)
# Label(root,text='File Transfer',font=("Acumin Variable Concept",20,'bold'),bg='#f4fdfe').place(x=20,y=30)
# Frame(root,width=400,height=2, bg='#f3f5f6').place(x=25,y=80)

# send_image = PhotoImage(file="../assets/upload.png")
# send= Button(root,image=send_image,bg='#f4fdfe',bd=0,command=Send)
# send.place(x=80, y=100)

# recieve_image = PhotoImage(file="../assets/received.png")
# recieve= Button(root,image=recieve_image,bg='#f4fdfe',bd=0,command=Receive)
# recieve.place(x=280, y=100)


# #label
# Label(root,text="Send",font=('Acumin Variable Concept',12),bg='#f4fdfe').place(x=83,y=160)
# Label(root,text="Recieve",font=('Acumin Variable Concept',12,),bg='#f4fdfe').place(x=275,y=160)

# background = PhotoImage(file='../assets/background1.png')
# Label(root,image=background).place(x=-2,y=300)



# root.mainloop()

import ftplib

FTP_HOST = "ftp.example.com"
FTP_USER = "ftp@example.com"
FTP_PASS = "Password@123"

ftp = ftplib.FTP(FTP_HOST, FTP_USER, FTP_PASS)
ftp.encoding = "utf-8"

filename = "requirments.txt"
with open(filename, "rb") as file:
    ftp.storbinary("STOR requirments.txt", file)
ftp.dir()
with open(filename, "wb") as file:
    ftp.retrbinary("RETR requirments.txt", file.write)

ftp.quit()
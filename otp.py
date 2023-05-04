import math,random    
# we can use OTP instead of PASSWORD
def generateOTP() :
    digits = "0123456789"
    OTP = ""
    for i in range(6) :
        OTP += digits[math.floor(random.random() * 10)]
    return OTP   

print(f"your otp is {generateOTP()}")
     
     
# from tkinter import *
# from tkinter import messagebox

# root=Tk()
# root.title("Login")  
# root.geometry('925x500+300+200')   
# root.configure(bg='#fff')
# root.resizable(False,False)

# img = PhotoImage(file='./assets/login.png')
# Label(root,image=img,bg='white').place(x=50, y=50)

# frame = Frame(root,width=350,height=350,bg='red')
# frame.place(x=480,y=70)
# root.mainloop()
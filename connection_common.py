# Receive data as chunks and rebuild message.
import time
def data_recive(socket, size_of_header, chunk_prev_message, buffer_size=65536):
    # print(socket,"--socket")
    prev_buffer_size = len(chunk_prev_message)
    headerMsg = bytes()
    # print(f'headerMsg {headerMsg}')
    if prev_buffer_size < size_of_header:
            headerMsg = socket.recv(size_of_header - prev_buffer_size)

            if len(headerMsg) != size_of_header:
                headerMsg = chunk_prev_message + headerMsg
                chunk_prev_message = bytes()

    elif prev_buffer_size >= size_of_header:
        headerMsg = chunk_prev_message[:size_of_header]
        chunk_prev_message = chunk_prev_message[size_of_header:]
    
    global msgSize,newMsg
    try:   
        msgSize = int(headerMsg.decode())
        # print(f'msgSize {msgSize}')
        newMsg = chunk_prev_message
        # print(f'newMsg {newMsg}')
        chunk_prev_message = bytes()
    except (ValueError):
        pass    

    if msgSize:
        while True:
            if len(newMsg) < msgSize:
                newMsg += socket.recv(buffer_size)
            elif len(newMsg) > msgSize:
                chunk_prev_message = newMsg[msgSize:]
                newMsg = newMsg[:msgSize]
            if len(newMsg) == msgSize:
                break
        return newMsg, chunk_prev_message
    else:
        return None

#Send data 
def send_data(socket, size_of_header, msg_data):
    msg_len = len(msg_data)
    if msg_len:
        header = f"{msg_len:<{size_of_header}}"
        # time.sleep(5)
        socket.send(bytes(header, "utf-8") + msg_data)  
# Receive data as chunks and rebuild message.
def data_recive(socket, size_of_header, prev_msg, buffer_size=65536):
    prev_buffer_size = len(prev_msg)
    headerMsg = bytes()

    if prev_buffer_size < size_of_header:
        headerMsg = socket.recv(size_of_header - prev_buffer_size)
        if len(headerMsg) != size_of_header:
            headerMsg = prev_msg + headerMsg
            prev_msg = bytes()

    elif prev_buffer_size >= size_of_header:
        headerMsg = prev_msg[:size_of_header]
        prev_msg = prev_msg[size_of_header:]

    msgSize = int(headerMsg.decode("utf-8"))
    newMsg = prev_msg
    prev_msg = bytes()

    if msgSize:
        while True:
            if len(newMsg) < msgSize:
                newMsg += socket.recv(buffer_size)
            elif len(newMsg) > msgSize:
                prev_msg = newMsg[msgSize:]
                newMsg = newMsg[:msgSize]
            if len(newMsg) == msgSize:
                break
        return newMsg, prev_msg
    else:
        return None

#Send data 
def send_data(socket, size_of_header, msg_data):
    msg_len = len(msg_data)
    if msg_len:
        header = f"{msg_len:<{size_of_header}}"
        socket.send(bytes(header, "utf-8") + msg_data)

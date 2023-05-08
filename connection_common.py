# Receive data as chunks and rebuild message.
def data_recive(socket, size_of_header, chunk_prev_message, buffer_size=65536):
    print(socket,"--socket")
    prev_buffer_size = len(chunk_prev_message)
    headerMsg = bytes()

    if prev_buffer_size < size_of_header:
        # try:
            headerMsg = socket.recv(size_of_header - prev_buffer_size)
            # print("headerMsg --",headerMsg)
            if len(headerMsg) != size_of_header:
                headerMsg = chunk_prev_message + headerMsg
                chunk_prev_message = bytes()
        # except (AttributeError):
        #     pass
    elif prev_buffer_size >= size_of_header:
        headerMsg = chunk_prev_message[:size_of_header]
        chunk_prev_message = chunk_prev_message[size_of_header:]

    msgSize = int(headerMsg.decode("utf-8"))
    newMsg = chunk_prev_message
    chunk_prev_message = bytes()

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
    # print('inside send data function')
    msg_len = len(msg_data)
    # print(socket,"--socket from send_data")
    if msg_len:
        header = f"{msg_len:<{size_of_header}}"
        # try:
        socket.send(bytes(header, "utf-8") + msg_data)
        # print('socket.send(bytes(header, "utf-8") + msg_data)',socket)
        # except (ConnectionAbortedError,OSError) as e :
        #  print(e.strerror)
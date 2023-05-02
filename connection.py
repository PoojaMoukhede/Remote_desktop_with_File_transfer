# Receive data in chunks and build the complete message.
def data_recive(socket, size_of_header, prev_msg, buffer_size=65536):

    header_msg = bytes()
    prev_buffer_size = len(prev_msg)

    if prev_buffer_size < size_of_header:
        header_msg = socket.recv(size_of_header - prev_buffer_size)
        if len(header_msg) != size_of_header:
            header_msg = prev_msg + header_msg
            prev_msg = bytes()

    elif prev_buffer_size >= size_of_header:
        header_msg = prev_msg[:size_of_header]
        prev_msg = prev_msg[size_of_header:]

    msg_size = int(header_msg.decode("utf-8"))
    new_msg = prev_msg
    prev_msg = bytes()

    if msg_size:
        while True:
            if len(new_msg) < msg_size:
                new_msg += socket.recv(buffer_size)
            elif len(new_msg) > msg_size:
                prev_msg = new_msg[msg_size:]
                new_msg = new_msg[:msg_size]
            if len(new_msg) == msg_size:
                break
        return new_msg, prev_msg

    else:
        return None

#Send data with a header attached to the message
def send_data(socket, size_of_header, msg_data):
    msg_len = len(msg_data)
    if msg_len:
        header = f"{msg_len:<{size_of_header}}"
        socket.send(bytes(header, "utf-8") + msg_data)


def retry(msg):
    check = True
    while check:
        choice = input(msg)
        if choice.lower() == "y":
            return True
        elif choice.lower() == "n":
            return False

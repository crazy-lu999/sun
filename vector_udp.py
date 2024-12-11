import socket
import struct
import math
import hashlib


def file_checksum(byte_stream):
    sum_value = sum(el for el in byte_stream)
    byte_stream = struct.pack('>I', sum_value)
    return byte_stream
    # return hashlib.sha256(byte_stream).hexdigest().encode('utf-8')


def udp_pack(CMD_max_payload,
             CMD_MAGIC_WORD=b'VectorCN',
             CMD_ID=0,
             CMD_Counter=0,
             CMD_Multiple=0,
             Reserve=0,
             Sequence_Number=0):
    if type(CMD_max_payload) == bytes:
        payload = [el for el in CMD_max_payload]
    else:
        payload = [CMD_max_payload]

    CMD_payload_lenth = len(payload)
    CMD_MSG = [CMD_ID, CMD_Counter, CMD_payload_lenth, CMD_Multiple, Reserve,
               Sequence_Number] + payload
    message = struct.pack(">IHHBBH%dB" % CMD_payload_lenth, *CMD_MSG)

    return CMD_MAGIC_WORD + message


class vector_udp:
    def __init__(self):
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        target_ip = "127.0.0.1"  # 目标IP地址，这里使用本地回环地址，可根据实际情况修改
        target_port = 5555  # 目标端口号，可根据需要调整
        self.send_socket.connect((target_ip, target_port))

    def send_udp(self, *args, **kwargs):
        msg = udp_pack(*args, **kwargs)

        self.send_socket.sendall(msg)
        self.response = self.send_socket.recv(1024)
        print(f"[PC_SEND]: {msg}\n[PC_RECV]: {self.response}")

    def file_load(self, files='', packet_size=10):
        with open(files, 'rb') as f:
            self.byte_stream = f.read()
            print(self.byte_stream)

        self.max_packet_size = packet_size
        self.num_packets = math.ceil(len(self.byte_stream) / self.max_packet_size)
        self.sha256_checksum = file_checksum(self.byte_stream)

    def file_transfer(self):
        pl = b'/home/camera_config/config.json'
        self.send_udp(CMD_Counter=0x101, CMD_max_payload=pl,
                      CMD_Multiple=0 if len(self.byte_stream) < 1024 else 1)

        for cnt in range(self.num_packets):
            if self.response[-1] == 0:
                payload = self.byte_stream[cnt * self.max_packet_size:(cnt + 1) * self.max_packet_size]
                self.send_udp(CMD_ID=0x102, CMD_Counter=cnt, CMD_max_payload=payload, Sequence_Number=cnt,
                              CMD_Multiple=0 if len(payload) < 1024 else 1)

        self.send_udp(CMD_ID=0x103, CMD_Counter=0, CMD_max_payload=self.sha256_checksum)

    def Authorization_check(self):
        self.send_udp(CMD_ID=0x11, CMD_Counter=0, CMD_max_payload=bytes([16]))
        if len(self.response[20:]) == 16:
            self.send_udp(CMD_ID=0x11, CMD_Counter=1, CMD_max_payload=bytes([1]))

    def Start_rtp(self, mode='hb'):
        self.send_udp(CMD_ID=0x21, CMD_Counter=0, CMD_max_payload=bytes([0 if mode == 'hb' else 1]))

    def stop_rtp(self, reset=False):
        self.send_udp(CMD_ID=0x22, CMD_Counter=0, CMD_max_payload=bytes([1 if reset else 0]))

    def conn_hb(self, silent=False):
        self.send_udp(CMD_ID=0x31, CMD_Counter=0, CMD_max_payload=bytes([1 if silent else 0]))


if __name__ == '__main__':
    a = vector_udp()

    a.file_load(files='config.json', packet_size=1024)
    a.file_transfer()
    # a.Authorization_check()
    # a.Start_rtp(mode='hb')
    # a.stop_rtp()
    # a.conn_hb()

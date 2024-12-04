import socket
import struct
import json
import math
import hashlib


class vector_udp:
    cmd_id_lookup = {'json_path': 0x101, 'json_content': 0x102, 'json_checksum': 0x103,
                     'author_check': 0x11,
                     'start_rtp': 0x21,
                     'stop_rtp': 0x22,
                     'connect': 0x31,
                     'get_error': 0x41}

    def __init__(self):
        self.sha256_checksum = None
        self.num_packets = None
        self.max_packet_size = None
        self.byte_stream = None
        self.send_socket = None

    def udp_pack(self, CMD_max_payload,
                 CMD_MAGIC_WORD=1,
                 CMD_ID=0x101,
                 CMD_Counter=65535,
                 CMD_Multiple=0,
                 Reserve=0,
                 Sequence_Number=0):

        if type(CMD_max_payload) == bytes:
            payload = [el for el in CMD_max_payload]
        else:
            payload = [CMD_max_payload]

        CMD_payload_lenth = len(payload)
        CMD_MSG = [CMD_MAGIC_WORD, CMD_ID, CMD_Counter, CMD_payload_lenth, CMD_Multiple, Reserve,
                   Sequence_Number] + payload
        message = struct.pack(">QIHHBBH%dB" % CMD_payload_lenth, *CMD_MSG)

        return message

    def udp_config(self):
        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        target_ip = "127.0.0.1"  # 目标IP地址，这里使用本地回环地址，可根据实际情况修改
        target_port = 1234  # 目标端口号，可根据需要调整
        self.send_socket.connect((target_ip, target_port))

    def file_load(self, files='', packet_size=10):
        try:
            with open(files, 'rb') as f:
                self.byte_stream = f.read()
                print(self.byte_stream)
        except FileNotFoundError:
            print(f"文件 {files} 未找到，请检查文件路径是否正确。")
        except Exception as e:
            print(f"发生其他错误：{e}")

        # 设置每个数据包的最大大小（可根据实际网络情况调整）
        self.max_packet_size = packet_size
        print(f"文件长度{len(self.byte_stream)}, 每个包最大长度{self.max_packet_size}")
        # 计算需要发送的数据包数量
        self.num_packets = math.ceil(len(self.byte_stream) / self.max_packet_size)
        print(f"除第一个包，文件一共分为{self.num_packets}个包")
        # 计算文件的checksum值
        self.sha256_checksum = hashlib.sha256(self.byte_stream).hexdigest()
        # print(f"checksum={self.sha256_checksum}")

    def files_transfer(self):
        """
        函数用于通过UDP发送数据
        """
        response = []
        try:
            for i in range(self.num_packets + 1):
                print(f"第{i}个包")
                if i == 0:
                    tmp = '/home/camera_config/config.json'
                    msg = self.udp_pack(CMD_Counter=i, CMD_max_payload=bytes(tmp, encoding='utf-8'))
                    self.send_socket.sendall(msg)
                    print("数据已发送:", msg)
                    response = self.send_socket.recv(1024)
                    print('接收SOC响应为：', response)
                else:
                    cnt = i - 1
                    if response[-1] == 0:
                        payload = self.byte_stream[cnt * self.max_packet_size:(cnt + 1) * self.max_packet_size]
                        msg = self.udp_pack(CMD_ID=0x102, CMD_Counter=i, CMD_max_payload=payload,
                                            Sequence_Number=i)
                        print(f"{cnt * self.max_packet_size},{(cnt + 1) * self.max_packet_size}, 数据：{msg}")
                        self.send_socket.send(msg)
                        response = self.send_socket.recv(1024)
                        print('接收SOC响应为：', response)

            msg = self.udp_pack(CMD_ID=0x103, CMD_Counter=self.num_packets + 1,
                                CMD_max_payload=self.sha256_checksum.encode('utf-8'),
                                Sequence_Number=self.num_packets + 1)

            print(f"第{self.num_packets + 1}个包")
            self.send_socket.sendall(msg)
            print("数据已发送:", msg)
            response = self.send_socket.recv(1024)
            print('接收SOC响应为：', response)

        except Exception as e:
            print("发送数据时出错:", e)
        finally:
            self.send_socket.close()

    def Authorization_check(self):
        msg = self.udp_pack(CMD_ID=0x11, CMD_max_payload=0x1)
        print(msg)
        self.send_socket.send(msg)

    def Start_RTP_transfer(self):
        msg = self.udp_pack(CMD_ID=0x12, CMD_max_payload=1)
        print(msg)
        self.send_socket.send(msg)


if __name__ == '__main__':
    a = vector_udp()

    a.udp_config()
    a.file_load(files='asm.xml', packet_size=1024)
    a.files_transfer()
    # a.Authorization_check()
    # a.Start_RTP_transfer()

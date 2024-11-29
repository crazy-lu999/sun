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
        self.num_packets = None
        self.max_packet_size = None
        self.json_bytes = None
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

    def json_file(self, files='', packet_size=100):
        # 读取JSON文件内容
        with open(files, 'r') as f:
            json_data = json.load(f)
        # 将JSON数据转换为字节流
        self.json_bytes = json.dumps(json_data)
        print(self.json_bytes)
        # 设置每个数据包的最大大小（可根据实际网络情况调整）
        self.max_packet_size = packet_size
        # 计算需要发送的数据包数量
        self.num_packets = math.ceil(len(self.json_bytes) / self.max_packet_size)
        print(f"除第一个包，文件一共分为{self.num_packets}个包")

        self.sha256_checksum = hashlib.sha256(self.json_bytes.encode('utf-8')).hexdigest()
        print(f"checksum={self.sha256_checksum}")

    def files_transfer(self):
        """
        函数用于通过UDP发送数据
        """
        try:
            for i in range(self.num_packets + 1):
                print(f"第{i}个包")
                if i == 0:
                    tmp = '/home/camera_config/config.json'
                    msg = self.udp_pack(CMD_Counter=i, CMD_max_payload=bytes(tmp, encoding='utf-8'))
                    self.send_socket.send(msg)
                    print("数据已发送:", msg)
                    response = self.send_socket.recv(1024)
                    print('接收SOC响应为：', response)
                else:
                    cnt = i - 1
                    if response[-1] == 0:
                        payload = self.json_bytes[cnt * self.max_packet_size:(cnt + 1) * self.max_packet_size]
                        payload = bytes(payload, encoding='utf-8')
                        msg = self.udp_pack(CMD_ID=0x102, CMD_Counter=i, CMD_max_payload=payload,
                                            Sequence_Number=i)
                        print(f"{cnt * self.max_packet_size},{(cnt + 1) * self.max_packet_size}, 数据：{msg}")
                        self.send_socket.send(msg)
                        response = self.send_socket.recv(1024)
                        print('接收SOC响应为：', response)

            msg = self.udp_pack(CMD_ID=0x103, CMD_Counter=self.num_packets + 1,
                                CMD_max_payload=self.sha256_checksum.encode('utf-8'),
                                Sequence_Number=self.num_packets + 1)
            self.send_socket.send(msg)
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
    a.json_file(files='config.json', packet_size=100)
    # a.files_transfer()
    # a.Authorization_check()
    a.Start_RTP_transfer()

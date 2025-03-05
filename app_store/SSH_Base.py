import paramiko


class SSHBase(object):
    def __init__(self, hostname, port=22, username=None, password=None):
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.ssh_client = None

    def connect(self):
        """建立SSH连接"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(hostname=self.hostname, port=self.port,
                                    username=self.username, password=self.password)
            print("Connected to {}.".format(self.hostname))
        except Exception as e:
            print("Failed to connect: {}".format(e))
            raise

    def exec_command(self, command):
        """在远程服务器上执行命令"""
        if not self.ssh_client:
            print("Please connect first.")
            return
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        print(stdout.read().decode())
        print(stderr.read().decode())

    def close(self):
        """关闭SSH连接"""
        if self.ssh_client:
            self.ssh_client.close()
            print("Connection closed.")

    def __enter__(self):
        """支持with语句自动打开连接"""
        self.connect()
        return self

    def __exit__(self, type, value, traceback):
        """支持with语句自动关闭连接"""
        self.close()


# 使用示例：
if __name__ == "__main__":
    with SSHBase(hostname='example.com', port=22, username='your_username', password='your_password') as ssh:
        ssh.exec_command('ls -l')
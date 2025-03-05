# -*- coding: utf-8 -*-

# Auther : hao.lu
# Date : 2025/3/5 16:34
# File : dd.py
import os


class RemoteFile_Down_and_Up:
    def __init__(self, ip, username, password, port=22):
        self.ip = ip
        self.username = username
        self.password = password
        self.port = port

    def download(self, remote_path=None, renamefile=None):
        os.system('pscp -pw %s -P %s -r %s@%s:%s %s'
                  % (self.password, self.port, self.username, self.ip, remote_path, renamefile))

    def upload(self, renamefile=None, remote_path=None):
        os.system('pscp -pw %s -P %s -r %s %s@%s:%s'
                  % (self.password, self.port, renamefile, self.username, self.ip, remote_path))

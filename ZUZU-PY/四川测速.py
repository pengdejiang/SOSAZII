# download_speed_test.py
import threading
from queue import Queue
import time
import random
from bs4 import BeautifulSoup
import re
from playwright.sync_api import sync_playwright
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime
import socket
import os
import requests
import time

def measure_speed(url, max_size=2*1024*1024, timeout=5):
    try:
        start_time = time.time()
        response = requests.get(url, stream=True, timeout=timeout)
        end_time = time.time()
        response.raise_for_status()
        
        # 限制下载大小为2MB
        content = response.content[:max_size]
        connection_time = end_time - start_time
        return connection_time
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

def test_channel_speed(line):
    # 解析行内容
    channel_name = line.split(',')[0]
    channel_url = line.split(',')[1].split('$')[0].strip()
    channel_ip_A = line.split(',')[1].split('/rtp')[0].strip()
    channel_ip_B = line.split(',')[1].split('/udp')[0].strip()
    
    # 创建两个集合来存储已经测试过的channel_ip_A和channel_ip_B
    tested_ips_A = set()
    tested_ips_B = set()
    
    # 检查channel_ip_A和channel_ip_B是否已经测试过
    if channel_ip_A not in tested_ips_A and channel_ip_B not in tested_ips_B:
        # 测速
        for _ in range(3):
            speed = measure_speed(channel_url)
            if speed is not None and speed <= timeout:
                # 下载成功，跳出循环
                break
            else:
                # 下载失败，继续下一次循环
                continue
        else:
            # 三次尝试都失败，标记该channel超时
            print(f"标记超时：{channel_name}")
            return None
        
        # 将channel_ip_A和channel_ip_B添加到已测试集合中
        tested_ips_A.add(channel_ip_A)
        tested_ips_B.add(channel_ip_B)
        
        # 判断速度并返回结果
        if speed is not None and speed <= timeout:
            return line
        else:
            print(f"删除行：{line.strip()}，速度 {speed:.2f} 秒")
            return None
    else:
        # 如果channel_ip_A或channel_ip_B已经测试过，则跳过测速
        print(f"跳过已测试的IP：{channel_ip_A}, {channel_ip_B}")
        return None

# 主程序
if __name__ == "__main__":
    # 打开并读取“四川电信.txt”文件
    with open("四川电信.txt", "r", encoding="utf-8") as file:
        lines = file.readlines()
    
    # 打开“四川测速结果.txt”文件，准备写入结果
    with open("四川测速结果.txt", "w", encoding="utf-8") as output_file:
        # 遍历每一行
        for line in lines:
            result = test_channel_speed(line)
            if result is not None:
                output_file.write(result)
				
				
				
				

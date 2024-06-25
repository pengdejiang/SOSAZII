import requests
import time

# 定义测速函数
def measure_speed(url):
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        end_time = time.time()
        response.raise_for_status()
        connection_time = end_time - start_time
        return connection_time
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None

# 打开并读取“四川电信.txt”文件
with open("四川电信.txt", "r", encoding="utf-8") as file:
    lines = file.readlines()

# 创建两个集合来存储已经测试过的channel_ip_A和channel_ip_B
tested_ips_A = set()
tested_ips_B = set()

# 打开“四川测速结果.txt”文件，准备写入结果
with open("四川测速结果.txt", "w", encoding="utf-8") as output_file:
    # 遍历每一行
    for line in lines:
        # 截取channel_name和channel_url
        channel_name = line.split(',')[0]
        channel_url = line.split(',')[1].split('$')[0].strip()
        
        # 截取channel_ip_A和channel_ip_B
        channel_ip_A = line.split(',')[1].split('/rtp')[0].strip()
        channel_ip_B = line.split(',')[1].split('/udp')[0].strip()
        
        # 检查channel_ip_A和channel_ip_B是否已经测试过
        if channel_ip_A not in tested_ips_A and channel_ip_B not in tested_ips_B:
            # 测速
            speed = measure_speed(channel_url)
            # 将channel_ip_A和channel_ip_B添加到已测试集合中
            tested_ips_A.add(channel_ip_A)
            tested_ips_B.add(channel_ip_B)
            
            # 判断速度并写入文件
            if speed is not None and speed > 0.2:
                output_file.write(line)
            elif speed is not None and speed <= 0.2:
                print(f"删除行：{line.strip()}，速度 {speed:.2f} 秒")
        else:
            # 如果channel_ip_A或channel_ip_B已经测试过，则跳过测速
            print(f"跳过已测试的IP：{channel_ip_A}, {channel_ip_B}")

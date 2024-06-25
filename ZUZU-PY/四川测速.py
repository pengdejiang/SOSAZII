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

# 打开并读取“四川电信”文件
with open("四川电信.txt", "r", encoding="utf-8") as file:
    lines = file.readlines()

# 打开“四川测速结果”文件，准备写入结果
with open("四川测速结果.txt", "w", encoding="utf-8") as output_file:
    # 遍历每一行
    for line in lines:
        # 截取channel_name和channel_url
        channel_name = line.split(',')[0]
        channel_url = line.split(',')[1].split('$')[0].strip()
        
        # 测速
        speed = measure_speed(channel_url)
        
        # 判断速度并写入文件
        if speed is not None and speed > 0.2:
            output_file.write(f"{channel_name},{channel_url}${speed}\n")
        elif speed is not None and speed <= 0.2:
            print(f"删除行：{line.strip()}，速度 {speed:.2f} 秒")

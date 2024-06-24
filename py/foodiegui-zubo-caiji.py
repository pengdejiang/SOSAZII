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
def init_browser():
    """
    初始化浏览器
    """
    playwright = sync_playwright().start()
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context()
    context.route("**/*", lambda route, request: intercept_requests(route, request))
    return browser, playwright

def intercept_requests(route, request):
    """
    拦截和过滤 HTTP 请求
    """
    url = request.url
    if "www.foodieguide.com" in url:
        route.continue_()
    else:
        print("拦截第三方内容:", url)
        route.abort()

def close_browser(browser, playwright):
    """
    关闭浏览器
    """
    browser.close()
    playwright.stop()



def fetch_channel_info_worker(task_queue, result_queue):
    browser, playwright = init_browser()
    page = browser.new_page()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
    }
    page.set_extra_http_headers(headers)

    while True:
        url_id = task_queue.get()
        if url_id is None:
            break

        channels_info = []
        try:
            page.on('route', lambda route: intercept_requests(route))
            page.goto(f'http://www.foodieguide.com/iptvsearch/hotellist.html?s={url_id}', timeout=240000)  # 增加超时时间到240秒
            time.sleep(random.uniform(5, 10))
            hidden_result = page.query_selector("#hiddenresult")
            if hidden_result:
                print("访问：", url_id, "找到 #hiddenresult")
                result_html = page.inner_html("#hiddenresult")
                soup = BeautifulSoup(result_html, 'html.parser')
                result_divs = soup.find_all('div', class_='result')

                for _ in range(3):
                    time.sleep(random.uniform(0.5, 1.5))
                    x = random.randint(100, 500)
                    y = random.randint(100, 500)
                    page.mouse.move(x, y)

                for result_div in result_divs:
                    channel_name_element = result_div.find('div', class_='channel')
                    channel_name_link = channel_name_element.find('a') if channel_name_element else None
                    if channel_name_link:
                        channel_name = channel_name_link.text.strip()
                    else:
                        continue
                    m3u8_element = result_div.find('div', class_='m3u8')
                    if m3u8_element:
                        url_td = m3u8_element.find('td', style=re.compile(r'padding-left:\s*6px;'))
                        if url_td:
                            channel_url = url_td.text.strip()
                        else:
                            continue
                    else:
                        continue
                    channels_info.append((channel_name, channel_url, 2))
            else:
                print("访问：", url_id, "未找到 #hiddenresult")

            if channels_info:
                result_queue.put((url_id, channels_info))

        except Exception as e:
            print(f"获取频道信息时发生异常: {e} - URL: {url_id}")

        task_queue.task_done()

    page.close()
    close_browser(browser, playwright)

def test_ip_port_connectivity(ip, port):
    """
    测试指定 IP 和端口的连通性
    """
    try:
        sock = socket.create_connection((ip, port), timeout=5)
        sock.close()
        return True
    except Exception as e:
        print(f"连接 {ip}:{port} 失败: {e}")
        return False

def get_hotel_multicast_search_results(search_term):
    """
    获取酒店 IPTV 组播搜索结果
    """
    browser, playwright = init_browser()
    page = browser.new_page()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0"
    }
    page.set_extra_http_headers(headers)
    url_dict = {}
    try:
        page.set_default_timeout(600000)
        page.on('route', lambda route: intercept_requests(route))
        page.goto('http://www.foodieguide.com/iptvsearch/hoteliptv.php')
        for char in search_term:
            page.type('#search', char, delay=random.uniform(0.1, 0.3))
            time.sleep(random.uniform(0.1, 0.3))
        time.sleep(random.uniform(1, 3))
        page.click('#form1 [type="submit"]')
        time.sleep(random.uniform(1, 3))
        channel_links = page.query_selector_all('.channel a')
        for i, link in enumerate(channel_links):
            href = link.get_attribute('href')
            ip_port = href.split("hotellist.html?s=")[-1]
            ip, port = ip_port.split(':')
            if test_ip_port_connectivity(ip, int(port)):
                url_dict[ip_port] = i
    except Exception as e:
        print("获取酒店组播时发生错误:", e)
    finally:
        page.close()
        close_browser(browser, playwright)  # 在这里关闭浏览器和 playwright 对象
    
    return url_dict

def get_hotel_multicast_channel_info(url_dict):
    """
    获取酒店 IPTV 频道信息
    """
    existing_urls = set()
    with open('log/url_log.txt', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            existing_urls.add(line)  # 直接将整行作为 URL 添加到集合中

    task_queue = Queue()
    result_queue = Queue()

    for url_id in url_dict.keys():
        if url_id not in existing_urls:
            task_queue.put(url_id)

    threads = []
    for _ in range(5):  # 创建 5 个线程
        worker_thread = threading.Thread(target=fetch_channel_info_worker, args=(task_queue, result_queue))
        worker_thread.start()
        threads.append(worker_thread)

    task_queue.join()

    for _ in range(5):  # 停止所有线程
        task_queue.put(None)
    for thread in threads:
        thread.join()

    channels_info_dict = {}
    new_url_info = {}
    while not result_queue.empty():
        url_id, channels_info = result_queue.get()
        if channels_info:
            for name, url, speed in channels_info:
                channels_info_dict[url] = (name, url, speed)
                if url_id not in existing_urls:
                    if url_id not in new_url_info:
                        new_url_info[url_id] = []
                    new_url_info[url_id].append((name, url, speed))

    channels_info = list(channels_info_dict.values())

    # 读取历史频道信息并合并
    history_channels = read_itv_file('log/itv.txt')
    all_channels_info = channels_info + history_channels

    # 去重处理
    unique_channels = {}
    for name, url, speed in all_channels_info:
        if url not in unique_channels:
            unique_channels[url] = (name, url, speed)

    unique_channels_info = list(unique_channels.values())

    if not unique_channels_info:
        print("未获取到链接")
    else:
        with open('log/itv.txt', 'w', encoding='utf-8') as f:
            for channel_info in unique_channels_info:
                f.write(f"{channel_info[0]},{channel_info[1]},{channel_info[2]}\n")

        # 将新记录的 URL 写入 url_log.txt
        with open('log/url_log.txt', 'a', encoding='utf-8') as f: 
            for url_id in new_url_info.keys():
                f.write(f"{url_id}\n")

    return unique_channels_info

def filter_and_modify_sources(sources):
    """
    过滤和修改源，并返回符合关键字的频道信息
    """
    filtered_sources = []
    name_dict = {
        ' ': '', '⁺': '+', '＋': '+', '-': '', '[R]': '', '超高清': '', '[超清]': '', 'LD': '', '超清': '', '高清': '', '高请': '',
        '画中画': '', 'BRTV北京': '北京', 'CHC': '', 'HD': '', 'IPTV': '', '电视台': '', '北京卡酷少儿': '', '教育卫视': '', '中文国际': '',
        'BTV': '北京', '北京北京': '北京', '（备）': '', 'CCTV少儿': 'CCTV14', 'CCTV音乐': 'CCTV15', 'CCTV风云音乐': 'CCTV15', '戏曲': 'CCTV10', 
        'CCTV农业': 'CCTV7', 'CCTV电视剧': 'CCTV8', 'CCTV电影': 'CCTV6', 'CCTV综艺': 'CCTV3', 'CCTV新闻': 'CCTV13', 'CCTV4国际': 'CCTV4', 
        'CCTV科教': 'CCTV9', '党建频道': '党建', '北京卡酷': '卡酷', '戏曲精选': '戏曲', '种养新影老故事': '老故事', '(国际版)': '', '国际': '', 
        '中国教育': 'CETV', '体验': '', '空中课堂': '', '阿语': '阿拉伯语', '安徽频道': '安徽卫视', '央视精品': '央视文化', '央视文化精品': '央视文化', 
        '兵器': '兵器科技', '四川康巴卫视': '四川康巴', '世界地理': 'CCTV世界地理', '兵器科技': 'CCTV兵器科技', '怀旧剧场': 'CCTV怀旧剧场', 
        '女性时尚': 'CCTV女性时尚', '央视网球': 'CCTV高尔夫网球', '风云足球': 'CCTV风云足球', '凤凰卫视中文台': '凤凰卫视', '凤凰卫视资讯台': '凤凰资讯', 
        '纪实': '纪实人文', '人文人文': '人文', '科技科技': '科技', 'CCTVCCTV': 'CCTV', '武术': '武术世界', '奥林匹克': ''
    }

    for name, url, speed in sources:
        for key, value in name_dict.items():
            name = name.replace(key, value)
        name = re.sub(r'\(\d+\)', '', name).strip()
        filtered_sources.append((name, url, speed))

    keywords = ["爱", "电影", "影院", "影视", "解密", "军事", "星影", "卫视", "CCTV", "凤凰"]
    unique_urls = set()
    unique_matching_sources = []

    with open('log/itv.txt', 'w', encoding='utf-8') as file:
        for name, url, speed in filtered_sources:
            if any(keyword in name for keyword in keywords) and url not in unique_urls:
                unique_urls.add(url)
                unique_matching_sources.append((name, url, speed))
                file.write(f"{name},{url},{speed}\n")

    return unique_matching_sources

def download_speed_test(channel):
    """
    执行下载速度测试
    """
    session = requests.Session()
    if len(channel) == 3:
        name, url, _ = channel
    else:
        name, url = channel
    chaoshi = 3
    for _ in range(2):
        try:
            start_time = time.time()
            response = session.get(url, stream=True, timeout=chaoshi)
            response.raise_for_status()
            size = 0
            for chunk in response.iter_content(chunk_size=1024):
                size += len(chunk)
                if time.time() - start_time >= chaoshi:
                    break
            else:
                continue
            download_time = time.time() - start_time
            download_rate = round(size / download_time / 1024 / 1024, 4)
            break
        except requests.RequestException:
            pass
    else:
        print(f"频道：{name}, URL: {url}, 0")
        return name, url, 0
    print(f"频道：{name}, URL: {url}, {download_rate}")
    return name, url, download_rate

def read_itv_file(file_path):
    """
    读取 ITV 文件，返回频道信息列表
    """
    channels = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) == 3:
                name, url, speed = parts
                channels.append((name, url, float(speed)))  # 将速度转换为浮点数
    return channels

def classify_and_sort_sources(speed_test_results):
    """
    对结果进行分类和排序
    """

    categories = {
        "央视频道": ["CCTV"],
        "卫视频道": ["卫视","凤凰卫"],
        "影视剧场": ["爱", "电影", "影院", "影视", "解密", "军事", "星影"]
        }

    def classify_sources(sources, categories):  
        classified = defaultdict(list)  
        for name, url, speed in sources:  
            if float(speed) > 0.1: 
                found = False  
                for category, channel_list in categories.items():  
                    for channel in channel_list:  
                        if channel in name:  
                            classified[category].append((name, url, speed))  
                            found = True  
                            break  
                    if found:  
                        break  
                if not found:  
                    classified["其他,"].append((name, url, speed))  
        return classified  

    def channel_key(channel_name, speed):  
        match = re.search(r'\d+', channel_name) 
        speed_int = int(speed) if isinstance(speed, int) or isinstance(speed, float) else 0  
        if match:
            num = int(match.group())  
        else:
            num = float('inf') 
        return (num, -float(speed))  

    classified_sources = classify_sources(speed_test_results, categories)  
    specific_order = ["央视频道,",  "卫视频道,", "影视剧场,", "地方频道,"]  
    other_categories = [cat for cat in categories if cat not in specific_order]  

    sorted_categories = specific_order + sorted(other_categories)  
    print(classified_sources)
    with open("itvlist.txt", "w", encoding="utf-8") as f:  
        for category in sorted_categories:  
            if category in classified_sources:  
                f.write(f"{category}#genre#\n")  
                source_list = classified_sources[category]  
                source_list.sort(key=lambda x: (channel_key(x[0], x[2]), x[0]) if "cctv" in x[0].lower() else (x[0], -x[2]))
                for name, url, speed in source_list:  
                    f.write(f"{name},{url}\n")  
                f.write("\n")  

def read_itv_file(file_path):
    """
    读取 ITV 文件，返回频道信息列表
    """
    channels = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            parts = line.strip().split(',')
            if len(parts) == 3:
                name, url, speed = parts
                channels.append((name, url, float(speed)))
    return channels

def classify_and_sort_sources( sources):
    """
    根据分类和排序规则对源进行分类和排序，并写入文件
    """
    categories = {
        "央视频道": ["CCTV"],
        "卫视频道": ["卫视"],
        "影视剧场": ["爱", "电影", "影院", "影视", "解密", "军事", "星影"]
    }

    def channel_key(channel):
        match = re.search(r'\d+', channel[0])
        channel_name = match.group() if match else "100"  # 如果没有数字，则赋予一个大于99的数字
        return (int(channel_name), -channel[2])

    classified_sources = {category: [] for category in categories}
    
    for name, url, speed in sorted(sources):
        for category, channels in categories.items():
            if any(channel in name for channel in channels):
                classified_sources[category].append((name, url, speed))
                break
        # else:
        #     classified_sources["其他频道"].append((name, url, speed))

    with open("itvlist.txt", "w", encoding="utf-8") as f:
        for category, channel_list in classified_sources.items():
            if channel_list:
                f.write(f"{category},#genre#\n")
                channel_list.sort(key=channel_key)
                for name, url, speed in channel_list:
                    f.write(f"{name},{url}\n")
                f.write("\n")

def upload_file_to_github(token, repo_name, file_path, branch='main'):
    """
    将结果上传到 GitHub
    """
    g = Github(token)
    repo = g.get_user().get_repo(repo_name)
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    git_path = file_path.split('/')[-1]
    try:
        contents = repo.get_contents(git_path, ref=branch)
    except:
        contents = None
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if contents:
            repo.update_file(contents.path, current_time, content, contents.sha, branch=branch)
            print("文件已更新")
        else:
            repo.create_file(git_path, current_time, content, branch=branch)
            print("文件已创建")
    except Exception as e:
        print("文件上传失败:", e)

if __name__ == "__main__":
    # 从环境变量中获取 GitHub Token
    token = os.getenv("GITHUB_TOKEN")

    sources = read_itv_file('log/itv.txt')
    if len(sources) < 1000:
        search_term = "北京"
        result = get_hotel_multicast_search_results(search_term)
        if result:
            sources = get_hotel_multicast_channel_info(result)
            if sources:
                sources += read_itv_file("log/itv.txt")

    filtered_sources =  filter_and_modify_sources(sources)
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_channel = {executor.submit(download_speed_test, source): source for source in filtered_sources}
        speed_test_results = []
        for future in as_completed(future_to_channel):
            channel = future_to_channel[future]
            try:
                result = future.result()
                speed_test_results.append(result)
            except Exception as exc:
                print(f"频道：{channel[0]} 测速时发生异常：{exc}")
    sources = []
    with open('log/itv.txt', 'w', encoding='utf-8') as file:
        for name, url, speed in speed_test_results:
            if speed > 0.2: #筛选速度大于0.2的
                sources.append((name, url, speed))
                file.write(f"{name},{url},{speed}\n")

    classify_and_sort_sources(sources)

    # 如果 Token 不为空，则上传文件到 GitHub
    if token:
        upload_file_to_github(token, "IPTV", "itvlist.txt")

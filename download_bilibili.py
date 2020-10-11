import json
import requests
from lxml import etree
import time
import subprocess
import os


def read_cookies(cookies_file):
    try:
        with open(cookies_file, 'r', encoding="utf-8") as f:
            cookies_str = f.read()
        cookies_dict = {}
        cookies_list = cookies_str.split(";")
        for cookies in cookies_list:
            cookie = cookies.lstrip()
            cookie_kv = cookie.split("=", 1)
            cookies_dict[cookie_kv[0]] = cookie_kv[1]
    # print(cookies_dict)
    # print("3")
        cookies_jar = requests.utils.cookiejar_from_dict(cookies_dict)
    # print(cookies_jar)
        return cookies_jar
    except:
        return None

def get_response(url, headers, cookies=None, method='get', data=None):
    session = requests.Session()
    session.headers = headers
    if cookies:
        session.cookies = cookies
    else:
        pass
    if method == 'get':
        response = session.get(url)
    elif method == 'post':
        response = session.post(url, data)
    elif method == 'options':
        response = session.options(url)
    else:
        print("Request method error!")
        return None
    # time.sleep(0.5)
    # response.encoding = "utf-8"
    # print(session.cookies)
    # print(response.text)
    return response

def get_bilibili_video_info(response):
    info_dict = {}
    ele = etree.HTML(response.content)
    # get 'window.__playinfo__' object
    videoPlayInfo = str(ele.xpath('//head/script[5]/text()')[0].encode('utf-8').decode('utf-8'))[20:]
    videoJson = json.loads(videoPlayInfo)
    video_initial_state = str(ele.xpath('//head/script[6]/text()')[0].encode('utf-8').decode('utf-8'))[25:].split(';(function()')[0]
    state_json = json.loads(video_initial_state)
    info_dict['videoName'] = state_json['videoData']['title']
    try:
        info_dict['subName'] = state_json['videoData']['pages']
    except:
        print('未能获取副标题！')
    # print('*'*20, videoPlayInfo, '*'*20)
    try:
        # after 2018
        info_dict['videoURL'] = videoJson['data']['dash']['video'][0]['baseUrl']
        info_dict['audioURl'] = videoJson['data']['dash']['audio'][0]['baseUrl']
    except Exception:
        # before 2018
        info_dict['videoURL'] = videoJson['data']['durl'][0]['url']
    return info_dict
    # print('videoURL: ', videoURL)
    # print('audioURl: ', audioURl)
    # print('flag: ', flag)

def file_download(url, name, filetype, headers, cookies):
    dirname = ("./videos/").encode("utf-8").decode("utf-8")
    if not os.path.exists(dirname):
        print('创建videos文件夹!')
        os.makedirs(dirname)
    headers.update({'origin': 'https://www.bilibili.com', 'referer': 'https://www.bilibili.com/', 'sec-fetch-dest': 'empty', 'sec-fetch-mode': 'cors', 'sec-fetch-site': 'cross-site'})
    print('请求下载...')
    seg_response = get_response(url, headers=headers, cookies=cookies, method='options')
    print('请求下载完成！')
    seg_length = 1024 * 1024 * 1
    begin = 0
    end = seg_length - 1
    br_point = 0
    while True:
        headers.update({'range': 'bytes={}-{}'.format(begin, end)})
        # print('开始请求新片段!', end='\r')
        seg_response = get_response(url, headers=headers, cookies=cookies)
        # print('请求片段中...')
        if seg_response.status_code == 206:
            begin = end + 1
            end += seg_length
            # print('该片段请求完成！', end='\r')
        elif seg_response.status_code == 416:
            headers.update({'range': 'bytes={}-'.format(begin)})
            print('开始下载最后一段！')
            seg_response = get_response(url, headers=headers, cookies=cookies)
            print('下载完成！')
            br_point = 1
        else:
            print('请求失败,再次请求！')
            time.sleep(1)
            seg_response = get_response(url, headers=headers, cookies=cookies)
            print('再次请求结束！')
            if seg_response.status_code == 206:
                print('再次请求成功！继续请求。')
                begin = end + 1
                end += seg_length
            else:
                print('再次请求失败！退出程序。')
                break
        print('共下载' + str(begin / 1048576) + 'MB！', end='\r')
        try:
            with open(dirname + name.encode("utf-8").decode("utf-8") + '_.' + filetype, 'ab') as f:
                f.write(seg_response.content)
        except:
            print('请自行创建videos文件夹！')
            break
            # print('本部分下载完成！')
        if br_point == 1:
            print('本部分下载完成！\n' + '*' * 30)
            break

def combine_files(video, audio, out):
    subprocess.call("ffmpeg -i " + video + " -i " + audio + ' -c copy ' + out, shell=True)

def main(url, merge):
    try:
        page = int(url.split('?')[-1].split('=')[-1])
        p = page - 1
    except:
        pass
    headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
}
    cookies = read_cookies('cookies.txt')
    print('分析url！')
    response = get_response(url, headers=headers, cookies=cookies)
    print('提取视频链接！')
    info_dict = get_bilibili_video_info(response)
    try:
        total_name = info_dict['videoName'] + '_' + info_dict['subName'][p]['part']
    except:
        total_name = info_dict['videoName']
    # print(info_dict['audioURl'])
    if info_dict['audioURl']:
        print('下载视频中...')
        file_download(info_dict['videoURL'], total_name, 'mp4', headers=headers, cookies=cookies)
        print('下载音频中...')
        file_download(info_dict['audioURl'], total_name, 'mp3', headers=headers, cookies=cookies)
        print('全部下载完成！')
        if merge != "2":
            print('开始合并！\n', '*'*50)
            try:
                combine_files("'./videos/" + total_name + "_.mp4'", "'./videos/" + total_name + "_.mp3'", "'./videos/" + total_name + ".mp4'")
                os.remove("./videos/" + total_name + "_.mp4")
                os.remove("./videos/" + total_name + "_.mp3")
                print('合并完成！\n', '*'*50)
            except:
                print('合并失败！')
        else:
            pass
    else:
        print('下载视频中...')
        file_download(info_dict['videoURL'], total_name, 'mp4', headers=headers, cookies=cookies)
        print('全部下载完成！')


if __name__ == '__main__':
    url = input('输入url: ')
    merge = input('合并音视频？ \n[1].合并\n2.不合并')
    number = input('下载本集？\n[1].本集\n2.全集\n')
    if number != '2':
        print('正在下载本集！')
        main(url, merge)
    else:
        try:
            url = url.split('?')[0]
        except:
            pass
        url_list = []
        parts = int(input('输入总集数: '))
        for p in range(parts):
            p_url = url + '?p=' + str(p + 1)
            url_list.append(p_url)
        for url in url_list:
            main(url, merge)
            print(url, '下载完成！\n', '*'*30, '\n', '#'*30, '\n', '*'*30)


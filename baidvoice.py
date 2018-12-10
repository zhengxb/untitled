#-*- coding:utf-8 -*-

from aip import AipSpeech

APP_ID = '10062189'
API_KEY = 'ZSn906TAPpRrGPwB30ppTRpG'
SECRET_KEY = 'd46e9ddea029d97e29c8f73a98fad22b'

client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)


# 读取文件
def get_file_content(filePath):
    with open(filePath, 'rb') as fp:
        return fp.read()

# 识别本地文件
print client.asr(get_file_content('awake.wav'), 'wav', 16000, {
    'lan': 'zh',
})
result  = client.synthesis('你好百度', 'zh', 1, {
    'vol': 5,
})
if not isinstance(result, dict):
    with open('auido.mp3', 'wb') as f:
        f.write(result)
# 从URL获取文件识别
client.asr('', 'pcm', 16000, {
    'url': 'http://121.40.195.233/res/16k_test.pcm',
    'callback': 'http://xxx.com/receive',
})
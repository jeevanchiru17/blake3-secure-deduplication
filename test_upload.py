import requests

files = {'file': open('datasets/large_video.mp4', 'rb')}
data = {
    'username': 'Alice',
    'public_key': 'testkey',
    'signature': 'testsig'
}
resp = requests.post("http://127.0.0.1:8000/upload", files=files, data=data)
print(resp.status_code)
print(resp.text)

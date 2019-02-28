import json
import requests
import threading
import re
import sys
import traceback

class MTDownloader:
    ua='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36'

    def __init__(self,url):
        self.url=url
    
    def fetch(self):
        headers={'User-Agent':self.ua}
        res=requests.head(self.url,headers=headers,allow_redirects=True,timeout=5)
        self.url=res.url
        self.length=int(res.headers["Content-Length"])
        self.filename=res.url.split('/')[-1]
        
        headers["Range"]="bytes=0-{}".format(self.length//2)
        res=requests.head(self.url,headers=headers,timeout=5)
        self.supported = (res.status_code==206)
        print('{}\nURL: {}\nContent length: {}\nFilename: {}\nRange: {}\n{}'.format(
            '='*20,
            self.url,self.length,self.filename,"Supported" if self.supported else "Not supported",
            '='*20
        ))

    def _singleWorker(self,lst,L,R):
        ev=lst[0]
        res=requests.get(self.url,headers={'User-Agent':self.ua,'Range':'bytes={}-{}'.format(L,R)},timeout=5)
        #print("Event: {} Download finished. {} bytes downloaded.".format(ev,len(res.content)))
        lst.append(res.content)
        ev.set()

    def _dowork(self):
        self.fetch()
        if(not self.supported or self.length<1024*1024*10):
            #print("File length less than 10M. Use single thread")
            res=requests.get(self.url,headers={'User-Agent':self.ua},timeout=5)
            with open(self.filename,'wb') as f:
                f.write(res.content)
        else:
            pieceLen=1024*1024*10
            nThread=self.length // pieceLen
            print("Spawn up to {} threads.".format(nThread))
            tasks=[]
            for i in range(nThread-1):
                lst=[]
                lst.append(threading.Event())
                lst[0].clear()
                tasks.append(lst)
                L=i*pieceLen
                R=(i+1)*pieceLen-1
                #print('Event: {} Range: {}-{} of {}'.format(lst[0],L,R,self.length))
                td=threading.Thread(target=MTDownloader._singleWorker,args=(self,lst,L,R))
                td.start()
            #print('Worker Range: {}-{} of {}'.format((nThread-1)*pieceLen,self.length,self.length))
            res=requests.get(self.url,headers={'User-Agent':self.ua,'Range':'bytes={}-{}'.format((nThread-1)*pieceLen,self.length)},timeout=5)
            with open(self.filename,'wb') as f:
                for lst in tasks:
                    ev=lst[0]
                    #print("Waiting for {}...".format(ev))
                    ev.wait()
                    content=lst[1]
                    f.write(content)
                f.write(res.content)

    def _work(self):
        try:
            self._dowork()
        except Exception as e:
            print('[Error] {} {}'.format(self.url,e))
        except:
            print("[Fatal] Unexpected error. {} {}".format(self.url,sys.exc_info()[0]))
        else:
            print("[Done] {}".format(self.url))
        self.tdev.set()
            
    def start(self):
        self.tdev=threading.Event()
        self.td = threading.Thread(target=MTDownloader._work,args=(self,))
        self.td.start()

    def wait(self,timeout):
        self.tdev.wait(timeout)

with open('info.json') as f:
    str=f.read()

print(str)
j=json.loads(str)

for key,value in j.items():
    ans=input('Do you want to download {}? (Y/n)'.format(key))
    if(ans=="" or ans=="Y"):
        print("[Started] Download {}...".format(key))
        MTDownloader(value).start()
    else:
        print("Skipped {}".format(key))

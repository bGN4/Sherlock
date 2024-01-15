# -*- coding: utf-8 -*-
import os
import re
import sys
import csv
import math
import time
import json
import queue
import random
import urllib
import asyncio
import inspect
import logging
import datetime
import argparse
import tempfile
import functools
import itertools
import threading
import traceback
import concurrent
import collections
from io import open
from lxml import etree
import requests
import aiohttp


PY2 = False
assert(sys.version_info.major>2 and sys.version_info.minor>8)
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.stderr.write( 'PWD=%s\n'%os.path.abspath(os.curdir) )
project_url = 'https://github.com/bGN4/Sherlock'
g_proxies = queue.Queue()
headers = {
    'User-Agent': '', # fill your UA in config.json
    'Cookie': '', # fill your cookie in config.json
}

class Web:
    def __new__(cls, *args, **kwargs):
        raise RuntimeError()
    @classmethod
    def adjust_parameters(cls, url, kwargs):
        if 'ua' not in kwargs and not kwargs.get('headers',{}).get('User-Agent',''):
            print('Warnning: will use default User-Agent.')
        kwargs.setdefault('headers', {'User-Agent': cls.ua_list[kwargs.pop('ua',0)]})
        kwargs.setdefault('allow_redirects', False)
        if (kwargs.get('proxy') or '').lower().startswith('api:'):
            url = 'http://'+url if '://' not in url else url
            url = kwargs.pop('proxy').removesuffix('/')[4:] + '/' + url.replace('://','/',1)
            key = requests.packages.urllib3.util.parse_url('ws://'+url.split('://',1)[-1]).auth
            if key and ':' not in key[1:-1]:
                kwargs['headers']['Authorization'] = 'Bearer ' + key
                url = url.replace(key+'@', '')
            #logging.error(url[:url.find('/http')+53]+' ...')
            #logging.error(kwargs['headers'].get('Authorization'))
        return url, kwargs
    @classmethod
    def fetch_resp(cls, url, **kwargs):
        url, kwargs = cls.adjust_parameters(url, kwargs)
        kwargs.setdefault('timeout', 30)
        retries = kwargs.pop('retries', {})
        proxies = kwargs.pop('proxy', None)
        session = cls.new_requests_session(retry=retries) if retries else cls.session
        if proxies: kwargs['proxies'] = dict(http=proxies, https=proxies)
        try: return session.get(url,**kwargs)
        except: traceback.print_exc()
    @classmethod
    def fetch_html(cls, url, **kwargs):
        r, x = cls.fetch_resp(url,**kwargs), None
        allow_redirects = kwargs.get('allow_redirects', False)
        #open('debug.page.html', 'wb').write( r.content )
        try: x = etree.HTML(r.content)
        except: pass
        if r and r.is_redirect and not allow_redirects and not hasattr(x,'xpath'):
            print( '[!] redirect to: ' + r.headers.get('Location') )
        return x
    @classmethod
    def fetch_json(cls, url, **kwargs):
        r, j = cls.fetch_resp(url,**kwargs), {}
        try: j = r.json()
        except: pass
        if j.get('ok')==0 or not j: print(colored(url), colored(j))
        return j
    @classmethod
    async def afetch_json(cls, url, **kwargs):
        (r, data), j = await cls.afetch_resp(url,**kwargs), {}
        try: j = data
        except: pass
        if j.get('ok')==0 or not j: print(colored(url), colored(j))
        return j
    @staticmethod
    def new_requests_session(retry=dict(total=0,read=False)):
        retries = requests.packages.urllib3.util.retry.Retry(**retry)
        adapter = requests.adapters.HTTPAdapter(max_retries=retries)
        session = requests.Session()
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    session = new_requests_session(retry=dict(total=3,backoff_factor=2.5))
    ua_list = [
        'Mozilla/5.0 (compatible; Baiduspider/2.0;+http://www.baidu.com/search/spider.html)',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:33.0) Gecko/20120101 Firefox/33.0',
        'Opera/9.80 (Windows NT 6.1) Presto/2.12.388 Version/12.14',
        'Mozilla/5.0 (MSIE 10.0; Windows NT 6.1; Trident/5.0)']

class Paginator:
    step = 1
    local = []
    proxy = None
    sleep = (3, 7)
    label = 'items'
    times = page = 0
    total = page_max = page_all = -1
    quiet = batch = daemon = finish = False
    def __str__(self):
        var = {n:v for n in dir(self) if '__' not in n and type(v:=getattr(self,n)) in (int,str,bool)}
        return '<%s: %s>'%(type(self).__name__,', '.join([n+'=%s'%v for n,v in var.items() if n[0] in 'bcmpstu']))
    def __repr__(self):
        return self.__str__()
    def __iter__(self):
        self.daemon = 'MainThread'!=threading.current_thread().name
        return self
    def __aiter__(self):
        return self
    def __next__(self):
        result = self.getnext(1)
        if not isinstance(result, LookupError): return result
        time.sleep( result.args[0] )
        if not self.daemon: self.log('>', end='\r', color=6)
        self.page += self.step
        self.times += 1
        self.finish = self.fetch()
        return self.__next__()
    def getnext(self, sync):
        if len(self.local)<1:
            if self.finish:
                self.log(f'Finish process {self.times} pages.', '='*10)
                raise (StopAsyncIteration,StopIteration)[sync]
            sec = random.randint(*(i*100 for i in ((0.1,min(self.sleep)) if self.times<1 else self.sleep)))/100
            msg = f'Waiting {self.total} {self.label} for page {self.page+self.step}/{self.page_all} in {sec}s...'
            self.log(msg.replace('ing -1 ','ing ').replace('/-1 ',' '), '='*10)
            return LookupError(sec)
        elif self.batch:
            batch, self.local = self.local, []
            return batch
        else: return self.local.pop(0)
    def setattr(self, args, kwargs):
        for key in args:
            if kwargs[key] is not None:
                if key=='uid': assert(kwargs[key].isdigit())
                setattr(self, key, kwargs[key])
        self.h = (kwargs.get('config') or {}).get('headers',{})
    def log(self, msg, wing='', end='\n', color=2):
        txt = f'{wing} {msg} {wing}' if wing else msg
        if not self.quiet: sys.stderr.write(colored(txt,color)+end)
    def fetch(self):
        self.local = [(0,2,3,4,9)[self.page-1]*10+i for i in range(10)]
        return self.page>4
    async def afetch(self):
        return self.fetch()

class PaginatorLite(Paginator):
    @property
    def url(self):
        return self.l()
    def fetch(self):
        return self.parse(        Web.fetch_json(self.url, proxy=self.proxy, headers=self.h) )
    async def afetch(self):
        return self.parse( await Web.afetch_json(self.url, proxy=self.proxy, headers=self.h) )

class FollowByTagApp(Paginator):
    label = 'follows'
    def __init__(self, uid, tag, config, args=None, sleep=None, quiet=False, batch=False, page_max=10, page=0, count=20):
        self.setattr( ('uid','tag','sleep','quiet','batch','page_max','page','count'), locals() )
        self.api = config['app']['follow_by_tag'].replace('&count=20','&count=%d'%count)
    def fetch(self):
        data = fetch_json( self.api%(self.uid,self.tag,self.page) ).get('data',{})
        self.total = data.get('member_count', -1)
        self.local = data.get('member_users',[])
        return self.page>=self.page_max or len(self.local)<self.count

class FollowByTagLite(PaginatorLite):
    def __init__(self, uid, tag, config, args=None, proxy=None, sleep=None, quiet=False, batch=False, page_max=10, page=0):
        self.setattr( ('uid','tag','proxy','sleep','quiet','batch','page_max','page'), locals() )
        self.label = config['category'][tag]+u'博主' if tag in config['category'] else 'follows'+tag[-3:]
        self.api = config['lite']['follow_by_tag'].replace('%s', str(uid), 1).replace('%s', self.tag)
        self.ref = (self.api%1)[:-11].replace('/api/container/getIndex','/p/index')
        self.h = {'User-Agent': Web.ua_list[1+int(str(uid)[-3])%4], 'Referer': self.ref}
        self.l = lambda: (self.api%self.page).removesuffix('&since_id=1')
        self.fetch_count = lambda: FollowingLite(uid,config,args,proxy=proxy,quiet=quiet,page_max=1).get_tags(True)
    def parse(self, data):
        info = data.get('data',{}).get('cardlistInfo',{})
        since = info.get('since_id', 1)
        cards = filter(lambda x: isinstance(x,dict) and 'card_group' in x, data.get('data',{}).get('cards',[]))
        group = functools.reduce( list.__add__, map(lambda x: x['card_group'], cards), [] )
        users = map(lambda x: x.get('user',{}), filter(lambda x: isinstance(x,dict) and 'user' in x, group))
        self.local = list(users)
        if len(self.local)<1 and self.total!=20*(self.page-1) and not info:
            c = self.fetch_count() if self.total<0 and inspect.stack()[1].function=='fetch' else {}
            if 20*(self.page-1) != (total:=c.get(self.tag,-1)): raise ValueError(self, c, data)
        page_max = min(self.page_max,self.page_all) if self.page_all>0 else self.page_max
        return self.page>=page_max or len(self.local)<15

class FollowingLite(PaginatorLite):
    label = 'follows'
    def __init__(self, uid, config, args=None, proxy=None, sleep=None, quiet=False, batch=False, page_max=10, page=0):
        self.setattr( ('uid','proxy','sleep','quiet','batch','page_max','page'), locals() )
        self.api = config['lite']['following'].replace('%s', str(uid))
        self.ref = (self.api%1)[:-7].replace('/api/container/getIndex','/p/index')
        self.h = {'User-Agent': Web.ua_list[1+int(str(uid)[-3])%4], 'Referer': self.ref}
        self.l = lambda: (self.api%self.page).removesuffix('&page=1')
    def get_tags(self, force=False):
        if not hasattr(self, 'tags'):
            if not force: raise RuntimeError('fetch page 1 first')
            self.__next__()
        return self.tags | dict(total=self.total)
    def parse(self, data):
        cards = [x for x in data.get('data',{}).get('cards',[]) if isinstance(x,dict) and 'card_group' in x]
        group = functools.reduce(list.__add__,map(lambda x: x['card_group'],filter(lambda x:x.get('itemid'),cards)),[])
        other = functools.reduce(list.__add__,map(lambda x: x['card_group'],filter(lambda x:not x.get('itemid'),cards)),[])
        users = map(lambda x: x.get('user',{}), filter(lambda x: isinstance(x,dict) and 'user' in x, group))
        items = filter(lambda x: isinstance(x,dict) and 'scheme' in x and 'desc' in x, other)
        match = map(lambda x: re.search(u'(tagCategory_\d+).*关注了(\d+)个', f'{x["scheme"]}#{x["desc"]}'), items)
        tags = {'1042015:'+r.group(1):int(r.group(2)) for r in match if r}
        info = data.get('data',{}).get('cardlistInfo',{}) # nextpage = info.get('page')
        if tags and getattr(self,'tags',{}): print(tags, self.tags)
        self.tags = tags or getattr(self, 'tags', {})
        self.total = info.get('total', self.total)
        self.local = list(users)
        if self.total>0: self.page_all = math.ceil(self.total/20)
        elif not info: raise ValueError(self, {}, data)
        return self.page>=min(self.page_max,self.page_all) or len(self.local)<1

class MicroBlogLite(PaginatorLite):
    label = 'blogs'
    since_id = 0
    def __init__(self, uid, config, args=None, proxy=None, sleep=None, quiet=False, batch=False):
        self.setattr( ('uid','proxy','sleep','quiet','batch'), locals() )
        self.api = config['lite']['mblogs'].replace('%s', str(uid), 1)
        self.ref = self.api.split('&',1)[0].replace('/api/container/getIndex?containerid=','/p/')
        self.h = {'User-Agent': Web.ua_list[1+int(str(uid)[-3])%4], 'Referer': self.ref}
        self.l = lambda: (self.api%self.since_id).removesuffix('&page_type=03&since_id=0')
    def parse(self, data):
        info = data.get('data',{}).get('cardlistInfo',{})
        self.since_id = info.get('since_id', 0)
        cards = filter(lambda x: isinstance(x,dict) and 'mblog' in x, data.get('data',{}).get('cards',[]))
        self.local = [card['mblog'] for card in cards]
        return not self.since_id

class LikesLite(PaginatorLite):
    label = 'likes'
    def __init__(self, mid, config, args=None, proxy=None, sleep=None, quiet=False, batch=False, page_max=-1, page=0):
        self.setattr( ('mid','proxy','sleep','quiet','batch','page_max','page'), locals() )
        self.api = config['lite']['attitudes'].replace('%s',str(self.mid))
        self.ref = None
        self.h = {'User-Agent': Web.ua_list[1+hash(mid)%4]}
        self.l = lambda: self.api%self.page
    def parse(self, data):
        self.page_all = data.get('data',{}).get('max', -1)
        self.total    = data.get('data',{}).get('total_number', -1)
        self.local    = data.get('data',{}).get('data', [])
        page_max = self.page_max if self.page_max>0 else self.page_all
        return self.page>=page_max or len(self.local)<50

class RepostsLite(PaginatorLite):
    label = 'reposts'
    def __init__(self, mid, config, args=None, sleep=None, quiet=False, batch=False, page_max=-1, page=0):
        self.setattr( ('mid','sleep','quiet','batch','page_max','page'), locals() )
        self.api = config['lite']['reposts'].replace('%s',str(self.mid))
        self.ref = None
        self.h = {'User-Agent': Web.ua_list[1+hash(mid)%4]}
        self.l = lambda: self.api%self.page
    def parse(self, data):
        self.page_all = data.get('data',{}).get('max', -1)
        self.total    = data.get('data',{}).get('total_number', -1)
        self.local    = data.get('data',{}).get('data',[])
        page_max = self.page_max if self.page_max>0 else self.page_all
        return self.page>=page_max or len(self.local)<8

class RepliesLite(PaginatorLite):
    label = 'replies'
    max_id = 0
    def __init__(self, cid, config, args=None, proxy=None, sleep=None, quiet=False, batch=False):
        self.setattr( ('cid','proxy','sleep','quiet','batch'), locals() )
        self.api = config['lite']['replies'].replace('%s',str(self.cid),1)
        self.ref = None
        self.h = {'User-Agent': Web.ua_list[1+hash(cid)%4]}
        self.l = lambda: self.api%self.max_id
    def parse(self, data):
        self.page_all = data.get('max', -1)
        self.max_id = data.get('max_id', 0)
        self.total = data.get('total_number', -1)
        self.local = data.get('data', [])
        return not self.max_id

class CommentsLite(PaginatorLite):
    label = 'comments'
    max_id = 0
    def __init__(self, mid, config, args=None, proxy=None, sleep=None, quiet=False, batch=False):
        self.setattr( ('mid','proxy','sleep','quiet','batch'), locals() )
        self.api = config['lite']['comment'].replace('%s', str(self.mid), 2)
        self.ref = None
        self.h = {'User-Agent': Web.ua_list[1+hash(mid)%4]}
        self.l = lambda: (self.api%self.max_id).replace('&max_id=0','')
    def parse(self, data):
        self.page_all = data.get('data',{}).get('max', -1)
        self.max_id   = data.get('data',{}).get('max_id', 0)
        self.total    = data.get('data',{}).get('total_number', -1)
        self.local    = data.get('data',{}).get('data', [])
        return not self.max_id

class CommentsWap(Paginator):
    label = 'comments'
    def __init__(self, bid, config, args=None, sleep=None, quiet=False, batch=False, page_max=-1, page=0):
        self.setattr( ('bid','sleep','quiet','batch','page_max','page'), locals() )
        self.api = config['wap']['comment'].replace('%s', bid)
    def fetch(self):
        selector = fetch_html( self.api%self.page if self.page>1 else self.api.split('?',1)[0] )
        self.local = export_single_page_comment(selector)
        self.page_all = get_page_num(selector)
        page_max = self.page_max if self.page_max>0 else self.page_all
        return self.page>=page_max or len(self.local)<1

class MicroBlogWap(Paginator):
    label = 'blogs'
    def __init__(self, uid, config, args=None, sleep=None, quiet=False, batch=False, page_max=-1, page=0, step=1):
        self.setattr( ('uid','sleep','quiet','batch','page_max','page','step'), locals() )
        self.api = config['wap']['domain'] + uid + '?page=%d'
    def fetch(self):
        selector = fetch_html( self.api%self.page )
        self.page_all = get_page_num(selector)
        self.local = export_single_page_mblog(selector)
        page_max = self.page_max if self.page_max>0 else self.page_all
        return self.page<=1 if self.step<0 else self.page>=page_max or len(self.local)<1

class BlockingWap(Paginator):
    label = 'blacks'
    def __init__(self, config, args=None, sleep=None, quiet=False, batch=False, page_max=-1, page=0, step=1):
        self.setattr( ('sleep','quiet','batch','page_max','page','step'), locals() )
        self.api = config['wap']['export'].split('?')[0]
    def fetch(self):
        selector = Web.fetch_html(f'{self.api}?page={self.page}'.removesuffix('?page=1'), headers=self.h)
        self.page_all = get_page_num(selector)
        self.local = export_single_page(selector)
        page_max = self.page_max if self.page_max>0 else self.page_all
        return self.page<=1 if self.step<0 else self.page>=page_max or len(self.local)<1

class BlockingWeb(Paginator):
    label = 'blacks'
    def __init__(self, config, args=None, sleep=None, quiet=False, batch=False, page_max=10, page=0):
        self.setattr( ('sleep','quiet','batch','page_max','page'), locals() )
        self.api = config['web']['export']
    def fetch(self):
        data = fetch_json( self.api%self.page )
        self.total = data.get('total', -1)
        self.local = data.get('card_group', [])
        return self.page>=self.page_max or len(self.local)<1
        print('next', data.get('next_cursor', 0))

class FileProxy(Paginator):
    label = 'Proxies'
    def __init__(self, config, args=None, sleep=(0.1,0.2), quiet=False, batch=False):
        self.setattr( ('sleep','quiet','batch'), locals() )
        self.path = args.proxy
        self.finish = False if os.path.isfile(self.path) else True
    def fetch(self):
        self.local = [dict(uri=l.strip().lower()) for l in open(self.path).readlines() if '://' in l]
        return True

def colored(string, color=90):
    return string if color is None else f'\033[{color}m{string}\033[0m'

def press(*args, **kwargs):
    try: __import__('pyautogui').press(*args, **kwargs)
    except: pass

def fmt(s, c):
    if not isinstance(s,str): s = str(s)
    total_cnt = len(s)
    ascii_cnt = sum(1 for _ in filter(str.isascii, s))
    space_u = abs(c) - total_cnt + ascii_cnt//2
    space_a = ascii_cnt%2
    padding = u'\u3000'*space_u + ' '*space_a
    padding = ' ' * (space_u*2+space_a)
    return s if space_u<0 else padding+s if c>0 else s+padding

def random_pause(a, b, q=False):
    prompt = sys.stderr.write if not q else lambda s: None
    (lo, hi) = (min((a,b)), max((a,b)))
    if hi == 0: return
    seconds = lo+(hi-lo)*random.random()
    prompt( colored('wait %.1fs...\r'%seconds,2) )
    time.sleep(seconds)
    prompt( colored('>',6)+' '*16+'\r' )

def iter_pause(items, span=(3,7), quiet=False):
    pause = [lambda: random_pause(*span,q=quiet) for _ in range(len(items)-1)]
    return itertools.zip_longest(items, pause, fillvalue=lambda: random_pause(0,0))

def fetch_html(url, allow_redirects=False, raw=False):
    r, selector = None, None
    try:
        r = requests.get(url, timeout=30, headers=headers, allow_redirects=allow_redirects)
        selector = r.content if raw else etree.HTML( r.content )
#       open('debug.page.html', 'wb').write( r.content )
    except:
        traceback.print_exc()
    if r and r.is_redirect and not allow_redirects and not hasattr(selector,'xpath'):
        print( 'Unexpect redirect: ' + r.headers.get('Location') )
    return selector

def fetch_json(url, allow_redirects=False):
    r, data = None, {}
    try:
        r = requests.get(url, timeout=30, headers=headers, allow_redirects=allow_redirects)
        data = r.json()
        if data.get('ok')==0: print(colored(url), colored(data))
    except:
        traceback.print_exc()
    return data

def trans_human_time(s, now=None):
    now = datetime.datetime.now()
    whole = re.match(r'([\d :-]{19})', s)
    if whole: return whole.group(1)
    year = re.match(u'(\d+)月(\d+)日 ([\d:]+)', s)
    if year: return u'{}-{}-{} {}:00'.format(now.year, year.group(1), year.group(2), year.group(3))
    today = re.match(u'今天 ([\d:]+)', s)
    if today: return u'{}-{:02}-{:02} {}:00'.format(now.year, now.month, now.day, today.group(1))
    return u'{}-{:02}-{:02} 00:00:00'.format(now.year, now.month, now.day)

def cfg_update_st(st, config):
    for key in ('export','import','remove','follow'):
        config['wap'][key] = re.sub(r'st=[a-f\d]+', 'st='+st, config['wap'][key])

def get_param_st_raw(config):
    content = Web.fetch_resp(config['wap']['domain'], headers=config['headers']).content
    st = ([b'']+re.findall(b'st=([a-f\d]+)',content))[-1].decode()
    print( colored('st=%s'%st,2) )
    return st

def get_param_st(selector):
    tip = str((selector.xpath('//div[@class="tip"]//a[contains(@href,"account")]/@href')+[''])[0])
    if not tip:
        tip = str((selector.xpath('//div[@class="u"]//a[contains(@href,"account")]/@href')+[''])[0])
    return (['']+re.findall(r'st=([a-f\d]+)',tip))[-1]

def get_page_num(selector, which='total'):
    page_text = selector.xpath('//div[@id="pagelist"]//input[@type="submit"]/following-sibling::text()')[0]
    page_list = [int(i) for i in re.search(r'(\d+)/(\d+)', page_text).groups()]
    return page_list[('current','total').index(which)]

def get_block_num(selector):
    for text in selector.xpath('//div[@class="c"]/text()'):
        result = re.search(u'将(\d+)人', text)
        if result:
            return int( result.group(1) )
    return -1

def export_single_page_mblog(selector):
    items = selector.xpath('//div[@class="c"][@id]/@id')
    total = len(items)
    return list( map(lambda x:x.removeprefix('M_'), items) )

def export_single_page_comment(selector):
    rows = []
    talks = selector.xpath('//div[starts-with(@id, "C_")]')
    total = len(talks)
    for i in range(0, total):
        hot = talks[i].xpath('span[@class="kt"]')
        loc = talks[i].xpath('span[@class="ct"]')
        ctt = talks[i].xpath('span[@class="ctt"]')
        user = talks[i].xpath('a[starts-with(@href, "/")]')
        spam = talks[i].xpath('a[starts-with(@href, "/spam/")]')
        if hot or not user or not ctt: continue
        uid = re.search(r'uid=(\d+)', spam[0].get('href')).group(1)
        name = user[0].text
        talk = ''.join(ctt[0].itertext())
        tkto = ctt[0].getchildren()[0].text if ctt[0].xpath('a') else ''
        show = '[{:x}] {}({}): '.format(i,name,uid)
        if tkto: show += u'回复' + tkto + ':'
        show += '（' + loc[-1].text + '）'
        rows.append( [uid, show, 'None' if talk is None else talk] )
        print(show)
        print(talk)
    return rows

def export_single_page(selector):
    rows = []
    users = selector.xpath('//table/tr/td/a[not(child::img)][not(contains(@href,"attention"))]')
    total = len(users)
    for i in range(0, total):
        name = users[i].text
        sid  = re.match('/([^/]{2,})', users[i].get('href'))
        sid  = sid.group(1) if sid else ''
        uid  = re.search(r'uid=(\d+)', users[i].getparent().getchildren()[-1].get('href')).group(1)
        time = trans_human_time( users[i].getnext().xpath('following-sibling::text()')[0], None)
        rows.append( [uid, sid, name, u'', u'', u'', time] )
        sys.stdout.write( '[%X/%X] '%(i+1,total) )
        sys.stdout.write( '%-29s'%(str([uid,sid])[:-1]+',') )
        sys.stdout.write( " u'"+fmt(name+"', ",-15) )
        print( str([u'', u'', time])[1:] )
    return rows

def import_single_user(uid):
    assert( uid.isdigit() )
    url = config['wap']['import']%uid
    headers['Referer'] = url.replace('act=addbc&', '')
    r = r302 = requests.get(url, headers=headers, allow_redirects=False)
    return r.status_code
    if r.status_code == 302:
        selector = fetch_html( 'https://weibo.cn'+r302.headers['Location'] )
        r = None
        result = selector.xpath('//div[@class="ps"]/text()')
        if len(result)>0:
            return result[0]
        return r302.headers['Location']
    return r.status_code

def remove_single_user(uid):
    assert( uid.isdigit() )
    url = config['wap']['remove']%uid
    headers['Referer'] = url.replace('act=delbc&','').replace('rl=0&','').replace('&st=','&rl=&st=')
    r = r302 = requests.get(url, headers=headers, allow_redirects=False)
    if r.status_code == 200:
        selector = etree.HTML(r.content)
        result = selector.xpath('//div[@class="ps"]/text()')
        if len(result)>0: print( result[0] )
    return r.status_code

def gen_user_processor(args, config, follow_me_only=False):
    user_processed = set()
    def proc(user):
        if follow_me_only and not user['follow_me']: return
        if user.get('following',False): return
        if str(user['id']) in user_processed: return
        user_processed.add( str(user['id']) )
        print( user['id'] )
    return proc

def calcula_okamoto(users, config={}, args=None):
    count = dict(zip(range(11),u'无单双三四五六七八九十'))
    badge = lambda i: ((count[i] if 0<=i<=10 else u'超')+u'冈').removeprefix(u'无冈')
    if isinstance(users, int): return badge(users)
    return badge( len([1 for user in users if str(user['id']) in config['dogs']]) )

def web_load(func):
    def wrapper(path):
        if path in (None, '', 'https:///'):
            path = 'https://raw.githubusercontent.com/bGN4/Sherlock/master/weibo.csv'
        if not re.match(r'(http|ftp)s?://', path):
            return func(path)
        ((f,path), url) = (tempfile.mkstemp(suffix='.csv'), path)
        os.close(f)
        try:
            print( 'Download: %s'%url )
            content = requests.get(url).content
            with open(path, 'wb') as f:
                f.write( content )
            print( 'Tempfile: %s'%path )
        except Exception as e:
            os.remove(path)
            if not type(e).__module__.startswith('requests.'):
                raise
            print(u'下载失败，请稍后再试或改为使用本地文件。(%s)'%type(e).__name__)
            print(u'小提示：食用佛跳墙增加智力后下载成功率会大大提高～')
        result = func(path)
        os.remove(path)
        return result
    return wrapper

@web_load
def do_load(path):
    if not os.path.exists(path): return (None, None)
    print( 'Loading: ' + path )
    (rows, maps, lines) = ([], {}, 0)
    with open(path, encoding='utf-8') as f:
        for row in csv.reader(f):
            lines += 1
            if not row[0].isdigit() and lines>1:
                print( f'Skip line {lines}: {row}' )
                continue
            maps[row[0]] = len(rows)
            rows.append(row)
    print( f'========== Loaded {len(rows)} rows from {lines} lines ==========' )
    assert( len(rows)==len(maps) )
    return (rows, maps)

def do_load_following(args, config):
    with open(args.follow, encoding='utf-8') as f:
        return {r[0]:r[1].split(',') for l in f.readlines() if len(r:=l.strip().split(':'))==2}

def do_remove_shield(uid, args, config):
    assert( uid.isdigit() )
    url = config['wap']['remove']%uid
    h = config['headers'].copy()
    h['Referer'] = url.replace('act=delbc&','').replace('rl=0&','').replace('&st=','&rl=&st=')
    r = Web.fetch_resp(url, headers=h)
    if r.status_code == 200:
        selector = etree.HTML(r.content)
        result = selector.xpath('//div[@class="ps"]/text()')
        if len(result)>0: return (r.status_code, result[0])
    return (r.status_code, (r.headers.get('Set-Cookie','').split('WEIBOCN_FROM=')+[''])[1].split(';')[0])

def do_fetch_shield_operation(uid, config, ban=''):
    body = Web.fetch_resp('https://weibo.cn/%s/operation?rl=0'%uid, headers=config['headers']).content
    delb = re.findall(b'<a href="/attention/delb?(.*?)">', body)
    if not delb:
        addb = re.findall(b'<a href="/attention/addb?(.*?)">', body)
        dead = re.findall(b'<div class="ps">(.*?)</div>', body)
        if addb:
            print( uid, 'not in blacklist', ban )
        if dead:
            info = Web.fetch_resp('https://weibo.cn/%s/info'%uid, headers=config['headers']).content
            print( uid, dead[0].decode(), ('?'*5,ban or '!'*5)[b'User does not exists' in info] )
        if not (addb or dead):
            print( uid, 'link not found', ban )
        return False
    return True

def do_fetch_user_latest(uid, args, config):
    selector = fetch_html( config['wap']['domain'] + uid )
    status = selector.xpath('/html/body/div[@class="me"]/text()')
    if status:
        print( uid, status )
        return ''
    name = selector.xpath('//div[@class="u"]/table//span[@class="ctt"][child::a]/text()')[0]
    date_list = list(map(trans_human_time, selector.xpath('//div[@class="c"][@id]//span[@class="ct"]/text()')))
    latest = max(date_list) if date_list else '-'
    print( uid, latest, name )
    return latest

def do_fetch_user_follow_by_tags(uid, args, config, tags=[], proxy=None, page_max=10):
    dogs, hits, users = config['dogs'], [], []
    if not tags: tags = ['total'] + ['1042015:tagCategory_'+g for g in ('060','007')]
    following = FollowingLite(uid, config, args, proxy=proxy, quiet=not args.debug, batch=True, page_max=page_max)
    firstpage = list(itertools.islice(following, 1))
    categories = following.get_tags()
    for tag in tags:
        count = categories.get(tag, -1)
        if tag=='total' and count>20*page_max: continue
        follow = FollowByTagLite(uid, tag, config, args, proxy=proxy, quiet=not args.debug, batch=True, page_max=page_max)
        if tag=='total': follow = itertools.chain(firstpage, following)
        elif count>0: follow.total, follow.page_all = count, math.ceil(count/20)
        for batch in follow:
            filtered = [user for user in batch if str(user['id']) in config['dogs']]
            hits.extend(filtered)
            users.extend(batch)
            for i,u in enumerate(filtered, 1):
                if not args.debug: break
                print('%3d/%-3d'%(len(hits)-len(filtered)+i,len(users)), uid, u['id'], u['screen_name'])
            logging.error(45*' '+f'{tag} %d/%d/%s'%(len(hits),len(users),categories.get('total')))
            if len(hits)>10: break
        if tag=='total' or len(hits)>10: break
    return hits, users

def do_fetch_user_info_wap(uid, args, config):
    selector = fetch_html( config['wap']['profile'].replace('%s',uid) )
    result = selector.xpath('//div[@class="c"]/text()') + ['']*4
    exists = selector.xpath('//div[@class="ps"]/text()') + ['']
    return dict(
        idstr = uid,
        screen_name = result[1][3:],
        domain = result[-4][result[-4].find('cn/')+3:],
        msg = u'已封号' if 'does not exists' in exists[0] else '',
        src = u'微博监督员'
    )

def do_fetch_user_info_web(uid, args, config):
    assert( uid.isdigit() )
    h = config['headers'].copy()
    h.update({
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': config['web']['domain'] + uid,
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36'
    })
    r = Web.fetch_resp(config['web']['profile']%uid, headers=h)
    if args.debug: print( colored(r.headers['Location'] if r.status_code==302 else r.content) )
    if r.status_code == 200 and 'data' in r.json():
        return r.json()['data']['user'] | dict(msg='')
    if b'Bad Request' in r.content:
        return dict(idstr=uid, screen_name='', msg='Bad Request')
    location = r.headers['Location'] if r.status_code==302 else r.json().get('url') or r.json().get('msg') or r.json().get('message')
    msg = urllib.parse.unquote(location)
    note = (list(filter(lambda k:config['exist'][k] in msg,config['exist'])) + [u'已封号'])[0]
    reason = msg.split('msg=')[1].split('&')[0].removeprefix(u'该账号因') if 'msg=' in msg else msg
    return dict(idstr=uid, msg=note, screen_name=reason.removesuffix(u'的相关规定，现已无法查看。查看帮助') )

def do_fetch_user_info_lite(uid, args, config):
    data = fetch_json( config['lite']['summary'].replace('%s',uid) )
    if data.get('ok')==1: return data['data']['userInfo'] | dict(idstr=uid, msg='')
    return (data if 'msg' in data else data | dict(msg='')) | dict(idstr=uid, screen_name='')

def do_reverse(path, backup):
    os.rename(path, backup)
    with open(path,'wb') as asc, open(backup,'rb') as desc:
        lines = desc.readlines()
        asc.writelines( reversed(lines) )
        print( '========== Reverse all %d records with timeline. =========='%len(lines) )
    os.remove(backup)

def do_read_ids(args, config):
    maps = {}
    for id in ('uid', 'mid'):
        if len(getattr(args,id))!=1: continue
        path = getattr(args,id)[0]
        if not os.path.isfile(path): continue
        print( f'{id} file mode: {path}' )
        getattr(args,id).clear()
        for row in map(str.split, filter(str.__len__, map(str.strip, open(path, encoding='utf-8').readlines()))):
            if not row[0].isalnum(): continue
            if len(row)>1: maps[row[0]] = row[1]
            getattr(args,id).append(row[0])
    return maps

def sb_wrong(args, config):
    print('Bad command')

def sb_test(args, config):
    for i,item in enumerate(Paginator(), 1):
        if item in (37,38,39,40,48,49) or 21<item<30: continue
        print(item, colored('<<<<====@@@@####%%%%&&&&====>>>>', item))

def sb_proxy(args, config):
    print('TODO')

def sb_follow(args, config):
    print('TODO')

def sb_mblog(args, config):
    _ = do_read_ids(args, config)
    for i,item in enumerate(MicroBlogWap(args.uid[0], config, args, page_max=args.pages, page=1-1), 1):
        print('# %d'%i, colored(str(item),93))
        args.mid = [item]
        sb_interact(args, config)

def sb_comment_wap(args, config):
    (rows, maps) = do_load(args.file)
    bid = args.mid[0]
    path = os.path.join( os.path.abspath(os.curdir), bid+'.log' )
    with open(path, ('w','wb')[PY2], **(({'newline':'','encoding':'utf-8'},{})[PY2])) as f:
        for i,lines in enumerate(CommentsWap(args.mid[0], config, args), 1):
            f.writelines( [j for i in zip(lines,itertools.repeat('\n',10)) for j in i] )

def sb_comment(args, config):
    text = lambda s: s[:s.find('<')][:28]
    name = lambda s: fmt(s[:s.find('(')],-16) if s[-1]==')' else s[:s.find('(')]+colored(s[s.find('('):])
    namex = lambda u: fmt(u['screen_name']+'(%s)'%'/'.join([str(u.get(k,'-')) for k in ('follow_count','followers_count','statuses_count','gender')]),-16)
    number = lambda n,m: (('%'+'%dd'%m)%n).replace(' ','─').removesuffix(str(n))[:-1]+' '+colored(str(n),35)
    province = lambda s: fmt(s.removeprefix(u'来自'),3)
    proc = gen_user_processor(args, config)
    for i,x in enumerate(CommentsLite(args.mid[0], config, args), 1):
        replies = (x['comments'] or []) if x['total_number']<=2 else RepliesLite(x['id'], config, args, quiet=True)
        if not args.debug: proc(x['user'])
        else: print('├─'+number(i,4),'%3d'%x['total_number'],x['user']['id'],province(x['source']),name(namex(x['user'])),text(x['text']))
        for j,y in enumerate(replies,1):
            if not args.debug: proc(y['user'])
            else: print('│    ├─'+number(j,3),y['user']['id'],province(y['source']),name(namex(y['user'])),text(y['text']))

def sb_repost(args, config):
    name = lambda s: fmt(s[:s.find('(')],-16) if s[-1]==')' else s[:s.find('(')]+colored(s[s.find('('):])
    namex = lambda u: fmt(u['screen_name']+'(%s)'%'/'.join([str(u.get(k,'-')) for k in ('follow_count','followers_count','statuses_count','gender')]),-16)
    province = lambda s: fmt(s.removeprefix(u'发布于 '),3)
    proc = gen_user_processor(args, config)
    for i,x in enumerate(RepostsLite(args.mid[0], config, args), 1):
        if not args.debug: proc(x['user']) # x['bid']
        else: print(colored('%3d'%i,35),'%10s'%x['user']['id'],province(x['region_name']),name(namex(x['user'])),fmt(x['source'],-10),x['raw_text'][:20])

def sb_like(args, config):
    relation = lambda u: colored(fmt('(%d/%s)'%(u['friends_count'],u['followers_count']),-5))
    proc = gen_user_processor(args, config)
    for i,x in enumerate(LikesLite(args.mid[0], config, args), 1):
        if not args.debug: proc(x['user'])
        else: print(colored('%3d'%i,35),fmt(x['created_at'],-5),'%10s'%x['user']['id'],fmt(x['user']['screen_name'],-16),relation(x['user']),x['source'])

def sb_interact(args, config):
    sb_comment(args, config)
    sb_repost(args, config)
    sb_like(args, config)

def sb_guard(args, config):
    print('TODO')

def sb_verify(args, config):
    (rows, maps) = do_load(args.file)
    names = do_read_ids(args, config)
    for i,uid in enumerate(args.uid, 1):
        if uid in maps: continue
        hits, _ = do_fetch_user_follow_by_tags(uid, args, config)
        print(colored('%3d'%i,35), '%2d'%len(hits), uid, names.get(uid,'-'))

def sb_alive(args, config):
    _ = do_read_ids(args, config)
    for i,(uid,sleep) in enumerate( iter_pause(args.uid,quiet=args.quiet), 1 ):
        user = do_fetch_user_info_web(uid, args, config)
        if False and user['msg'] == 'Bad Request':
            user = do_fetch_user_info_wap(uid, args, config)
        print( '{u[idstr]},{u[screen_name]},,,（{u[msg]}）,'.format(u=user).replace('（）','') )
        sleep()

def sb_pop(args, config):
    start, count = max(int(args.uid[0]),1), args.pages or 1
    with open(args.file,encoding='utf-8') as f, open('weibo.add.csv','w',encoding='utf-8',newline='') as o:
        writer = csv.writer(o)
        for i, line in enumerate(itertools.islice(f, start-1, start-1+count), start):
            row = line.strip().split(',')
            uid, ban = row[0], 'baned' if re.search(u'已封号', line) else ''
            user = dict(zip(['idstr','domain','screen_name','','src','msg','time'],row))
            if not uid.isdigit(): continue
            if i>start: random_pause(3, 7)
            code, msg, is_black = 0, '', do_fetch_shield_operation(uid, config, ban)
            if is_black: (code, msg) = do_remove_shield(uid, args, config)
            if code != 302 or msg != 'deleted' or not is_black:
                user = do_fetch_user_info_web(uid, args, config)
            row[-2] = (u'（%s）'%user['msg']).replace(u'（）','')
            writer.writerow(row)
            print( uid, '%6d'%i, code, '%5s'%ban, row[-2], msg )

def sb_remove(args, config):
    _ = do_read_ids(args, config)
    for (uid,sleep) in iter_pause(args.uid):
        (code, msg) = do_remove_shield(uid, args, config)
        print( uid, code, msg )
        sleep()
    num = get_block_num( fetch_html( config['wap']['export'].split('&',1)[0] ) )
    print( '%d/5000'%num )

def sb_clean(args, config):
    selector = fetch_html( config['wap']['export'].split('?',1)[0] )
    cfg_update_st(get_param_st(selector), config)
    page_all = args.pages if args.pages>0 else get_page_num(selector)
    for i,row in enumerate(BlockingWap(config, args, page=page_all+1, step=-1), 1):
        break
        (code, msg) = do_remove_shield(row[0], args, config)
        print( row[0], code, msg )
        time.sleep(1.3)

def sb_merge(args, config):
    (rows_base, maps_base) = do_load(args.file)
    (rows_add, maps_add) = do_load(args.append)
    (rows_new, maps_new) = ([], {})
    for row in rows_add:
        index = maps_base.get(row[0])
        if index is not None:
            if rows_base[index][0] == row[0]:
                if row[-1] and row[-1] != rows_base[index][-1]:
                    print( 'Update @{} from {} to {}'.format(row[0],rows_base[index][-1],row[-1]) )
                    rows_base[index][-1] = row[-1]
                if len( set([rows_base[index][-2],row[-2],'']) ) > 2:
                    print( 'Skip @{} from {} to {}'.format(row[0],rows_base[index][-2],row[-2]) )
                elif row[-2] and not rows_base[index][-2]:
                    print( 'Update @{} from {} to {}'.format(row[0],rows_base[index][-2],row[-2]) )
                    rows_base[index][-2] = row[-2]
            else:
                print( 'Broken data: ({},{}!={})'.format(index,rows_base[index][0],row[0]) )
        else:
            rows_new.append(row)
    rows_base.extend(sorted(rows_new, key=lambda x:datetime.datetime.strptime(x[-1],'%Y-%m-%d %H:%M:%S')))
    with open(args.file, ('w','wb')[PY2], **(({'newline':'','encoding':'utf-8'},{})[PY2])) as f:
        writer = csv.writer(f)
        writer.writerows(rows_base)
    print( f'========== Merge {len(maps_base)} + {len(maps_add)} => {len(rows_base)} ==========' )

def sb_export(args, config):
    """Share Blocking Records Export"""
    path = args.file
    (update, _) = do_load(path)
    if update is not None: path = args.append = args.file + '.tmp'
    with open(path, ('w','wb')[PY2], **(({'newline':'','encoding':'utf-8'},{})[PY2])) as f:
        writer = csv.writer(f)
        for i,row in enumerate(BlockingWap(config, args, page_max=args.pages, page=1-1), 1):
            writer.writerow( row )
    if not args.desc: do_reverse(path, path+'.desc')
    if update is not None: sb_merge(args, config)
    if os.path.exists(args.append): os.remove(args.append)

def sb_import(args, config):
    """Share Blocking Records Import"""
    (rows, maps) = do_load(args.load)
    (add, count, total) = (0, 0, len(rows))
    selector = fetch_html( config['wap']['export'].split('&',1)[0] )
    latest = (export_single_page(selector)+[None])[0]
    index = maps[latest[0]] if latest is not None else -1
    for (i,row) in enumerate(rows):
        count += 1
        if i<=index or 'uid'==row[0] or row[-1]<'2013': continue
        if True or add>0: time.sleep(random.randint(3,9))
        sys.stdout.write( '[%d/%d] Blocking @%s'%(i+1,total,row[0]) )
        result = import_single_user(row[0])
        print( '\t(%s)'%result )
        add += 1
    print( f'========== Finish process {add}/{count} user. ==========' )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', help='export/import/merge/remove/comment/repost/like')
    parser.add_argument('-C', default='config.json', help='(default: config.json)', metavar='FILE', dest='config')
    parser.add_argument('-O', default='weibo.csv', help='export csv file (default: weibo.csv)', dest='file')
    parser.add_argument('-I', default='https:///', help='import csv file', metavar='',     dest='load')
    parser.add_argument('-A', default='',          help='append csv file', metavar='FILE', dest='append')
    parser.add_argument('-F', default='',          help='follow database', metavar='FILE', dest='follow')
    parser.add_argument('-E', default='',          help='exclude uid/mid', metavar='FILE', dest='exclude')
    parser.add_argument('-P','--proxy', default='',help='proxy pool',      metavar='')
    parser.add_argument('-N', default=0, type=int, help='how many pages/count', dest='pages')
    parser.add_argument('-M', default=[], nargs='+', help='mid list or file', metavar='MID', dest='mid')
    parser.add_argument('-U', default=[], nargs='+', help='uid list or file', metavar='UID', dest='uid')
    parser.add_argument('--desc',    action='store_true', help='keep desc timeline without reverse')
    parser.add_argument('--debug',   action='store_true', help='print more information')
    parser.add_argument('--quiet',   action='store_true', help='print less information')
    parser.add_argument('--dry-run', action='store_true', help='do not perform actions')
    parser.add_argument('--cookie', default='', help='cookie string or cookie file', metavar='')
    args = parser.parse_args()
    with open(args.config, encoding='utf-8') as f:
        config = json.loads(f.read())
    headers = config['headers']
    if args.command in ('follow',):
        g_proxies.put( dict(uri=None) )
        do_load_proxy(args, config, True)
    elif args.command in ('okamoto',): pass
    else: assert( config['headers']['User-Agent'] and config['headers']['Cookie'] )
    if args.command in ('import', 'remove', 'pop'):
        cfg_update_st(get_param_st_raw(config), config)
    globals().get('sb_{args.command}'.format(args=args),sb_wrong)(args, config)


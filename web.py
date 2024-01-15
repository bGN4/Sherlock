import os
import csv
import uuid
import logging
import tornado.web
from tornado import gen, httpclient

SECRET_KEY = str(uuid.uuid4())
DB_WEIBO = {}

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('./hostingstart.html')

class WeiboHandler(tornado.web.RequestHandler):
    def get(self, s):
        user = DB_WEIBO.get(s, {})
        if not user:
            self.set_status(404)
        self.finish( user )

    def head(self, s):
        if s not in DB_WEIBO:
            self.set_status(404)
        self.finish()

    def post(self, s):
        payload = {} # tornado.escape.json_decode(self.request.body)
        self.finish('TODO')

class ProxyHandler(tornado.web.RequestHandler):
    async def get(self, scheme, host):
        url = self.request.uri.replace(f'/api/proxy/{scheme}/{host}',f'{scheme}://{host}')
        h = {k:v for k,v in self.request.headers.items() if k.lower() not in ('host','connection','auth')}
        if h.pop('Authorization','$').split()[-1] != os.environ.get('AUTH_TOKEN',SECRET_KEY):
            raise tornado.web.HTTPError(404)
        r = await httpclient.AsyncHTTPClient().fetch(url, headers=h, raise_error=True)
        for k,v in r.headers.items():
            if k.lower() in ('content-length','transfer-encoding'): continue
            self.set_header(k, v)
        self.set_status(r.code)
        self.finish(r.body)

def do_load():
    path, db = 'db.csv', {}
    try:
        with open(path, 'wb') as f:
            url = 'https://raw.githubusercontent.com/bGN4/Sherlock/master/weibo.csv'
            f.write( __import__('urllib',{},{},['request']).request.urlopen(url).read() )
    except:
        path = 'weibo.csv'
    with open(path, encoding='utf-8', newline='') as f:
        count = 0
        for row in csv.DictReader(f):
            row['link'] = ['https://weibo.com/u/%s'%row[k] for k in ('uid','alias') if row[k]]
            if row['alias']: db[row['alias']] = row
            db[row['uid']] = row
            count += 1
        print( '[%d/%d] %s'%(len(db),count,path) )
    return db

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    logging.basicConfig(level=20, format='[%(asctime).19s] %(message)s')
    logging.getLogger('tornado.access').level = 10
    DB_WEIBO = do_load()
    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/weibo/(\w+)", WeiboHandler),
        (r"/api/proxy/(\w+)/([\w.\d]+)/.*", ProxyHandler),
    ], autoreload=True)
    app.listen(int(os.environ.get('HTTP_PLATFORM_PORT','10086')), '127.0.0.1')
    tornado.ioloop.IOLoop.current().start()


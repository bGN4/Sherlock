import os
import csv
import logging
import tornado.web


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
        payload = tornado.escape.json_decode(self.request.body)
        self.finish('TODO')


if __name__ == '__main__':
    global DB_WEIBO
    DB_WEIBO = dict()
    with open('weibo.csv', encoding='utf-8', newline='') as f:
        count = 0
        for row in csv.DictReader(f):
            row['link'] = ['https://weibo.com/u/%s'%row[k] for k in ('uid','alia') if row[k]]
            if row['alia']: DB_WEIBO[row['alia']] = row
            DB_WEIBO[row['uid']] = row
            count += 1
        print( '[%d/%d] weibo.csv'%(len(DB_WEIBO),count) )
    logging.basicConfig(level=20, format='[%(asctime).19s] %(message)s')
    logging.getLogger('tornado.access').level = 10
    app = tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/weibo/(\w+)", WeiboHandler),
    ], autoreload=True)
    app.listen(int(os.environ.get('HTTP_PLATFORM_PORT','10086')), '127.0.0.1')
    tornado.ioloop.IOLoop.current().start()


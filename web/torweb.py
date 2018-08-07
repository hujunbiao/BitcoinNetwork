import json
import tornado.ioloop
import tornado.web
from tornado.httpclient import AsyncHTTPClient

import db

MAX_TRY_COUNT = 3


class ReportHandler(tornado.web.RequestHandler):
    def post(self):
        global version_counter
        ip = self.get_body_argument('ip')
        port = self.get_body_argument('port')
        rtype = self.get_body_argument('type')
        if rtype == 'new':
            tornado.ioloop.IOLoop.current().spawn_callback(resolve, ip, port, 0)
        elif rtype == 'version':
            version = self.get_body_argument('version')
            services = self.get_body_argument('services')
            agent = self.get_body_argument('agent')
            tornado.ioloop.IOLoop.current().spawn_callback(update_version, ip, agent, version, services)
            
        self.write("ok")


def make_app():
    return tornado.web.Application([
        (r"/bitcoin_network/report", ReportHandler)
    ])


async def resolve(ip, port, count):
    if count == 0:
        with db.DB.cursor() as cursor:
            cursor.execute(db.INSERT_ADDR_TABLE_IP_SQL, (ip, port))

    await tornado.gen.sleep(0.2 * count)
    http_client = AsyncHTTPClient()
    try:
        rsp = await http_client.fetch('http://ip.taobao.com/service/getIpInfo.php?ip={}'.format(ip))
        body = rsp.body.decode('utf-8')
        data = json.loads(body.strip())
        if data['code'] == 0:
            data = data['data']
            country = data['country'] if data['country'] != 'XX' else ''
            region = data['region'] if data['region'] != 'XX' else ''
            city = data['city'] if data['city'] != 'XX' else ''

            with db.DB.cursor() as cursor:
                cursor.execute(db.UPDATE_ADDR_TABLE_GEO_SQL, (country, region, city, ip))
                cursor.close()
            db.DB.commit()
    except BaseException:
        if count < MAX_TRY_COUNT:
            tornado.ioloop.IOLoop.current().spawn_callback(resolve, ip, port, count+1)


async def update_version(ip, agent, version, services):
    with db.DB.cursor() as cursor:
        cursor.execute(db.UPDATE_ADDR_TABLE_VERSION_SQL, (agent, version, services, ip))
    db.DB.commit()

def start():
    db.init_db()
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    start()

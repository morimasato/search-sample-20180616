# -*- coding: utf-8 -*-

import os
import re
import json
import logging
import jinja2
import webapp2

from google.appengine.api import search

class CreateHandler(webapp2.RequestHandler):
    def get(self):
        # READ JSON DATA
        f = open(os.path.dirname(__file__) + '/data.json')
        gnavi = json.loads(f.read())
        if 'rest' in gnavi:
            for rest in gnavi['rest']:
                id = rest['id']
                try:
                    # CREATE INDEX
                    index = search.Index(name='sample')
                    create_document = search.Document(
                        doc_id=id,
                        fields=[
                            search.TextField(name='name', value=rest['name']),
                            search.TextField(name='content', value=rest['pr']['pr_long']),
                            search.TextField(name='image', value=rest['image_url']['shop_image1']),
                            search.TextField(name='address', value=rest['address']),
                            search.TextField(name='tel', value=rest['tel']),
                            search.TextField(name='mobile_coupon', value=rest['flags']['mobile_coupon']),
                            search.GeoField(name='location', value=search.GeoPoint(latitude=float(rest['latitude']),
                                                                                   longitude=float(rest['longitude'])))
                        ]
                    )
                    index.put(create_document)
                except Exception, e:
                    logging.exception("#-- CreateHandler Exception: id:%s exception:%s" % (id, e))

        self.redirect('/')

class SearchHandler(webapp2.RequestHandler):
    def get(self):
        # QUERY STRING
        q = self.request.get('q', default_value='')
        mobile_coupon = self.request.get('mobile_coupon', default_value='')
        latlong = self.request.get('latlong', default_value='')

        results = []
        number_found = 0
        try:
            index = search.Index(name='sample')
            # 位置情報で並び替え
            expressions = []
            if latlong:
                expressions.append(
                    search.SortExpression(
                        expression='distance(location, geopoint(%s))' % latlong,
                        direction=search.SortExpression.ASCENDING,
                        default_value=None
                    )
                )
            # ソートキーの設定
            sort_opts = search.SortOptions(
                match_scorer=search.MatchScorer(),
                expressions=expressions
            )

            # 結果フィールドの設定
            options = search.QueryOptions(
                limit=100,
                returned_fields=['name', 'content', 'image', 'address', 'tel', 'location'],
                snippeted_fields=['content'],
                sort_options=sort_opts,
                number_found_accuracy=10000,
                cursor=None
            )

            # 検索クエリの編集
            query_string = u''
            if q:
                query_string = u'(content:(%s) OR name:(%s))' % (q, q)
            if mobile_coupon:
                query_string += u' mobile_coupon:(%s)' % (mobile_coupon)

            # 検索実行
            query = search.Query(query_string=query_string, options=options)
            documents = index.search(query)

            # 検索結果
            number_found = documents.number_found
            for document in documents:
                # スニペット編集
                expressions = []
                for expression in document.expressions:
                    expressions.append(expression.value)
                results.append({
                    'doc_id': document.doc_id,
                    'name': document.field('name').value,
                    'content': document.field('content').value,
                    'image': document.field('image').value,
                    'snippet': ''.join(expressions),
                    'address': document.field('address').value,
                    'tel': document.field('tel').value
                })
            # logging.info("#-- SearchHandler : results:%s" % (results))

        except Exception, e:
            logging.exception("#-- SearchHandler Error: id:%s exception:%s" % (id, e))

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render({
            'q': q,
            'mobile_coupon': mobile_coupon,
            'latlong': latlong,
            'results': results,
            'number_found': number_found
        }))

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')),
    extensions=['jinja2.ext.autoescape'], autoescape=True)

app = webapp2.WSGIApplication([
    ('/create', CreateHandler),
    ('/', SearchHandler)
], debug=True)

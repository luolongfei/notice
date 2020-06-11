#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
@author mybsdc <mybsdc@gmail.com>
@date 2020/6/9
@time 13:50
"""

import os
import re
import time
import datetime
import ssl
import traceback
import smtplib
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import requests
from pyquery import PyQuery as pq
from lxml import etree
from dotenv import load_dotenv


def catch_exception(origin_func):
    def wrapper(self, *args, **kwargs):
        """
        用于异常捕获的装饰器
        :param origin_func:
        :return:
        """
        try:
            return origin_func(self, *args, **kwargs)
        except AssertionError as ae:
            print('参数错误：{}'.format(str(ae)))
        except Exception as e:
            print('出错：{} 位置：{}'.format(str(e), traceback.format_exc()))
        finally:
            pass

    return wrapper


class Notice(object):
    symbol_regex = re.compile('{(?!})|(?<!{)}')

    def __init__(self):
        # 加载环境变量
        load_dotenv(verbose=True, override=True, encoding='utf-8')

        self.headers = {
            'Accept-Language': 'zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7,und;q=0.6',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36'
        }
        self.max_timestamp = self.date2timestamp('2020-05-31')

    def __get_all_news(self) -> list:
        r = requests.get('http://www.dykszx.com/index.php?catid=20', headers=self.headers)
        r.encoding = 'utf-8'

        d = pq(r.text)
        li = d('.newslist li')

        news_list = []
        for item in li.items():
            title = item.find('.r b').text()
            date = '{}-{}'.format(item.find('.l i').text(), item.find('.l span').text())
            url = 'http://www.dykszx.com' + item.find('a').attr('href')

            news_list.append({
                'title': title,
                'date': date,
                'timestamp': Notice.date2timestamp(date),
                'url': url
            })

        return news_list

    @staticmethod
    def date2timestamp(date):
        return time.mktime(datetime.datetime.strptime(date, '%Y-%m-%d').timetuple())

    @staticmethod
    def symbol_replace(val):
        real_val = val.group()
        if real_val == '{':
            return '@<@'
        elif real_val == '}':
            return '@>@'
        else:
            return ''

    @staticmethod
    def sendMail(subject: str, content: str or tuple, to=None, template='default') -> None:
        """
        发送邮件
        :param subject:
        :param content:
        :param to:
        :param template:
        :return:
        """
        if not to:
            to = os.getenv('INBOX')

        # 发信邮箱账户
        username = os.getenv('MAIL_USERNAME')
        password = os.getenv('MAIL_PASSWORD')

        # 根据发信邮箱类型自动使用合适的配置
        if '@gmail.com' in username:
            host = 'smtp.gmail.com'
            secure = 'tls'
            port = 587
        elif '@qq.com' in username:
            host = 'smtp.qq.com'
            secure = 'tls'
            port = 587
        elif '@163.com' in username:
            host = 'smtp.163.com'
            secure = 'ssl'
            port = 465
        else:
            raise ValueError(f'「{username}」 是不受支持的邮箱。目前仅支持谷歌邮箱、QQ邮箱以及163邮箱，推荐使用谷歌邮箱。')

        # 格式化邮件内容
        if isinstance(content, tuple):
            with open('./mail/{}.html'.format(template), 'r', encoding='utf-8') as f:
                template_content = f.read()
                text = Notice.symbol_regex.sub(Notice.symbol_replace, template_content).format(*content)
                real_content = text.replace('@<@', '{').replace('@>@', '}')
        elif isinstance(content, str):
            real_content = content
        else:
            raise TypeError(f'邮件内容类型仅支持 list 或 str，当前传入的类型为 {type(content)}')

        # 邮件内容分为多段
        msg = MIMEMultipart('alternative')

        msg['From'] = formataddr(('Im Robot', username))
        msg['To'] = formataddr(('', to))
        msg['Subject'] = subject

        # 添加网页
        page = MIMEText(real_content, 'html', 'utf-8')
        msg.attach(page)

        # 添加 html 内联图片
        with open('mail/images/ting.jpg', 'rb') as img:
            avatar = MIMEImage(img.read())
            avatar.add_header('Content-ID', '<avatar>')
            msg.attach(avatar)

        with smtplib.SMTP_SSL(host=host, port=port) if secure == 'ssl' else smtplib.SMTP(host=host,
                                                                                         port=port) as server:
            # 启用 tls 加密，优于 ssl
            if secure == 'tls':
                server.starttls(context=ssl.create_default_context())

            server.login(username, password)
            server.sendmail(from_addr=username, to_addrs=to, msg=msg.as_string())

    @catch_exception
    def run(self):
        all_news = self.__get_all_news()
        real_news = list(filter(lambda item: item['timestamp'] > self.max_timestamp and '教师' in item['title'], all_news))

        for n in real_news:
            print(n['title'])
        # 公告已经出了，故此脚本没用了，后期可以在这个基础上改造


if __name__ == '__main__':
    notice = Notice()
    notice.run()

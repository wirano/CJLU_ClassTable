import os
import sys
import json
import re
from datetime import datetime, timedelta
import getopt
from getpass import getpass

import requests

sys.path.insert(1, sys.path[0] + '/pyrsa')
from PyRsa.pyrsa import RsaKey
from PyRsa.pyb64 import Base64


class Jwxt(object):
    def __init__(self, domain, student_number, pwd):
        self.__ua = 'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.2 (KHTML, like Gecko) Chrome/22.0.1216.0 Safari/537.2'
        self.__domain = domain
        self.__student_number = student_number
        self.session = requests.session()

        self.__csrf_token = self.__get_csrf_token()
        self.__modulus, self.__exponent = self.__get_public_key()
        self.__cookies = self.__get_jsessionid(pwd)

    def __get_public_key(self):
        url = f'https://{self.__domain}/xtgl/login_getPublicKey.html'

        headers = {
            'Host': self.__domain,
            'User-Agent': self.__ua,
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'X-Requested-With': 'XMLHttpRequest',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': f'https://{self.__domain}/xtgl/login_slogin.html',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin'
        }

        res = self.session.get(url, headers=headers)
        res_json = res.json()
        return res_json.get('modulus'), res_json.get('exponent')

    def __get_csrf_token(self):
        url = f'https://{self.__domain}/xtgl/login_slogin.html'

        headers = {
            'Host': self.__domain,
            'User-Agent': self.__ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
        }

        res = self.session.get(url, headers=headers)
        csrf_line = re.findall(r"value=\"[0-9a-z\-,]+\"", res.text)
        csrf = re.findall(r"[0-9a-z\-,]+", csrf_line[0])
        return csrf[1]

    def __get_jsessionid(self, pwd):
        rsakey = RsaKey()
        rsakey.set_public(Base64().b64tohex(self.__modulus), Base64().b64tohex(self.__exponent))
        rr = rsakey.rsa_encrypt(pwd)
        enpsw = Base64().hex2b64(rr)

        data = {
            'csrftoken': self.__csrf_token,
            'yhm': self.__student_number,
            'mm': enpsw
        }
        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;'
                      'q=0.8,application/signed-exchange;v=b3',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Content-Length': '470',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Host': self.__domain,
            'Origin': f'https://{self.__domain}',
            'Referer': f'https://{self.__domain}/xtgl/login_slogin.html',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': self.__ua
        }
        url = f'https://{self.__domain}/xtgl/login_slogin.html'

        res = self.session.post(url, headers=headers, data=data)
        if len(res.history) and res.history[0].status_code == 302:
            cookies = requests.utils.dict_from_cookiejar(res.history[0].cookies)
            return cookies

    def dump_class_json(self, academic_year, term):
        term_map = {'1': '3', '2': '12', '3': '16'}

        url = f'https://{self.__domain}/kbcx/xskbcx_cxXsKb.html?gnmkdm=N2151&su={self.__student_number}'
        headers = {
            'Host': f'{self.__domain}',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:91.0) Gecko/20100101 Firefox/91.0',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': f'https://{self.__domain}',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Referer': f'https://{self.__domain}/kbcx/xskbcx_cxXskbcxIndex.html?gnmkdm=N2151&layout=default&su={self.__student_number}',
            'Cookie': f"dptech={self.__cookies['dptech']}; JSESSIONID={self.__cookies['JSESSIONID']}",
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0',
        }
        data = {
            'xnm': academic_year,
            'xqm': term_map[term],
            'kzlx': 'ck'
        }

        res = self.session.post(url=url, headers=headers, data=data)
        return json.loads(res.text)


class ClassTable(object):
    def __init__(self, start_date):
        self.__start_date = start_date
        self.class_table = []

    def read_class(self, json_obj):
        for i in json_obj['kbList']:
            weeks_group = i.get('zcd').split(',')
            weeks_group = list(map(lambda s: re.findall(r"\d+", s), weeks_group))
            weeks_group = list(map(lambda s: s + s if len(s) == 1 else s, weeks_group))  # 单周补齐list最后一个元素
            weeks_group = list(map(lambda s: list(map(lambda y: int(y), s)), weeks_group))  # str to int
            # 因为套了2层list，最外层map的参数是[[]]（给lambda的参数是[]]），内层map参数是[](给lambda就是单个元素）

            self.class_table.append(dict(name=i.get('kcmc'), start_end_time=i.get('jcs').split('-'),
                                         weekday=int(i.get('xqj')),
                                         week_start_end=weeks_group,
                                         location=i.get('cdmc'), teacher=i.get('xm')))
        return self.class_table

    def cal_gen(self, file_name):
        begin_time = {'1': timedelta(hours=8, minutes=0), '2': timedelta(hours=8, minutes=50),
                      '3': timedelta(hours=10, minutes=0), '4': timedelta(hours=10, minutes=50),
                      '5': timedelta(hours=13, minutes=30), '6': timedelta(hours=14, minutes=20),
                      '7': timedelta(hours=15, minutes=15), '8': timedelta(hours=16, minutes=5),
                      '9': timedelta(hours=18, minutes=0), '10': timedelta(hours=18, minutes=50),
                      '11': timedelta(hours=19, minutes=40)}

        end_time = {'1': timedelta(hours=8, minutes=45), '2': timedelta(hours=9, minutes=35),
                    '3': timedelta(hours=10, minutes=45), '4': timedelta(hours=11, minutes=35),
                    '5': timedelta(hours=14, minutes=15), '6': timedelta(hours=15, minutes=5),
                    '7': timedelta(hours=16, minutes=00), '8': timedelta(hours=16, minutes=50),
                    '9': timedelta(hours=18, minutes=45), '10': timedelta(hours=19, minutes=35),
                    '11': timedelta(hours=20, minutes=25)}

        payload = 'BEGIN:VCALENDAR\nPRODID:-//wirano@github//CJLU ClassTable ' \
                  'Gen//EN\nVERSION:2.0\nCALSCALE:GREGORIAN\nBEGIN:VTIMEZONE\nTZID:Asia/Shanghai\nTZURL:http' \
                  '://tzurl.org/zoneinfo-outlook/Asia/Shanghai\nX-LIC-LOCATION:Asia/Shanghai\nBEGIN:STANDARD' \
                  '\nTZOFFSETFROM:+0800\nTZOFFSETTO:+0800\nTZNAME:CST\nDTSTART:19700101T000000\nEND:STANDARD\nEND' \
                  ':VTIMEZONE'

        for i in self.class_table:
            for j in i['week_start_end']:
                payload += '\nBEGIN:VEVENT\nDTSTAMP:' + datetime.now().strftime("%Y%m%dT%H%M%SZ") + \
                           '\nDTSTART;TZID=Asia/Shanghai:' + \
                           (self.__start_date + timedelta(weeks=j[0] - 1, days=i['weekday'] - 1) + begin_time[
                               i['start_end_time'][0]]).strftime("%Y%m%dT%H%M%S") + \
                           '\nDTEND;TZID=Asia/Shanghai:' + \
                           (self.__start_date + timedelta(weeks=j[0] - 1, days=i['weekday'] - 1) + end_time[
                               i['start_end_time'][1]]).strftime("%Y%m%dT%H%M%S") + \
                           '\nRRULE:FREQ=WEEKLY;COUNT=' + str(j[1] - j[0] + 1) + \
                           '\nSUMMARY:' + i['name'] + \
                           '\nLOCATION:' + i['location'] + \
                           '\nDESCRIPTION:' + i['teacher'] + \
                           '\nBEGIN:VALARM' + '\nTRIGGER:-PT15M' + '\nREPEAT:1' + '\nDURATION:PT1M' + '\nEND:VALARM' + '\nEND:VEVENT'
        payload += '\nEND:VCALENDAR'

        f = open(file_name, 'w')
        f.write(payload)
        f.close()


def main(argv):
    doc = f"Usage: {os.path.basename(sys.argv[0])} <options...>\n" + "    -s, --student_number <student number>    Your student number\n" + "    -d, --start_date <date>                  Term start date(ISO format e.g. 2021-09-06)\n" + "    -o, --output <file name>                 Output file name\n"
    file_name = 'timetable.ics'
    try:
        opts, args = getopt.getopt(argv[1:], "hs:d:o", ["help", "student_number=", "start_date=", "output"])
    except getopt.GetoptError:
        print(doc)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-s', '--student_number'):
            s_num = arg
        elif opt in ('-d', '--start_date'):
            start_date = datetime.fromisoformat(arg)
            if start_date.month > 6:
                term = '1'
                academic_year = str(start_date.year)
            else:
                term = '2'
                academic_year = str(start_date.year - 1)
        elif opt in ('-o', '--output'):
            file_name = arg
        else:
            print(doc)
            sys.exit(0)

    jw = Jwxt('jwxt.cjlu.edu.cn', s_num, getpass('Enter your password:'))
    table = jw.dump_class_json(academic_year, term)
    ct = ClassTable(start_date)
    ct.read_class(table)
    ct.cal_gen(file_name)


if __name__ == '__main__':
    main(sys.argv)

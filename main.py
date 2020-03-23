#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import datetime
import time
import schedule
import threading

import smartmeter
import logging_util

logging_util.configure_logging('logging_config_main.yaml')
logger = logging_util.get_logger(__name__)

CONFIG_FILE = 'config.yaml'
config = None

lock = threading.Lock()
wattPool = []

def dumpEnergyLog(deviceId, date, power, data_dir):
    import json
    message = {}
    message['device_id'] = deviceId
    message['datetime'] = date.strftime('%Y/%m/%d %H:%M:%S')
    message['power'] = power

    record = {}
    record['topic'] = "energy_log/notify"
    record['message'] = message

    filename = "{0}_{1}.json".format(deviceId, date.strftime('%Y-%m-%dT%H:%M:%S'))
    filepath = os.path.join(data_dir, filename)

    with open(filepath, 'w+') as f:
        json.dump(record, f)

def calcWattMinuteScheduleJob():
    now = datetime.datetime.now()
    now = datetime.datetime(now.year, now.month, now.day, now.hour, now.minute, 0)

    lock.acquire()
    global wattPool
    wattMinute = round(0 if len(wattPool) == 0 else sum(wattPool) / len(wattPool), 4)
    wattPool = []
    lock.release()

    logger.info('電力:{0}[W]'.format(wattMinute))
    dumpEnergyLog(0, now, wattMinute, config['general']['data_dir'])

def instantPowerCallback(power, date):
    lock.acquire()
    global wattPool
    wattPool.append(power)
    lock.release()

def integratePowerCallback(power, date):
    logger.info('30分電力量:{0}[kWh]'.format(power))
    dumpEnergyLog(1, date, power, config['general']['data_dir'])    

def load_config(config_path):
    import yaml
    with open(config_path, 'r') as f:
        return yaml.safe_load(f.read())

def main():
    global config
    config = load_config(os.path.join(os.path.dirname(__file__), CONFIG_FILE))

    # スマートメーターとの接続
    smartMeter = smartmeter.smartmeter(config['general'], config['broute'], instantPowerCallback, integratePowerCallback)
    smartMeter.initialize()
    smartMeter.connect()

    # 5秒の毎に瞬時電力を取得する
    schedule.every(5).seconds.do(smartMeter.getInstantPower)

    # 毎分00秒に平均電力値を算出する
    schedule.every(1).minutes.at(":00").do(calcWattMinuteScheduleJob)

    # 昨日一日分の30毎の積算電力を取得する（取りこぼし補完目的）
    schedule.every().day.at("04:00").do(smartMeter.getIntegratePower)
 
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

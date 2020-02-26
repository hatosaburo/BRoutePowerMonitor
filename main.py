#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import datetime
from time import sleep
import CommunicateSmartMeter
import PublishAWSIoTMessage
import schedule

CONFIG_FILE = 'config.yaml'

def getPowerMeasurementScheduleJob(smartMeter, awsIot):
    smartMeter.getPowerMeasurement(awsIot.queueInstantPowerMessage)

def getIntegratePowerScheduleJob(smartMeter, awsIot):
    smartMeter.getIntegratePower(awsIot.queueIntegratePowerMessage)

def publishAwsIotScheduleJob(awsIot):
    awsIot.uploadQueueMessages()

def load_config(config_path):
    import yaml
    with open(config_path, 'r') as f:
        return yaml.safe_load(f.read())

def main():
    config = load_config(os.path.join(os.path.dirname(__file__), CONFIG_FILE))

    # スマートメーターとの接続
    smartMeter = CommunicateSmartMeter.CommunicateSmartMeter(config['general'], config['broute'])
    smartMeter.initialize()
    smartMeter.connect()

    # AWS IoT 接続パラメータの設定
    awsIot = PublishAWSIoTMessage.PublishAWSIoTMessage(config['awsiot'])

    # 毎分00秒の電力を取得する
    schedule.every(1).minutes.at(":00").do(getPowerMeasurementScheduleJob, smartMeter, awsIot)

    # 取得したデータを15分ごとにAWS(DynamoDB)にアップする
    schedule.every().hour.at("00:30").do(publishAwsIotScheduleJob, awsIot)
    schedule.every().hour.at("15:30").do(publishAwsIotScheduleJob, awsIot)
    schedule.every().hour.at("30:30").do(publishAwsIotScheduleJob, awsIot)
    schedule.every().hour.at("45:30").do(publishAwsIotScheduleJob, awsIot)

    # 昨日一日分の30毎の積算電力を取得する
    schedule.every().day.at("00:00").do(getIntegratePowerScheduleJob, smartMeter, awsIot)

    while True:
        schedule.run_pending()
        sleep(1)

if __name__ == "__main__":
    main()



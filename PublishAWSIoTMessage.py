import os
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import logging
import time
import json
import enum
import datetime

class DeviceId(enum.IntEnum):
    SmartMeter_Instant = 0,
    SmartMeter_Integrate = 1

class PublishAWSIoTMessage:

    def __init__(self, config_awsiot, clientId = "hemsController"):
        self.__host = config_awsiot['host']
        self.__rootCAPath = os.path.join(os.path.dirname(__file__), config_awsiot['root_ca'])
        self.__certificatePath = os.path.join(os.path.dirname(__file__), config_awsiot['cert_pem'])
        self.__privateKeyPath = os.path.join(os.path.dirname(__file__), config_awsiot['private_key'])
        self.__clientId = clientId
        self.__messageQueue = []
        # Port defaults
        port = 8883

        # Init AWSIoTMQTTClient
        self.__myAWSIoTMQTTClient = AWSIoTMQTTClient(self.__clientId)
        self.__myAWSIoTMQTTClient.configureEndpoint(self.__host, port)
        self.__myAWSIoTMQTTClient.configureCredentials(self.__rootCAPath, self.__privateKeyPath, self.__certificatePath)

        # AWSIoTMQTTClient connection configuration
        self.__myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
        self.__myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
        self.__myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
        self.__myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
        self.__myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec
    
    def queueInstantPowerMessage(self, power, time):
        message = {}
        message['device_id'] = DeviceId.SmartMeter_Instant
        message['datetime'] = time.strftime('%Y/%m/%d %H:%M:%S')
        message['power'] = power

        record = {}
        record['topic'] = "energy_log/notify"
        record['message'] = message
        self.__messageQueue.append(record)
    
    def queueIntegratePowerMessage(self, powers, date):
        message = {}
        for power in powers:
            message['device_id'] = DeviceId.SmartMeter_Integrate
            message['datetime'] = date.strftime('%Y/%m/%d %H:%M:%S')
            message['power'] = power

            record = {}
            record['topic'] = "energy_log/notify"
            record['message'] = message
            self.__messageQueue.append(record)

            date += datetime.timedelta(minutes=30)

    def uploadQueueMessages(self):

        # Connect to AWS IoT
        self.__myAWSIoTMQTTClient.connect()

        for queue in self.__messageQueue:
            messageJson = json.dumps(queue['message'])
            self.__myAWSIoTMQTTClient.publish(queue['topic'], messageJson, 1)
            print('Published topic %s: %s' % (queue['topic'], messageJson))

        self.__messageQueue.clear()

        self.__myAWSIoTMQTTClient.disconnect()
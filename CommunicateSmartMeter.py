#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import serial
import time
import datetime
import threading
from enum import Enum

class connectStatus(Enum):
    INIT = 0
    SETPASSWORD = 1
    SETACCOUNT = 2
    SCANNETWORK = 3
    SETCHANNEL = 4
    SETPANID = 5
    GETIPADDR6 = 6
    JOINNETWORK = 7
    CONNECTED = 8

class CommunicateSmartMeter():

    def __init__(self, config_general, config_broute):
        self.__ser = None
        self.__rbid = config_broute['account']
        self.__rbpwd = config_broute['password']
        self.__serialPortDev = config_general['serial']
        self.__ipv6Addr = None
        self.__status = connectStatus.INIT

    def __recvSerialPortThread(self):
        scanDuration = 4   # スキャン時間。サンプルでは6なんだけど、4でも行けるので。（ダメなら増やして再試行）
        scanRes = {} # スキャン結果の入れ物
        recvBuffer = b""

        while True:
            recvMessage = self.__ser.readline()
            # print(recvMessage, end="\r\n")

            # \r\nで終わるまで継続して受信データを待つ
            if not recvMessage.endswith(b"\r\n"):
                recvBuffer += recvMessage.rstrip(b"\n")
                continue
            else:
                recvBuffer += recvMessage
                recvMessage = recvBuffer
                recvBuffer = b""

            if recvMessage == self.__sendingCommand:
                # エコーバック受信
                pass

            elif recvMessage == b'OK\r\n':
                if self.__status == connectStatus.SETPASSWORD:
                    # Bルート認証ID設定
                    self.__sendCommand(b"SKSETRBID " + self.__rbid.encode('utf-8') + b"\r\n")
                    self.__status = connectStatus.SETACCOUNT

                elif self.__status == connectStatus.SETACCOUNT:
                    scanDuration = 4   # スキャン時間。サンプルでは6なんだけど、4でも行けるので。（ダメなら増やして再試行）
                    strCommand = "SKSCAN 2 FFFFFFFF " + str(scanDuration) + "\r\n"
                    self.__sendCommand(strCommand.encode(encoding='utf-8'))
                    self.__status = connectStatus.SCANNETWORK

                elif self.__status == connectStatus.SETCHANNEL:
                    self.__sendCommand(b"SKSREG S3 " + scanRes[b"Pan ID"] + b"\r\n")
                    self.__status = connectStatus.SETPANID
                    
                elif self.__status == connectStatus.SETPANID:
                    self.__sendCommand(b"SKLL64 " + scanRes[b"Addr"] + b"\r\n")
                    self.__status = connectStatus.GETIPADDR6

            elif self.__status == connectStatus.SCANNETWORK:
                if recvMessage.startswith(b"  "):
                    # スキャンして見つかったらスペース2個あけてデータがやってくる
                    cols = recvMessage.strip().split(b':')
                    scanRes[cols[0]] = cols[1]

                elif recvMessage.startswith(b"EVENT 22"):
                    # スキャン完了 
                    if b"Channel" in scanRes:
                        self.__sendCommand(b"SKSREG S2 " + scanRes[b"Channel"] + b"\r\n")
                        self.__status = connectStatus.SETCHANNEL
                    else:
                        scanDuration += 1
                        strCommand = "SKSCAN 2 FFFFFFFF " + str(scanDuration) + "\r\n"
                        self.__sendCommand(strCommand.encode(encoding='utf-8'))

            elif self.__status == connectStatus.GETIPADDR6:
                self.__ipv6Addr = recvMessage.strip()
                self.__sendCommand(b"SKJOIN " + self.__ipv6Addr + b"\r\n")
                self.__status = connectStatus.JOINNETWORK

            elif self.__status == connectStatus.JOINNETWORK:
                if recvMessage.startswith(b"EVENT 24") :
                    print("PANA 接続失敗..接続再試行")
                    self.__status = connectStatus.INIT
                    self.connect()
                    
                elif recvMessage.startswith(b"EVENT 25") :
                    self.__status = connectStatus.CONNECTED
                    # 積算電力量の単位を取得する
                    self.__requestPropertyRW(b"\xE1")

            elif self.__status == connectStatus.CONNECTED:
                if recvMessage.startswith(b"ERXUDP") :
                    cols = recvMessage.replace(b"\r\n", b"").split(b' ')
                    res = cols[8]   # UDP受信データ部分
                    seoj = res[4:4+3] # 送信者
                    ESV = res[10:10+1]
                    if seoj == b"\x02\x88\x01":
                        # スマートメーター(028801)から来たなら
                        self.__handleSmartMeterMessage(ESV, res[12:])
    
    def __handleSmartMeterMessage(self, ESV, data):
        while not data == b'':
            EPC = data[0:0+1]
            length = data[1]
            if not len(data[2:]) >= length:
                print(u"不完全データは破棄:{0}".format(data))
                break
            
            if EPC == b"\xE1":
                self.__unit = int.from_bytes(data[2:2+1], 'big')
                # 積算電力収集日を設定する
                self.__requestPropertyRW(b"\xE5", read=False, data=data.to_bytes(1, 'big'))
            elif EPC == b"\xE2":
                # 前日を日付を設定
                date = datetime.datetime.now() - datetime.timedelta(days=int.from_bytes(data[2:2+2], 'big'))
                date = datetime.date(date.year, date.month, date.day)

                # 30分値電力を取得
                data_powers = data[4:]
                powers = []
                while len(data_powers) > 0:
                    powers.append(int.from_bytes(data_powers[0:0+4], 'big'))
                    data_powers = data_powers[4:]
                print(u"積算電力履歴(IN):{0} [{1}]", date, powers)
                self.__callbackE2(powers, date)
            elif EPC == b"\xE5":
                pass
            elif EPC == b"\xE7":
                # 瞬時電力計測値
                power = int.from_bytes(data[2:2+4], 'big')
                print(u"{0}:瞬時電力計測値:{1}[W] ".format(self.__requestTime, power))
                self.__callbackE7(power, self.__requestTime)
            elif EPC == b"\xEA":
                # 30分電力積算量(IN)
                year, month, day, hour, minute, second, power = int.from_bytes(data[2:2+2], 'big'), data[4], data[5], data[6], data[7], data[8], int.from_bytes(data[9:9+4], 'big')
                print(u"30分電力積算量(IN):{0}/{1}/{2} {3}:{4}:{5} {6}kWh".format(year, month, day, hour, minute, second, power))
            elif EPC == b"\xEB":
                # 30分電力積算量(OUT)
                year, month, day, hour, minute, second, power = int.from_bytes(data[2:2+2], 'big'), data[4], data[5], data[6], data[7], data[8], int.from_bytes(data[9:9+4], 'big')
                print(u"30分電力積算量(OUT):{0}/{1}/{2} {3}:{4}:{5} {6}kWh".format(year, month, day, hour, minute, second, power))

            data = data[1 + 1 + length:]

    def __sendCommand(self, command):
        self.__sendingCommand = command
        self.__ser.write(command)


    def initialize(self):
        # シリアルポート初期化
        self.__ser = serial.Serial(self.__serialPortDev, 115200)
        self.__recvThread = threading.Thread(target=self.__recvSerialPortThread)
        self.__recvThread.start()

    def connect(self):
        self.__sendCommand(b"SKSETPWD C " + self.__rbpwd.encode('utf-8') + b"\r\n")
        self.__status = connectStatus.SETPASSWORD

    def getIntegratePower(self, callback):
        """積算消費電力量を取得します"""
        self.__callbackE2 = callback
        return self.__requestPropertyRW(b"\xE2")

    def getInstantPower(self, callback):
        """瞬時電力消費量を取得します"""
        self.__requestTime = datetime.datetime.now()
        self.__callbackE7 = callback
        return self.__requestPropertyRW(b"\xE7")

    def __requestPropertyRW(self, epc, read=True, data=b""):
        if self.__status != connectStatus.CONNECTED:
            return -1

        echonetLiteFrame = b""
        echonetLiteFrame += b"\x10\x81"      # EHD (参考:EL p.3-2)
        echonetLiteFrame += b"\x00\x01"      # TID (参考:EL p.3-3)
        # ここから EDATA
        echonetLiteFrame += b"\x05\xFF\x01"  # SEOJ (参考:EL p.3-3 AppH p.3-408～)
        echonetLiteFrame += b"\x02\x88\x01"  # DEOJ (参考:EL p.3-3 AppH p.3-274～)       
        echonetLiteFrame += b"\x62" if read == True else b"\x60"   # ESV(62:プロパティ値読み出し要求) (参考:EL p.3-5)
        echonetLiteFrame += b"\x01"          # OPC(1個)(参考:EL p.3-7)
        echonetLiteFrame += epc              # EPC(参考:EL p.3-7 AppH p.3-275)
        echonetLiteFrame += "{0:01X}".format(len(data)).encode(encoding='utf-8')          # PDC(参考:EL p.3-9)
        echonetLiteFrame += data

        # コマンド送信
        command = b"SKSENDTO 1 " + self.__ipv6Addr + b" 0E1A 1 " + "{0:04X}".format(len(echonetLiteFrame)).encode(encoding='utf-8') + b" " + echonetLiteFrame + b"\r\n"
        self.__sendCommand(command)

        return 0

    def close(self,) :
        self.__ser.close()
# BRoutePowerMonitor

* Bルートで家庭のスマートメーターから電力使用量を取得する
* 取得したデータはAWS IoTでAWS上にアップする

## 動作環境

|||
|---|---|
|OS|Raspbian / Windows 10|
|ハード|[Raspberry Pi 4 (4GBモデル)](https://www.amazon.co.jp/LABISTS-Raspberry4-4B-64GB%EF%BC%88%E6%8A%80%E9%81%A9%E3%83%9E%E3%83%BC%E3%82%AF%E5%85%A5%EF%BC%89MicroSDHC%E3%82%AB%E3%83%BC%E3%83%8964G-NOOBS%E3%82%B7%E3%82%B9%E3%83%86%E3%83%A0%E3%83%97%E3%83%AA%E3%82%A4%E3%83%B3%E3%82%B9%E3%83%88%E3%83%BC%E3%83%AB-HDMI%E3%82%B1%E3%83%BC%E3%83%96%E3%83%AB%E3%83%A9%E3%82%A4%E3%83%B3/dp/B082VVBKRP/ref=sr_1_fkmr1_2?__mk_ja_JP=%E3%82%AB%E3%82%BF%E3%82%AB%E3%83%8A&keywords=raspberry+4+kit&qid=1582698329&sr=8-2-fkmr1) / ASUS Zenbook14|
||[WSR35A1-00](https://www.amazon.co.jp/JORJIN-WSR35A1-00/dp/B01FLAP3FK/ref=cm_cr_arp_d_bdcrb_top?ie=UTF8)|
|言語|python 3.8.0|
|ライブラリ|pyserial, schedule, AWSIoTPythonSDK.MQTTLib|

## 機能概要

* 毎分0秒に瞬時電力値を取得する
* 日を跨いだ際に前日の積算電力値（３０分間隔）を取得する
* 毎時15分間隔で、取得した電力データをAWSにアップする

## 使用方法

* config.yamlに各設定値を記載する
* main.pyをコンソールから起動する

## 制限事項（というか残AI）

* エラー処理未検討…
* リトライ処理未検討…
* 電力量単位とってるけど使ってない
* 30分値電力は都度通知されるものをAWSに上げていき、取得できなかったものを保管するために履歴を取得するほうがよいかもしれない

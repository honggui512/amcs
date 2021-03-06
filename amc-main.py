"""
# code is far away from bugs with the god animal protecting
I love animals. They taste delicious.

online  change
             ┏┓   ┏┓
            ┏┛┻━━━┛┻┓
卍          ┃   ☀   ┃
            ┃ ┳┛ ┗┳ ┃
            ┃   ┻   ┃ 
            ┗━┓   ┏━┛
              ┃   ┗━━━┓
              ┃  神兽保佑 ┣┓
              ┃　永无BUG！ ┏┛
              ┗┓┓┏━┳┓┏┛
               ┃┫┫ ┃┫┫
               ┗┻┛ ┗┻┛

"""
import sys
from PyQt5 import sip  # 未添加时，生成的exe文件会损坏
import modbus_tk.defines as cst
from modbus_tk import modbus_tcp
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtCore import QThread
from PyQt5.QtGui import QPixmap

import ipconnect
import HMI

from time import sleep

# 用于TCP打包传输
from socket import *
from ctypes import *
from struct import *
# OpenCV调用库。feature是莫编辑
import cv2
import feature

"""
  "__pad定义时"，使用class调用时报错
  通道号  1
  产品号，
  程序号"autocomp"
  检测序号
  现在在加工的  +1
"""


class PLCRequest(Structure):
    _fields_ = [("magic", c_uint32),
                ("version", c_uint8),
                ("pad", c_char * 3),
                ("machineId", c_char * 64),
                ("partNumber", c_char * 64),
                ("routineName", c_char * 64),
                ("partSeq", c_uint64),
                ("partSeqCutting", c_uint64)
                ]


"""
  "__pad定义时"，使用class调用时报错
"""


class PLCResponse(Structure):
    _fields_ = [("magic", c_uint32),
                ("version", c_uint8),
                ("status", c_uint8),
                ("pad", c_char * 2),
                ("machineId", c_char * 64),
                ("partNumber", c_char * 64),
                ("partSeq", c_uint64),
                ("message", c_char * 256)
                ]


'''
    线程T1：
    一直扫描PLC点位
'''


class GetPlcDateTread(QThread):
    def __init__(self, win):  # 复用原调用类的类变量
        super(GetPlcDateTread, self).__init__()
        self.win = win
        self.HmiWin = win.HmiWin
        self.isStart = False

    def run(self):
        while self.isStart:
            try:
                '''
                    先判断X0（急停），断开后，停止线程，同时还原界面显示
                    X0为零（非急停状态）正常扫描IO点位进入其他线程并动作
                '''
                stop = self.win.master.execute(2, cst.READ_COILS, 63488, 1)
                if int(stop[0]) == 1:
                    self.HmiWin.run_key.setChecked(False)
                    self.HmiWin.run_key.setText("运行状态")
                    self.HmiWin.rst_key.setText("复位")
                    self.HmiWin.zrn_key.setText("回零")
                    self.HmiWin.mes_lab1.setText("")
                    self.HmiWin.mes_lab2.setText("")
                    self.HmiWin.mes_lab3.setText("急停中")
                    self.HmiWin.next_key.hide()
                    self.win.T5.isStart = False
                    self.win.T5.quit()
                else:
                    res = self.win.master.execute(1, cst.READ_HOLDING_REGISTERS, 112, 8)
                    coil = self.win.master.execute(2, cst.READ_COILS, 20, 10)
                    # region status-switch
                    if int(coil[0]) == 1 and int(coil[1]) == 0:
                        self.HmiWin.mes_lab1.setText(str(res[0]))
                        self.HmiWin.mes_lab2.setText(str(res[2]))
                    elif int(coil[0]) == 0 and int(coil[1]) == 1:
                        self.HmiWin.mes_lab1.setText(str(res[4]))
                        self.HmiWin.mes_lab2.setText(str(res[6]))
                    else:
                        self.HmiWin.mes_lab1.setText("0")
                        self.HmiWin.mes_lab2.setText("0")
                        # self.HmiWin.photo.hide()
                    if (int(coil[4]) == 1 or int(coil[6]) == 1) and self.win.T2.isStart is False:
                        self.win.T2.isStart = True
                        self.win.T2.start()
                        sleep(0.1)
                        self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 24, output_value=[0])
                        self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 26, output_value=[0])
                    if int(coil[8]) == 1 and self.win.T4.isStart is False:  # 防止反复开启
                        self.win.T4.isStart = True
                        self.win.T4.start()
                        sleep(0.1)
                    # endregion-
                    m_error = self.win.master.execute(2, cst.READ_COILS, 400, 15)
                    # <editor-fold desc="m_error-switch">
                    if m_error[0] == 1:
                        self.HmiWin.mes_lab3.setText("气缸0°超时报警，处理完，复位回零！")
                    elif m_error[1] == 1:
                        self.HmiWin.mes_lab3.setText("气缸180°超时报警，处理完，复位回零！")
                    elif m_error[2] == 1:
                        self.HmiWin.mes_lab3.setText("夹爪开报警，处理完，复位回零！")
                    elif m_error[3] == 1:
                        self.HmiWin.mes_lab3.setText("夹爪合报警，处理完，复位回零！")
                    elif m_error[4] == 1:
                        self.HmiWin.mes_lab3.setText("支撑上报警，处理完，复位回零！")
                    elif m_error[5] == 1:
                        self.HmiWin.mes_lab3.setText("支撑下报警，处理完，复位回零！")
                    elif m_error[6] == 1:
                        self.HmiWin.mes_lab3.setText("漏斗前报警，处理完，复位回零！")
                    elif m_error[7] == 1:
                        self.HmiWin.mes_lab3.setText("漏斗后报警，处理完，复位回零！")
                    elif m_error[8] == 1:
                        self.HmiWin.mes_lab3.setText("风刀前报警，处理完，复位回零！")
                    elif m_error[9] == 1:
                        self.HmiWin.mes_lab3.setText("风刀后报警，处理完，复位回零！")
                    elif m_error[10] == 1:
                        self.HmiWin.mes_lab3.setText("自锁到达超时")
                    elif m_error[11] == 1:
                        self.HmiWin.mes_lab3.setText("自锁检测超时，处理完，复位回零！")
                    elif m_error[12] == 1:
                        self.HmiWin.mes_lab3.setText("低通到达超时")
                    elif m_error[13] == 1:
                        self.HmiWin.mes_lab3.setText("低通检测超时，处理完，复位回零！")  # 报警显示
                    elif m_error[14] == 1:
                        self.HmiWin.mes_lab3.setText("漏斗卡料超时，处理完，复位回零！")  # 报警显示
                    # </editor-fold>
            except(RuntimeError, TypeError, NameError):

                self.HmiWin.hide()  # 不需要close
                self.win.show()
                self.isStart = False
                self.quit()  # 退出线程


class ZrnWaitTread(QThread):
    def __init__(self, win):  # 复用原调用类的类变量
        super(ZrnWaitTread, self).__init__()
        self.win = win
        self.HmiWin = win.HmiWin

    def run(self):
        coil = self.win.master.execute(2, cst.READ_COILS, 2, 1)
        while coil[0] == 0:
            coil = self.win.master.execute(2, cst.READ_COILS, 2, 1)
            pass
        self.HmiWin.mes_lab3.setText("回零完成")
        self.quit()  # 退出线程


class GetCmmDateTread(QThread):
    def __init__(self, win):  # 复用原调用类的类变量
        super(GetCmmDateTread, self).__init__()
        self.win = win
        self.HmiWin = win.HmiWin
        self.isStart = False
        self.tcp_tx1 = PLCRequest(0xC0FEED0C, 1, b'', b'machine_1', b'routine_1', b'partZZZ', 55111, 55239)
        self.tcp_tx2 = PLCRequest(0xC0FEED0C, 1, b'', b'machine_2', b'routine_2', b'partBBB', 55111, 55239)

        self.tcp_rx1 = PLCResponse(0xC0FEED0D, 1, 2, b'', b'routine_1', b'partZZZ', 5311, b'')
        self.tcp_rx2 = PLCResponse(0xC0FEED0D, 1, 2, b'', b'routine_2', b'partBBB', 5311, b'')

    """
    Modbus-TCP读取完成标志位
        if 
            读取想要的三个信息
            写入到pack中，tcp发送数据
            while True
                读取TCP完成信号，OK及NG
                unpack方式
                同时去除标志位(M20/21/22/23)
                计时报警跳出报警界面
                QMessageBox.information(self, "TCP通讯失败",self.tr("请检查CMM软件状态!"))
    """

    def run(self):
        try:
            res = self.win.master.execute(1, cst.READ_HOLDING_REGISTERS, 112, 8)
            coil = self.win.master.execute(2, cst.READ_COILS, 20, 5)
            if int(coil[0]) == 1 and int(coil[1]) == 0:
                self.tcp_tx1.partSeqCutting = int(res[0] + 1)
                self.tcp_tx1.partSeq = int(res[2])
                buf = pack('!IB3s64s64s64sQQ', self.tcp_tx1.magic, self.tcp_tx1.version, self.tcp_tx1.pad,
                           self.tcp_tx1.machineId, self.tcp_tx1.partNumber, self.tcp_tx1.routineName,
                           self.tcp_tx1.partSeq, self.tcp_tx1.partSeqCutting)
                print("pack 成功")
                self.win.tcpCliSock.sendall(buf)
                size = sizeof(PLCResponse)
                buf = b''
                while len(buf) < size:
                    more = self.win.tcpCliSock.recv(size - len(buf))
                    if not more:
                        break
                    buf += more
                # 许后泽协助编辑
                resp = PLCResponse()
                resp.magic, resp.version, resp.status, \
                resp.__pad, resp.machineId, resp.partNumber, \
                resp.partSeq, resp.message = unpack('!IBB2s64s64sQ256s', buf)
                print(resp.message)
                print('-----------------------')
                print(resp.status)
                print(type(resp.status))
                if resp.message != b'Image capture failure':
                    if resp.magic == self.tcp_rx1.magic and resp.version == self.tcp_rx1.version:
                        message = str(resp.message, encoding="utf-8")
                        ab = message.split('|')
                        if self.win.diameter1 <= float(ab[2]) <= self.win.diameter2 and \
                                self.win.height1 <= float(ab[4]) <= self.win.height2:
                            print("OK")
                            self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 22, output_value=[1, 0, 0, 1])
                            self.HmiWin.mes_lab3.setText("ok")
                        elif (self.win.diameter1 - 1.00) > float(ab[2]) or float(ab[4]) > (self.win.height2 + 1):
                            print("错误尺寸，需要吹气")
                            self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 64524, output_value=[1])
                            sleep(2)
                            self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 64524, output_value=[0])
                            self.HmiWin.mes_lab3.setText("平台除尘完成")
                        else:
                            print("NG")
                            self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 22, output_value=[0, 0, 0, 1])
                            self.HmiWin.mes_lab3.setText("NG")

                else:
                    self.HmiWin.mes_lab3.setText(resp.message.decode("utf-8"))
            self.isStart = False
            self.quit()  # 退出线程
        except(RuntimeError, TypeError, NameError):
            self.HmiWin.hide()  # 不需要close
            self.win.show()
            self.isStart = False
            print("CMM线程挂了")
            self.quit()  # 退出线程
            self.win.T1.isStart = False
            self.win.statusTcp = False  # 再次通信时，打开
            self.win.T1.quit()


'''
    OpenCV判断产品正反问题
'''


class MiscolorTread(QThread):
    def __init__(self, win):  # 复用原调用类的类变量
        super(MiscolorTread, self).__init__()
        self.win = win
        self.HmiWin = win.HmiWin
        self.isStart = False
        self.flag = False
        self.max1 = 0
        self.mean1 = 0
        self.name1 = 0
        self.max2 = 0
        self.mean2 = 0
        self.name2 = 0
        self.match_path = 0
        self.showPhoto = 0

    def run(self):
        self.flag = True
        self.win.cap.read()  # 预读一次，防止黑屏

        while self.flag:  # 循环检测，直到有结果
            ret, frame = self.win.cap.read()
            cv2.imwrite(self.win.photoPath, feature.cropImg(frame))
            self.max1, self.mean1, self.name1 = feature.match(self.win.path1, self.win.photoPath)
            self.max2, self.mean2, self.name2 = feature.match(self.win.path2, self.win.photoPath)
            if max(self.max1, self.max2) > 30:
                if self.max1 > self.max2:
                    self.match_path = self.win.path1
                    self.flag = False
                else:
                    self.match_path = self.win.path2
                    self.flag = False
            else:
                if self.mean1 - self.mean2 > 0.5:
                    self.match_path = self.win.path1
                    self.flag = False
                elif self.mean2 - self.mean1 > 0.5:
                    self.match_path = self.win.path2
                    self.flag = False
                else:
                    print("不可信")
        if self.match_path == self.win.path1:
            self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 28, output_value=[0, 0])
        elif self.match_path == self.win.path2:
            self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 28, output_value=[0, 1])
        if max(self.max1, self.max2) < 10 and abs(self.mean1 - self.mean2) > 0.5:
            image_path = feature.append(self.match_path, self.win.photoPath)
            feature.save_descriptor(self.match_path, image_path, cv2.xfeatures2d.SIFT_create())
        self.showPhoto = QPixmap(self.win.photoPath)
        self.HmiWin.photo.setPixmap(self.showPhoto)  # 在label上显示图片
        self.HmiWin.photo.setScaledContents(True)  # 让图片自适应label大小
        self.HmiWin.photo.show()
        sleep(0.1)
        self.isStart = False
        self.quit()  # 退出线程


class AutoCompareTread(QThread):
    def __init__(self, win):  # 复用原调用类的类变量
        super(AutoCompareTread, self).__init__()
        self.win = win
        self.HmiWin = win.HmiWin
        self.isStart = False
        self.D0 = 0

    def run(self):
        while self.isStart:
            coil = self.win.master.execute(2, cst.READ_COILS, 20, 2)
            res = self.win.master.execute(1, cst.READ_HOLDING_REGISTERS, 112, 8)
            if int(res[0]) != self.D0:
                self.D0 = int(res[0])
                if (self.D0 - self.win.baseValue) % self.win.hz_int == 0 and self.win.auto_start_flag is True:
                    if coil[0] == 0 and coil[1] == 0:
                        self.win.master.execute(2, cst.WRITE_MULTIPLE_COILS, 20, output_value=[1, 0])
                    else:
                        self.HmiWin.mes_lab6.setText("循环周期比较短，待运行完成后，重新更改频率")
                        self.HmiWin.auto_key.setChecked(False)
                        self.win.auto_start_flag = False
                        self.win.hz_choose_flag = False
                        self.isStart = False
                        self.quit()


'''
原先问题：子界面关闭时，不会关闭主界面添加的线程T1
解决:信号与槽函数的编辑。
重新定义结束的方法，添加信号
'''


class HmiWin(QtWidgets.QDialog, HMI.Ui_HMI):
    signal = QtCore.pyqtSignal(str)  # str是返回的数据类型

    def __init__(self):
        super(HmiWin, self).__init__()
        self.setupUi(self)

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(self.centralwidget,
                                               '本程序',
                                               "是否要退出程序？",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            print("it's over")
            cv2.destroyAllWindows()
            self.signal.emit("12345")  # 传递数据，可以在槽函数中调用数据
            event.accept()
        else:
            event.ignore()


class MainWin(QtWidgets.QMainWindow, ipconnect.Ui_MainWindow):
    def __init__(self):
        super(MainWin, self).__init__()
        self.setupUi(self)
        self.ip_line.setText("192.168.1.5")
        self.ip_key.clicked.connect(self.ip_connect)
        self.path1 = 'C:/Caron Engineering/up_picture'
        self.path2 = 'C:/Caron Engineering/down_picture'
        self.photoPath = "C:/Caron Engineering/momotest.jpg"
        self.cap = cv2.VideoCapture()
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 5000)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 5000)
        self.h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.cap.read()
        self.HmiWin = HmiWin()
        self.HmiWin.len_choose_key.clicked.connect(self.len_choose_met)
        self.HmiWin.hz_choose_key.clicked.connect(self.hz_choose_met)
        self.HmiWin.auto_key.clicked.connect(self.auto_start_met)
        self.HmiWin.hold_key.clicked.connect(self.auto_hold_met)
        self.HmiWin.run_key.clicked.connect(self.run_met)
        self.HmiWin.next_key.clicked.connect(self.next_met)
        self.HmiWin.rst_key.clicked.connect(self.rst_met)
        self.HmiWin.zrn_key.clicked.connect(self.zrn_met)
        self.HmiWin.signal.connect(self.hmi_close_thread)  # 槽函数的使用
        self.showPhoto = QPixmap(self.photoPath)

        self.HmiWin.D_key1.clicked.connect(self.diameter_met1)
        self.HmiWin.D_key2.clicked.connect(self.diameter_met2)
        self.HmiWin.H_key1.clicked.connect(self.height_met1)
        self.HmiWin.H_key2.clicked.connect(self.height_met2)
        self.HmiWin.ok_key.clicked.connect(self.ok_met)
        self.diameter1 = 2.98
        self.diameter2 = 2.98
        self.height1 = 10.0
        self.height2 = 10.0

        self.T1 = GetPlcDateTread(self)
        self.T2 = GetCmmDateTread(self)
        self.T3 = ZrnWaitTread(self)
        self.T4 = MiscolorTread(self)
        self.T5 = AutoCompareTread(self)
        self.master = modbus_tcp.TcpMaster(host=self.ip_line.text(), port=502)

        self.statusTcp = False
        self.len_choose_flag = False
        self.length_int = 0
        self.hz_choose_flag = False
        self.hz_int = 0
        self.auto_start_flag = False
        self.baseValue = 0

        self.status = 0
        self.HOST = 'localhost'  # 主机地址
        self.PORT = 1088  # 端口号
        self.ADDR = (self.HOST, self.PORT)  # 链接地址
        self.BUFSIZ = 2048  # 缓存区大小，单位是字节，这里设定了2K的缓冲区
        self.PLC_MAX_VER = 1
        self.PLC_REQ_MAGIC = 0xC0FEED0C
        self.PLC_RESP_MAGIC = 0xC0FEED0D
        self.tcpCliSock = socket(AF_INET, SOCK_STREAM)  # 创建一个TCP套接字

    def diameter_met1(self):
        text, ok = QInputDialog.getDouble(self.centralwidget, '直径下限', '请输入数值mm：', 2.98, 2.3, 8, 2)
        if ok:
            print(text)
            print(type(text))
            self.diameter1 = text

    def diameter_met2(self):
        text, ok = QInputDialog.getDouble(self.centralwidget, '直径上限', '请输入数值mm：', 2.98, 2.3, 8, 2)
        if ok:
            print(text)
            print(type(text))
            self.diameter2 = text

    def height_met1(self):
        text, ok = QInputDialog.getDouble(self.centralwidget, '高度下限', '请输入数值mm：', 10.00, 9.0, 29, 2)
        if ok:
            print(text)
            print(type(text))
            self.height1 = text

    def height_met2(self):
        text, ok = QInputDialog.getDouble(self.centralwidget, '高度上限', '请输入数值mm：', 10.00, 9.0, 29, 2)
        if ok:
            print(text)
            print(type(text))
            self.height2 = text

    def ok_met(self):
        ok = QMessageBox.information(self.centralwidget, '请确认设定尺寸',
                                     ('直径下限' + str(self.diameter1) + 'mm' + '直径上限' + str(self.diameter2) + 'mm'
                                      + '\r'
                                      + '高度下限' + str(self.height1) + 'mm' + '高度上限' + str(self.height2) + 'mm'),
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if ok:
            if self.diameter1 <= self.diameter2 and self.height1 <= self.height2:
                print("没事.")
            else:
                QMessageBox.information(self.centralwidget, "warning", self.tr("请重新确认上下限的选择"),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def hmi_close_thread(self, str_msg):
        print(str_msg)  # 信号被打开后会调用并传递数据
        self.cap.release()
        cv2.destroyAllWindows()
        self.T1.isStart = False
        self.T1.quit()
        self.T2.isStart = False
        self.T2.quit()
        self.T3.isStart = False
        self.T3.quit()
        self.T4.isStart = False
        self.T4.quit()
        self.T5.isStart = False
        self.T5.quit()

    def tcp_connect(self):

        while True:
            try:
                self.tcpCliSock.connect(self.ADDR)  # 绑定地址
                self.statusTcp = True
                break
            except(RuntimeError, TypeError, NameError):
                QMessageBox.information(self.centralwidget, "请先打开CMM软件", self.tr("IP：localhost，port：1088"),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def ip_connect(self):
        try:
            self.master = modbus_tcp.TcpMaster(host=self.ip_line.text(), port=502)
            self.master.set_timeout(1.0)
            self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 1, output_value=[0])  # 测试有没通讯成功，可以初始化
            """
            再次连接后，需要还原原先界面数据
            """
            self.HmiWin.auto_key.setChecked(False)
            self.HmiWin.hold_key.setChecked(False)
            self.HmiWin.run_key.setChecked(False)
            self.HmiWin.len_choose_key.setChecked(False)
            self.HmiWin.hz_choose_key.setChecked(False)

            self.HmiWin.run_key.setText("运行状态")
            self.HmiWin.rst_key.setText("复位")
            self.HmiWin.zrn_key.setText("回零")
            self.HmiWin.mes_lab1.setText("")
            self.HmiWin.mes_lab2.setText("")
            self.HmiWin.mes_lab3.setText("")
            self.HmiWin.mes_lab4.setText("")
            self.HmiWin.mes_lab5.setText("")
            self.HmiWin.mes_lab6.setText("")
            self.len_choose_flag = False
            self.hz_choose_flag = False
            self.auto_start_flag = False

            self.HmiWin.next_key.hide()
            self.HmiWin.photo.hide()
            if self.statusTcp is False:
                self.tcp_connect()
            self.HmiWin.show()
            sleep(0.2)
            self.hide()  # 不需要close
            self.T1.isStart = True
            self.T1.start()
        except(RuntimeError, TypeError, NameError):
            text, ok = QInputDialog.getText(self.centralwidget, '通讯未成功，请确认CMM、PLC',
                                            '请先打开CMM并输入正确的IP号，“确认”连接', QLineEdit.Normal, "192.168.1.1",
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            if ok:
                self.ip_line.setText(str(text))
            self.T1.isStart = False
            self.T1.quit()

    def len_choose_met(self):
        coil_zrn = self.master.execute(2, cst.READ_COILS, 2, 1)
        coil_doing = self.master.execute(2, cst.READ_COILS, 100, 1)
        if int(coil_zrn[0]) == 1:
            if int(coil_doing[0]) == 0:
                text, ok = QInputDialog.getInt(self.centralwidget, '高度设置', '请输入高度mm：', 10, 10, 100, 1, flags=0)
                if ok:
                    if 10 <= int(text) <= 25:
                        self.HmiWin.mes_lab4.setText(str(text) + 'mm')
                        self.len_choose_flag = True
                        self.length_int = int(text)
                        self.HmiWin.len_choose_key.setChecked(True)
                        self.HmiWin.run_key.setText("自动运行中")
                        return 0
                    else:
                        QMessageBox.information(self.centralwidget, "warning", self.tr("请选择10mm~25mm自锁螺丝产品"),
                                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            else:
                QMessageBox.information(self.centralwidget, "warning", self.tr("运行中，请勿切换!"),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        else:
            QMessageBox.information(self.centralwidget, "warning", self.tr("请先回零，再进行动作!"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        self.HmiWin.len_choose_key.setChecked(False)

    def hz_choose_met(self):
        coil_zrn = self.master.execute(2, cst.READ_COILS, 2, 1)
        coil_doing = self.master.execute(2, cst.READ_COILS, 100, 1)
        if int(coil_zrn[0]) == 1:
            if int(coil_doing[0]) == 0:
                text, ok = QInputDialog.getInt(self.centralwidget, '循环次数设定', '请输入循环部件书：', 3,
                                               2, 100, 1, flags=0)
                if ok:
                    if 3 <= int(text):
                        self.HmiWin.mes_lab5.setText(str(text) + '件')
                        self.hz_choose_flag = True
                        self.hz_int = int(text)
                        self.HmiWin.hz_choose_key.setChecked(True)

                        self.HmiWin.run_key.setText("自动运行中")
                    else:
                        QMessageBox.information(self.centralwidget, "warning", self.tr("最低输入三个"),
                                                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            else:
                QMessageBox.information(self.centralwidget, "warning", self.tr("运行中，请勿切换!"),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        else:
            QMessageBox.information(self.centralwidget, "warning", self.tr("请先回零，再进行动作!"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def auto_start_met(self):
        coil_zrn = self.master.execute(2, cst.READ_COILS, 2, 1)
        res = self.master.execute(1, cst.READ_HOLDING_REGISTERS, 112, 8)

        if int(coil_zrn[0]) == 1:
            if self.len_choose_flag is True and self.hz_choose_flag is True:
                ok = QMessageBox.information(self.centralwidget, '请确认尺寸',
                                             '长度' + str(self.length_int) + 'mm' + '循环个数' + str(self.hz_int),
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
                if ok:
                    if self.auto_start_flag is False:
                        self.HmiWin.len_choose_key.setChecked(True)
                        self.HmiWin.hz_choose_key.setChecked(False)
                        self.master.execute(1, cst.WRITE_MULTIPLE_REGISTERS, 200, output_value=[(self.length_int - 10)])
                        self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 20, output_value=[1, 0])
                        self.auto_start_flag = True

                        self.HmiWin.hold_key.setChecked(False)
                        self.HmiWin.auto_key.setChecked(True)
                        self.baseValue = int(res[0])
                        self.T5.D0 = self.baseValue
                        self.HmiWin.mes_lab6.setText("")

                        self.HmiWin.photo.show()
                        self.HmiWin.photo.setPixmap(self.showPhoto)  # 在label上显示图片
                        self.HmiWin.photo.setScaledContents(True)  # 让图片自适应label大小
                        self.T5.isStart = True
                        self.T5.start()
                        sleep(0.1)
            else:
                QMessageBox.information(self.centralwidget, "warning", self.tr("请先选择好产品种类及循环次数"),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        else:
            QMessageBox.information(self.centralwidget, "warning", self.tr("请先回零，再进行动作!"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

    def auto_hold_met(self):
        coil_zrn = self.master.execute(2, cst.READ_COILS, 2, 1)
        if int(coil_zrn[0]) == 1:
            if self.len_choose_flag is True and self.hz_choose_flag is True \
                    and self.auto_start_flag is True:
                self.auto_start_flag = False
                self.HmiWin.auto_key.setChecked(False)
                self.HmiWin.hold_key.setChecked(True)
                self.T5.isStart = False
                self.T5.quit()
                self.HmiWin.hold_key.setChecked(True)
                self.HmiWin.auto_key.setChecked(False)
        else:
            QMessageBox.information(self.centralwidget, "warning", self.tr("请先回零，再进行动作!"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.HmiWin.hold_key.setChecked(False)

    def run_met(self):
        coil_zrn = self.master.execute(2, cst.READ_COILS, 2, 1)
        if int(coil_zrn[0]) == 1:
            self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 801, output_value=[self.HmiWin.run_key.isChecked()])
            if self.HmiWin.run_key.isChecked():
                self.HmiWin.run_key.setText("单步执行")
                self.HmiWin.next_key.show()
                self.status = 0
            else:
                self.HmiWin.run_key.setText("自动运行中")
                self.HmiWin.next_key.hide()
        else:
            QMessageBox.information(self.centralwidget, "warning", self.tr("请先回零，再进行动作!"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            self.HmiWin.run_key.setChecked(False)

    def next_met(self):
        self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 800, output_value=[1])
        if self.status:
            self.HmiWin.next_key.setText("下一步")
            self.status = 0
        else:
            self.HmiWin.next_key.setText("再下一步")
            self.status = 1

    def rst_met(self):
        self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 4, output_value=[1])
        sleep(0.5)
        self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 4, output_value=[0])

    def zrn_met(self):
        """
        回零按钮触发时，查看是否运行中，（正在回零，正在测量M20低通M21自锁）
            1、防止回零成功后，多次回零。M2测试是否为1
            2、运行过程中（包括正在跑程序，回零过程中，报警）
        """
        coil_zrn = self.master.execute(2, cst.READ_COILS, 2, 1)
        coil_doing = self.master.execute(2, cst.READ_COILS, 100, 1)
        if int(coil_doing[0]) == 1:
            QMessageBox.information(self.centralwidget, "warning", self.tr("运行中，请勿回零!"),
                                    QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        else:
            if int(coil_zrn[0]) == 1:
                QMessageBox.information(self.centralwidget, "warning", self.tr("已经回零成功，无需回零!"),
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            else:
                self.HmiWin.mes_lab3.setText("")  # 报警显示
                self.master.execute(2, cst.WRITE_MULTIPLE_COILS, 1, output_value=[1])
                self.T3.start()

    def closeEvent(self, event):
        reply = QtWidgets.QMessageBox.question(self.centralwidget,
                                               '本程序',
                                               "是否要退出程序？",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.cap.release()
            cv2.destroyAllWindows()
            self.T1.isStart = False
            self.T1.quit()
            self.T2.isStart = False
            self.T2.quit()
            self.T3.isStart = False
            self.T3.quit()
            self.T4.isStart = False
            self.T4.quit()
            self.T5.isStart = False
            self.T5.quit()
            event.accept()
        else:
            event.ignore()


def main():
    app = QtWidgets.QApplication(sys.argv)  # 创建应用程序
    run = MainWin()
    run.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

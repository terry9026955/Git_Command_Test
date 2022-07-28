from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys
import mainui as ui
import subprocess
import use_inbox_delete_smi_driver_tp
import configparser
import os
import logging
import time
from functools import partial

# Default branch: Echoharbor_N38A_Main


# Counter for recursion times recording and restarting program
counter = 0

cwd = os.getcwd()
print("current path: ", cwd)

class Main(QMainWindow, ui.Ui_MainWindow):
    eventloop = False
    SHA = None  # 全域
    stopmissionFlag = False
    version_number = "20220718A_BETA"
    # determine if application is a script file or frozen exe
    if getattr(sys, 'frozen', False):   #確認是打包好的exe檔案還是本地的script檔案
        wrapper_path = os.path.dirname(sys.executable) #抓路徑位址
    elif __file__:
        wrapper_path = os.path.dirname(__file__)
    print("Wrapper Path is: ", wrapper_path)

        
    def __init__(self): #建構子
        super().__init__()  #繼承QtWidgets.QMainWindow跟Ui_MainWindow建構子的內容
        self.setupUi(self)  #將UI做建立的動作
        #self.setAcceptDrops(True)
        self.initiAct()     
        self.setAcceptDrops(True)   #使能夠支持拖動操作
        
        
        # 這邊可能要改成 thread 去做
        self.list_add_text() #應該是關於拖動功能
        self.pushButton_2.clicked.connect(partial(self.removeSel, "select")) #按鈕功能
        self.pushButton_3.clicked.connect(self.getfile)
        self.pushButton_4.clicked.connect(self.tiggerStopcommand)
        self.pushButton.clicked.connect(self.getInfo)

        self.comboBox.currentIndexChanged.connect(self.enableCheckbox)  #用於事件改動時的處理方式(改A框，B框內容自動改變)
    

    def tiggerStopcommand(self):
        Main.stopmissionFlag = True
        return
    
    
    
    def getInfo(self):
        #Initializaion of stopmissionFlag
        Main.stopmissionFlag = False
        
        ini = self.loadini()
        folderPath = ini.value("Folder/path")
        gitPath = ini.value("Git_path/path")
        print("getInfo called!") # TEST
        print("gitPath: " , gitPath)
        
        # get number of list 
        listNumber = self.listWidget.count()
        # get name of batch file
        scriptList = []
        for i in range(listNumber):
            #res = yield self.listWidget.item(i)
            scriptname = str(self.listWidget.item(i).text())
            
            global checkedFlag
            
            if "0-1_NVMe_Preparation" in scriptname:
                if self.checkBox.isChecked():
                    checkedFlag = True # (golbal) 
                else:
                    checkedFlag = False
            
            
            scriptList.append(scriptname)
            
        ini_branch = ini.value("Branch/branch")
        # Set delay before execute renewINI
        time.sleep(2)
        self.renewini_fromlistWidget()
        self.threadRunSHA(folderPath, listNumber, scriptList, ini_branch, gitPath)
        
    
    def threadRunSHA(self, folderpath, listWidget_count, scriptList, branch, gitPath):
        print("threadRunSHA called!")
        print("now the branch is " + branch)
        self.thread = QThread(parent=self)  # 開新Thread
        
        self.worker = getSHA()
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        
        self.thread.started.connect(partial(self.worker.main, gitPath, branch)) # 迴圈跳來會重新開一個新Thread做Thread2的事情

        # 當收到finished, 線程結束
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        
        
        self.thread.finished.connect(self.thread.deleteLater)
        
        # commit
        self.worker.SHAwrite.connect(self.SHAwrite)
        self.worker.endTigger.connect(partial(self.threadRunbatch, folderpath, listWidget_count, scriptList, branch, Main.SHA, gitPath))
        # Start the thread
        self.thread.start()
        
    
    def threadRunbatch(self, folderpath, listWidget_count, scriptList, branch, SHA, gitPath, endTigger):
        
        #print(endTigger, folderpath, listWidget_count, scriptList, branch, SHA)
        self.thread = QThread(parent=self)
        
        self.worker = runBatchcommand()
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        
        self.thread.started.connect(partial(self.worker.mainWork, endTigger, folderpath, listWidget_count, scriptList, branch, SHA, gitPath))

        self.worker.loopTigger.connect(partial(self.threadRunSHA, folderpath, listWidget_count, scriptList, branch))
        self.worker.restartTigger.connect(self.setRestarttigger)
        
        # 當收到finished, 線程結束
        
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        
        
        self.thread.finished.connect(self.thread.deleteLater)

        
        # Start the thread
        self.thread.start()


    def enableCheckbox(self):
        val = str(self.comboBox.currentText()) #目前選項中的值

        if val == "DVT":
            self.checkBox.setEnabled(True)  #設定元件是否可用
            self.checkBox.setChecked(False) 
        elif val == "3rd party":
            self.checkBox.setEnabled(False)
            self.checkBox.setChecked(True)
        else:
            self.checkBox.setEnabled(True)



    #抓ini路徑
    def loadini(self):
        # 原本寫的樣子:
        settings = QSettings(Main.wrapper_path+'/config.ini', QSettings.IniFormat)
        
        # 先設絕對路徑看能不能寫:
        # settings = QSettings('D:\Tinghao.Chen\Desktop\Git_Command_Test', QSettings.IniFormat)
        print("Loadini setting is: ", settings)
        return settings


    def initiAct(self):
        try:
            config = configparser.ConfigParser()    #python讀取ini設定檔案
            config.read(Main.wrapper_path+'/config.ini')

            ini = self.loadini()

            ini_selection = ini.value("test_plan/selection")    #QSettings.value(): read
            ini_branch = ini.value("Branch/branch")
            ini_SHA = ini.value("SHA/sha")
            ini_path = ini.value("Folder/path")
            Runonce_trigger = ini.value("Runonce_trigger/tigger")
            self.comboBox.addItems(ini_selection)
            
            if os.path.isdir(ini_path.replace("/","\\")):
                try:

                    ini_file = config['%General']

                    filelist = ini_file.parser._sections["%General"]
                    
                    for k,v in filelist.items():
                        
                        self.listWidget.addItem(filelist[k])

                    
                except:
                    tigger = False
                    with open(Main.wrapper_path+"/config.ini", 'r') as f:
                        for row in f:
                            if "[%General]" in row:
                                tigger = True
                                pass
                            if tigger == True:
                                #print(row)
                                if "filepath_" in row:
                                    name = row.split("=")[1]
                                    #print(name)
                                    
                                    self.listWidget.addItem(name)
            else:
                self.removeSel("autodelete")
                

            self.lineEdit.setText(ini_branch)
            self.lineEdit_2.setText(ini_SHA)
            if Runonce_trigger == "1":
                self.runMemorythread()
                
        except Exception:
            Log_Format = "%(levelname)s %(asctime)s - %(message)s"
            real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            log_name = Main.wrapper_path+"/log/"+real_time+"_logfile.log"
            logging.basicConfig(filename = log_name,
                                filemode = "w",
                                format = Log_Format, 
                                level = logging.DEBUG)

            logger = logging.getLogger()

            #Testing our Logger

            logger.error("Error Message from initiAct", exc_info=True)
        

    def dragEnterEvent(self, event):

        
        event.accept()
        event.acceptProposedAction()
        



    def dropEvent(self,event):

        
        file_name = event.mimeData().text()

        if 'file:///' in file_name:
            file_name = file_name.replace('file:///', '')
            #print(file_name)
        
            self.listWidget.addItem(file_name) 
            


    def list_add_text(self):

        self.listWidget.setDragEnabled(True) #支援拖動操作
        self.listWidget.setAcceptDrops(True)

        return


    def removeSel(self, mode):

        config = configparser.ConfigParser()
        config.read(Main.wrapper_path+'/config.ini')
        if mode == "select":
            listItems = self.listWidget.selectedItems()
        else:
            for i in config.options("%General"):
                
                    if config.has_section("%General") == True:

                        config.remove_option("%General", i)
                        config.write(open(Main.wrapper_path+'/config.ini', 'w'))
                        
            return
                        
        if not listItems:
            return

        for item in listItems:
            
            a = self.listWidget.item(self.listWidget.row(item)).text()
            print(a)
            self.listWidget.takeItem(self.listWidget.row(item))

            
            for i in config.options("%General"):
                if config.get("%General", i) == a:

                    print(i, '=', config.get("%General", i))
                
                    if config.has_section("%General") == True:

                        config.remove_option("%General", i)
                        config.write(open(Main.wrapper_path+'/config.ini', 'w'))



    def setRestarttigger(self, nextScript):
        ini = self.loadini()
        ini.setValue("Runonce_trigger/tigger", str("1"))
        ini.setValue("Runonce_trigger/started", nextScript)
        
        self.createbatchforRunOnce(Main.wrapper_path)
        runonceFlag = self.regRunonce(Main.wrapper_path)
        if runonceFlag == True:
            Main.eventloop = True
        else:
            print("RunonceFlag False")
            
            
    # set trigger to 0
    def rebuildRunonce(self):
        Main.loop = False
        ini = self.loadini()
        ini.setValue("Runonce_trigger/tigger", "0")
        

    # 存取開卡時的 CMD 資料用
    # def cmdSave(self):
    #     # 抓 D:/Tinghao.Chen/Desktop/Test_menu 的  batch file
    #     ini = self.loadini()
    #     batchName = ini.value("General/filepath_1")
    #     p = subprocess.run(batchName, stdout=subprocess.PIPE)   # 在資料夾下去執行ini裡面紀錄的batch file name
    #     str_List = str(p.stdout.decode('cp950')).split('\r\n\r\n')  # i.replace("\r\n", "")  #替換特定字串用
        
    #     # Write batch output into data.log (寫入)
    #     with open("commandData.log", "w") as dataWrite:
    #         print("Writing str_List into data.log")
    #         for line in str_List:
    #             dataWrite.write(line)
    #             dataWrite.write("\n")


    #     # Print SHA code of the data.log
    #     with open("commandData.log", "r") as dataRead:
    #         print("Reading SHA code")
    #         dataSHA = dataRead.readlines()[19]  # Read the specific line (SHA code)
        
    #     # Write the SHA code into Debug_log file 
    #     with open(real_time + "_Debug_log.log", "w") as dataWrite:
    #         print("SHA code is written into Debug_log")
    #         dataWrite.write(dataSHA)
        
        
            

    # def get_list_item(self):

    #     for i in range(self.listWidget.count()):
    #         #res = yield self.listWidget.item(i)
        
    #         print(self.listWidget.item(i).text())

    
        


    def createbatchforRunOnce(self, wrapper_path):
        file_name = wrapper_path + '\\RunOnce.bat'
        f = open(file_name, 'w')
        script = "cd /d "+ wrapper_path + "\ncall " + wrapper_path+"\\test_plan_ui_"+Main.version_number+".exe"
        f.write(script)
        f.close()
        

    def regRunonce(self, wrapper_path):
        cmd_reg = ["reg", "add", "HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\RunOnce", "/v", "RunScript", "/t", "REG_SZ", "/d", wrapper_path+"\\RunOnce.bat"]
        r = subprocess.run(cmd_reg, stdout=subprocess.PIPE)
        if r.returncode == 0:
            return True
        else:
            print(r.returncode)
            return False
        


    def getfile(self):

        # 選取資料夾對話視窗
        dig = QFileDialog.getExistingDirectory()
        # # setting gui can open any files

        config = configparser.ConfigParser()
        config.read(Main.wrapper_path+'/config.ini')
        config.set('Folder',"path", str(dig))
        newini = open("config.ini", 'w')
        config.write(newini)
        newini.close
        try:
            config.add_section('%General')
        except:
            pass

        if dig != "":
            filelist = os.listdir(dig)
            print(filelist)

            if len(filelist) != 0:
                
                filenumber = 0

                for i in range(len(filelist)):
                    
                    if ".bat" in filelist[i]:
                        
                        filenumber = filenumber + 1

                        self.listWidget.addItem(filelist[i])

                        config.set('%General',"filepath_"+str(filenumber), filelist[i])

                        newini = open("config.ini", 'w')
                        config.write(newini)
                        newini.close

                        #ini.setValue("General/filepath_"+str(i+1), filelist[i])

                    if ".exe" in filelist[i]:
                        
                        filenumber = filenumber + 1

                        self.listWidget.addItem(filelist[i])


                        config.set('%General',"filepath_"+str(filenumber), filelist[i])

                        newini = open(Main.wrapper_path+'/config.ini', 'w')
                        config.write(newini)
                        newini.close
            else:
                None


        return


    def renewini_fromlistWidget(self):
        
        new_scriptlist = []
        config = configparser.ConfigParser()
        config.read(Main.wrapper_path+'/config.ini')

        for i in range(self.listWidget.count()):
            #res = yield self.listWidget.item(i)
            scriptname = str(self.listWidget.item(i).text())
            new_scriptlist.append(scriptname)

        ini_file = config['%General']

        filelist = ini_file.parser._sections["%General"]
        
        istep = 0
        restigger = False
        for op,s in filelist.items():
            istep = istep + 1

            if restigger == True:
                config.set("Runonce_trigger", "started", op)
                restigger = False

            config.set("%General", op, new_scriptlist[istep-1])
            if "Restart" in new_scriptlist[istep-1]:
                restigger = True
                
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
        
        

    def runMemorythread(self):
        self.thread = QThread(parent=self)  # 開新Thread
        
        self.worker = runMemory()
        # Move worker to the thread
        self.worker.moveToThread(self.thread)
        # Connect signals and slots
        self.thread.started.connect(self.worker.runmemoryMain)
        self.worker.rebuildRunonce.connect(self.rebuildRunonce)
        self.worker.getInfoTigger.connect(self.getInfo)
        # 當收到finished, 線程結束
        
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        
        # Start the thread
        self.thread.start()


    
    
    
    # 這邊做讀寫新舊SHA，然後做紀錄
    def SHAwrite(self, remoteSHA):
        ini = self.loadini()
        
        currentSHA = ini.value("SHA/sha")
        lastSHA = ini.value("Last_SHA/last_sha")
        
        if (currentSHA == "" and lastSHA == ""):
            ini.setValue("SHA/sha", remoteSHA)
            ini.setValue("Last_SHA/last_sha",remoteSHA)
        elif(currentSHA != "" and currentSHA != remoteSHA):
            ini.setValue("Last_SHA/last_sha", currentSHA)
            ini.setValue("SHA/sha", remoteSHA)
            
            
        



    # def get_list_item(self, endTigger):
        
    #     try:
    #         if endTigger == True:
    #             self.renew_ini()
    #             branch_input = self.lineEdit.text()
    #             SHA_input = self.lineEdit_2.text()

    #             setting = self.loadini()
    #             setting.setValue("Branch/branch", branch_input)
    #             setting.setValue("SHA/SHA", SHA_input)

    #             folderpath = setting.value("Folder/path")
                
    #             for i in range(self.listWidget.count()):
    #                 #res = yield self.listWidget.item(i)
    #                 scriptname = str(self.listWidget.item(i).text())

    #                 file_path = folderpath + "/" + scriptname
                    

    #                 if scriptname != "":
                        
    #                     if "0-1_NVMe_Preparation_2269" in file_path:

    #                         if branch_input == "":

    #                             branch_input = ""

    #                         if SHA_input == "":

    #                             SHA_input = ""

    #                         procress = subprocess.run([file_path, branch_input, SHA_input])

    #                         if self.checkBox.isChecked():
    #                             command = use_inbox_delete_smi_driver_tp.main()
    #                             print(123)

    #                     elif "Restart" in file_path:

    #                         setting.setValue("Runonce_trigger/tigger", "1")
    #                         self.create_batch_run(Main.wrapper_path)
    #                         self.reboot_reg(Main.wrapper_path)
    #                         procress = subprocess.run([file_path])

    #                         break

    #                     else:

    #                         procress = subprocess.run([file_path])

    #                     if procress.returncode == 0:
    #                         pass
    #                     else:
    #                         print("Got return code not success.")
    #                         print(procress.stdout)
    #         else:
                
    #             print("endTigger recived None")


    #     except Exception:

    #         Log_Format = "%(levelname)s %(asctime)s - %(message)s"
    #         real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    #         log_name = Main.wrapper_path+"/log/"+real_time+"_logfile.log"
    #         logging.basicConfig(filename = log_name,
    #                             filemode = "w",
    #                             format = Log_Format, 
    #                             level = logging.DEBUG)

    #         logger = logging.getLogger()

    #         #Testing our Logger

    #         logger.error("Error Message from get_list_item", exc_info=True)
         
         

class getSHA(QThread):
    
    finished = pyqtSignal()

    endTigger = pyqtSignal(bool)
    
    SHAreturn = pyqtSignal(str)
    
    # Write SHA to main thread
    SHAwrite = pyqtSignal(str)
    
    def __init__(self, parent=None):
        QThread.__init__(self, parent=parent)
        
        

    def checkBranch(self, real_time, branch):
        print("\nChecking branch...\n")

        # Get the latest SHA of github
        remoteSHA = str(subprocess.check_output("git rev-parse " + str(branch)))
        remoteSHA = remoteSHA.replace("b'", "")
        remoteSHA = remoteSHA[:8]   # Get former 8 SHA codes
        
        localSHA = str(subprocess.check_output("git rev-parse HEAD"))
        localSHA = localSHA.replace("b'", "")
        localSHA = localSHA[:8]

        print("remote SHA: ", remoteSHA)
        print("local SHA: ", localSHA)
        
        if((remoteSHA) == (localSHA)):  # Check SHA of 2 side
            print("\'Remote】\' and \'Loacal\' are \'same\' branch.")
            self.SHAwrite.emit(str(remoteSHA))
            #return False    # 會循環印，但不會寫入到log.txt
            return True    # 不會循環印
        else:
            print("\'Remote\' and \'Loacal\' are \'different\' branch.")
            #self.gitPull()

        # return SHA
        self.writeSHA(real_time, remoteSHA, localSHA)
        Main.SHA = str(remoteSHA)
        print("Main.SHA: ", Main.SHA)
        
        # using signal write to main thread 
        self.SHAwrite.emit(str(remoteSHA))
        return True
        
    # Write SHA info into SHA.log
    def writeSHA(self, real_time, remoteSHA, localSHA):
        with open(Main.wrapper_path+"/auto_log/"+ real_time +"_SHA_log.log", "w") as file:
            file.write(real_time + ": \n")
            file.write("remote SHA: " + remoteSHA + "\n")
            file.write("local SHA:  " + localSHA + "\n\n")


    def gitPull(self):
        subprocess.call("git fetch -p")
        subprocess.call("git pull") 


    def gitPush(self):
        subprocess.call("git add .")
        subprocess.call("git commit -am \"File modified.\"")
        subprocess.call("git push")


    def gitCheck(self):
        subprocess.call("git --version")
        subprocess.call("git status")


    def showFile(self):
        subprocess.call('dir', shell=True, cwd = 'D:/Tinghao.Chen/Desktop/SMIGIT') 
        subprocess.call('dir', shell=True) 


    def gotoPath(self, gitPath):
        print("now in the gotoPath of getSHA")
        os.chdir(gitPath)
        # os.chdir('D:/SourceCode_SM2269')
        cwd = os.getcwd() 
        print("Current working directory is:", cwd)
        

    def gitLog(self):
        logInfo = str(subprocess.check_output("git log -p -1"))
        logInfo = logInfo.split("\\n")
        

        with open(Main.wrapper_path + "\log.txt", "w") as file:     # 使用此路徑來讀寫
            #file.write(logInfo)
            for line in logInfo:
                file.write(line)
                file.write("\n")
        
        print("Wrapper_path: ", Main.wrapper_path)
        
        # 抓出關鍵字
        with open(Main.wrapper_path + "\log.txt", "r") as read:
            for line in logInfo:
                if "Author" in line:
                    print("Author info: ", line)
                    break
                    
            
            #readfile = read.readlines()[19]
            
        #print("Author: " + readfile)
        
        return True
        
        
    def main(self, gitPath, branch):
        try:
            print("In getSHA_main")
            #counter for recording revursion (這邊先註解掉，因為會害程式卡住)
            if counter >= 1000:
                #重開機
                #restart()   # 重啟?!?!
                print("Restart")
                #pass
            else:
                print("counter += 1")
                #pass
            
            real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            # Go to directory (git repository)
            print("calling gotoPath...")
            print("gitPath:", gitPath)
            self.gotoPath(gitPath)
            print("After gotoPath calling...")
            # showFile()
            # gitCheck()

            # Get SHA
            compareTigger = self.checkBranch(real_time, branch) # 注意版本要打對(在ini裡面改即可)
            
            if compareTigger == True:
                tiggerList = self.gitLog()
                
                self.endTigger.emit(tiggerList)
                
                self.finished.emit()
            else:
                
                for i in range(3):
                    if Main.stopmissionFlag == True:
                        break
                    else:
                        time.sleep(1)
                        
                if Main.stopmissionFlag == True:
                    self.finished.emit()
                else:   
                    self.main(gitPath, branch)
            
        except Exception:

            Log_Format = "%(levelname)s %(asctime)s - %(message)s"
            real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            log_name = Main.wrapper_path+"/log/"+real_time+"_logfile.log"
            logging.basicConfig(filename = log_name,
                                filemode = "w",
                                format = Log_Format, 
                                level = logging.DEBUG)

            logger = logging.getLogger()
            logger.error("Error Message from Class of getSHA", exc_info=True)
            self.finished.emit()
            
        

class runBatchcommand(QThread):
    
    finished = pyqtSignal()
    
    loopTigger = pyqtSignal(str)
    
    restartTigger = pyqtSignal(str)
    
    
    def __init__(self, parent=None):
        QThread.__init__(self, parent=parent)
    
    
    def mainWork(self, endTigger, folderpath, listWidget_count, scriptList, branch_input, SHA_input, gitPath):

        try:
            if endTigger == True:
                


                #folderpath = setting.value("Folder/path")
                
                for i in range(listWidget_count):
                    #res = yield self.listWidget.item(i)
                    stopFlag = Main.stopmissionFlag
                    
                    time.sleep(3)
                    if stopFlag == False:
                        scriptname = str(scriptList[i])

                        file_path = folderpath + "/" + scriptname
                        

                        if scriptname != "":
                            
                            if "0-1_NVMe_Preparation" in file_path:

                                if branch_input == None:

                                    branch_input = ""

                                if SHA_input == None:

                                    SHA_input = ""
                                    
                                if branch_input != "" and SHA_input != "":
                                    branch_input = ""

                                print("Before run 0-1 batch file!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                procress = subprocess.run([file_path, branch_input, SHA_input]) # 卡住不動5分鐘的話就timeout
                                
                                print("After run 0-1 batch file!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                                                   
                                # i.replace("\r\n", "")  #替換特定字串用
                                # let decode useless or not
                                str_List = str(procress.stdout).split('\r\n\r\n')   
                                # str_List = str(procress.stdout).split('\r\n\r\n') 

                                print("After The decode!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

                                # Write batch output into CMD_MSG.log (寫入)
                                real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
                                with open(Main.wrapper_path+"/auto_log/"+ real_time +"_CMD_MSG.log", "w") as dataWrite:
                                    print("Writing str_List into data.log")
                                    for line in str_List:
                                        dataWrite.write(line)
                                        dataWrite.write("\n")
                                                         
                                

                                if checkedFlag == True:   #if global checkbox is true...
                                    
                                    command = use_inbox_delete_smi_driver_tp.main()     # delete driver
                                    
                                    if command == True:
                                        pass
                                    else:
                                        # ADD error handle
                                        self.finished.emit()
                                        break
                                    

                            elif "Restart" in file_path or "restart" in file_path:
                                
                                nextScript=str(scriptList[i+1])
                                
                                self.restartTigger.emit(nextScript)
                                while True:
                                    if Main.eventloop == True:
                                        break
                                    else:
                                        time.sleep(1)
                                        
                                procress = subprocess.run([file_path])

                                break

                            else:

                                procress = subprocess.run([file_path], timeout=300)

                            if procress.returncode == 0:
                                pass
                            else:
                                print("Got return code not success.")
                                print(procress.stdout)
                    else:
                        
                        
                        break
                
            else:
                
                print("endTigger recived False")
                

            
            
        except Exception:

            Log_Format = "%(levelname)s %(asctime)s - %(message)s"
            real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            log_name = Main.wrapper_path+"/log/"+real_time+"_logfile.log"
            logging.basicConfig(filename = log_name,
                                filemode = "w",
                                format = Log_Format, 
                                level = logging.DEBUG)

            logger = logging.getLogger()

            #Testing our Logger

            logger.error("Error Message from get_list_item", exc_info=True)
        
        if stopFlag == False:
            self.loopTigger.emit(gitPath)
        else:
            self.finished.emit()



class runMemory(QThread):
    
    finished = pyqtSignal()
    
    rebuildRunonce = pyqtSignal()

    getInfoTigger = pyqtSignal()
    
    def __init__(self, parent=None):
        QThread.__init__(self, parent=parent)
    
    
    def runmemoryMain(self):
        
        try:
            config = configparser.ConfigParser()
            config.read(Main.wrapper_path+'/config.ini')

            tigger = config['Runonce_trigger']['tigger']
            path = config['Folder']['path']
            path = path.replace("/", "\\")
            started_tigger = False
            if tigger == "1":
                print("RunOnce Trigger == 1")
                started = config['Runonce_trigger']['started']
                filelist = config['%General']
                for key in filelist:
                    keyFile = config['%General'][key]
                    print(keyFile)
                    if keyFile == started:
                        print("key == started1")
                        started_tigger = True
                        # print(key)
                        # print(config['%General'][key])
                    if started_tigger == True:
                        print("started_tigger == True")
                        next_file = config['%General'][key]
                        next_file = next_file.split(".")[0]
                        print("Run on next file or script : " + next_file)
                        #print(path+"\\"+next_file+".bat")
                        #r = subprocess.run(["cd", "/d", path], stdout=subprocess.PIPE)
                        self.rebuildRunonce.emit()
                        r = subprocess.run([path+"/"+next_file+".bat"], stdout=subprocess.PIPE, shell=True)

                        if r.returncode != 0:
                            print("Got return code not success.")
                            print(r.stdout)


                
                
                # def rebuildRunonce():
                #     config.set('Runonce_trigger',"tigger", "0")

                #     newini = open(Main.wrapper_path+'/config.ini', 'w')
                #     config.write(newini)
                #     newini.close

        except Exception:

            Log_Format = "%(levelname)s %(asctime)s - %(message)s"
            real_time = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            log_name = Main.wrapper_path+"/log/"+real_time+"_logfile.log"
            logging.basicConfig(filename = log_name,
                                filemode = "w",
                                format = Log_Format, 
                                level = logging.DEBUG)

            logger = logging.getLogger()

            #Testing our Logger

            logger.error("Error Message from run_memory", exc_info=True)

        self.getInfoTigger.emit()
        self.finished.emit()
        
        
if __name__ == '__main__':
    # 防止程式整個崩潰掉
    sys.setrecursionlimit(100000)  
    
    app = QtWidgets.QApplication(sys.argv)
    window = Main()
    window.show()
    sys.exit(app.exec_())
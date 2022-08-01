from email.message import EmailMessage
import smtplib



# 資料設定
email_sender = "你的帳號@gmail.com"
email_receiver = "tinghao.chen@siliconmotion.com"
email_password = "系統產生的應用程式密碼" 



# 下面這兩種寫法都會錯
#email_password = "原本的google密碼"
#email_password = os.environ.get('EMAIL_PASSWORD')



# 標題與內文
subject = "Hello, this is email testing"
body = """I've just sent you an email message for testing!"""



# 建立訊息物件，利用物件建立基本設定
em = EmailMessage()
em["From"] = email_sender
em["To"] = email_receiver
em["Subject"] = subject
em.set_content(body)



# 寄信
try:
    with smtplib.SMTP('smtp.gmail.com', 587, timeout = 120) as smtp:    # 用SMTP_SSL也會出錯
        smtp.starttls()                                                 # 連server
        smtp.login(email_sender, email_password)                        # 登入帳密
        smtp.sendmail(email_sender, email_receiver, em.as_string())     #寄信
        print("Send successfully!")
except:
    print("Send failed......   connection error!")
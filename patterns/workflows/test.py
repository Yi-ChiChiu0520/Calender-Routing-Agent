import smtplib

sender = "ethanchiu940520@gmail.com"
password = "nrpp ssje cfuf wrxm"
receiver = "chiuetha@usc.edu"

msg = "Subject: Test\n\nThis is a test email."

with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
    smtp.starttls()
    smtp.login(sender, password)
    smtp.sendmail(sender, receiver, msg)
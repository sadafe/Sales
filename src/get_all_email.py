from database import EmailDatabase

db = EmailDatabase()
emails = db.get_all_emails()
with open('all_emails.txt', 'w', encoding='utf-8') as file:
    for email_info in emails:
        print(f"{email_info['company_name']} - {email_info['email']}")
        file.write(f"{email_info['company_name']} - {email_info['email']}\n")
print('All emails write in all_emails.txt file')

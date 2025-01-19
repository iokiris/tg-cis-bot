import csv


def save_top_100(filename, top_100):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ID', 'Name', 'Referrals']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for user in top_100:
            writer.writerow({'ID': user[0], 'Name': user[1], 'Referrals': user[2]})


def save_all_users(filename, all_users):
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['ID', 'Name', 'Referrals']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for user in all_users:
            writer.writerow({'ID': user[0], 'Name': user[1], 'Referrals': user[2]})

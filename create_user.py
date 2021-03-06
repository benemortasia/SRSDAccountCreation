#!/usr/bin/env python
import logging
import datetime
import string
import os.path
import glob
import sys
import getpass
from logging.handlers import RotatingFileHandler
from re import compile
from bisect import bisect_left, insort_left
from random import randint, SystemRandom
from collections import deque, OrderedDict
from subprocess import call
# from time import sleep

# installed dependencies
import requests
import pysftp
from profanityfilter import ProfanityFilter
from ldap3 import Server, Connection, NONE, SUBTREE
# from selenium import webdriver
# from selenium.common.exceptions import TimeoutException
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By

__author__ = 'Jordan Page'
__license__ = 'MIT'
__version__ = '1.0.1'
__email__ = 'jpage628@gmail.com'
__date__ = '8/21/2019'
__status__ = 'Development'


def create_student(information_list, grade_level_list):
    while True:
        logging.info("Enter the student's First name: ")
        first_name = input().strip()
        while check_name(first_name) is False:
            logging.info("A name must be alphabetical, or contain hyphens, spaces, or apostrophes.")
            logging.info("Enter the student's First name: ")
            first_name = input().strip()

        logging.info("Enter the student's Last name: ")
        last_name = input().strip()
        while check_name(last_name) is False:
            logging.info("A name must be alphabetical, or contain hyphens, spaces, or apostrophes.")
            logging.info("Enter the student's Last name: ")
            last_name = input()

        while True:
            try:
                logging.info("Enter the student's Grade level (-2 - 12): ")
                grade_level = int(input())
            except ValueError:
                logging.info("The grade level must be a number (-2 - 12).")
                continue
            break

        while grade_level not in range(-2, 13):
            logging.info("The grade level must be between -2 and 12.")
            logging.info("Enter the student's Grade level (-2 - 12): ")

            try:
                grade_level = int(input())
            except ValueError:
                logging.info("The grade level must be a number (-2 - 12).")
                continue

        graduation_year = (datetime.date.today().year + (12 - grade_level))
        first_name_split = split_name(first_name)
        last_name_split = split_name(last_name)
        grade_level_list.append(grade_level)

        username_list = usernames_from_sftp()[0]

        if len(last_name_split) >= 5:
            candidate = (str(graduation_year)[2:] + last_name_split[:5] + first_name_split[0]).lower()
            while check_name_in_ldap(candidate) is False:
                candidate = \
                    resolve_username(candidate, username_list, first_name_split, last_name_split[:5], graduation_year,
                                     'student')
        else:
            candidate = (str(graduation_year)[2:] + last_name_split + first_name_split[0]).lower()
            while check_name_in_ldap(candidate) is False:
                candidate = \
                    resolve_username(candidate, username_list, first_name_split, last_name_split, graduation_year,
                                     'student')

        logging.info('\nCandidate username is: ' + candidate)

        word_list = make_word_file()

        secure_random = SystemRandom()
        first_word = secure_random.choice(word_list).strip()
        second_word = secure_random.choice(word_list).strip()

        # check if the password is either too long or contains profanity
        pf = ProfanityFilter()
        while len(first_word + second_word) > 10 or len(first_word + second_word) < 6 or \
                "'" in first_word or "'" in second_word or pf.is_profane(first_word) or pf.is_profane(second_word):
            first_word = secure_random.choice(word_list).strip()
            second_word = secure_random.choice(word_list).strip()

        pwd = (first_word + second_word + str(randint(0, 9)) + str(randint(0, 9)))

        full_name = first_name.title() + ' ' + last_name.title()
        email = candidate + "@xyz.org"
        logging.info("\nInformation:")
        information =\
            pwd + ',' + candidate + ',' + full_name + ',' + last_name.title() + ',' + first_name.title() + ',' + email
        logging.info(information)

        logging.info("\nDo you want to keep creating student accounts?(y/n): ")
        user_prompt = input().lower()
        while not ((user_prompt == 'y') or (user_prompt == 'yes') or
                   (user_prompt == 'n') or (user_prompt == 'no')):
            logging.info("You must enter y, yes, n, or no.")
            logging.info("Do you want to keep creating student accounts?(y/n): ")
            user_prompt = input().lower()
        if (user_prompt == 'y') or (user_prompt == 'yes'):
            information_list.append(information)
            continue
        elif (user_prompt == 'n') or (user_prompt == 'no'):
            information_list.append(information)
            return information_list, grade_level_list


# Simply checks a given name to see if it only contains
# alphabetical characters, hyphens, spaces, or apostrophes
def check_name(name):
    allowed_chars = string.ascii_letters + "'- "
    if name == '':
        return False

    for letter in name:
        if letter in allowed_chars:
            continue
        else:
            return False

    return True


# Ensure that the given first or last name splits before a hyphen, space, or apostrophe
def split_name(name):
    return name.split(None, 1)[0]


def usernames_from_sftp():
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    # *** ENTER FTP USERNAME AND PASSWORD HERE
    srv = pysftp.Connection(host='www.xxx.yyy.zzz', username='myname', password='mysecretpassword', port=22, cnopts=cnopts)
    srv.get('/sample.csv', preserve_mtime=True)

    srv.close()
    sis_user_list_path = os.path.join(os.getcwd(), 'sample.csv')
    sis_user_list = dict()
    needs_username_list = []
    wrong_web_id = dict()
    pattern = compile(r'^\d\d[a-zA-Z]{2,6}')

    with open(sis_user_list_path, mode='r', encoding='utf-8') as f:
        for line in f.readlines():
            curr_username = str(line.split(',')[2]).lower()
            first_name = str(line.split(',')[0]).title()
            last_name = str(line.split(',')[1]).title()
            curr_grade = str(line.split(',')[3]).strip()
            birthday = str(line.split(',')[4]).strip()
            student_id = str(line.split(',')[5]).strip()

            if int(curr_grade) < -2:
                continue
            if (int(curr_grade) == -1):
                curr_grade = 'PK4'
            elif (int(curr_grade) == -2):
                curr_grade = 'PK3'
            if "'" in curr_username:
                curr_username = curr_username.replace("'", "")
            if " " in curr_username:
                curr_username = curr_username.replace(" ", "")

            if curr_username == '':
                needs_username_list.append([first_name, last_name, curr_grade, birthday, student_id])
            elif not pattern.fullmatch(curr_username):
                wrong_web_id[curr_username] = \
                    [split_name(first_name), split_name(last_name), curr_grade, birthday, student_id]
            else:
                sis_user_list[curr_username] = [first_name, last_name, curr_grade, birthday, student_id]
        f.close()

    logging.info('\nStudent list successfully obtained via SFTP.\n')

    logging.info('Students who need SIS usernames: ')
    # Issue is here, str(curr_grade) is pulling the last curr_grade as opposed to the grade associated with each student
    # Think that should work but not sure until it's run  Missed a parenthesis smiling 
    for student in needs_username_list:
        logging.info(student[0] + ' ' + student[1] + ', Grade ' + str(student[2]))
    logging.info('\n')

    logging.info("Students with incorrect web ID's: ")
    for student in wrong_web_id:
        logging.info(student)
    logging.info('\n')
    if len(wrong_web_id) > 0:
        new_web_id = []
        for student in wrong_web_id.keys():
            if user[2] == 'PK3':
                graduation_year = datetime.date.today().year + 14
            elif user[2] == 'PK4':
                graduation_year = datetime.date.today().year + 13
            else:
                graduation_year = (datetime.date.today().year + (12 - int(user[2])))
                new_web_id.append(resolve_username(student, sis_user_list, wrong_web_id[student][0],
                                               wrong_web_id[student][1], graduation_year, student))
        logging.info("Recommended new web ID's: ")
        for student in new_web_id:
            logging.info(student)
        logging.info('\n')
        
    return sis_user_list, needs_username_list


def compare_to_ldap(sis_users, needs_sis_username=0):
    server = Server(host='www.xxx.yyy.zzz', port=636, use_ssl=True, get_info=NONE)
    # logging.info('Please enter your LDAP username: ')
    login_name = 'myname'
    password = 'supersecretpassword'
    attempts = 0
    conn = Connection(server, user='cn=' + login_name + ',o=xyz', password=password)
    conn.bind()

    while conn.result['description'] == 'invalidCredentials':
        logging.info('Incorrect username or password. Please try again.')
        logging.info('Please enter your LDAP username: ')
        login_name = str(input())
        password = getpass.getpass()
        attempts += 1
        if attempts >= 3:
            sys.exit(0)
        conn = Connection(server, user='CN=' + login_name + ',o=xyz', password=password)
        conn.bind()

    logging.info('LDAP Login successful')

    ldap_un_list = []

    logging.info('\n')
    search_filter = '(objectclass=Person)'
    for i in range(3, 5):
        curr_grade = 'Grade-PK' + str(i)
        search_base = 'ou=' + curr_grade + ',o=xyz'
        logging.info('Searching ' + curr_grade)
        conn.search(search_base=search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['uid'])

        for entry in conn.entries:
            uid = entry['uid'].value
            ldap_un_list.append(uid.lower())
    
    for i in range(0, 13):
        curr_grade = 'Grade-' + str(i).zfill(2)
        search_base = 'ou=' + curr_grade + ',o=xyz'
        logging.info('Searching ' + curr_grade)
        conn.search(search_base=search_base,
                    search_filter=search_filter,
                    search_scope=SUBTREE,
                    attributes=['uid'])

        for entry in conn.entries:
            uid = entry['uid'].value
            ldap_un_list.append(uid.lower())

    ldap_un_list.sort()

    # *** Add any potential chromebook enrollment accounts here if necessary. e.g., PK3 or PK4
    exclusion_list = ['PK3', 'PK4', '00', '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th', 'billybob']
    for name in exclusion_list:
        if name in ldap_un_list:
            ldap_un_list.remove(name)

    if needs_sis_username == 1:
        return ldap_un_list

    logging.info('\n' + str(len(ldap_un_list)) + ' total students in LDAP, Grades PK3-12.')
    with open('ldap_un_list.log', mode='w') as file:
        for student in ldap_un_list:
            file.write(student + '\n')
    needs_deletion = []
 
    for student in ldap_un_list:
        if student in sis_users.keys():
            continue
        needs_deletion.append(student)

    logging.info('\nStudents who need to be deleted from LDAP:')
    logging.info(needs_deletion)
    logging.info('\n' + str(len(needs_deletion)) + ' accounts recommended to be deleted.')

    needs_account = OrderedDict()
    for student in sis_users.keys():
        conn.search(search_base='o=xyz',
                    search_filter='(uid=' + student + ')',
                    search_scope=SUBTREE)
        if len(conn.entries) > 0:
            continue
        needs_account[student] = sis_users[student]

    logging.info('\nStudents who need to be added to LDAP:')
    logging.info(needs_account.keys())
    logging.info('\n' + str(len(needs_account)) + ' accounts to be created in LDAP.')

    if len(needs_deletion) == 0:
        logging.info('No accounts need to be deleted.')
    else:
        error_count = 0
        # User exists in LDAP but not SIS -> we can delete them from LDAP
        for username in needs_deletion:
            conn.search(search_base='o=xyz',
                        search_filter='(uid=' + username + ')')
            user = conn.entries[0].entry_dn
            conn.delete(user)
            if str(conn.result['description']) == 'success':
                logging.info('Success - ' + username + ' deleted.')
            else:
                logging.info('Error - ' + username + ' could not be deleted.')
                error_count += 1
            logging.info('\n')
        logging.info('\nAccount deletion process completed with ' + str(error_count) + ' errors.')

    pass_list = create_ldap_accounts(needs_account)
    update_students_in_sis(needs_account, pass_list)
    conn.unbind()


def create_ldap_accounts(user_list):
    info, pass_list = convert_information(user_list)
    grade_level_list = deque([])
    for value in user_list.values():
        grade_level_list.append(value[2])

    make_info_files(info, grade_level_list)
    make_dynamic_ctl_files(grade_level_list)
    import_using_jrb()

    return pass_list


def convert_information(user_list):
    information_list = deque([])
    pass_list = dict()
    for k in user_list.keys():
        word_list = make_word_file()

        secure_random = SystemRandom()
        first_word = secure_random.choice(word_list).strip()
        second_word = secure_random.choice(word_list).strip()

        # check if the password is either too long or contains profanity
        pf = ProfanityFilter()
        while len(first_word + second_word) > 10 or len(first_word + second_word) < 6 or \
                "'" in first_word or "'" in second_word or pf.is_profane(first_word) or pf.is_profane(second_word):
            first_word = secure_random.choice(word_list).strip()
            second_word = secure_random.choice(word_list).strip()

        pwd = (first_word + second_word + str(randint(0, 9)) + str(randint(0, 9)))
        pass_list[k] = pwd

        first_name = user_list[k][0].title()
        last_name = user_list[k][1].title()
        full_name = first_name + ' ' + last_name
        email = k + "@xyz.org"
        information = pwd + ',' + k + ',' + full_name + ',' + last_name + ',' + first_name + ',' + email

        information_list.append(information)

    return information_list, pass_list


def search(lst, item):
    item += '\n'
    i = bisect_left(lst, item)
    if i is None: return None
    
    if i != len(lst) and lst[i] == item:
        return i
    return None


# generates a new username if one is taken
def resolve_username(curr_username, username_list, first_name, last_name, graduation_year, category):
    last_name_partition = last_name
    num_attempts = 0

    logging.info(username_list)

    if category == 'student':
        #while search(username_list, curr_username) is not None:
        while curr_username in username_list:
            logging.info('\nUsername ' + curr_username + ' exists.')

            # extreme edge case - all possible usernames are taken
            if num_attempts > 15:
                logging.info('Username could not be resolved.')
                sys.exit(1)

            if len(curr_username) < 8:
                last_name_partition = last_name_partition[:-1]
                first_name_partition = first_name[:6 - len(last_name_partition)]
                curr_username = str(graduation_year)[2:] + last_name_partition + first_name_partition
                # curr_username = str(graduation_year)[2:] + last_name[:-1] + first_name[:8 - len(curr_username)]
            else:
                last_name_partition = last_name_partition[:-1]
                first_name_partition = first_name[:6 - len(last_name_partition)]
                curr_username = str(graduation_year)[2:] + last_name_partition + first_name_partition

            num_attempts += 1
    else:
        while search(username_list, curr_username) is not None:
            logging.info('\nUsername ' + curr_username + ' exists.')

            # extreme edge case - all possible usernames are taken
            if num_attempts > 15:
                logging.info('Username could not be resolved.')
                sys.exit(1)

            if len(curr_username) < 8:
                curr_username = last_name[:4] + first_name[:4]
            else:
                last_name_partition = last_name_partition[:-1]
                first_name_partition = first_name[:8 - len(last_name_partition)]
                curr_username = last_name_partition = first_name_partition

            num_attempts += 1

    logging.info('Username modified to: ' + curr_username)
    return curr_username


# Rather than pulling the word list from the website every time,
# it would be much faster to just read the list from a local txt file.
# make_word_file opens the word list file if it exists, and makes the
# file if it doesn't exist.
# returns the list of possible words
def make_word_file():
    word_list_path = os.path.join(sys.path[0], 'xxx_yyy_word_list.txt')

    try:
        f = open(word_list_path)
        word_list = f.readlines()
        f.close()
    except FileNotFoundError:
        logging.info("File not found. Generating word list file...")
        word_site = "http://svnweb.freebsd.org/csrg/share/dict/words?view=co&content-type=text/plain"
        response = requests.get(word_site)
        word_list = response.content.splitlines()

        for i in range(0, len(word_list)):
            word_list[i] = word_list[i].decode('utf-8')

        with open(word_list_path, mode='w+', encoding='utf-8') as myfile:
            myfile.write('\n'.join(word_list))

    return word_list


# Return false if the potential username is in ldap already, return true otherwise
# cn = username, ou = Grade##, o = xyz
def check_name_in_ldap(candidate):
    server = Server(host='myserver.xyz.org', port=636, use_ssl=True, get_info=NONE)
    conn = Connection(server, read_only=True)
    conn.bind()

    conn.search(search_base='o=xyz', search_filter='(uid=' + candidate + ')')
    if len(conn.entries) > 0:
        logging.info('Username exists in ldap: ')
        logging.info(conn.entries[0])
        return False
    logging.info('Username not found in ldap.')
    return True


# Creates comma delimited .dat files to import to JRB
def make_info_files(information, grade_level_list):
    file_path = 'c:\\jrb\\account_info'
    if not os.path.exists('c:\\jrb'):
        os.makedirs('c:\\jrb')

    # Delete all of the previous account info files, so that we only have accounts that need to be added
    for filename in glob.glob(file_path + '*'):
        try:
            os.remove(filename)
        except OSError:
            logging.info('File ' + filename + ' is currently in use. Close the file and try again.')

    for grade in grade_level_list:
        new_path = file_path + '_Grade' + str(grade).zfill(2) + '.dat'
        if os.path.exists(new_path):
            with open(new_path, mode='a') as f:
                f.write(information[0] + '\n')
        else:
            with open(new_path, mode='w') as f:
                f.write(information[0] + '\n')

        information.popleft()


# Dynamically creates ctl files to know which Context (Grade level) to add the students to
def make_dynamic_ctl_files(grade_level_list):
    logging.info(grade_level_list)
    dynamic_file_path = 'c:\\jrb\\dynamic_ctl_file.ctl'

    template = ['\t\tSEPARATOR=,', '\t\tSet Universal Passwords=y', '\t\tUSER TEMPLATE=Y', '\t\tUse two passes=Y', 'FIELDS', '\tPassword',
                '\tName', '\tFull Name', '\tLast Name', '\tGiven Name', '\tInternet Email Address']

    # Delete all of the dynamic ctl files, so that we only have templates for the grades we need to upload
    for filename in glob.glob('c:\\jrb\\dynamic_ctl_file*'):
        try:
            os.remove(filename)
        except OSError:
            logging.info('File ' + filename + ' is currently in use. Close the file and try again.')

    while len(grade_level_list) != 0:
        with open(dynamic_file_path, mode='w') as dynamic_file:
            dynamic_file.write('IMPORT CONTROL\n')
            dynamic_file.write('\t\tNAME CONTEXT="' + '.Grade-' + str(grade_level_list[0]).zfill(2) + '.xyz"\n')
            dynamic_file.write('\n'.join(template))

        if not os.path.exists('c:\\jrb\\dynamic_ctl_file' + '_Grade' + str(grade_level_list[0]).zfill(2) + '.ctl'):
            os.rename(dynamic_file_path, 'c:\\jrb\\dynamic_ctl_file' +
                      '_Grade' + str(grade_level_list[0]).zfill(2) + '.ctl')

        grade_level_list.popleft()


# Create user accounts through JRButils using the created info and ctl files
def import_using_jrb():
    directory = 'c:\\jrb'

    info_file_list = []
    ctl_file_list = []

    for filename in glob.glob(directory + '\\account_info_Grade*'):
        insort_left(info_file_list, filename)
    for filename in glob.glob(directory + '\\dynamic_ctl_file_Grade*'):
        insort_left(ctl_file_list, filename)

    for i in range(0, len(info_file_list)):
        curr_info_file = info_file_list[i]
        curr_ctl_file = ctl_file_list[i]
        call(['c:\\jrb\\Part_4\\jrbimprt.exe', curr_ctl_file, curr_info_file,
              '/$', '/e', '/v', '/x=10'])


# Take the newly added first graders and update SIS fields
def update_students_in_sis(user_list, pass_list):
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    # *** ENTER FTP USERNAME AND PASSWORD HERE
    srv = pysftp.Connection(host='www.xxx.yyy.zzz', username='myname', password='mysecretpassword', port=22, cnopts=cnopts)

    directory = os.getcwd()
    filename = os.path.join(directory, 'new_stds.txt')

    if len(user_list) == 0:
        logging.info('No students need to be updated.')
        return

    with open(filename, mode='a+') as new_stds:
        # new_stds.write('student_number\tWeb_ID\tWeb_Password\tAllowWebAccess\t' +
        #               'Student_Web_ID\tStudent_Web_Password\tStudent_AllowWebAccess\tLunch_ID\n')
        for k in user_list.keys():
            password = pass_list[k]
            student_number = user_list[k][4]
            new_stds.write(student_number)
            new_stds.write('\t')
            new_stds.write(str(excel_date(user_list[k][3])) + user_list[k][0][:3].lower())
            new_stds.write('\t')
            new_stds.write(student_number)
            new_stds.write('\t')
            new_stds.write('1')
            new_stds.write('\t')
            new_stds.write(k)
            new_stds.write('\t')
            new_stds.write(password)
            new_stds.write('\t')
            new_stds.write('1')
            new_stds.write('\t')
            new_stds.write(student_number)
            new_stds.write('\n')

        new_stds.close()

    srv.put(filename, '/sample.txt', preserve_mtime=True)

    srv.close()


# Generates a parent's username by converting student's birthday to Excel ordinal
def excel_date(date):
    temp = datetime.datetime(1899, 12, 31)
    delta = datetime.datetime.strptime(date, '%m/%d/%Y') - temp
    return int(delta.days) + int(int(delta.seconds) / 86400) + 1

# templates
# user[first_name, last_name, curr_grade, birthday, student_id]
# resolve_username(curr_username, username_list, first_name, last_name, graduation_year, category):
def handle_new_sis_users(needs_username_list):
    new_username_list = dict()
    empty_dict = dict()

    # temporary list to hold candidates, twin problem
    temp_list = []

    ldap_un_list = compare_to_ldap(empty_dict, 1)
    # logging.info(ldap_un_list)
    
    for user in needs_username_list:
        if user[2] == 'PK3':
            graduation_year = datetime.date.today().year + 14
            # logging.info('Graduation year is ' + str(graduation_year))
        elif user[2] == 'PK4':
            graduation_year = datetime.date.today().year + 13
            # logging.info('Graduation year is ' + str(graduation_year))
        else:
            graduation_year = (datetime.date.today().year + (12 - int(user[2])))
        first_name_split = split_name(user[0])
        last_name_split = split_name(user[1])

        if len(last_name_split) >= 5:
            candidate = (str(graduation_year)[2:] + last_name_split[:5] + first_name_split[0]).lower()
            while (candidate in ldap_un_list) or (candidate in temp_list):
                candidate = \
                    resolve_username(candidate, ldap_un_list + temp_list, first_name_split, last_name_split[:5],
                                     graduation_year, 'student')

        else:
            candidate = (str(graduation_year)[2:] + last_name_split + first_name_split[0]).lower()
            while (candidate in ldap_un_list) or (candidate in temp_list):
                candidate = \
                    resolve_username(candidate, ldap_un_list + temp_list, first_name_split, last_name_split, graduation_year,
                                     'student')

        logging.info('Successful candidate: ' + candidate)
        new_username_list[candidate] = [user[0], user[1], user[2], user[3], user[4]]
        temp_list.append(candidate)

    pass_list = create_ldap_accounts(new_username_list)
    update_students_in_sis(new_username_list, pass_list)


# main function
def create_user():
    while True:
        logging.info('\n')
        logging.info('1) Run the manual student creation utility ' +
              '(creates student in LDAP. Will have to be manually added to SIS)')
        logging.info('2) Run the automated student creation/deletion utility (also updates student info in SIS)')
        logging.info('3) Quit')
        menu_prompt = int(input().strip())
        # menu_prompt = 2

        if menu_prompt == 1:
            # print("Are you creating a student or staff account?: ")
            # user_prompt = input().lower().strip()
            # delete the line below once staff is implemented
            user_prompt = "student"

            if not (user_prompt == "student") and not (user_prompt == "staff"):
                logging.info("You must enter either student or staff.")
                continue
            else:
                if user_prompt == "student":
                    student_information_list = deque([])
                    grade_level_list = deque([])
                    information, grade_levels = create_student(student_information_list, grade_level_list)
                # else:
                #     create_staff()

                logging.info("\nWould you like to create another account?(y/n): ")
                user_prompt = input().lower().strip()
                while not ((user_prompt == 'y') or (user_prompt == 'yes') or
                           (user_prompt == 'n') or (user_prompt == 'no')):
                    logging.info("You must enter y, yes, n, or no.")
                    logging.info("Would you like to create another account?(y/n): ")
                    user_prompt = input().lower().strip()
                if (user_prompt == 'y') or (user_prompt == 'yes'):
                    continue
                elif (user_prompt == 'n') or (user_prompt == 'no'):
                    # Finally add the students that we created through this program to LDAP
                    make_info_files(information, grade_levels)
                    make_dynamic_ctl_files(grade_levels)
                    import_using_jrb()
        elif menu_prompt == 2:
            sis_user_list, needs_username_list = usernames_from_sftp()
            compare_to_ldap(sis_user_list)

            # here might work, needs to delete students who no longer attend BEFORE adding more
            if len(needs_username_list) > 0:
                handle_new_sis_users(needs_username_list)
                
            sys.exit(0)
        elif menu_prompt == 3:
            sys.exit(0)
        else:
            logging.info('Only 1, 2, or 3 may be entered.')
            continue


if __name__ == '__main__':
    log_formatter = logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s')

    logFile = 'logfile.txt'

    h1 = RotatingFileHandler(filename=logFile, mode='a', maxBytes=20 * 1024 * 1024, backupCount=2)
    h1.setFormatter(log_formatter)
    h1.setLevel(logging.DEBUG)

    h2 = logging.StreamHandler(sys.stdout)
    h2.setLevel(logging.INFO)
    h2.setFormatter(logging.Formatter('%(message)s'))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    root.addHandler(h1)
    root.addHandler(h2)

    create_user()

    for handler in root.handlers:
        handler.close()
        root.removeFilter(handler)

# Currently not in use
#
# def generate_staff_username_list():
#
# def create_staff():
#     while True:
#         print("Enter the staff's First name: ")
#         first_name = input().strip()
#         while check_name(first_name) is False:
#             print("A name must be alphabetical, or contain hyphens,spaces, or apostrophes.")
#             print("Enter the staff's First name: ")
#             first_name = input().strip()
#
#         print("Enter the staff's Last name: ")
#         last_name = input().strip()
#         while check_name(last_name) is False:
#             print("A name must be alphabetical, or contain hyphens, spaces, or apostrophes.")
#             print("Enter the staff's Last name: ")
#             last_name = input().strip()
#
#         while last_name == '':
#             print("A name cannot be empty.")
#             print("Enter the staff's First name: ")
#             last_name = input()
#
#         candidate = last_name[:4] + first_name[:4]
#         print('\n' + candidate)
#
#         username_list = generate_student_username_list()
#
#         candidate = resolve_username(candidate, username_list, first_name, last_name, 0, 'staff')
#
#         word_list = make_word_file()
#
#         secure_random = SystemRandom()78
#         first_word = secure_random.choice(word_list)
#         second_word = secure_random.choice(word_list)
#
#         # check to see if the words are profane
#         pf = ProfanityFilter()
#
#         while pf.is_profane(first_word) is True:
#             first_word = secure_random.choice(word_list)
#         while pf.is_profane(second_word) is True:
#             second_word = secure_random.choice(word_list)
#
#         pwd = (first_word.strip() + second_word.strip() +
#                str(randint(0, 9)) + str(randint(0, 9)))
#         print(pwd)
#
#         full_name = first_name.title() + ' ' + last_name.title()
#         email = candidate + "@xyz.org"
#         print("\nInformation:")
#         print(pwd + ',' + candidate + ',' + full_name + ','
#               + last_name.title() + ',' + first_name.title() + ',' + email)
#
#         print("\nDo you want to keep creating staff accounts?(y/n): ")
#         user_prompt = input().lower()
#         while not ((user_prompt == 'y') or (user_prompt == 'yes') or
#                    (user_prompt == 'n') or (user_prompt == 'no')):
#             print("You must enter y, yes, n, or no.")
#             print("Do you want to keep creating staff accounts?(y/n): ")
#             user_prompt = input().lower()
#         if (user_prompt == 'y') or (user_prompt == 'yes'):
#             continue
#         elif (user_prompt == 'n') or (user_prompt == 'no'):
#             return
# Grabs all student usernames from SIS
# def generate_student_username_list():
#     student_list_path = os.path.join(sys.path[0], 'student.export.TEXT')
#     student_username_list = os.path.join(sys.path[0], 'student_usernames.txt')
#
#     # try:
#     #     f = open(student_username_list)
#     #     l1 = f.readlines()
#     #     f.close()
#     # except FileNotFoundError:
#     #     print('\nUsername file not found.')
#
#     print('\nEnter your SIS username: ')
#     sis_username = input()
#
#     while sis_username == '':
#         print('Usernames cannot be empty.')
#         print('\nEnter your SIS username: ')
#         sis_username = input()
#
#     sis_password = getpass.getpass('SIS password: ')
#     url = 'httsis://sis.xyz.org/admin/pw.html'
#
#     # setup the browser profile so that the file downloads to the right place without asking
#     profile = webdriver.FirefoxProfile()
#     profile.set_preference('browser.download.folderList', 2)
#     profile.set_preference('browser.download.manager.showWhenStarting', False)
#     profile.set_preference('browser.download.dir', sys.path[0])
#     profile.set_preference('browser.helperApsis.neverAsk.saveToDisk', 'text/sis-export')
#     profile.set_preference('browser.helperApsis.alwaysAsk.force', False)
#     profile.set_preference('browser.helperApsis.neverAsk.openFile', 'text/sis-export')
#     profile.set_preference('browser.download.manager.useWindow', False)
#     profile.set_preference('browser.download.manager.focusWhenStarting', False)
#     profile.set_preference('browser.download.manager.alertOnEXEOpen', False)
#     profile.set_preference('browser.download.manager.showAlertOnComplete', False)
#     profile.set_preference('browser.download.manager.closeWhenDone', True)
#
#     driver = webdriver.Firefox(firefox_profile=profile,
#                                executable_path='C:\\Users\\pagejord\\PycharmProjects\\geckodriver.exe')
#     driver.get(url)
#
#     username = driver.find_element_by_name('username')
#     password = driver.find_element_by_name('password')
#     username.send_keys(sis_username)
#     password.send_keys(sis_password)
#
#     driver.find_element_by_name('LoginForm').submit()
#     delay = 10
#
#     # This is where everything gets ugly
#     # wait for the login to complete and the search button can be clicked
#     try:
#         WebDriverWait(driver, delay).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="searchButton"]')))
#     except TimeoutException:
#         print('Timed out waiting for search button to be clickable.')
#         print('Current timeout is: ' + str(delay) + ' seconds.')
#         sys.exit(1)
#
#     sleep(2)
#     # click the search button to bring up the list of all students
#     driver.find_element_by_xpath('//*[@id="searchButton"]').click()
#     sleep(2)
#
#     # wait for the dropdown menu to load before attempting to choose the Export option
#     try:
#         driver.find_element_by_xpath('//*[@id="selectFunctionDropdownButton"]').click()
#         WebDriverWait(driver, delay).until(EC.element_to_be_clickable((By.XPATH,
#                                                                        '// *[ @ id = "lnk_ExportUsingTemplate"]')))
#     except TimeoutException:
#         print('Timed out waiting for dropdown menu to load.')
#         print('Current timeout is: ' + str(delay) + ' seconds.')
#         sys.exit(1)
#
#     driver.find_element_by_xpath('// *[ @ id = "lnk_ExportUsingTemplate"]').click()
#
#     # Selects 'Students' in Export Using Template dropdown menu
#     sleep(2)
#     driver.find_element_by_xpath('/html/body/form/div[1]/div[3]/div[2]/div[3]/table/tbody/tr[2]/td[2]/select/ \
#         option[2]').click()
#
#     # wait for the new page to load, wait for "The selected students" option to load
#     try:
#         WebDriverWait(driver, delay).until(EC.element_to_be_clickable((By.XPATH, '/html/body/form/div[1]/div[3]/ \
#                                                                                      div[2]/div[3]/table/tbody/tr[4]/ \
#                                                                                      td[2]/p/input[2]')))
#     except TimeoutException:
#         print('Timed out waiting for template page to update.')
#         print('Current timeout is: ' + str(delay) + ' seconds.')
#         sys.exit(1)
#
#     # selects the "For Creating Student User Accs" template and the "All selected students" option
#     driver.find_element_by_xpath('/html/body/form/div[1]/div[3]/div[2]/div[3]/table/tbody/tr[3]/td[2]/select/ \
#         option[15]').click()
#
#     driver.find_element_by_xpath('/html/body/form/div[1]/div[3]/div[2]/div[3]/table/tbody/tr[4]/td[2]/p/input[2]') \
#         .click()
#
#     # clicks the submit button to download the list to where the Python script runs
#     driver.find_element_by_xpath('//*[@id="btnSubmit"]').click()
#
#     # make sure the export file is actually downloaded before attempting to extract anything from it
#     while True:
#         if os.path.isfile('student.export.text.part'):
#             sleep(1)
#             continue
#         break
#
#     driver.close()
#
#     # finally, we can extract the list of student usernames
#     f = open(student_list_path)
#     l1 = []
#     with open(student_username_list, mode='a+') as username_file:
#         next(f)
#         for line in f.readlines():
#             if line.split(',')[9] == '':
#                 continue
#             l1.append(line.split(',')[9])
#         l1.sort()
#         username_file.write('\n'.join(l1))
#     f.close()
#
#     return l1

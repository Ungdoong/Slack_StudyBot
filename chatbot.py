# -*- coding: utf-8 -*-
import re
import json
import urllib.request

from bs4 import BeautifulSoup
from flask import Flask, request
from slack import WebClient
from slack.web.classes import extract_json
from slack.web.classes.blocks import *
from slack.web.classes.elements import *
from slack.web.classes.interactions import MessageInteractiveEvent
from slackeventsapi import SlackEventAdapter
from datetime import datetime

SLACK_TOKEN =''
SLACK_SIGNING_SECRET =''

app = Flask(__name__)
# /listening 으로 슬랙 이벤트를 받습니다.
slack_events_adaptor = SlackEventAdapter(SLACK_SIGNING_SECRET, "/listening", app)
slack_web_client = WebClient(token=SLACK_TOKEN)

#유저 객체 클래스
class User:
    def __init__(self, user_id, channel_id, topic, study_group=None, study_pair=None):
        self.user_id = user_id
        self.channel_id = channel_id
        #topic = 'python' or 'clang' or 'java' or 'english' or 'freestudy'
        self.topic = topic
        #study_group = 그룹이 없음 : 0 or 그룹이 존재 : 1 or 그룹을 찾는 중 : 2
        self.study_group = 0 if study_group is None else study_group
        #study_group = 페어가 없음 : 0 or 페어가 존재 : 1 or 페어을 찾는 중 : 2
        self.study_pair = 0 if study_pair is None else study_pair


# 크롤링 함수 구현하기
def _crawl_study_map(text):
    # 여기에 함수를 구현해봅시다.
    if not "스터디" in text:
        return "`@<봇이름> 장소(명)스터디` 과 같이 멘션해주세요."
    else:
        query_text = urllib.parse.quote_plus(text)
        query_text = query_text.replace("%5C", "%")
        search_url = "https://search.naver.com/search.naver?sm=top_hty&fbm=0&ie=utf8&query="+query_text
        source_code = urllib.request.urlopen(search_url).read()
        soup = BeautifulSoup(source_code, "html.parser")

        room_name = []
        location = []
        call_num = []
        study_list = []
        for tag in soup.find_all("a", class_="tit _sp_each_url _sp_each_title"):
            room_name.append(tag["title"])
    # for tag in soup.find_all("span", class_="rllt__details lqhpac"):
   	# 	for t in tag.find_all("div"):
    	#    	location.append(tag.get_text().strip())
    	# search = soup.find_all("dl", class_="info_area")
    	# dd = search.find_all("dd")
    	# search = dd[1].find_all("span")
        for tag in soup.find_all("span", class_="tell"):
            call_num.append(tag.get_text().strip())
        for ten in range(len(room_name)):
            s_room = room_name[ten]  + " \n 전화번호 : "
                #+ "\n 위치: " + location[ten]\
            study_list.append(s_room)
            if ten>=5:
                break

        return '*< '+text+' 검색 결과 >*\n' + '\n'.join(room_name)


#instructions.txt의 내용을 출력하기 위한 함수
def _dis_instructions():
    inst_list = []
    with open('instructions.txt', encoding='UTF-8') as file:
        for line in file.readlines():
            inst_list.append(line)

    return ''.join(inst_list)

#카테고리 블록을 생성하는 함수
def _make_category(name):
    head_section = SectionBlock(
        text="<@"+name+">\n*< 카테고리를 선택해주세요 >*",
    )
    button_actions = ActionsBlock(
        block_id="category",
        elements = [
            ButtonElement(
                text= "Python",
                action_id="python", value="1",
            ),
            ButtonElement(
                text="C 언어",
                action_id="clang", value="2",
            ),
            ButtonElement(
                text="자바",
                action_id="java", value="2",
            ),
            ButtonElement(
                text="영어",
                action_id="english", value="3",
            ),
            ButtonElement(
                text="자율학습",
                action_id="freestudy", value="4",
            ),
        ]
    )

    return [head_section, button_actions]

#버튼을 클릭 시 실행 될 함수
def _button_response(topic, id):
    keyword_dis = ["Python", "C 언어", "자바", "영어", "자율학습","스터디 모임", "페어 스터디"]
    keywords = ['python', 'clang', 'java', 'english', 'freestudy', 'study_group', 'study_pair']
    topics = ['python', 'clang', 'java', 'english', 'freestudy']
    study_types = ['study_group', 'study_pair']
    for i in range(len(keywords)):
        if topic == keywords[i]:
            keyword_index = i

    if topic in topics:
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< "+ keyword_dis[keyword_index] + "카테고리를 선택했습니다 >*\n"
            + "*< 원하시는 형태를 선택해주세요. >*",
        )
        button_actions = ActionsBlock(
            block_id="category",
            elements=[
                ButtonElement(
                    text="스터디 모임",
                    action_id="study_group", value="11",
                ),
                ButtonElement(
                    text="페어 스터디",
                    action_id="study_pair", value="12",
                ),
            ]
        )
        return [head_section, button_actions]
    elif topic in study_types:
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< " + keyword_dis[keyword_index] + "을 선택하셨습니다 >*\n"
            + "*< " + keyword_dis[keyword_index] + " 대기열에 등록했습니다 >*\n"
            + "*< 원하는 상대를 찾으면 알려드리겠습니다 ^__^ >*"
        )
        return [head_section]
    elif topic == 'already_group':
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< 이미 그룹이 존재합니다. 그룹을 새로 찾길 원하시나요? >*\n"
        )
        button_actions = ActionsBlock(
            block_id="category",
            elements=[
                ButtonElement(
                    text="예",
                    action_id="already_group_yes", value="11",
                ),
                ButtonElement(
                    text="아니요",
                    action_id="already_group_no", value="12",
                ),
            ]
        )
        return [head_section, button_actions]
    elif topic == 'searching_group':
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< 그룹을 찾고 있습니다. 그룹찾기를 중지할까요? >*\n"
        )
        button_actions = ActionsBlock(
            block_id="category",
            elements=[
                ButtonElement(
                    text="예",
                    action_id="searching_group_yes", value="11",
                ),
                ButtonElement(
                    text="아니요",
                    action_id="searching_group_no", value="12",
                ),
            ]
        )
        return [head_section, button_actions]
    elif topic == 'already_pair':
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< 이미 페어가 존재합니다. 페어를 새로 찾길 원하시나요? >*\n"
        )
        button_actions = ActionsBlock(
            block_id="category",
            elements=[
                ButtonElement(
                    text="예",
                    action_id="already_pair_yes", value="11",
                ),
                ButtonElement(
                    text="아니요",
                    action_id="already_pair_no", value="12",
                ),
            ]
        )
        return [head_section, button_actions]
    elif topic == 'searching_pair':
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< 페어을 찾고 있습니다. 페어 찾기를 중지할까요? >*\n"
        )
        button_actions = ActionsBlock(
            block_id="category",
            elements=[
                ButtonElement(
                    text="예",
                    action_id="searching_pair_yes", value="11",
                ),
                ButtonElement(
                    text="아니요",
                    action_id="searching_pair_no", value="12",
                ),
            ]
        )
        return [head_section, button_actions]
    elif topic == 'searching_stop':
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< 매칭을 중지하였습니다 >*\n"
        )
        return [head_section]
    elif topic == 'none_user':
        head_section = SectionBlock(
            text="<@" + id + ">\n"
            +"*< 카테고리를 먼저 선택해주세요 >*\n"
        )
        return [head_section]

#CSV 파일의 유저정보를 유저객체의 리스트 형태로 변환
def load_CSV(filename):
    user_list = []
    with open(filename) as file:
        if filename == 'group_list.csv':
            group_list = []
            for line in file.readlines():
                if line != '':
                    tmp_user = line.strip().split(',')
                    if len(tmp_user) == 20:
                        user1 = User(tmp_user[0], tmp_user[1], tmp_user[2], int(tmp_user[3]), int(tmp_user[4]))
                        user2 = User(tmp_user[5], tmp_user[6], tmp_user[7], int(tmp_user[8]), int(tmp_user[9]))
                        user3 = User(tmp_user[10], tmp_user[11], tmp_user[12], int(tmp_user[13]), int(tmp_user[14]))
                        user4 = User(tmp_user[15], tmp_user[16], tmp_user[17], int(tmp_user[18]), int(tmp_user[19]))
                        group_list.append([user1,user2,user3,user4])
            return group_list
        elif filename == 'pair_list.csv':
            pair_list = []
            for line in file.readlines():
                if line != '':
                    tmp_user = line.strip().split(',')
                    if len(tmp_user) == 10:
                        user1 = User(tmp_user[0], tmp_user[1], tmp_user[2], int(tmp_user[3]), int(tmp_user[4]))
                        user2 = User(tmp_user[5], tmp_user[6], tmp_user[7], int(tmp_user[8]), int(tmp_user[9]))
                        pair_list.append((user1,user2))
            return pair_list
        else:
            for line in file.readlines():
                if line != '':
                    tmp_user = line.strip().split(',')
                    if len(tmp_user) == 5:
                        user = User(tmp_user[0], tmp_user[1], tmp_user[2], int(tmp_user[3]), int(tmp_user[4]))
                        user_list.append(user)

        return user_list

#유저 리스트를 CSV파일에 저장
def save_CSV(filename, user_list):
    with open(filename, 'w') as file:
        for user in user_list:
            string = ','.join([user.user_id, user.channel_id, user.topic, str(user.study_group),str(user.study_pair)])
            string += '\n'
            file.write(string)

def group_matching(group_wait_list, group_list):
    users_list = []
    indexes = []
    matching_flag = False

    num_wait_list = len(group_wait_list)
    last_person_topic = group_wait_list[num_wait_list - 1].topic

    for i in range(num_wait_list - 1):
        if group_wait_list[i].topic == last_person_topic:
            indexes.append(i)

        if len(indexes) >= 3:
            group_list.append(group_wait_list.pop(num_wait_list - 1))
            for j in range(3):
                group_list.append(group_wait_list.pop(indexes[2 - j]))
            matching_flag = True
            break

    return group_wait_list, group_list, matching_flag

#페어를 찾는 함수
def pair_matching(pair_wait_list, pair_list):
    matching_flag = False
    num_wait_list = len(pair_wait_list)
    last_user_topic = pair_wait_list[num_wait_list-1].topic

    for i in range(num_wait_list-1):
        if pair_wait_list[i].topic == last_user_topic:
            pair_list.append((pair_wait_list.pop(num_wait_list - 1), pair_wait_list.pop(i)))
            matching_flag = True
            break

    return (pair_wait_list, pair_list, matching_flag)

def _matching_success(type, group_list):
    if type == 'group':
        head_section = SectionBlock(
            text="<@" + group_list[0].user_id + "><@"+ group_list[1].user_id + "><@"
                 + group_list[2].user_id + "><@"+ group_list[3].user_id + ">\n"
                 + "*< 스터디 그룹을 완성했습니다! >*\n"
        )
    elif type == "pair":
        head_section = SectionBlock(
            text="<@" + group_list[0].user_id + "><@" + group_list[1].user_id + ">\n"
                 + "*< 두분은 이제 페어입니다! >*\n"
        )
    return [head_section]

def _matching_breaking(type, user_list):
    if type == 'group':
        head_section = SectionBlock(
            text="<" + user_list[0].user_id + ">, <" + user_list[1].user_id + ">. <"
                 + user_list[2].user_id + ">, <" + user_list[3].user_id + ">"
                 + "*< 스터디 그룹을 누군가 파괴했습니다^^ >*\n"
        )
    if type == 'pair':
        head_section = SectionBlock(
            text="<" + user_list[0].user_id + ">, <" + user_list[1].user_id + ">"
                 + "*< 페어가 증발했습니다^^* >*\n"
        )

    return [head_section]

# 챗봇이 멘션을 받았을 경우
@slack_events_adaptor.on("app_mention")
def app_mentioned(event_data):
    channel = event_data["event"]["channel"]
    text = event_data["event"]["text"]
    user_name = event_data["event"]["user"]
    
    matches = re.search(r"<@U\w+>\s+(.+)", text)
    if matches:
        keyword = matches.group(1)
    else:
        keyword = ''

    if keyword == '카테고리':
        category_blocks = _make_category(user_name)

        slack_web_client.chat_postMessage(
            channel=channel,
            blocks=extract_json(category_blocks)
        )
    elif keyword == '':
        keywords = _dis_instructions()
        slack_web_client.chat_postMessage(
            channel=channel,
            text=keywords
        )
    else:
        keywords = _crawl_study_map(keyword)
        slack_web_client.chat_postMessage(
            channel=channel,
            text=keywords
        )

# / 로 접속하면 서버가 준비되었다고 알려줍니다.
@app.route("/", methods=["GET"])
def index():
    return "<h1>Server is ready.</h1>"

#클릭 이벤트
@app.route("/click", methods=["GET", "POST"])
def on_button_clicked():
    #유저 정보 읽어오기 및 변수 초기화
    user_list = load_CSV('user_list.csv')
    group_list = load_CSV('group_list.csv')
    pair_list = load_CSV('pair_list.csv')
    group_wait_list = load_CSV('group_wait_list.csv')
    pair_wait_list = load_CSV('pair_wait_list.csv')
    group_matching_flag = False
    pair_matching_flag = False
    log = ''
    now = datetime.now()

    #페이로드 읽어오기
    payload = request.values["payload"]
    click_event = MessageInteractiveEvent(json.loads(payload))
    user_id = click_event.user.id
    action_id = click_event.action_id
    channel = click_event.channel.id
    
    #로그 기록
    str_log = str(now) + '\t' + user_id + " " + action_id + " 선택 ( 채널 : " + channel + " )"
    print(str_log)
    log += str_log + "\n"
    with open('log.txt', 'a') as log_file:
        log_file.write(log)
    
    #실행 위치에 따라 유저정보 업데이트
    if action_id == 'study_group':
        for user in user_list:
            if user.user_id == user_id and user.study_group == 1:
                action_id = 'already_group'
            elif user.user_id == user_id and user.study_group == 2:
                action_id = 'searching_group'
            elif user.user_id == user_id and user.study_group == 0:
                user.study_group = 2
                group_wait_list.append(user)
                #TODO:그룹 매칭 함수
                group_wait_list, group_list, group_matching_flag \
                    = group_matching(group_wait_list, group_list)
            else:
                action_id = 'none_user'
        if not user_list:
            action_id = 'none_user'
    elif action_id == 'study_pair':
        for user in user_list:
            if user.user_id == user_id and user.study_pair == 1:
                action_id = 'already_pair'
            elif user.user_id == user_id and user.study_pair == 2:
                action_id = 'searching_pair'
            elif user.user_id == user_id and user.study_pair == 0:
                user.study_pair = 2
                pair_wait_list.append(user)
                #TODO:페어 매칭 함수
                pair_wait_list, pair_list, pair_matching_flag \
                    = pair_matching(pair_wait_list, pair_list)

            else:
                action_id = 'none_user'
        if not user_list:
            action_id = 'none_user'
    elif action_id == 'already_group_yes':
        action_id = 'study_group'
        for user in user_list:
            if user.user_id == user_id and user.study_group == 1:
                user.study_group = 2
                group_wait_list.append(user)
                #TODO:그룹 매칭 함수
                group_wait_list, group_list, group_matching_flag \
                    = group_matching(group_wait_list, group_list)
            else:
                return "OK", 200
        if not user_list:
            return "OK", 200
        #TODO : 같은 그룹원에게 메시지처리함수
        #그룹 서칭
        for group in group_list:
            for member in group:
                if user_id == member.user_id:
                    breaked_group = group
        #그룹원에게 메시지
        for index in range(len(group)):
            matching_blocks = _matching_breaking("group", breaked_group)
            slack_web_client.chat_postMessage(
                channel=breaked_group[index].channel_id,
                blocks=extract_json(matching_blocks)
            )
    elif action_id == 'already_pair_yes':
        action_id = 'study_pair'
        for user in user_list:
            if user.user_id == user_id and user.study_pair == 1:
                user.study_pair = 2
                pair_wait_list.append(user)
                #TODO:페어 매칭 함수
                pair_wait_list, pair_list, pair_matching_flag \
                    = pair_matching(pair_wait_list, pair_list)
            else:
                return "OK", 200
        if not user_list:
            return "OK", 200
        #TODO : 페어에게 메시지처리함수
        for pair in pair_list:
            for member in pair:
                if user_id == member.user_id:
                    breaked_pair = pair
        #그룹원에게 메시지
        for index in range(len(pair)):
            matching_blocks = _matching_breaking("pair", breaked_pair)
            slack_web_client.chat_postMessage(
                channel=breaked_pair[index].channel_id,
                blocks=extract_json(matching_blocks)
            )
    elif action_id == 'searching_group_yes':
        action_id = 'searching_stop'
        for user in user_list:
            if user.user_id == user_id and user.study_group == 2:
                user.study_group = 0
            else:
                return "OK", 200
        if not user_list:
            return "OK", 200
    elif action_id == 'searching_pair_yes':
        action_id = 'searching_stop'
        for user in user_list:
            if user.user_id == user_id and user.study_pair == 2:
                user.study_pair = 0
            else:
                return "OK", 200
        if not user_list:
            return "OK", 200
    elif action_id == 'already_group_no':
        return "OK", 200
    elif action_id == 'already_pair_no':
        return "OK", 200
    elif action_id == 'searching_group_no':
        return "OK", 200
    elif action_id == 'searching_pair_no':
        return "OK", 200
    else:
        topic = action_id
        print(len(user_list))
        if len(user_list) > 0:
            for user in user_list:
                if user_id == user.user_id:
                    user.topic = topic
                else:
                    user_list.append(User(user_id=user_id, channel_id=channel, topic=topic))
        else:
            user_list.append(User(user_id=user_id, channel_id=channel, topic=topic))
        
    category_blocks = _button_response(action_id, user_id)
    
    slack_web_client.chat_postMessage(
        channel=click_event.channel.id,
        blocks=extract_json(category_blocks)
    )

    if group_matching_flag:
        matched_group = group_list[len(group_list) - 1]
        matching_blocks = _matching_success("group", matched_group)
        slack_web_client.chat_postMessage(
            channel=channel,
            blocks=extract_json(matching_blocks)
        )
    elif pair_matching_flag:
        matched_pair = pair_list[len(pair_list) - 1]
        matching_blocks = _matching_success("pair", matched_pair)
        slack_web_client.chat_postMessage(
            channel=channel,
            blocks=extract_json(matching_blocks)
        )

    save_CSV('user_list.csv', user_list)
    
    return "OK", 200

if __name__ == '__main__':
    app.run('127.0.0.1', port=8080)
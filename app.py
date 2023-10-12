from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from bs4 import BeautifulSoup
import requests
import os

from flask_sqlalchemy import SQLAlchemy

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
  'sqlite:///' + os.path.join(basedir, 'database.db')

db = SQLAlchemy(app)

# MBTI 검사 질문지 DB
class Question(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  title = db.Column(db.String(255))
  choose_type = db.Column(db.String(2))
  option_A = db.Column(db.String(255))
  option_B = db.Column(db.String(255))
  answer = db.Column(db.Integer)

# MBTI 검사 결과 DB
class MBTI(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  mbti_type = db.Column(db.String(100), nullable=False)
  description = db.Column(db.String(10000), nullable=False)
  book = db.Column(db.String(100), nullable=False)
  
# 책 매장 검색 결과 DB
class Store(db.Model):
  Id = db.Column(db.String(255), primary_key=True)
  title = db.Column(db.String(255))
  price = db.Column(db.String(255))
  offCode = db.Column(db.String(255))
  offName = db.Column(db.String(255))
  link = db.Column(db.String(255))

with app.app_context():
  db.create_all()

@app.route("/main")
def main():
  # 가져올 베스트셀러 권 수 (디폴트 4권)
  numOfBook = 4
  # 가져올 날짜 ('YYYY-MM-DD', 공백시 오늘날짜)
  date = ''

  # 날짜 구하기
  inputDate = datetime.strptime(date, "%Y-%m-%d") if date != '' else datetime.today()
  def getDate(inputDate):
    date = inputDate.strftime("%Y-%m-%d").split('-')
    year, month = date[0], date[1]
    firstDay = inputDate.replace(day=1)
    week = (inputDate - firstDay).days // 7 + 1
    return year, month, week

  # 구한 날짜로 해당 주의 베스트셀러 불러오기
  year, month, week = getDate(inputDate)
  res = requests.get(f"https://www.aladin.co.kr/ttb/api/ItemList.aspx?ttbkey=ttbgarry94571426002&QueryType=Bestseller&MaxResults={numOfBook}&start=1&SearchTarget=Book&output=js&Year={year}&Month={month}&Week={week}&Version=20131101")
  rjson = res.json()
  context = rjson['item']
  return render_template("main.html", data=context)

@app.route("/team")
def team():
  return render_template("team.html")

# MBTI 결과 계산 함수
def calculate_mbti():
  types = {}  # 각 choose_type에 대한 누적 점수를 저장할 딕셔너리
  questions = Question.query.all()

  # 모든 질문에 대해 choose_type에 따라 누적 점수 계산
  for question in questions:
    if question.choose_type not in types:
      types[question.choose_type] = 0
    types[question.choose_type] += question.answer

  # 각 choose_type의 누적 점수가 양수면 두 번째 글자를 사용, 음수면 첫 번째 글자 사용
  mbti_result = ""
  for choose_type, score in types.items():
    if score >= 0:
      mbti_result += choose_type[1]
    else:
      mbti_result += choose_type[0]

  return mbti_result

@app.route("/test")
def test():
  # 첫번쨰 질문만 제시, 다음 이어지는 질문들을 가져오는건 일단은 answer에서 진행 (개선 예정)
  question = Question.query.first()
  return render_template("test.html", data=question)

@app.route("/answer", methods=["POST"])
def answer():
  question_id = request.form['question_id']
  selected_option = request.form['option']  # 선택된 옵션 (A 또는 B)
  question = Question.query.get(question_id)

  # 사용자의 선택에 따라 answer 값을 저장
  if selected_option == 'A':
    question.answer = -1
  elif selected_option == 'B':
    question.answer = 1
  db.session.commit()

  # 다음 질문 가져오기 (id값 대조)
  next_question = Question.query.filter(Question.id > question.id).first()
  # 다음 질문이 있으면 진행, 아니면 MBTI 계산
  if next_question:
    return render_template('test.html', data=next_question)
  else:
    calculated_mbti = calculate_mbti()
    answer = MBTI.query.filter_by(mbti_type=calculated_mbti).first()
    return render_template("answer.html", data=answer)


@app.route("/result")
def result():
  mbti_res = MBTI.query.all()
  return render_template("result.html", data=mbti_res)


@app.route("/map")
def map():
    store = Store.query.all()

    return render_template("map.html", data=store)

@app.route("/map/store/")
def map_store():
    TTB_Key = 'ttbkjw12431355001'
    Title = '혼자 공부하는 파이썬 - 1:1 과외하듯 배우는 프로그래밍 자습서, 개정판'
    URL = f'http://www.aladin.co.kr/ttb/api/ItemSearch.aspx?ttbkey={TTB_Key}&Query={Title}&QueryType=Title&MaxResults=3&start=1&SearchTarget=Book&output=xml&Version=20131101'

    # API로 데이터 불러오기
    rq = requests.get(URL)
    soup = BeautifulSoup(rq.text, 'xml')

    isbn = ""
    title = ""
    price = ""

    for item in soup.find_all('item'):
        isbn = item.find('isbn').text
        title = item.find('title').text
        price = item.find('priceSales').text

    URL2 = f'http://www.aladin.co.kr/ttb/api/ItemOffStoreList.aspx?ttbkey={TTB_Key}&itemIdType=ISBN&ItemId={isbn}&output=xml'
    rq2 = requests.get(URL2)
    soup2 = BeautifulSoup(rq2.text, 'xml')

    offStoreInfo_elements = soup2.find_all('offStoreInfo')

    for offStoreInfo in offStoreInfo_elements:
        offCode = offStoreInfo.find('offCode').text
        offName = offStoreInfo.find('offName').text
        link = offStoreInfo.find('link').text

    # 데이터를 DB에 저장하기
    # 수정된 부분: request.args를 사용하여 데이터 받기
    isbn_receive = isbn
    title_receive = title
    price_receive = price
    offCode_receive = offCode
    offName_receive = offName
    link_receive = link
    
    existing_store = Store.query.filter_by(Id=isbn_receive).first()
    if existing_store:
    # 이미 존재하는 레코드가 있는 경우 업데이트
      existing_store.title = title_receive
      existing_store.price = price_receive
      existing_store.offCode = offCode_receive
      existing_store.offName = offName_receive
      existing_store.link = link_receive
    else:
    # 새로운 레코드 추가
      stor = Store(Id=isbn_receive, title=title_receive, price=price_receive, offCode=offCode_receive, offName=offName_receive, link=link_receive)
      db.session.add(stor)

    db.session.commit()
    

    return redirect(url_for('map'))  # 수정된 부분: url_for() 인자 수정

if __name__ == "__main__":
  app.run(debug=True)
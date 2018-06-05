from django.shortcuts import render
from django.conf import settings
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse
from django.core import serializers
from django.views.decorators.csrf import csrf_exempt

import re
import imgkit
import string
import random
from PIL import Image
from lxml.html import fromstring
import json
from bs4 import BeautifulSoup
import urllib3
import apiai
import requests
import base64
from datetime import datetime
from dfchatbox.models import Procedure
from haystack.query import SearchQuerySet

# Create your views here.
# -*- coding: utf-8 -*-

@require_http_methods(['POST','GET'])
def index(request):
	if request.method == 'POST':
		message = request.POST['message']
		sessionID = request.POST['sessionID']

		print("*****SESSION ID*****   ",sessionID)
		if(message=="pomoč"):
			help ="<b>Da vam pomagam najti razpoložljivo storitev potrebujem naslednje informacije:<br><em>-kateri poseg iščete (npr. pregled kolka)<br><em>-v kateri regiji iščete (npr. Gorenjska)<br><em>-kako nujno potrebujete poseg (npr. redno)<br><br><small>Vendar ne skrbite za regijo in nujnost vas bom povprašal sam.<br>Vi mi samo povejte katero storitev iščete."
			return HttpResponse('{{"text_answer":"{0}","response_type":"{1}","data":"{2}"}}'.format(help,"none",[]))
		message=translate(message)

		#print("user input: ", message)

		# url = "http://translate.dis-apps.ijs.si/translate?sentence=" + message

		# response = requests.get(url)
		# translation = response.text[1:-3]

		# if translation != "":
		# 	message = translation

		## TODO:
		## prepoznavanje regije?
		print("message:",message)
		if not hasNumbers(message) and message.find("NONE") < 0:
			if checkRegion(message):
				whoosh_data = whoosh(message)
				print(whoosh_data)
				if len(whoosh_data) > 1:
					return HttpResponse('{{"text_answer":"{0}","response_type":"{1}","data":"{2}"}}'.format("Ste mislili:","procedures",whoosh_data))

		print(message)

		#THINKEHR
		#CLIENT_ACCESS_TOKEN = "631305ebeec449618ddeeb2f96a681e9"
		#WAITING LINES
		CLIENT_ACCESS_TOKEN = "15bddeda0b5246cba6cd27fcd67576a3"
		#MyEHR
		#CLIENT_ACCESS_TOKEN = "7f7cb0e7be2e4b83b08b7106485a2078"

		contexts = []

		ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

		request = ai.text_request()
		request.session_id = sessionID
		request.lang = 'en'
		request.contexts = contexts
		request.query = message

		data = request.getresponse().read().decode('utf-8')

		answer_json = json.loads(data)

		print(answer_json)

		text_answer = answer_json['result']['fulfillment']['messages'][0]['speech']

		#text_answer = text_answer.replace('\\','\\\\')

		print(text_answer)

		data = ""
		response_type = ""
		url = ""

		if 'data' in answer_json['result']['fulfillment']:
		    data = answer_json['result']['fulfillment']['data']['data']
		    response_type = answer_json['result']['fulfillment']['data']['responseType']
		    print("RESPONSE TYPE: ",response_type)
		    url = answer_json['result']['fulfillment']['data']['url']
		    if url[:5] != "https":
		    	url = "https:" + url[5:]

		    

		if text_answer == "Kako hitro potrebujete poseg?":
			print("A")
			urgencies = [{"name":"Zelo hitro","value":"Very fast"},{"name":"Redno","value":"normal"},{"name":"Hitro","value":"fast"}]
			return HttpResponse('{{"text_answer":"{0}","response_type":"{1}","data":"{2}"}}'.format("Kako hitro potrebujete poseg?","procedures",urgencies))

		if text_answer == "V kateri regiji iščete?":
			print("A")
			regions = [{ "name": "Vse regije", "value": "all regions" }, { "name": "Gorenjska regija", "value": "Gorenjska" }, { "name": "Goriška regija", "value": "Goriska" }, { "name": "Jugovzhodna Slovenija", "value": "Southeast" }, { "name": "Koroška regija", "value": "Koroška" }, { "name": "Obalno-kraška regija", "value": "Obalno-Kraska" }, { "name": "Osrednjeslovenska regija", "value": "Ljubljana" }, { "name": "Podravska regija", "value": "Podravska" }, { "name": "Pomurska regija", "value": "Pomurje" }, { "name": "Posavska regija", "value": "Posavska region" }, { "name": "Primorsko-notranjska regija", "value": "Primorsko-Inner" }, { "name": "Savinjska regija", "value": "Savinjska" }, { "name": "Zasavska regija", "value": "Zasavska" }]
			return HttpResponse('{{"text_answer":"{0}","response_type":"{1}","data":"{2}"}}'.format("V kateri regiji iščete?","procedures",regions))

		return HttpResponse('{{"text_answer":"{0}","response_type":"{1}","data":"{2}","url":"{3}"}}'.format(text_answer,response_type,data,url))
	else:
		return render(request,'dfchatbox/index.html')
	

@require_http_methods(['POST'])
def check_links(request):
	if request.method == 'POST':
		message = request.POST['message']

		urls = re.findall("((https://www|http://www|www\.|http://|https://).*?(?=(www\.|http://|https://|$)))", message)

		print("These are the urls: ", urls)

		if len(urls) != 0:
			url = urls[0][0]

			print("We'll check this url: ", url)

			html = requests.get(url)

			# soup = BeautifulSoup(html.text,"lxml")

			# file_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20)) + ".html"
			# file = "dfchatbox/static/dfchatbox/data/" + file_name

			# with open(file, "w", encoding='utf8') as f:
			# 	f.write(str(soup))

			tree = fromstring(html.content)
			title = tree.findtext('.//title')
			title = title.replace('"','\\"')

			image_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=20)) + ".jpg"
			image_path = "dfchatbox/static/dfchatbox/img/" + image_name

			#config = imgkit.config(wkhtmltoimage='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltoimage.exe')
			options = {'zoom': '1.2', 'width': '500', 'height': '500'}
			#imgkit.from_url(url,image_path,config=config,options=options)
			imgkit.from_url(url,image_path,options=options)

			img = Image.open(image_path)

			return HttpResponse('{{"url":"{0}", "data":"{1}", "image_name":"{2}"}}'.format(url,title,image_name))

		else:
			return HttpResponse(urls)

@require_http_methods(['GET'])
def entry_tree(request,data):
	return render(request,'dfchatbox/tree.html',{data:data})


#stara metoda za komunikacijo z dialogflowom

# @require_http_methods(['POST','GET'])
# def index(request):
#     if request.method == 'POST':
#         message = request.POST['message']

#         dialogflow = Dialogflow(**settings.DIALOGFLOW)
        
#         answer = dialogflow.text_request(message)
        
#         print("The answer: ", answer)

#         if len(answer) == 0 or answer[0][-6:] == "again?":
#         	print("Agent did not respond")
#         	response = [{'option': 'How are you?','6': 7},{'option': 'Do you like the weather?','6': 7}]
#         	data = [msg['option'] for msg in response]
#         	data = json.dumps(data)
#         	return HttpResponse(data)
#         	#return HttpResponse("*Agent did not answer*")
#         else:
#         	return HttpResponse(answer[0])
    
#     else: 
#         return render(request,'dfchatbox/index.html')

############################################################## WEBHOOK ##################################################################

@csrf_exempt
def webhook(request):

	answer_json = json.loads(request.body)
	
	print("=========== WEBHOOK =============")

	parameter_action = answer_json['result']['action']
	json_response = {}
	response_data = {}
	answer = "Prosim ponovno postavite zahtevo."

	if parameter_action == "labResults":
		print("labResults")
		json_response = getLabResultsData(answer_json)
	if parameter_action == "patientInfo":
		print("patientInfo")
		json_response = getPatientInfoData(answer_json)
	if parameter_action == "ECGResults":
		print("ECGResults")
		json_response = getECGResultsData(answer_json)
	if parameter_action == "allEntries":
		print("allEntries")
		json_response = getAllEntries(answer_json)
		response_data['ehrid'] = json_response['ehrid']
		del json_response['ehrid']
	if parameter_action == "getEntry":
		print("getEntry")
		json_response = getEntryData(answer_json)
		print(json_response)

	answer = json_response['answer']
	del json_response['answer']
	response_data['speech'] = answer
	response_data['displayText'] = answer
	response_data['data'] = json_response
	response_data['source'] = "thinkEHR"
	print("=========== END WEBHOOK =============")
	return HttpResponse(
			json.dumps(response_data, indent=4),
			content_type="application/json"
			)

def getPatientInfoData(answer_json):

	baseUrl = 'https://rest.ehrscape.com/rest/v1'
	base = base64.b64encode(b'ales.tavcar@ijs.si:ehrscape4alestavcar')
	authorization = "Basic " + base.decode()

	queryUrl = baseUrl + "/demographics/party/query"

	searchData = []
	json_response = {"responseType": "userInfo"}
	json_object = {}

	parameter_name =answer_json['result']['parameters']['given-name']
	parameter_last_name =answer_json['result']['parameters']['last-name']

	if parameter_name != "":
		searchData.append({"key": "firstNames", "value": parameter_name})
	if parameter_last_name != "":
		searchData.append({"key": "lastNames", "value": parameter_last_name})

	print("queryUrl: ", queryUrl)
	print("searchData: ", searchData)

	r = requests.post(queryUrl, data=json.dumps(searchData), headers={"Authorization": authorization, 'content-type': 'application/json'})

	if r.status_code == 200:
		js = json.loads(r.text)
		json_object["name"] = js['parties'][0]['firstNames']
		json_object["lastname"] = js['parties'][0]['lastNames']
		json_object["gender"] = js['parties'][0]['gender']
		json_object["dateofbirth"] = js['parties'][0]['dateOfBirth']

		answer = "Za podano ime sem našel sledeče podatke."
	else:
		answer = "Za podano ime nisem našel ustreznih vnosov."	


	json_response['answer'] = answer
	json_response['data'] = json_object
	json_response['url'] = "http://www.rtvslo.si"

	return json_response

def getLabResultsData(answer_json):
	print(answer_json)

	baseUrl = 'https://rest.ehrscape.com/rest/v1'
	#ehrId = 'd8dcc924-edaf-4df5-8b84-e9e6d0ec590f'
	ehrId = ''
	base = base64.b64encode(b'ales.tavcar@ijs.si:ehrscape4alestavcar')
	authorization = "Basic " + base.decode()

	# Match the action -> provide correct data
	parameter_action = answer_json['result']['action']
	json_response = {"responseType": "list"}
	searchData = []
	json_lab_results = []
	json_object = {} 

	# Obtain ehrID of patient from name
	queryUrl = baseUrl + "/demographics/party/query"

	parameter_name =answer_json['result']['parameters']['given-name']
	parameter_last_name =answer_json['result']['parameters']['last-name']

	if parameter_name != "":
		searchData.append({"key": "firstNames", "value": parameter_name})
	if parameter_last_name != "":
		searchData.append({"key": "lastNames", "value": parameter_last_name})

	r = requests.post(queryUrl, data=json.dumps(searchData), headers={"Authorization": authorization, 'content-type': 'application/json'})

	if r.status_code == 200:
		js = json.loads(r.text)
		ehrId = js['parties'][0]['partyAdditionalInfo'][0]['value']
		print("Found ehrid "+ehrId+" for user "+parameter_name+" "+parameter_last_name)
		answ_part = "Za pacienta "+parameter_name+" "+parameter_last_name

	#Use provided ehrid
	parameter_ehrid =answer_json['result']['parameters']['ehrid']
	if parameter_ehrid != "":
		ehrId = str(parameter_ehrid)
		answ_part = "Za ehrid "+ehrId

	#User wants to see lab results for a specific date or date period.
	if ehrId != '':
		parameter_date_range =answer_json['result']['parameters']['date-period']
		parameter_date =answer_json['result']['parameters']['date']
		queryUrl = baseUrl + "/view/"+ehrId+"/labs"
		r = requests.get(queryUrl, headers={"Authorization": authorization})
		js = json.loads(r.text)

		answer = "Za podan datum ni zabeleženih rezultatov laboratorijskih preiskav."
		if parameter_date_range != "":
			dateFrom  = datetime.strptime(parameter_date_range.split("/")[0], '%Y-%M-%d')
			dateTo  = datetime.strptime(parameter_date_range.split("/")[1], '%Y-%M-%d')

			for lab in js:
				datetime_object = datetime.strptime(lab['time'].split('T')[0], '%Y-%M-%d')
				if dateFrom <= datetime_object <= dateTo:
					print(lab['name']+" = "+lab['name']+" time: "+str(datetime_object))
					json_object['name'] = lab['name']
					json_object['value'] = str(lab['value'])+" "+lab['unit']
					json_object['date'] = str(datetime_object)
					json_lab_results.append(json_object)
					json_object = {}
			if json_lab_results:	
				answer = answ_part + " in podani casovni okvir sem nasel sledece izvide laboratorijskih preiskav:"
		elif parameter_date != "":
			print(parameter_date)
			dateFrom  = datetime.strptime(parameter_date, '%Y-%M-%d')
			dateTo  = dateFrom
			for lab in js:
				datetime_object = datetime.strptime(lab['time'].split('T')[0], '%Y-%M-%d')
				if dateFrom <= datetime_object <= dateTo:
					print(lab['name']+" = "+lab['name']+" time: "+str(datetime_object))
					json_object['name'] = lab['name']
					json_object['value'] = str(lab['value'])+" "+lab['unit']
					json_object['date'] = str(datetime_object)
					json_lab_results.append(json_object)
					json_object = {}
			if json_lab_results:	
				answer = answ_part + " in podan datum "+str(parameter_date)+" sem nasel sledece laboratorijske izvide:"
		else:
			for lab in js:
				datetime_object = datetime.strptime(lab['time'].split('T')[0], '%Y-%M-%d')
				json_object['name'] = lab['name']
				json_object['value'] = str(lab['value'])+" "+lab['unit']
				json_object['date'] = str(datetime_object)
				json_lab_results.append(json_object)
				json_object = {}
				if json_lab_results:	
					answer = answ_part + " sem nasel sledece laboratorijske izvide:"
	else: 
		answer = "Za podanega pacienta nisem nasel podatkov v sistemu."
	# Generate the JSON response
	json_response['answer'] = answer
	json_response['data'] = json_lab_results
	json_response['url'] = "http://www.rtvslo.si"

	return json_response

def getECGResultsData(answer_json):
	#print(answer_json)

	baseUrl = 'https://rest.ehrscape.com/rest/v1'
	ehrId = ''
	base = base64.b64encode(b'ales.tavcar@ijs.si:ehrscape4alestavcar')
	authorization = "Basic " + base.decode()

	# Match the action -> provide correct data
	parameter_action = answer_json['result']['action']
	json_response = {"responseType": "list"}
	searchData = []
	json_lab_results = []
	json_object = {} 

	# Obtain ehrID of patient from name
	queryUrl = baseUrl + "/demographics/party/query"

	parameter_name =answer_json['result']['parameters']['given-name']
	parameter_last_name =answer_json['result']['parameters']['last-name']

	if parameter_name != "":
		searchData.append({"key": "firstNames", "value": parameter_name})
	if parameter_last_name != "":
		searchData.append({"key": "lastNames", "value": parameter_last_name})

	r = requests.post(queryUrl, data=json.dumps(searchData), headers={"Authorization": authorization, 'content-type': 'application/json'})

	if r.status_code == 200:
		js = json.loads(r.text)
		ehrId = js['parties'][0]['partyAdditionalInfo'][0]['value']
		print("Found ehrid "+ehrId+" for user "+parameter_name+" "+parameter_last_name)
		answ_part = "Za pacienta "+parameter_name+" "+parameter_last_name

	#Use provided ehrid
	parameter_ehrid =answer_json['result']['parameters']['ehrid']
	if parameter_ehrid != "":
		ehrId = str(parameter_ehrid)
		answ_part = "Za ehrid "+ehrId

	#User wants to see lab results for a specific date or date period.
	if ehrId != '':
		parameter_date_range =answer_json['result']['parameters']['date-period']
		parameter_date =answer_json['result']['parameters']['date']

		aql = "/query?aql=select a from EHR e[ehr_id/value='{}'] contains COMPOSITION a".format(ehrId)

		queryUrl = baseUrl + aql

		r = requests.get(queryUrl, headers={"Authorization": authorization,'content-type': 'application/json'})

		js = json.loads(r.text)
		js = js['resultSet']

		answer = "Za podan datum ni zabeleženih rezultatov EKG preiskav."

		if parameter_date_range != "":
			dateFrom  = datetime.strptime(parameter_date_range.split("/")[0], '%Y-%M-%d')
			dateTo  = datetime.strptime(parameter_date_range.split("/")[1], '%Y-%M-%d')

			for item in js:
				if item['#0']['archetype_details']['template_id']['value'] == "Measurement ECG Report":
					datetime_object = datetime.strptime(item['#0']['context']['start_time']['value'].split('T')[0], '%Y-%M-%d')

					if dateFrom <= datetime_object <= dateTo:
						#print(lab['name']+" = "+lab['name']+" time: "+str(datetime_object))
						#json_object['name'] = lab['name']
						json_object['start_time'] = str(datetime_object)
						json_object['setting'] = item['#0']['context']['setting']['value']
						json_lab_results.append(json_object)
						json_object = {}

			if json_lab_results:	
				answer = answ_part + " in podani casovni okvir sem nasel sledece izvide EKG preiskav:"

		elif parameter_date != "":
			print(parameter_date)
			dateFrom  = datetime.strptime(parameter_date, '%Y-%M-%d')
			dateTo  = dateFrom

			for item in js:
				if item['#0']['archetype_details']['template_id']['value'] == "Measurement ECG Report":
					datetime_object = datetime.strptime(item['#0']['context']['start_time']['value'].split('T')[0], '%Y-%M-%d')

					if dateFrom <= datetime_object <= dateTo:
						#print(lab['name']+" = "+lab['name']+" time: "+str(datetime_object))
						#json_object['name'] = lab['name']
						json_object['start_time'] = str(datetime_object)
						json_object['setting'] = item['#0']['context']['setting']['value']
						json_lab_results.append(json_object)
						json_object = {}

			if json_lab_results:	
				answer = answ_part + " in podan datum "+str(parameter_date)+" sem nasel sledece EKG izvide:"
		else:
			for item in js:
				if item['#0']['archetype_details']['template_id']['value'] == "Measurement ECG Report":
					datetime_object = datetime.strptime(item['#0']['context']['start_time']['value'].split('T')[0], '%Y-%M-%d')

					#json_object['name'] = lab['name']
					json_object['start_time'] = str(datetime_object)
					json_object['setting'] = item['#0']['context']['setting']['value']
					json_lab_results.append(json_object)
					json_object = {}

			if json_lab_results:	
				answer = answ_part + " sem nasel sledece EKG izvide:"
	else:
		answer = "Za podanega pacienta nisem nasel podatkov v sistemu."

	# Generate the JSON response
	json_response['answer'] = answer
	json_response['data'] = json_lab_results
	json_response['url'] = "http://www.rtvslo.si"

	return json_response

def getAllEntries(answer_json):
	print(answer_json)

	baseUrl = 'https://rest.ehrscape.com/rest/v1'
	ehrId = ''
	base = base64.b64encode(b'ales.tavcar@ijs.si:ehrscape4alestavcar')
	authorization = "Basic " + base.decode()

	# Match the action -> provide correct data
	parameter_action = answer_json['result']['action']
	json_response = {"responseType": "button"}
	searchData = []
	json_entries = []
	json_object = {} 

	# Obtain ehrID of patient from name
	queryUrl = baseUrl + "/demographics/party/query"

	parameter_name =answer_json['result']['parameters']['given-name']
	parameter_last_name =answer_json['result']['parameters']['last-name']

	if parameter_name != "":
		searchData.append({"key": "firstNames", "value": parameter_name})
	if parameter_last_name != "":
		searchData.append({"key": "lastNames", "value": parameter_last_name})

	r = requests.post(queryUrl, data=json.dumps(searchData), headers={"Authorization": authorization, 'content-type': 'application/json'})

	if r.status_code == 200:
		js = json.loads(r.text)
		ehrId = js['parties'][0]['partyAdditionalInfo'][0]['value']
		print("Found ehrid "+ehrId+" for user "+parameter_name+" "+parameter_last_name)
		answ_part = "Za pacienta "+parameter_name+" "+parameter_last_name

	#Use provided ehrid
	parameter_ehrid = answer_json['result']['parameters']['ehrid']

	if parameter_ehrid != "":
		ehrId = str(parameter_ehrid)

	if ehrId != '':
		json_response['ehrid'] = ehrId

		aql = "/query?aql=select a from EHR e[ehr_id/value='{}'] contains COMPOSITION a".format(ehrId)

		queryUrl = baseUrl + aql

		r = requests.get(queryUrl, headers={"Authorization": authorization,'content-type': 'application/json'})

		js = json.loads(r.text)
		js = js['resultSet']

		if not len(js):
			answer = "Podani pacient nima vpisov v sistemu."
		else:
			answer = "Za podanega pacienta sem našel naslednje vpise v sistemu:"

			for counter,item in enumerate(js):
				json_object['name'] = item['#0']['archetype_details']['template_id']['value']
				json_object['value'] = str(counter)
				json_entries.append(json_object)
				json_object = {}

	else: 
		answer = "Za podanega pacienta nisem nasel podatkov v sistemu."
		json_response['ehrid'] = ehrId
	# Generate the JSON response
	json_response['answer'] = answer
	json_response['data'] = json_entries
	json_response['url'] = "http://www.rtvslo.si"


	return json_response

def getEntryData(answer_json):
	baseUrl = 'https://rest.ehrscape.com/rest/v1'
	ehrId = ''
	base = base64.b64encode(b'ales.tavcar@ijs.si:ehrscape4alestavcar')
	authorization = "Basic " + base.decode()

	# Match the action -> provide correct data
	parameter_action = answer_json['result']['action']
	json_response = {"responseType": "entry"}
	searchData = []
	json_entries = []
	#json_object = {}

	number = answer_json['result']['contexts'][0]['parameters']['number']
	#ehrId = answer_json['result']['fulfillment']['data']['ehrid']

	queryUrl = baseUrl + "/demographics/party/query"

	parameter_name =answer_json['result']['contexts'][0]['parameters']['given-name']
	parameter_last_name =answer_json['result']['contexts'][0]['parameters']['last-name']

	if parameter_name != "":
		searchData.append({"key": "firstNames", "value": parameter_name})
	if parameter_last_name != "":
		searchData.append({"key": "lastNames", "value": parameter_last_name})

	r = requests.post(queryUrl, data=json.dumps(searchData), headers={"Authorization": authorization, 'content-type': 'application/json'})

	if r.status_code == 200:
		js = json.loads(r.text)
		ehrId = js['parties'][0]['partyAdditionalInfo'][0]['value']
		print("Found ehrid "+ehrId+" for user "+parameter_name+" "+parameter_last_name)
		answ_part = "Za pacienta "+parameter_name+" "+parameter_last_name

	#Use provided ehrid
	parameter_ehrid = answer_json['result']['parameters']['ehrid']

	if parameter_ehrid != "":
		ehrId = str(parameter_ehrid)

	if ehrId != '':
		aql = "/query?aql=select a from EHR e[ehr_id/value='{}'] contains COMPOSITION a".format(ehrId)

		queryUrl = baseUrl + aql

		r = requests.get(queryUrl, headers={"Authorization": authorization,'content-type': 'application/json'})

		js = json.loads(r.text)
		js = js['resultSet']

		if not len(js):
			answer = "Podani pacient nima vpisov v sistemu."
		elif int(number) >= len(js):
			answer = "Izbrani vpis ne obstaja."
		else:
			answer = "Našel sem podatke o vpisu."

			for counter,item in enumerate(js):
				print(counter,number)
				if counter == int(number):
					uid = item['#0']['uid']['value']

					queryUrl = baseUrl + "/composition/"

					queryUrl += uid

					r = requests.get(queryUrl, headers={"Authorization": authorization, 'content-type': 'application/json'})

					if r.status_code == 200:
						json_entries = json.loads(r.text)['composition']
						print(json_entries)
						json_response['tree_url'] = "/entry_tree/{}".format(str(data))
						break

					else:
						answer = "Prišlo je do napake. Prosim, poskusite ponovno."
						break


	else: 
		answer = "Prišlo je do napake. Prosim, poskusite ponovno."

	# Generate the JSON response
	json_response['answer'] = answer
	json_response['data'] = json_entries

	return json_response

@require_http_methods(['GET'])
def update_db(request):
	url = "https://cakalnedobe.ezdrav.si/Home/GetProcedures"
	procedures = json.loads(requests.get(url).text)
	print (len(procedures))
	Procedure.objects.all().delete()
	print(len(Procedure.objects.all()))
	for procedure in procedures:
		nameSLO=edit(procedure['Name'])
		nameENG=translate(nameSLO).lower()
		pid=procedure['Id']
		#print(nameSLO)
		#print(nameENG)
		#print()
		new_procedure=Procedure(nameENG=nameENG, nameSLO=nameSLO, procedure_id=pid)
		new_procedure.save()
		print(len(Procedure.objects.all()))
	return HttpResponse('Database Updated')

def edit(input):
	return input.replace(",","").replace("("," ").replace(")"," ").replace("-"," ").replace("/"," ")

def translate(input):
	url = "http://translate.dis-apps.ijs.si/translate?sentence="+input
	req = requests.get(url)
	if req.text == '{"errors": {"sentence": "Invalid text value provided"}}' or req.text[1:-3] == '':
		output=""
		words=input.split(" ")
		if(len(words)>1):
			for word in words:
				print(word)
				word=word.replace('rad','like to')
				print(word)
				if word:
					output+=translate(word)+" "
			return output
		return input
	return req.text[1:-3]

#FOR TESTING ONLY 
# TODO: TRANSFER INTO DB
def standardize_input(input):
	input = input.lower()
	return input.replace('arm', 'hand').replace('operation','surgery').replace("'"," ").replace("x-ray","rtg")

def standardize_db(procedures):
	for procedure in procedures:
		name = procedure.nameENG
		print (name)
		name = name.replace("operation","surgery").replace("operations","surgery").replace("surgerys","surgery").replace('need','needs')
		print(name)
		procedure.nameENG=name
		procedure.save()
	return

def whoosh(input):
	input = standardize_input(input)
	keywords = getKeywords(input)
	all_results = SearchQuerySet().all()
	data = []
	if keywords:
		all_results = query(all_results, keywords)
		# for keyword in keywords:
		# 	all_results = all_results.filter(content=keyword)

		for result in all_results:
			dict ={}
			dict['name']=result.object.nameSLO
			dict['value']=input + " " + result.object.procedure_id
			data.append(dict)
			#print(result.score)
		none={}
		none['name']="Nobeden izmed zgoraj naštetih"
		none['value']=input + " NONE"
		data.append(none)

	return data

def getKeywords(input):
	words = input.split(' ')
	keywords = []
	for keyword in words:
		if not keyword:
			continue
		if(SearchQuerySet().filter(content=keyword).count() > 0):
			keywords.append(keyword)
	print("keywords:",keywords)
	return keywords

def hasNumbers(inputString):
	return any(char.isdigit() for char in inputString)

def checkRegion(message):
	if message.find('regions') > -1:
		message = message.replace('regions','')
		data = whoosh(message)
		if len(data) > 1:
			return True
		return False
	return True

def query(set,keywords):
	if len(keywords) == 1:
		return set.filter(content=keywords[0])
	pairs = pair(keywords)
	result = set
	for p in pairs:
		new_set = set.filter(content=p[0]).filter(content=p[1])
		result |= new_set
	return result

def pair(list):
	result = []
	for item in list:
		for item2 in list:
			if list.index(item) > list.index(item2):
				result.append([item,item2])
	return result


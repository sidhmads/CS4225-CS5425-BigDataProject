from django.shortcuts import render
from django.views.decorators import gzip
from django.http import HttpResponseRedirect
from django.core.files.storage import FileSystemStorage
import cv2
import os
import subprocess
import requests

def index(request):
    return render(request, 'fashion/index.html')


def capture(request):
    filename = use_webcam()
    context = {'success': True,
               'message': 'Capture Success', 'imageList': [filename]}
    return render(request, 'fashion/index.html', context)


def use_webcam():
    camera = cv2.VideoCapture(0)
    cv2.namedWindow("Fashion Detector")
    ret, frame = camera.read()
    cv2.imshow("Fashion Detector", frame)
    fs = FileSystemStorage()
    filePath = os.path.dirname(__file__)
    dirPath = os.path.abspath(os.path.dirname(filePath))
    newDirPath = os.path.join(dirPath, 'media')
    img_name = "fashion-capture.jpg"
    if ret == True:
        cv2.imwrite(os.path.join(newDirPath, img_name), frame)
        uploaded_file_url = fs.url(img_name)
    camera.release()
    cv2.destroyAllWindows()
    return uploaded_file_url


def upload(request):
    if request.method == 'POST' and request.FILES['myfile']:
        myfile = request.FILES['myfile']
        fs = FileSystemStorage()
        myfile.name = "fashion-upload.jpg"
        if(fs.exists(myfile.name)):
            fs.delete(myfile.name)
        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)
        return render(request, 'fashion/index.html', {
            'success': True,
            'message': 'Upload Success',
            'imageList': [uploaded_file_url]
        })
    return render(request, 'fashion/index.html')


def runmodel(request):
    subProcess = subprocess.Popen("spark-submit --packages databricks:spark-deep-learning:1.5.0-spark2.4-s_2.11 .\predict.py", shell=True)
    subProcess.wait()
    predictResult =[]
    if(subProcess.returncode == 0):
        f = open("predict_output.txt", "r")
        for line in f.read().split("\n"):
            predictResult.append(line)
        context = {'success': True,
               'message': 'Predicted Successfully!', 'modal': True, 'predictResult': predictResult}
    else:
        context = {'success': True,
               'message': 'Failed! Retry Again', 'modal': True, 'predictResult': predictResult}
    
    return render(request, 'fashion/index.html', context)

def search(request):
    search = request.POST.get('search')
    params = {'q': search, 'size': '10', 'scroll': '1m'}
    context = searchElasticCluster("_search", params)
    return render(request, 'fashion/search.html', context)

def showsimilar(request):
    masterCategoryList = []
    subCategoryList = []
    articleTypeList = []
    f = open("predict_output.txt", "r")
    for line in f.read().split("\n"):
        if line != "":
            splitString = line.split('=')[1]
            masterCategory, subCategory, articleType = splitString.split('_')
            masterCategoryList.append(masterCategory.strip())
            subCategoryList.append(subCategory.strip())
            articleTypeList.append(articleType.strip())
    params = {'q': articleTypeList, 'size': '10', 'scroll': '1m'}
    context = searchElasticCluster("_search", params)
    return render(request, 'fashion/search.html', context)

    
def searchElasticCluster(type, params):
    try:
        lazyLoad = False
        if type == "_search/scroll":
            lazyLoad = True
        response = requests.get("http://localhost:9200/"+type, params)
        if response.status_code == 200:
            data = response.json()
            resultArray = []
            for hit in data['hits']['hits']:
                resultArray.append(hit['_source'])
            message = "Search Success"
            showAlert = True
            scrollId = data['_scroll_id']
            context = {'search': resultArray, 'message':message, 'success': showAlert, 'scrollId': scrollId, 'lazyLoad': lazyLoad}
            return context
        else:
            message = "Search Failed"
            showAlert = True
            context = {'message': message, 'success': showAlert}
            return context
    except:
        message = "No Elastic Cluster Found"
        showAlert = True
        context = {'message': message, 'success': showAlert}
        return context

def lazyload(request):
    scrollid = request.POST.get('scrollid')
    params = {'scroll_id': scrollid, 'scroll': '1m'}
    context = searchElasticCluster("_search/scroll", params)
    return render(request, 'fashion/search.html', context)
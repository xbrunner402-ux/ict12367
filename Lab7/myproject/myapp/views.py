from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
    return HttpResponse("<h1>ICT12367 SPU</h1>")

def about(request):
    return HttpResponse("<h1>เกี่ยวกับเรา</h1>")

def form(request):
    return HttpResponse("<h1>แบบฟอร์มบันทึกข้อมูล</h1>")

def contact(request):
    return HttpResponse("<h1>68098988 อาร์ดีฟ สุระกำแหง</h1>")

def forms(request):
    return render(request, 'form.html')
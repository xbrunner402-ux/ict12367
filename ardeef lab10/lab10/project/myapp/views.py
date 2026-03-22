from django.shortcuts import render
from .models import Population

def index(request):
    people = Population.objects.all()
    return render(request, 'index.html', {'people': people})

def register(request):
    return render(request, 'form.html')

def about(request):
    return render(request, 'about.html')
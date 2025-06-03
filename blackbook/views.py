from django.shortcuts import render
from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.
def index(request):
    return render(request, 'blackbook/index.html', {
        'content123': 'Your name here',
    })


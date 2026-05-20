from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.dashboard,   name='dashboard'),
    path('words/',                    views.words,       name='words'),
    path('words/add/',                views.add_word,    name='add_word'),
    path('words/delete/<str:word>/',  views.delete_word, name='delete_word'),
    path('history/',                  views.history,     name='history'),
    path('users/',                    views.users,       name='users'),
]
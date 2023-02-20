from django.urls import path
from . import views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns =[
    path('',views.index, name='index'),
    path('mcomment/<str:pk>',views.mcomment, name='mcomment'),
    path('frontpage/<str:pk>',views.frontpage, name='frontpage'),
]

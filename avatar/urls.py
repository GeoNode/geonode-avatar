from django.conf.urls import url

from . import views

urlpatterns = [  # 'avatar.views',
    url('^add/$', views.add, name='avatar_add'),
    url('^change/$', views.change, name='avatar_change'),
    url('^delete/$', views.delete, name='avatar_delete'),
    url('^render_primary/(?P<user>[\+\w]+)/(?P<size>[\d]+)/$', views.render_primary, name='avatar_render_primary'),
]

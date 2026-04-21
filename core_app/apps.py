from django.apps import AppConfig


class CoreAppConfig(AppConfig):
    name = 'core_app'


'''
>>> 
>>> 
>>> from core_app.models import *
>>> 
>>> 
>>> User.objects.get(id=2)
<User: shubham>
>>> u  = User.objects.get(id=2)
>>> 
>>> u
<User: shubham>
>>> a = Address.objects.filter(user = u)
>>> a
<QuerySet [<Address: shubham>, <Address: shubham>]>
>>> u.user_address.all()
<QuerySet [<Address: shubham>, <Address: shubham>]>
>>> 

'''

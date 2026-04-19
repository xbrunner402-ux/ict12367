from django.db import models

class Person(models.Model):
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    date = models.DateField(auto_now_add=True) # ฟิลด์นี้จะเก็บวันที่อัตโนมัติ
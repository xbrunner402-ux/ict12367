from django.db import models

class Population(models.Model):

    pid = models.IntegerField()
    name = models.CharField(max_length=100)
    age = models.IntegerField()

    def __str__(self):
        return self.name
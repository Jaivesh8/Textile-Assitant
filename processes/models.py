from django.db import models

# Create your models here.
class Supplier(models.Model):
    name = models.CharField(max_length=255)
    material=models.CharField(max_length=255)
    process=models.CharField(max_length=255)
    address=models.TextField()
    city=models.CharField(max_length=255)
    state=models.CharField(max_length=255)
    latitude=models.FloatField()
    longitude=models.FloatField()
    contact=models.CharField(max_length=255,blank=True,null=True)

    def __str__(self):
        return f"{self.name} - {self.material}"